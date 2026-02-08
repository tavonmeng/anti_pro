#!/bin/bash

# =================================================================
# 阿里云 ECS (Ubuntu/Debian) 项目自动部署脚本
# 适用项目: Vite + Vue 3
# 功能: 安装 Node.js, Nginx, 构建并配置服务
# =================================================================

# 配置变量 (根据实际情况修改)
PROJECT_NAME="unique-vision-website"
DEPLOY_DIR="/var/www/$PROJECT_NAME"
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"

echo "🚀 开始部署项目: $PROJECT_NAME..."

# 1. 更新系统软件包
echo "📦 正在更新系统软件包..."
sudo apt update && sudo apt upgrade -y

# 2. 安装 Node.js (使用 NodeSource 20.x 版本)
if ! command -v node &> /dev/null; then
    echo "🟢 正在安装 Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
else
    echo "✅ Node.js 已安装: $(node -v)"
fi

# 3. 安装 Nginx
if ! command -v nginx &> /dev/null; then
    echo "🟢 正在安装 Nginx..."
    sudo apt install -y nginx
else
    echo "✅ Nginx 已安装"
fi

# 4. 创建部署目录并设置权限
echo "📂 准备目录: $DEPLOY_DIR..."
sudo mkdir -p $DEPLOY_DIR
sudo chown -R $USER:$USER $DEPLOY_DIR

# 5. 安装依赖并构建项目
echo "🏗️ 开始构建项目..."
cd "$(dirname "$0")" # 进入脚本所在目录（假设脚本位于项目根目录）
npm install
npm run build

# 6. 将构建产物移动到 Nginx 目录
echo "🚚 部署构建产物到 $DEPLOY_DIR..."
sudo rm -rf $DEPLOY_DIR/*
sudo cp -r dist/* $DEPLOY_DIR/

# 7. 配置 Nginx
echo "⚙️ 配置 Nginx 虚拟主机..."
sudo tee $NGINX_CONF > /dev/null <<EOF
server {
    listen 80;
    server_name _; # 如果有域名，请替换为您的域名

    root $DEPLOY_DIR;
    index index.html;

    # 处理 Vue Router 路由跳转问题
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # 开启 gzip 压缩以提高加载速度
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 缓存静态资源
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|mp4)$ {
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    error_page 404 /index.html;
}
EOF

# 8. 启用 Nginx 配置并重启服务
echo "🔄 重启 Nginx..."
sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
# 移除默认配置（如果存在）
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo "✨ 部署成功! 请通过 ECS 的公网 IP 访问。"
echo "💡 提示: 请确保阿里云安全组已开启 80 端口访问权限。"
