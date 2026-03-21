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

# 1. 环境准备
echo "📦 安装依赖库 (Node.js, Nginx, Python, pyenv相关)..."
apt update -y || yum makecache || true
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs || yum install -y nodejs || true
fi
if ! command -v nginx &> /dev/null; then
    apt install -y nginx || yum install -y nginx || true
fi
if ! command -v python3 &> /dev/null; then
    apt install -y python3 python3-pip python3-venv || yum install -y python3 python3-pip python3-venv || true
fi
apt install -y gunicorn uvicorn || true

mkdir -p $WEBSITE_DIR
mkdir -p $CURSOR_FE_DIR

# 2. 部署官网 (Website) -> Nginx 80 端口
echo "🌐 开始构建官网..."
cd "$PROJECT_ROOT/website"
npm install
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
if [ ! -d "venv" ]; then
    python3 -m venv venv
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
Type=notify
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
