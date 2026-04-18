#!/bin/bash
# 快速修复 systemd 服务配置

set -e

echo "=========================================="
echo "  修复 systemd 服务配置"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检测实际的后端目录
CURRENT_DIR=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACTUAL_BACKEND_DIR=""
if [ -d "$CURRENT_DIR/backend" ] && [ -f "$CURRENT_DIR/backend/requirements.txt" ]; then
    ACTUAL_BACKEND_DIR="$CURRENT_DIR/backend"
elif [ -d "$SCRIPT_DIR/backend" ] && [ -f "$SCRIPT_DIR/backend/requirements.txt" ]; then
    ACTUAL_BACKEND_DIR="$SCRIPT_DIR/backend"
fi

if [ -z "$ACTUAL_BACKEND_DIR" ]; then
    echo -e "${RED}错误: 未找到后端目录${NC}"
    exit 1
fi

echo -e "${GREEN}找到后端目录: $ACTUAL_BACKEND_DIR${NC}"

# 检查虚拟环境
cd "$ACTUAL_BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 检查虚拟环境是否有效
PYTHON_PATH=$(readlink -f venv/bin/python 2>/dev/null || echo "")
if [[ "$PYTHON_PATH" == *"/Users/"* ]] || [[ "$PYTHON_PATH" == *"/home/"* ]] && [[ "$PYTHON_PATH" != *"$(whoami)"* ]]; then
    echo -e "${YELLOW}检测到跨机器的虚拟环境，重新创建...${NC}"
    rm -rf venv
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
if [ ! -f "venv/bin/gunicorn" ]; then
    echo -e "${YELLOW}安装依赖...${NC}"
    # 使用虚拟环境的 pip
    venv/bin/pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        venv/bin/pip install -r requirements.txt
    fi
    venv/bin/pip install gunicorn
fi

# 验证 gunicorn
if [ ! -f "venv/bin/gunicorn" ]; then
    echo -e "${RED}错误: gunicorn 安装失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 虚拟环境和 gunicorn 已就绪${NC}"

# 更新 systemd 服务配置
SERVICE_NAME="order-api"
LOG_DIR="/var/log/order-api"

echo -e "${YELLOW}检测系统环境...${NC}"

# 判断服务运行用户
SERVICE_USER="www-data"
SERVICE_GROUP="www-data"
if [[ "$ACTUAL_BACKEND_DIR" == /root/* ]]; then
    SERVICE_USER="root"
    SERVICE_GROUP="root"
    chmod 755 /root /root/workspace /root/workspace/code 2>/dev/null || true
else
    chown -R www-data:www-data "$ACTUAL_BACKEND_DIR"
    chmod -R 755 "$ACTUAL_BACKEND_DIR"
    find "$ACTUAL_BACKEND_DIR" -name "*.db" -exec chmod 664 {} \; 2>/dev/null || true
fi

# 创建日志目录
mkdir -p "$LOG_DIR"
chown "$SERVICE_USER":"$SERVICE_GROUP" "$LOG_DIR"
chmod 750 "$LOG_DIR"

echo -e "${YELLOW}更新 systemd 服务配置...${NC}"

cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Order Management API
After=network.target

[Service]
Type=notify
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$ACTUAL_BACKEND_DIR
Environment="PATH=$ACTUAL_BACKEND_DIR/venv/bin"
ExecStart=$ACTUAL_BACKEND_DIR/venv/bin/gunicorn app.main:app -c $ACTUAL_BACKEND_DIR/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 检查 gunicorn_config.py 是否存在
if [ ! -f "$ACTUAL_BACKEND_DIR/gunicorn_config.py" ]; then
    echo -e "${YELLOW}创建 gunicorn 配置...${NC}"
    cat > "$ACTUAL_BACKEND_DIR/gunicorn_config.py" << 'EOF'
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
loglevel = "info"
accesslog = "/var/log/order-api/access.log"
errorlog = "/var/log/order-api/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
EOF
fi

# 重新加载 systemd
systemctl daemon-reload

# 重启服务
echo -e "${YELLOW}重启服务...${NC}"
systemctl restart $SERVICE_NAME

# 等待服务启动
sleep 2

# 检查服务状态
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ 服务已成功启动${NC}"
    systemctl status $SERVICE_NAME --no-pager -l
else
    echo -e "${RED}服务启动失败，查看日志：${NC}"
    journalctl -xeu $SERVICE_NAME --no-pager -n 20
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo "  服务修复完成！"
echo "==========================================${NC}"

