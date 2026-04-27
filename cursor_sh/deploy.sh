#!/bin/bash
# ============================================================
#  阿里云一键部署脚本  —  AI设计平台
#  使用方法:
#    sudo bash deploy.sh              # 全量部署
#    sudo bash deploy.sh restart      # 仅重启后端服务
#    sudo bash deploy.sh stop         # 停止服务
#    sudo bash deploy.sh env          # 仅重新配置 .env
#    sudo bash deploy.sh ssl          # 仅申请 SSL 证书
# ============================================================

set -e

# ---- 颜色 ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓] $*${NC}"; }
warn()  { echo -e "${YELLOW}[!] $*${NC}"; }
err()   { echo -e "${RED}[✗] $*${NC}"; }
title() { echo -e "\n${CYAN}════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}════════════════════════════════════════${NC}"; }

# ---- 必须 root ----
if [ "$EUID" -ne 0 ]; then err "请使用 root 用户运行: sudo bash deploy.sh"; exit 1; fi

# ---- 配置常量 ----
CMD="${1:-deploy}"
SERVICE_NAME="order-api"
NGINX_SITE_NAME="order-management"

# ---- 自动检测项目根目录 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/backend/requirements.txt" ] && [ -f "$SCRIPT_DIR/package.json" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
elif [ -f "$(pwd)/backend/requirements.txt" ] && [ -f "$(pwd)/package.json" ]; then
    PROJECT_DIR="$(pwd)"
else
    err "无法找到项目根目录（需包含 backend/ 和 package.json）"
    err "请在项目根目录下执行此脚本"
    exit 1
fi

BACKEND_DIR="$PROJECT_DIR/backend"
NGINX_DIR="/var/www/order-management"
LOG_DIR="/var/log/$SERVICE_NAME"

info "项目目录: $PROJECT_DIR"
info "后端目录: $BACKEND_DIR"

# ---- 工具函数 ----
service_exists() { systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE_NAME}.service"; }
service_running() { systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; }

# ============================================================
#  命令分派: stop / restart / env / ssl
# ============================================================
if [ "$CMD" = "stop" ]; then
    title "停止服务"
    if service_exists; then
        systemctl stop "$SERVICE_NAME" || true
        info "后端服务已停止"
    else
        warn "未检测到已安装的服务"
    fi
    exit 0
fi

if [ "$CMD" = "restart" ]; then
    title "重启服务"
    if service_exists; then
        systemctl daemon-reload
        systemctl restart "$SERVICE_NAME"
        sleep 2
        if service_running; then
            info "后端服务重启成功"
        else
            err "后端服务重启失败"
            journalctl -xeu "$SERVICE_NAME" --no-pager -n 30
        fi
    else
        err "未检测到服务，请先执行完整部署: sudo bash deploy.sh"
    fi
    exit 0
fi

# ============================================================
#  .env 交互式配置（可独立调用: sudo bash deploy.sh env）
# ============================================================
generate_env() {
    title "配置后端环境变量 (.env)"
    ENV_FILE="$BACKEND_DIR/.env"

    if [ -f "$ENV_FILE" ]; then
        warn "检测到已有 .env 文件"
        read -p "是否覆盖重新配置？(y/N): " OVERWRITE
        if [[ "${OVERWRITE,,}" != "y" ]]; then
            info "保留现有 .env 文件"
            return 0
        fi
        cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"
        info "旧 .env 已备份"
    fi

    # --- 生成安全密钥 ---
    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

    # --- 数据库配置 ---
    echo ""
    echo -e "${CYAN}── 数据库配置 ──${NC}"
    echo "  1. SQLite（轻量本地，适合测试）"
    echo "  2. MySQL / RDS（生产推荐）"
    read -p "请选择数据库类型 (1/2，默认 1): " DB_CHOICE

    DB_TYPE="sqlite"
    DB_HOST="localhost"
    DB_PORT="3306"
    DB_NAME="app"
    DB_USER=""
    DB_PASSWORD=""

    if [ "${DB_CHOICE}" = "2" ]; then
        DB_TYPE="mysql"
        read -p "  RDS 内网地址 (如 rm-xxx.mysql.rds.aliyuncs.com): " DB_HOST
        read -p "  数据库端口 (默认 3306): " input_port
        DB_PORT="${input_port:-3306}"
        read -p "  数据库名 (默认 anti_pro_db): " input_name
        DB_NAME="${input_name:-anti_pro_db}"
        read -p "  数据库用户名: " DB_USER
        read -sp "  数据库密码: " DB_PASSWORD
        echo ""
        info "MySQL 配置完成"
    else
        info "使用 SQLite 本地数据库 (./app.db)"
    fi

    # --- AI API 配置 ---
    echo ""
    echo -e "${CYAN}── AI / 语音识别配置 ──${NC}"
    read -p "阿里云百炼 API Key (AI_API_KEY，留空跳过): " AI_KEY

    # --- 管理员配置 ---
    echo ""
    echo -e "${CYAN}── 初始管理员账户 ──${NC}"
    read -p "管理员用户名 (默认 admin): " input_admin_user
    ADMIN_USER="${input_admin_user:-admin}"
    read -p "管理员手机号 (默认 13800000000): " input_admin_phone
    ADMIN_PHONE="${input_admin_phone:-13800000000}"
    read -sp "管理员密码 (默认 123456): " input_admin_pass
    echo ""
    ADMIN_PASS="${input_admin_pass:-123456}"

    # --- 短信服务 ---
    echo ""
    echo -e "${CYAN}── 短信验证码服务 (可选，留空跳过) ──${NC}"
    read -p "阿里云 AccessKey ID: " SMS_AK_ID
    read -p "阿里云 AccessKey Secret: " SMS_AK_SECRET
    read -p "短信签名名称: " SMS_SIGN
    read -p "短信模板 CODE: " SMS_TPL

    # --- CORS 域名 ---
    echo ""
    echo -e "${CYAN}── 域名 / CORS 配置 ──${NC}"
    PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || curl -s --connect-timeout 3 ip.sb 2>/dev/null || echo "")
    if [ -n "$PUBLIC_IP" ]; then
        info "检测到公网 IP: $PUBLIC_IP"
    fi
    read -p "生产域名 (留空使用 IP 访问): " PROD_DOMAIN
    if [ -n "$PROD_DOMAIN" ]; then
        CORS_VAL="[\"https://${PROD_DOMAIN}\",\"http://${PROD_DOMAIN}\"]"
    elif [ -n "$PUBLIC_IP" ]; then
        CORS_VAL="[\"http://${PUBLIC_IP}\"]"
    else
        CORS_VAL="[\"http://localhost\"]"
    fi

    # --- 写入 .env ---
    cat > "$ENV_FILE" << ENVEOF
# ===== 自动生成于 $(date) =====
# 运行环境
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8000
DEBUG=false

# JWT 安全密钥（已自动生成）
JWT_SECRET_KEY=${JWT_SECRET}

# 数据库
DB_TYPE=${DB_TYPE}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# 审计日志库（默认 SQLite，与主库隔离）
AUDIT_DATABASE_URL=sqlite+aiosqlite:///./audit.db

# CORS
CORS_ORIGINS=${CORS_VAL}

# 初始管理员
INIT_ADMIN_USERNAME=${ADMIN_USER}
INIT_ADMIN_PASSWORD=${ADMIN_PASS}
INIT_ADMIN_PHONE=${ADMIN_PHONE}

# AI / 语音识别
AI_API_KEY=${AI_KEY}
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL_NAME=qwen-max

# 短信
SMS_ENABLED=$( [ -n "$SMS_AK_ID" ] && echo "true" || echo "false" )
SMS_ACCESS_KEY_ID=${SMS_AK_ID}
SMS_ACCESS_KEY_SECRET=${SMS_AK_SECRET}
SMS_SIGN_NAME=${SMS_SIGN}
SMS_TEMPLATE_CODE=${SMS_TPL}

# 日志
LOG_ENABLED=true
LOG_LEVEL=INFO

# 限流
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
ENVEOF

    chmod 600 "$ENV_FILE"
    info ".env 文件已生成: $ENV_FILE"
}

# 如果是 env 命令，仅配置环境
if [ "$CMD" = "env" ]; then
    generate_env
    warn "请重启服务使配置生效: sudo bash deploy.sh restart"
    exit 0
fi

# ============================================================
#  SSL 证书申请（可独立调用: sudo bash deploy.sh ssl）
# ============================================================
setup_ssl() {
    title "配置 SSL 证书 (Let's Encrypt)"
    read -p "请输入域名 (如 example.com): " SSL_DOMAIN
    if [ -z "$SSL_DOMAIN" ]; then
        err "域名不能为空"
        return 1
    fi

    if ! command -v certbot &>/dev/null; then
        info "安装 certbot..."
        apt update -qq
        apt install -y certbot python3-certbot-nginx
    fi

    certbot --nginx -d "$SSL_DOMAIN" --non-interactive --agree-tos --email "admin@${SSL_DOMAIN}" || {
        warn "自动申请失败，尝试交互式申请..."
        certbot --nginx -d "$SSL_DOMAIN"
    }

    # 配置自动续期
    systemctl enable certbot.timer 2>/dev/null || true
    info "SSL 证书配置完成！已启用自动续期"
    info "HTTPS 访问: https://$SSL_DOMAIN"
}

if [ "$CMD" = "ssl" ]; then
    setup_ssl
    exit 0
fi

# ============================================================
#  全量部署流程开始
# ============================================================
title "AI设计平台 — 一键部署"

# ---- 停止现有服务 ----
if service_exists && service_running; then
    warn "停止已有服务..."
    systemctl stop "$SERVICE_NAME" || true
fi

# ============================================================
#  步骤 1: 系统依赖安装
# ============================================================
title "步骤 1/7: 安装系统依赖"

apt update -qq

# Python
if ! command -v python3 &>/dev/null; then
    info "安装 Python3..."
    apt install -y python3 python3-pip python3-venv
else
    # 确保 venv 可用
    python3 -m venv --help > /dev/null 2>&1 || apt install -y python3-venv
    info "Python3 已就绪: $(python3 --version)"
fi

# Node.js
if ! command -v node &>/dev/null; then
    info "安装 Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt install -y nodejs
else
    info "Node.js 已就绪: $(node --version)"
fi

# Nginx
if ! command -v nginx &>/dev/null; then
    info "安装 Nginx..."
    apt install -y nginx
    systemctl enable nginx
    systemctl start nginx
else
    info "Nginx 已就绪"
fi

# ============================================================
#  步骤 2: 配置 .env 环境变量
# ============================================================
if [ ! -f "$BACKEND_DIR/.env" ]; then
    generate_env
else
    info "检测到已有 .env，跳过配置（如需重新配置: sudo bash deploy.sh env）"
fi

# ============================================================
#  步骤 3: 后端 Python 环境
# ============================================================
title "步骤 3/7: 配置后端 Python 环境"

cd "$BACKEND_DIR"

# 检查虚拟环境
VENV_OK=false
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    if venv/bin/python --version > /dev/null 2>&1; then
        VENV_OK=true
        info "虚拟环境已存在且有效"
    else
        warn "虚拟环境损坏，重新创建..."
        rm -rf venv
    fi
fi

if [ "$VENV_OK" = false ]; then
    info "创建 Python 虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q

if [ -f "requirements.txt" ]; then
    info "安装 Python 依赖（这可能需要几分钟）..."
    pip install -r requirements.txt -q
    info "Python 依赖安装完成"
else
    err "未找到 requirements.txt"
    exit 1
fi

# 确保上传目录存在
mkdir -p uploads
info "后端环境配置完成"

# ============================================================
#  步骤 4: 前端打包
# ============================================================
title "步骤 4/7: 构建前端"

cd "$PROJECT_DIR"

# 安装前端依赖
if [ ! -d "node_modules" ] || ! node -e "require('vite')" > /dev/null 2>&1; then
    info "安装前端依赖..."
    rm -rf node_modules package-lock.json 2>/dev/null
    npm install --legacy-peer-deps
else
    info "前端依赖已存在"
fi

# 打包
info "构建前端项目（可能需要1-2分钟）..."
BUILD_OK=false
if npm run build > /tmp/frontend-build.log 2>&1; then
    BUILD_OK=true
    info "前端构建成功"
elif npx vite build > /tmp/frontend-build.log 2>&1; then
    BUILD_OK=true
    info "前端构建成功（跳过类型检查）"
fi

if [ "$BUILD_OK" = false ]; then
    err "前端构建失败！最后 30 行日志："
    tail -30 /tmp/frontend-build.log
    exit 1
fi

# 复制到 Nginx 目录
mkdir -p "$NGINX_DIR"
if [ -d "dist" ]; then
    cp -r dist/* "$NGINX_DIR/"
    chown -R www-data:www-data "$NGINX_DIR"
    info "前端文件已复制到 $NGINX_DIR"
else
    err "未找到 dist 目录"
    exit 1
fi

# ============================================================
#  步骤 5: Systemd 后端服务
# ============================================================
title "步骤 5/7: 配置后端服务 (systemd)"

# 判断运行用户
SERVICE_USER="www-data"
SERVICE_GROUP="www-data"
if [[ "$BACKEND_DIR" == /root/* ]]; then
    SERVICE_USER="root"
    SERVICE_GROUP="root"
    chmod 755 /root 2>/dev/null || true
else
    chown -R www-data:www-data "$BACKEND_DIR"
fi
chmod -R 755 "$BACKEND_DIR"
find "$BACKEND_DIR" -name "*.db" -exec chmod 664 {} \; 2>/dev/null || true

# 日志目录
mkdir -p "$LOG_DIR"
chown "$SERVICE_USER":"$SERVICE_GROUP" "$LOG_DIR"

# 创建 systemd service
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=AI Design Platform Backend (FastAPI + Uvicorn)
After=network.target

[Service]
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/stdout.log
StandardError=append:$LOG_DIR/stderr.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# 启动！
info "启动后端服务..."
if systemctl start "$SERVICE_NAME"; then
    sleep 3
    if service_running; then
        info "后端服务启动成功！"
    else
        err "后端服务启动失败，查看日志："
        journalctl -xeu "$SERVICE_NAME" --no-pager -n 30
        exit 1
    fi
else
    err "后端服务启动失败"
    journalctl -xeu "$SERVICE_NAME" --no-pager -n 30
    exit 1
fi

# ============================================================
#  步骤 6: Nginx 配置
# ============================================================
title "步骤 6/7: 配置 Nginx"

# 获取 IP
PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || curl -s --connect-timeout 3 ip.sb 2>/dev/null || echo "")
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")

read -p "请输入域名（直接回车使用 IP 访问）: " DOMAIN

if [ -z "$DOMAIN" ]; then
    SERVER_NAME="_"
    USE_DOMAIN=false
    info "将使用 IP 地址访问"
else
    SERVER_NAME="$DOMAIN www.$DOMAIN"
    USE_DOMAIN=true
    info "域名: $DOMAIN"
fi

cat > /etc/nginx/sites-available/$NGINX_SITE_NAME << NGINXEOF
server {
    listen 80;
    server_name $SERVER_NAME;

    # 前端静态文件
    root $NGINX_DIR;
    index index.html;

    # Vue Router SPA 支持
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API 接口代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket 支持（语音识别等）
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # 上传文件大小限制
        client_max_body_size 50m;
    }

    # AI 聊天接口代理
    location /ai/ {
        proxy_pass http://127.0.0.1:8000/ai/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;

        # SSE 长连接支持
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 用户上传文件（营业执照、初稿等）
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
    }

    # 案例静态资源（视频、封面图）
    location /static/cases/ {
        proxy_pass http://127.0.0.1:8000/static/cases/;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml+rss;
}
NGINXEOF

# 激活配置
ln -sf /etc/nginx/sites-available/$NGINX_SITE_NAME /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试并重启
if nginx -t 2>/dev/null; then
    systemctl restart nginx
    info "Nginx 配置完成并已重启"
else
    err "Nginx 配置有误："
    nginx -t
    exit 1
fi

# ============================================================
#  步骤 7: 防火墙 + SSL
# ============================================================
title "步骤 7/7: 防火墙与 SSL"

if command -v ufw &>/dev/null; then
    ufw allow 22/tcp > /dev/null 2>&1
    ufw allow 80/tcp > /dev/null 2>&1
    ufw allow 443/tcp > /dev/null 2>&1
    ufw --force enable > /dev/null 2>&1
    info "防火墙已配置 (22/80/443)"
fi

# 询问是否配置 SSL
if [ "$USE_DOMAIN" = true ]; then
    echo ""
    read -p "是否现在申请 SSL 证书？(推荐，语音功能需要 HTTPS) (Y/n): " SSL_CHOICE
    if [[ "${SSL_CHOICE,,}" != "n" ]]; then
        setup_ssl
    else
        warn "已跳过 SSL。注意：语音录入功能在非 HTTPS 下无法使用"
        warn "之后可执行: sudo bash deploy.sh ssl"
    fi
else
    warn "未配置域名，跳过 SSL。语音功能需要 HTTPS + 域名"
    warn "配置域名后可执行: sudo bash deploy.sh ssl"
fi

# ============================================================
#  部署完成 🎉
# ============================================================
echo ""
title "🎉 部署完成！"
echo ""
echo -e "${GREEN}服务状态：${NC}"
systemctl status "$SERVICE_NAME" --no-pager -l | head -10
echo ""

echo -e "${CYAN}── 访问方式 ──${NC}"
if [ "$USE_DOMAIN" = true ]; then
    echo "  用户端:     http://$DOMAIN"
    echo "  管理后台:   http://$DOMAIN/admin/login"
    echo "  API 文档:   http://$DOMAIN/api/docs"
else
    [ -n "$PUBLIC_IP" ] && echo "  公网访问:   http://$PUBLIC_IP"
    [ -n "$LOCAL_IP" ]  && echo "  内网访问:   http://$LOCAL_IP"
    echo "  管理后台:   http://${PUBLIC_IP:-$LOCAL_IP}/admin/login"
fi
echo ""

echo -e "${CYAN}── 默认管理员账户 ──${NC}"
ADMIN_U=$(grep INIT_ADMIN_USERNAME "$BACKEND_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "admin")
ADMIN_P=$(grep INIT_ADMIN_PHONE "$BACKEND_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "13800000000")
echo "  用户名:  ${ADMIN_U:-admin}"
echo "  手机号:  ${ADMIN_P:-13800000000}"
echo "  密码:    (你在 .env 中设置的密码)"
echo ""

echo -e "${CYAN}── 常用命令 ──${NC}"
echo "  查看后端日志:    journalctl -fu $SERVICE_NAME"
echo "  重启后端:        sudo bash $0 restart"
echo "  停止服务:        sudo bash $0 stop"
echo "  重新配置 .env:   sudo bash $0 env"
echo "  申请 SSL 证书:   sudo bash $0 ssl"
echo "  编辑 .env:       nano $BACKEND_DIR/.env"
echo ""

warn "重要提示："
echo "  1. 语音录入功能需要 HTTPS，请尽快配置 SSL 证书"
echo "  2. 首次启动会自动建表和创建管理员账户"
echo "  3. 如需修改配置，编辑 $BACKEND_DIR/.env 然后执行 sudo bash $0 restart"
echo ""
