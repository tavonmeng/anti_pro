#!/bin/bash

# =================================================================
# 阿里云 ECS 项目自动部署脚本 v2.1 (支持 CentOS/Alibaba Cloud Linux/Ubuntu/Debian)
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

echo "----------------------------------------------------"
echo "🚀 启动部署流程"
echo "项目名称: $PROJECT_NAME"
echo "监听端口: $LISTEN_PORT"
echo "域名配置: $DOMAIN_NAME"
echo "部署目录: $DEPLOY_DIR"
echo "----------------------------------------------------"

# 1. 检测系统和包管理器
if command -v apt &> /dev/null; then
    PKG_MGR="apt"
    OS_TYPE="debian"
    NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"
    NGINX_ENABLED_DIR="/etc/nginx/sites-enabled/"
elif command -v yum &> /dev/null; then
    PKG_MGR="yum"
    OS_TYPE="centos"
    NGINX_CONF="/etc/nginx/conf.d/$PROJECT_NAME.conf"
    NGINX_ENABLED_DIR=""
else
    echo "❌ 无法识别包管理器 (apt 或 yum 均未找到)，退出安装。"
    exit 1
fi

# 1. 更新系统软件包缓存
echo "📦 检测到系统类型: $OS_TYPE, 正在刷新软件源..."
if [ "$PKG_MGR" = "apt" ]; then
    sudo apt update -y
else
    sudo yum makecache
fi

# 2. 环境检查与安装 (Node.js & Nginx)
if ! command -v node &> /dev/null; then
    echo "🟢 正在安装 Node.js (v20)..."
    if [ "$PKG_MGR" = "apt" ]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y nodejs
    else
        curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
        sudo yum install -y nodejs
    fi
else
    echo "✅ Node.js 已安装: $(node -v)"
fi

if ! command -v nginx &> /dev/null; then
    echo "🟢 正在安装 Nginx..."
    sudo $PKG_MGR install -y nginx
else
    echo "✅ Nginx 已安装"
fi

# 3. 端口占用检查
if command -v ss &> /dev/null; then
    if sudo ss -tlnp | grep -q ":$LISTEN_PORT "; then
        echo "⚠️  警告: 端口 $LISTEN_PORT 已被占用。Nginx 配置后可能无法正常启动。"
    fi
elif command -v lsof &> /dev/null; then
    if sudo lsof -Pi :$LISTEN_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  警告: 端口 $LISTEN_PORT 已被占用。Nginx 配置后可能无法正常启动。"
    fi
else
    echo "⚠️  提示: 缺少端口检查工具 (ss 或 lsof)，跳过占用检测..."
fi

# 4. 创建部署目录
echo "📂 准备部署目录..."
sudo mkdir -p $DEPLOY_DIR
sudo chown -R $USER:$USER $DEPLOY_DIR

# 5. 执行项目构建
echo "🏗️ 开始本地构建..."
if [ -f "package.json" ]; then
    npm install

    # 配置管理后台的动态环境变量
    echo "🌐 配置管理后台 (Dashboard) 访问路径..."
    TEMP_PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "")
    if [ -n "$TEMP_PUBLIC_IP" ]; then
        DEFAULT_DASHBOARD="http://$TEMP_PUBLIC_IP"
    else
        DEFAULT_DASHBOARD="http://localhost"
    fi
    echo "请选择 Dashboard 的访问方式："
    echo "1. 自动填入当前服务器公网 IP ($DEFAULT_DASHBOARD)"
    echo "2. 手动指定"
    read -p "请输入 [1/2] (默认 1): " DASHBOARD_CHOICE
    case "${DASHBOARD_CHOICE:-1}" in
        1)
            DASHBOARD_URL=$DEFAULT_DASHBOARD
            ;;
        2)
            read -p "请输入详细的前端访问网址 (例如 http://xxxx:3000 或 https://xxx.com): " DASHBOARD_URL
            ;;
        *)
            DASHBOARD_URL=$DEFAULT_DASHBOARD
            ;;
    esac
    
    echo "VITE_DASHBOARD_URL=$DASHBOARD_URL" > .env.production
    echo "✅ 已生成前端控制台变量: VITE_DASHBOARD_URL=$DASHBOARD_URL"

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
if [ -n "$NGINX_ENABLED_DIR" ]; then
    sudo ln -sf $NGINX_CONF $NGINX_ENABLED_DIR
    if [ "$LISTEN_PORT" == "80" ]; then
        sudo rm -f /etc/nginx/sites-enabled/default
    fi
else
    if [ "$LISTEN_PORT" == "80" ] && [ -f "/etc/nginx/conf.d/default.conf" ]; then
        sudo mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak 2>/dev/null
    fi
fi

# 检查配置合法性
if sudo nginx -t; then
    sudo systemctl restart nginx
    echo "----------------------------------------------------"
    echo "✨ 部署成功!"
    echo "访问地址: http://您的服务器IP:$LISTEN_PORT"
    echo "⚠️  重要提示: 请确保阿里云安全组/防火墙已放行端口: $LISTEN_PORT"
    echo "----------------------------------------------------"
else
    echo "❌ Nginx 配置错误，请检查日志。"
    exit 1
fi
