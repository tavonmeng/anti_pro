#!/bin/bash

# =================================================================
# 阿里云 ECS (Ubuntu/Debian) 项目自动部署脚本 v2.0
# 适用项目: Vite + Vue 3
# 功能: 基础环境安装、多端口支持、自定义域名、自动构建与部署
# =================================================================

# 默认基础配置
DEFAULT_PROJECT_NAME="unique-vision-website"
DEFAULT_PORT="80"
DEFAULT_DOMAIN="_"

# 获取输入参数
PROJECT_NAME=${1:-$DEFAULT_PROJECT_NAME}
LISTEN_PORT=${2:-$DEFAULT_PORT}
DOMAIN_NAME=${3:-$DEFAULT_DOMAIN}

DEPLOY_DIR="/var/www/$PROJECT_NAME"
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"

echo "----------------------------------------------------"
echo "🚀 启动部署流程"
echo "项目名称: $PROJECT_NAME"
echo "监听端口: $LISTEN_PORT"
echo "域名配置: $DOMAIN_NAME"
echo "部署目录: $DEPLOY_DIR"
echo "----------------------------------------------------"

# 1. 更新系统软件包
echo "📦 正在更新系统软件包..."
sudo apt update && sudo apt upgrade -y

# 2. 环境检查与安装 (Node.js & Nginx)
if ! command -v node &> /dev/null; then
    echo "🟢 正在安装 Node.js (v20)..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
else
    echo "✅ Node.js 已安装: $(node -v)"
fi

if ! command -v nginx &> /dev/null; then
    echo "🟢 正在安装 Nginx..."
    sudo apt install -y nginx
else
    echo "✅ Nginx 已安装"
fi

# 3. 端口占用检查
if sudo lsof -Pi :$LISTEN_PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  警告: 端口 $LISTEN_PORT 已被占用。Nginx 配置后可能无法正常启动。"
fi

# 4. 创建部署目录
echo "📂 准备部署目录..."
sudo mkdir -p $DEPLOY_DIR
sudo chown -R $USER:$USER $DEPLOY_DIR

# 5. 执行项目构建
echo "🏗️ 开始本地构建..."
if [ -f "package.json" ]; then
    npm install
    npm run build
else
    echo "❌ 错误: 未找到 package.json，请在项目根目录下运行此脚本。"
    exit 1
fi

# 6. 部署产物
if [ -d "dist" ]; then
    echo "🚚 正在同步构建产物..."
    sudo rm -rf $DEPLOY_DIR/*
    sudo cp -r dist/* $DEPLOY_DIR/
else
    echo "❌ 错误: 构建失败，未生成 dist 目录。"
    exit 1
fi

# 7. 动态生成 Nginx 配置
echo "⚙️  正在生成 Nginx 配置 ($NGINX_CONF)..."
sudo tee $NGINX_CONF > /dev/null <<EOF
server {
    listen $LISTEN_PORT;
    server_name $DOMAIN_NAME;

    root $DEPLOY_DIR;
    index index.html;

    # 增强安全性与性能
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options "nosniff";

    # Vue Router 路由支持
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 静态资源长期缓存
    location ~* \.(?:ico|css|js|gif|jpe?g|png|svg|woff2?|mp4|webm)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    error_page 404 /index.html;
}
EOF

# 8. 启用配置并重启服务
echo "🔄 验证并应用 Nginx 配置..."
sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/

# 如果监听非 80 端口，建议保留默认配置以防冲突，但这里为了纯净默认移除 default
if [ "$LISTEN_PORT" == "80" ]; then
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# 检查配置合法性
if sudo nginx -t; then
    sudo systemctl restart nginx
    echo "----------------------------------------------------"
    echo "✨ 部署成功!"
    echo "访问地址: http://您的服务器IP:$LISTEN_PORT"
    echo "⚠️  重要提示: 请确保阿里云安全组已放行端口: $LISTEN_PORT"
    echo "----------------------------------------------------"
else
    echo "❌ Nginx 配置错误，请检查日志。"
    exit 1
fi
