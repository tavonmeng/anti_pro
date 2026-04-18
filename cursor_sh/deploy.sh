#!/bin/bash
# 阿里云快速部署脚本
# 使用方法: bash deploy.sh

set -e

echo "=========================================="
echo "  订单管理系统 - 阿里云部署脚本"
echo "=========================================="

# 可选命令: stop | restart | deploy(默认)
CMD="${1:-deploy}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 root 用户运行此脚本${NC}"
    exit 1
fi

# 配置变量
PROJECT_DIR="/opt/order-management"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR"
NGINX_DIR="/var/www/order-management"
LOG_DIR="/var/log/order-api"
SERVICE_NAME="order-api"

# 简单的服务存在检测
service_exists() {
    systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"
}

# 仅停止服务
if [ "$CMD" = "stop" ]; then
    echo -e "${YELLOW}停止服务 ${SERVICE_NAME}...${NC}"
    if service_exists; then
        systemctl stop "${SERVICE_NAME}" || true
        systemctl disable "${SERVICE_NAME}" || true
        echo -e "${GREEN}服务已停止${NC}"
    else
        echo -e "${YELLOW}未检测到已安装的服务（跳过）${NC}"
    fi
    exit 0
fi

# 仅重启服务
if [ "$CMD" = "restart" ]; then
    echo -e "${YELLOW}重启服务 ${SERVICE_NAME}...${NC}"
    if service_exists; then
        systemctl daemon-reload
        systemctl restart "${SERVICE_NAME}"
        sleep 1
        systemctl status "${SERVICE_NAME}" --no-pager -l | head -30
    else
        echo -e "${RED}未检测到服务，请先执行部署（deploy）${NC}"
        exit 1
    fi
    exit 0
fi

echo -e "${GREEN}步骤 1: 检查系统环境...${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}安装 Python3...${NC}"
    apt update
    apt install -y python3 python3-pip python3-venv
else
    # 确保 python3-venv 已安装（即使 python3 已存在）
    if ! python3 -m venv --help > /dev/null 2>&1; then
        echo -e "${YELLOW}安装 python3-venv...${NC}"
        apt update
        apt install -y python3-venv
    fi
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}安装 Node.js...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt install -y nodejs
fi

# 检查 Nginx
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}安装 Nginx...${NC}"
    apt install -y nginx
    systemctl enable nginx
    systemctl start nginx
fi

# 检查 PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}安装 PostgreSQL...${NC}"
    apt install -y postgresql postgresql-contrib
    systemctl enable postgresql
    systemctl start postgresql
fi

echo -e "${GREEN}步骤 2: 创建项目目录...${NC}"
mkdir -p $PROJECT_DIR
mkdir -p $NGINX_DIR

echo -e "${GREEN}步骤 3: 配置后端...${NC}"

# 部署前尝试停止已有服务，避免占用端口与文件锁
if service_exists; then
    echo -e "${YELLOW}检测到已有服务，先停止 ${SERVICE_NAME}...${NC}"
    systemctl stop "${SERVICE_NAME}" || true
fi

# 检测实际的后端目录
ACTUAL_BACKEND_DIR=""
CURRENT_DIR=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 优先检查当前目录
if [ -d "$CURRENT_DIR/backend" ] && [ -f "$CURRENT_DIR/backend/requirements.txt" ]; then
    ACTUAL_BACKEND_DIR="$CURRENT_DIR/backend"
    echo -e "${GREEN}✓ 在当前目录找到后端代码: $ACTUAL_BACKEND_DIR${NC}"
# 检查脚本目录
elif [ -d "$SCRIPT_DIR/backend" ] && [ -f "$SCRIPT_DIR/backend/requirements.txt" ]; then
    ACTUAL_BACKEND_DIR="$SCRIPT_DIR/backend"
    echo -e "${GREEN}✓ 在脚本目录找到后端代码: $ACTUAL_BACKEND_DIR${NC}"
# 检查部署目录
elif [ -d "$BACKEND_DIR" ] && [ -f "$BACKEND_DIR/requirements.txt" ]; then
    ACTUAL_BACKEND_DIR="$BACKEND_DIR"
    echo -e "${GREEN}✓ 在部署目录找到后端代码: $ACTUAL_BACKEND_DIR${NC}"
fi

if [ -n "$ACTUAL_BACKEND_DIR" ]; then
    cd $ACTUAL_BACKEND_DIR
    # 更新 BACKEND_DIR 变量以便后续使用
    BACKEND_DIR="$ACTUAL_BACKEND_DIR"
    
    # 检查虚拟环境是否有效
    VENV_VALID=false
    if [ -d "venv" ]; then
        # 检查虚拟环境的 python 是否存在且可执行
        if [ -f "venv/bin/python" ]; then
            # 检查 python 路径是否指向其他机器（跨机器复制的虚拟环境）
            PYTHON_PATH=$(readlink -f venv/bin/python 2>/dev/null || echo "")
            if [[ "$PYTHON_PATH" == *"/Users/"* ]] || [[ "$PYTHON_PATH" == *"/home/"* ]] && [[ "$PYTHON_PATH" != *"$(whoami)"* ]]; then
                echo -e "${YELLOW}虚拟环境存在但路径指向其他机器 ($PYTHON_PATH)，将重新创建${NC}"
            elif venv/bin/python --version > /dev/null 2>&1; then
            # 检查 gunicorn 是否存在
            if [ -f "venv/bin/gunicorn" ]; then
                VENV_VALID=true
                echo -e "${GREEN}虚拟环境已存在且有效${NC}"
            else
                echo -e "${YELLOW}虚拟环境存在但 gunicorn 未安装，将重新安装依赖${NC}"
            fi
        else
                echo -e "${YELLOW}虚拟环境存在但 python 无法执行，将重新创建${NC}"
            fi
        else
            echo -e "${YELLOW}虚拟环境存在但 python 不存在，将重新创建${NC}"
        fi
    fi
    
    # 如果虚拟环境无效，重新创建
    if [ "$VENV_VALID" = false ]; then
        if [ -d "venv" ]; then
            echo -e "${YELLOW}删除旧的虚拟环境...${NC}"
            rm -rf venv
        fi
        echo -e "${GREEN}创建新的虚拟环境...${NC}"
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        echo -e "${GREEN}安装 Python 依赖...${NC}"
        pip install -r requirements.txt
        echo -e "${GREEN}安装 Gunicorn...${NC}"
        pip install gunicorn
    else
        echo -e "${YELLOW}警告: 未找到 requirements.txt${NC}"
    fi
    
    # 验证 gunicorn 是否安装成功
    if [ ! -f "venv/bin/gunicorn" ]; then
        echo -e "${RED}错误: gunicorn 安装失败${NC}"
        exit 1
    fi
    
    # 创建 Gunicorn 配置
    cat > gunicorn_config.py << 'EOF'
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
EOF

    # 修复数据库文件权限（确保 www-data 用户可以读写）
    if [ -f "app.db" ]; then
        echo -e "${GREEN}修复数据库文件权限...${NC}"
        chown www-data:www-data app.db
        chmod 664 app.db
    fi
    
    # 确保后端目录权限正确（www-data 需要读写权限）
    chown -R www-data:www-data $BACKEND_DIR
    chmod -R 755 $BACKEND_DIR
    # 数据库文件需要写权限
    find $BACKEND_DIR -name "*.db" -exec chmod 664 {} \;
    
    echo -e "${GREEN}后端配置完成${NC}"
else
    echo -e "${YELLOW}警告: 后端目录不存在，请先上传代码${NC}"
fi

echo -e "${GREEN}步骤 4: 配置前端...${NC}"

# 检查前端代码是否存在（尽可能智能地定位）
FRONTEND_CODE_FOUND=false
CURRENT_DIR=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 如果已检测到 BACKEND_DIR，则前端一般在其上级目录
PARENT_OF_BACKEND="$(cd "$BACKEND_DIR/.." 2>/dev/null && pwd || echo "")"

echo -e "${YELLOW}检查前端代码位置...${NC}"
echo -e "  部署目录: $FRONTEND_DIR"
echo -e "  当前目录: $CURRENT_DIR"
echo -e "  脚本目录: $SCRIPT_DIR"
echo -e "  后端目录: $BACKEND_DIR"
echo -e "  后端上级: $PARENT_OF_BACKEND"

# 优先检查：后端目录的上级（常见项目结构）
if [ -n "$PARENT_OF_BACKEND" ] && [ -f "$PARENT_OF_BACKEND/package.json" ] && [ -d "$PARENT_OF_BACKEND/src" ]; then
    FRONTEND_CODE_FOUND=true
    FRONTEND_SOURCE_DIR="$PARENT_OF_BACKEND"
    echo -e "${GREEN}✓ 在后端上级目录找到前端代码: $FRONTEND_SOURCE_DIR${NC}"
# 其次：当前目录（从项目根目录直接运行脚本）
elif [ -f "$CURRENT_DIR/package.json" ] && [ -d "$CURRENT_DIR/src" ]; then
    FRONTEND_CODE_FOUND=true
    FRONTEND_SOURCE_DIR="$CURRENT_DIR"
    echo -e "${GREEN}✓ 在当前目录找到前端代码: $CURRENT_DIR${NC}"
# 再次：脚本所在目录（通过绝对路径调用脚本的情况）
elif [ -f "$SCRIPT_DIR/package.json" ] && [ -d "$SCRIPT_DIR/src" ]; then
    FRONTEND_CODE_FOUND=true
    FRONTEND_SOURCE_DIR="$SCRIPT_DIR"
    echo -e "${GREEN}✓ 在脚本目录找到前端代码: $SCRIPT_DIR${NC}"
# 最后：部署目录（/opt/order-management）
elif [ -d "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ] && [ -d "$FRONTEND_DIR/src" ]; then
    FRONTEND_CODE_FOUND=true
    FRONTEND_SOURCE_DIR="$FRONTEND_DIR"
    echo -e "${GREEN}✓ 在部署目录找到前端代码: $FRONTEND_DIR${NC}"
else
    echo -e "${RED}错误: 未找到前端代码${NC}"
    echo -e "${YELLOW}请确保以下之一：${NC}"
    echo "  1. 前端代码与后端同级（例如: $PARENT_OF_BACKEND）"
    echo "  2. 在包含 package.json 和 src 目录的项目根目录中运行此脚本"
    echo "  3. 或将前端代码复制到部署目录: $FRONTEND_DIR"
    echo ""
    echo -e "${YELLOW}前端代码应包含以下文件：${NC}"
    echo "  - package.json"
    echo "  - src/ 目录"
    echo "  - index.html"
    exit 1
fi

if [ "$FRONTEND_CODE_FOUND" = true ]; then
    cd $FRONTEND_SOURCE_DIR
    
    # 检查并修复 npm 依赖问题（rollup 可选依赖问题）
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/rollup/dist/native.js" ]; then
        echo -e "${YELLOW}安装前端依赖...${NC}"
        # 如果 node_modules 存在但有问题，先删除
        if [ -d "node_modules" ]; then
            echo -e "${YELLOW}检测到依赖问题，清理旧的依赖...${NC}"
            rm -rf node_modules package-lock.json
        fi
        npm install
    else
        # 检查 rollup 是否正常工作
        if ! node -e "require('rollup')" > /dev/null 2>&1; then
            echo -e "${YELLOW}检测到 rollup 依赖问题，重新安装依赖...${NC}"
            rm -rf node_modules package-lock.json
            npm install
        else
            echo -e "${GREEN}前端依赖已存在且正常${NC}"
        fi
    fi
    
    # 检查并创建 .env.production 文件
    # 先询问用户是否使用 IP 访问（用于配置 API 地址）
    echo -e "${YELLOW}配置前端 API 地址...${NC}"
    if [ ! -f ".env.production" ]; then
        # 获取服务器 IP 地址（用于提示）
        TEMP_PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "")
        TEMP_LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")
        
        echo -e "${YELLOW}请选择 API 地址配置方式：${NC}"
        echo "1. 使用公网 IP 访问（推荐，如果没有域名）"
        echo "2. 使用域名访问"
        echo "3. 使用 localhost（仅本地访问）"
        read -p "请选择 (1/2/3，默认 1): " API_CHOICE
        
        case "${API_CHOICE:-1}" in
            1)
                if [ -n "$TEMP_PUBLIC_IP" ]; then
                    API_URL="http://$TEMP_PUBLIC_IP/api"
                    echo -e "${GREEN}API 地址设置为: $API_URL${NC}"
                else
                    echo -e "${YELLOW}无法自动获取公网 IP，请手动输入${NC}"
                    read -p "请输入公网 IP 地址: " MANUAL_IP
                    if [ -n "$MANUAL_IP" ]; then
                        API_URL="http://$MANUAL_IP/api"
                    else
                        API_URL="http://localhost/api"
                        echo -e "${YELLOW}使用默认地址: $API_URL${NC}"
                    fi
                fi
                ;;
            2)
                read -p "请输入域名 (例如: example.com): " DOMAIN_FOR_API
                if [ -n "$DOMAIN_FOR_API" ]; then
                    API_URL="http://$DOMAIN_FOR_API/api"
                else
                    API_URL="http://localhost/api"
                fi
                ;;
            3)
                API_URL="http://localhost/api"
                ;;
            *)
                API_URL="http://localhost/api"
                ;;
        esac
        
        echo "VITE_API_BASE_URL=$API_URL" > .env.production
        echo -e "${GREEN}已创建 .env.production 文件，API 地址: $API_URL${NC}"
    else
        echo -e "${GREEN}.env.production 文件已存在${NC}"
        CURRENT_API=$(grep VITE_API_BASE_URL .env.production | cut -d '=' -f2 || echo "")
        if [ -n "$CURRENT_API" ]; then
            echo -e "${YELLOW}当前 API 地址: $CURRENT_API${NC}"
        fi
    fi
    
    # 构建前端
    echo -e "${GREEN}构建前端项目...${NC}"
    # 尝试先进行类型检查，如果失败则跳过类型检查直接构建
    BUILD_SUCCESS=false
    if npm run build > /tmp/build.log 2>&1; then
        echo -e "${GREEN}前端构建成功（包含类型检查）${NC}"
        BUILD_SUCCESS=true
    else
        # 检查是否是 rollup 依赖问题
        if grep -q "@rollup/rollup-linux-x64-gnu\|Cannot find module.*rollup" /tmp/build.log 2>/dev/null; then
            echo -e "${YELLOW}检测到 rollup 依赖问题，尝试修复...${NC}"
            rm -rf node_modules package-lock.json
            npm install
            # 重试构建
            if npm run build > /tmp/build.log 2>&1; then
                echo -e "${GREEN}前端构建成功（修复依赖后）${NC}"
                BUILD_SUCCESS=true
    else
        echo -e "${YELLOW}类型检查失败，跳过类型检查直接构建...${NC}"
        # 直接使用 vite build，跳过 vue-tsc
                if npx vite build > /tmp/build.log 2>&1; then
            echo -e "${GREEN}前端构建成功（跳过类型检查）${NC}"
                    BUILD_SUCCESS=true
                fi
            fi
        else
            echo -e "${YELLOW}类型检查失败，跳过类型检查直接构建...${NC}"
            # 直接使用 vite build，跳过 vue-tsc
            if npx vite build > /tmp/build.log 2>&1; then
                echo -e "${GREEN}前端构建成功（跳过类型检查）${NC}"
                BUILD_SUCCESS=true
            fi
        fi
    fi
    
    if [ "$BUILD_SUCCESS" = false ]; then
        echo -e "${RED}前端构建失败，错误日志：${NC}"
        tail -50 /tmp/build.log
            exit 1
    fi
    
    # 复制构建文件
    if [ -d "dist" ]; then
        echo -e "${GREEN}复制构建文件到 Nginx 目录...${NC}"
        cp -r dist/* $NGINX_DIR/
        chown -R www-data:www-data $NGINX_DIR
        echo -e "${GREEN}前端构建完成！文件已复制到 $NGINX_DIR${NC}"
    else
        echo -e "${RED}错误: 构建后未找到 dist 目录${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}步骤 5: 配置 systemd 服务...${NC}"

# 检查后端目录是否已配置
if [ -z "$BACKEND_DIR" ] || [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}错误: 后端目录未找到，无法配置服务${NC}"
    exit 1
fi

# 检查 gunicorn 是否存在
if [ ! -f "$BACKEND_DIR/venv/bin/gunicorn" ]; then
    echo -e "${RED}错误: gunicorn 未安装，请先完成后端配置${NC}"
    exit 1
fi

# 确保 gunicorn_config.py 存在
if [ ! -f "$BACKEND_DIR/gunicorn_config.py" ]; then
    echo -e "${YELLOW}创建 gunicorn 配置文件...${NC}"
    cat > "$BACKEND_DIR/gunicorn_config.py" << 'GUNICORN_EOF'
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
GUNICORN_EOF
fi

# 判断使用哪个用户运行服务
# 如果项目在 /root 目录下，使用 root 用户；否则使用 www-data
SERVICE_USER="www-data"
SERVICE_GROUP="www-data"
if [[ "$BACKEND_DIR" == /root/* ]]; then
    echo -e "${YELLOW}检测到项目在 /root 目录下，使用 root 用户运行服务${NC}"
    SERVICE_USER="root"
    SERVICE_GROUP="root"
    # 设置目录权限，确保 root 可以访问
    chmod 755 /root /root/workspace /root/workspace/code 2>/dev/null || true
else
    # 确保 www-data 用户可以访问后端目录
    chown -R www-data:www-data "$BACKEND_DIR"
    chmod -R 755 "$BACKEND_DIR"
    # 数据库文件需要写权限
    find "$BACKEND_DIR" -name "*.db" -exec chmod 664 {} \; 2>/dev/null || true
fi

# 创建日志目录
mkdir -p "$LOG_DIR"
chown "$SERVICE_USER":"$SERVICE_GROUP" "$LOG_DIR"
chmod 750 "$LOG_DIR"

# 创建 systemd 服务配置
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Order Management API
After=network.target

[Service]
Type=notify
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/gunicorn app.main:app -c $BACKEND_DIR/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME

# 尝试启动服务
if systemctl restart $SERVICE_NAME; then
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}服务启动成功${NC}"
    else
        echo -e "${YELLOW}服务启动可能有问题，查看状态：${NC}"
        systemctl status $SERVICE_NAME --no-pager -l | head -20
        echo -e "${YELLOW}查看详细日志：journalctl -xeu $SERVICE_NAME${NC}"
    fi
else
    echo -e "${RED}服务启动失败，查看日志：${NC}"
    journalctl -xeu $SERVICE_NAME --no-pager -n 20
    exit 1
fi

echo -e "${GREEN}步骤 6: 配置 Nginx...${NC}"

read -p "请输入您的域名 (例如: example.com，直接回车使用 IP 访问): " DOMAIN

# 获取服务器 IP 地址
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "")
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")

if [ -z "$DOMAIN" ]; then
    # 没有输入域名，使用 IP 访问
    DOMAIN="localhost"
    USE_IP=true
    if [ -n "$PUBLIC_IP" ]; then
        echo -e "${GREEN}检测到公网 IP: $PUBLIC_IP${NC}"
        echo -e "${YELLOW}将配置 Nginx 支持通过 IP 地址访问${NC}"
    fi
else
    USE_IP=false
fi

# 配置 server_name
if [ "$USE_IP" = true ]; then
    # 使用 IP 访问时，server_name 设置为 _（匹配所有域名和 IP）
    SERVER_NAME="_"
else
    # 使用域名时，设置域名
    SERVER_NAME="$DOMAIN www.$DOMAIN"
fi

cat > /etc/nginx/sites-available/order-management << EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    root $NGINX_DIR;
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

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
}
EOF

# 启用配置
ln -sf /etc/nginx/sites-available/order-management /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试配置
nginx -t

# 重启 Nginx
systemctl restart nginx

echo -e "${GREEN}步骤 7: 配置防火墙...${NC}"

if command -v ufw &> /dev/null; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
fi

echo ""
echo -e "${GREEN}=========================================="
echo "  部署完成！"
echo "==========================================${NC}"
echo ""
echo "服务状态："
systemctl status $SERVICE_NAME --no-pager -l
echo ""
echo "下一步："
echo "1. 配置数据库连接（编辑 $BACKEND_DIR/.env）"
echo "2. 初始化数据库：cd $BACKEND_DIR && source venv/bin/activate && python -m app.database init_db"

# 根据是否使用域名显示不同的提示
if [ "$DOMAIN" = "localhost" ]; then
    # 获取服务器 IP 地址
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "无法获取")
    LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "无法获取")
    
    echo "3. 获取服务器 IP 地址："
    if [ "$PUBLIC_IP" != "无法获取" ]; then
        echo "   - 公网 IP: $PUBLIC_IP"
    else
        echo "   - 公网 IP: 无法自动获取，请手动查询"
    fi
    if [ "$LOCAL_IP" != "无法获取" ]; then
        echo "   - 内网 IP: $LOCAL_IP"
    else
        echo "   - 内网 IP: 无法自动获取，请手动查询"
    fi
    echo "4. 访问方式："
    echo "   - 本地访问: http://localhost"
    if [ "$PUBLIC_IP" != "无法获取" ]; then
        echo "   - 公网访问: http://$PUBLIC_IP"
    fi
    if [ "$LOCAL_IP" != "无法获取" ]; then
        echo "   - 内网访问: http://$LOCAL_IP"
    fi
    echo ""
    echo -e "${YELLOW}提示: 如果没有使用域名，可以通过服务器 IP 地址访问。${NC}"
    echo -e "${YELLOW}如果需要使用域名，请：${NC}"
    echo "   - 将域名解析到服务器 IP"
    echo "   - 重新运行此脚本并输入域名"
    echo "   - 或手动配置 Nginx 并申请 SSL 证书"
else
    echo "3. 配置 SSL 证书（推荐）："
    echo "   certbot --nginx -d $DOMAIN -d www.$DOMAIN"
    echo "4. 访问: http://$DOMAIN 或 https://$DOMAIN"
    echo ""
    echo -e "${YELLOW}提示: 建议配置 SSL 证书以启用 HTTPS 访问。${NC}"
fi
echo ""


