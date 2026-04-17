#!/bin/bash

# =================================================================
# 全栈系统 (官网+业务前端+后端) 阿里云部署整合脚本
# 参考了 website/deploy.sh 的干净设计思路
# 1. 官网运行在 Nginx 80 端口
# 2. 业务系统运行在 Nginx 8080 端口，前端和 API 反向代理
# =================================================================

set -e

echo "🚀 开始整合部署..."

# 确保以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "❌ 请使用 root 用户运行此脚本 (例如: sudo bash scripts/deploy_system.sh)"
    exit 1
fi

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"

WEBSITE_DIR="/var/www/unique-vision-website"
CURSOR_FE_DIR="/var/www/order-management-fe"
SERVICE_NAME="order-api"
AI_SERVICE_NAME="ai-agent-api"

# 1. 环境准备
echo "📦 安装依赖库 (Node.js, Nginx, Python, pyenv相关)..."

if command -v apt &> /dev/null; then
    PKG_MGR="apt"
elif command -v yum &> /dev/null; then
    PKG_MGR="yum"
else
    echo "❌ 无法识别包管理器 (apt 或 yum 均未找到)，退出安装。"
    exit 1
fi

if [ "$PKG_MGR" = "apt" ]; then
    apt update -y || true
else
    yum makecache || true
fi

if ! command -v node &> /dev/null; then
    if [ "$PKG_MGR" = "apt" ]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt install -y nodejs || true
    else
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
        yum install -y nodejs || true
    fi
fi

if ! command -v nginx &> /dev/null; then
    $PKG_MGR install -y nginx || true
fi

# ================= 新增：自动升级并选用 Python 3.9+ =================
if [ "$PKG_MGR" = "yum" ]; then
    echo "📦 针对 Alinux/CentOS，尝试优先安装 Python 3.9..."
    # AL8/RHEL8 支持模块化安装或包名 python3.9 / python38
    yum install -y python3.9 python3.9-pip || yum module install -y python39 || yum install -y python39 python39-pip || yum install -y python3.8 || yum install -y python38 || yum install -y python3 python3-pip || true
    
    if command -v python3.9 &> /dev/null; then
        PYTHON_CMD="python3.9"
    elif command -v python3.8 &> /dev/null; then
        PYTHON_CMD="python3.8"
    else
        PYTHON_CMD="python3"
    fi
else
    # 对于 Ubuntu/Debian 体系
    if ! command -v python3 &> /dev/null; then
        apt install -y python3 python3-pip python3-venv || true
    fi
    PYTHON_CMD="python3"
fi
echo "🐍 将使用 $PYTHON_CMD 构建后端环境"
# =================================================================

mkdir -p $WEBSITE_DIR
mkdir -p $CURSOR_FE_DIR

# 2. 部署官网 (Website) -> Nginx 80 端口
echo "🌐 开始构建官网..."
cd "$PROJECT_ROOT/website"
npm install

# 自动获取当前服务器 IP 生成正确的 控制台跳转链接 (端口为8080)
echo "🔍 自动探测服务器公网 IP 并配置跳转链接..."
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "")
if [ -n "$PUBLIC_IP" ]; then
    DASHBOARD_URL="http://$PUBLIC_IP:8080"
else
    DASHBOARD_URL="http://localhost:8080"
fi
echo "VITE_DASHBOARD_URL=$DASHBOARD_URL" > .env.production
echo "✅ 已生成前端跳转配置: VITE_DASHBOARD_URL=$DASHBOARD_URL"

npm run build
cp -r dist/* $WEBSITE_DIR/
chown -R www-data:www-data $WEBSITE_DIR || chown -R root:root $WEBSITE_DIR

# 3. 部署业务系统前端 (Cursor Frontend) -> Nginx 8080 端口
echo "💻 开始构建业务前端..."
cd "$PROJECT_ROOT/cursor_sh"
# 写入生产环境API变量到 .env.production
echo "VITE_API_BASE_URL=/api" > .env.production 
npm install
npm run build
cp -r dist/* $CURSOR_FE_DIR/
chown -R www-data:www-data $CURSOR_FE_DIR || chown -R root:root $CURSOR_FE_DIR

# 4. 部署业务系统后端 (Cursor Backend) -> 本地 8000 端口
echo "⚙️ 开始部署业务后端..."
cd "$PROJECT_ROOT/cursor_sh/backend"

# ================= 新增：自动生成环境变量文件保护 =================
if [ ! -f ".env" ]; then
    echo "⚠️ 检测到缺少 .env 配置文件！"
    echo "📄 正在自动从 .env.example 复制基础模板..."
    cp .env.example .env
    echo "❌ 自动中止部署引擎：请先手动编辑 $(pwd)/.env 文件"
    echo "📝 填入你的阿里云 AK/SK 等真实密钥后，再次重新运行此部署脚本。"
    exit 1
fi
# =============================================================

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn uvicorn

cat > gunicorn_config.py << 'EOF'
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
EOF

USER_TO_RUN=$(id -un)
GROUP_TO_RUN=$(id -gn)

cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Order Management API
After=network.target

[Service]
Type=simple
User=$USER_TO_RUN
Group=$GROUP_TO_RUN
WorkingDirectory=$PROJECT_ROOT/cursor_sh/backend
Environment="PATH=$PROJECT_ROOT/cursor_sh/backend/venv/bin"
ExecStart=$PROJECT_ROOT/cursor_sh/backend/venv/bin/gunicorn app.main:app -c $PROJECT_ROOT/cursor_sh/backend/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

# 4.5 (可选) 部署旧版独立AI后端 — 新版 AI 已集成进主后端 (8000端口)
# 如果 ai_backend 目录存在，仍然部署以保持向后兼容
if [ -d "$PROJECT_ROOT/ai_backend" ] && [ -f "$PROJECT_ROOT/ai_backend/requirements.txt" ]; then
    echo "🤖 检测到独立 AI 后端目录，部署中..."
    cd "$PROJECT_ROOT/ai_backend"
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn uvicorn

    cat > gunicorn_config.py << 'EOF'
bind = "127.0.0.1:8001"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
EOF

    cat > /etc/systemd/system/$AI_SERVICE_NAME.service << EOF
[Unit]
Description=AI Agent API (Legacy)
After=network.target

[Service]
Type=simple
User=$USER_TO_RUN
Group=$GROUP_TO_RUN
WorkingDirectory=$PROJECT_ROOT/ai_backend
Environment="PATH=$PROJECT_ROOT/ai_backend/venv/bin"
ExecStart=$PROJECT_ROOT/ai_backend/venv/bin/gunicorn main:app -c $PROJECT_ROOT/ai_backend/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable $AI_SERVICE_NAME
    systemctl restart $AI_SERVICE_NAME
else
    echo "ℹ️ 未检测到独立 AI 后端目录，跳过此步骤（AI 已集成在主后端中）"
fi

# 5. 配置 Nginx
echo "🛠 配置 Nginx..."

# 官网配置 (80端口)
cat > /etc/nginx/conf.d/unique-vision.conf << EOF
server {
    listen 80;
    server_name _;
    root $WEBSITE_DIR;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

# 业务系统配置 (8080端口，同时反代API)
cat > /etc/nginx/conf.d/cursor-sh.conf << EOF
server {
    listen 8080;
    server_name _;
    root $CURSOR_FE_DIR;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # AI 大模型端点（已集成在主后端 8000 端口）
    location /ai {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 180s;
    }
}
EOF

# 清理默认冲突文件
rm -f /etc/nginx/sites-enabled/default

# 再次验证 nginx 并重启
if nginx -t; then
    systemctl restart nginx
    echo "================================================="
    echo "✅ 全系统部署成功！"
    echo "1. 官网访问端口: 80"
    echo "2. 控制台(业务前端+后端)访问端口: 8080"
    echo "⚠️ 重点提示：请前往阿里云安全组，放行 [80] 和 [8080] 两个 TCP 端口"
    echo "================================================="
else
    echo "❌ Nginx 配置验证失败，请检查相关逻辑。"
    exit 1
fi
