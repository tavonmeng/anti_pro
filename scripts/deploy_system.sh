#!/bin/bash

# =================================================================
# 全栈系统 (官网 + 业务前端 + 后端) 阿里云一键部署脚本
#
# 架构：
#   - 官网+管理系统 → Nginx 80 端口 (合并后的单 Vue 应用)
#   - 后端 API    → 本地 8000 端口 (Gunicorn + Uvicorn)
#
# 用法：
#   sudo bash scripts/deploy_system.sh              # 全量部署
#   sudo bash scripts/deploy_system.sh restart       # 仅重启后端
#   sudo bash scripts/deploy_system.sh stop          # 停止所有服务
#   sudo bash scripts/deploy_system.sh env           # 仅配置 .env
#   sudo bash scripts/deploy_system.sh ssl           # 申请 SSL 证书
# =================================================================

set -e

# ---- 颜色输出 ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓] $*${NC}"; }
warn()  { echo -e "${YELLOW}[!] $*${NC}"; }
err()   { echo -e "${RED}[✗] $*${NC}"; exit 1; }
title() { echo -e "\n${CYAN}════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}════════════════════════════════════════${NC}"; }

# ---- 必须 root ----
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 请使用 root 用户运行: sudo bash scripts/deploy_system.sh${NC}"
    exit 1
fi

# ---- 定位项目根目录 ----
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"

if [ ! -d "$PROJECT_ROOT/cursor_sh/backend" ] || [ ! -d "$PROJECT_ROOT/cursor_sh/src" ]; then
    echo -e "${RED}❌ 无法定位项目根目录，请确保从项目内运行此脚本${NC}"
    echo "  期望的目录结构: PROJECT_ROOT/cursor_sh/backend/ + PROJECT_ROOT/cursor_sh/src/"
    echo "  当前检测到的根目录: $PROJECT_ROOT"
    exit 1
fi

info "项目根目录: $PROJECT_ROOT"

# ---- 配置常量 ----
CMD="${1:-deploy}"
DEPLOY_DIR="/var/www/unique-vision"      # 统一部署目录（官网 + 管理系统合并后）
SERVICE_NAME="order-api"
AI_SERVICE_NAME="ai-agent-api"
BACKEND_DIR="$PROJECT_ROOT/cursor_sh/backend"

# ---- 工具函数 ----
service_exists() { systemctl list-unit-files 2>/dev/null | grep -q "^${1}.service"; }
service_running() { systemctl is-active --quiet "$1" 2>/dev/null; }

# ==============================================================
#  命令分派: stop / restart / env / ssl
# ==============================================================

if [ "$CMD" = "stop" ]; then
    title "停止所有服务"
    for svc in "$SERVICE_NAME" "$AI_SERVICE_NAME"; do
        if service_exists "$svc"; then
            systemctl stop "$svc" 2>/dev/null || true
            info "$svc 已停止"
        fi
    done
    exit 0
fi

if [ "$CMD" = "restart" ]; then
    title "重启后端服务"
    systemctl daemon-reload
    for svc in "$SERVICE_NAME" "$AI_SERVICE_NAME"; do
        if service_exists "$svc"; then
            systemctl restart "$svc"
            sleep 2
            if service_running "$svc"; then
                info "$svc 重启成功"
            else
                warn "$svc 重启失败，查看日志: journalctl -xeu $svc"
            fi
        fi
    done
    exit 0
fi

# ==============================================================
#  交互式 .env 配置
# ==============================================================
generate_env() {
    title "配置后端环境变量 (.env)"
    local ENV_FILE="$BACKEND_DIR/.env"

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

    # 安全密钥
    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

    # --- 数据库 ---
    echo ""
    echo -e "${CYAN}── 数据库配置 ──${NC}"
    echo "  1. SQLite（轻量，适合测试/小规模）"
    echo "  2. MySQL / 阿里云 RDS（生产推荐）"
    read -p "请选择 (1/2，默认 1): " DB_CHOICE

    DB_TYPE="sqlite"; DB_HOST="localhost"; DB_PORT="3306"; DB_NAME="app"; DB_USER=""; DB_PASSWORD=""

    if [ "${DB_CHOICE}" = "2" ]; then
        DB_TYPE="mysql"
        read -p "  RDS 内网地址 (如 rm-xxx.mysql.rds.aliyuncs.com): " DB_HOST
        read -p "  数据库端口 (默认 3306): " inp; DB_PORT="${inp:-3306}"
        read -p "  数据库名 (默认 anti_pro_db): " inp; DB_NAME="${inp:-anti_pro_db}"
        read -p "  数据库用户名: " DB_USER
        read -sp "  数据库密码: " DB_PASSWORD; echo ""
        info "MySQL 配置完成"
    else
        info "使用 SQLite 本地数据库"
    fi

    # --- AI ---
    echo ""
    echo -e "${CYAN}── AI / 语音识别 ──${NC}"
    read -p "阿里云百炼 API Key (AI_API_KEY，留空跳过): " AI_KEY

    # --- 管理员 ---
    echo ""
    echo -e "${CYAN}── 初始管理员账户 ──${NC}"
    read -p "管理员用户名 (默认 admin): " inp; ADMIN_USER="${inp:-admin}"
    read -p "管理员手机号 (默认 13800000000): " inp; ADMIN_PHONE="${inp:-13800000000}"
    read -sp "管理员密码 (默认 123456): " inp; echo ""; ADMIN_PASS="${inp:-123456}"

    # --- 短信 ---
    echo ""
    echo -e "${CYAN}── 短信验证码 (可选，留空跳过) ──${NC}"
    read -p "阿里云 AccessKey ID: " SMS_AK_ID
    read -p "阿里云 AccessKey Secret: " SMS_AK_SECRET
    read -p "短信签名: " SMS_SIGN
    read -p "短信模板 CODE: " SMS_TPL

    # --- 域名/CORS ---
    echo ""
    echo -e "${CYAN}── 域名配置 ──${NC}"
    PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || curl -s --connect-timeout 3 ip.sb 2>/dev/null || echo "")
    [ -n "$PUBLIC_IP" ] && info "检测到公网 IP: $PUBLIC_IP"
    read -p "生产域名 (留空使用 IP 访问): " PROD_DOMAIN
    if [ -n "$PROD_DOMAIN" ]; then
        CORS_VAL="[\"https://${PROD_DOMAIN}\",\"http://${PROD_DOMAIN}\"]"
    elif [ -n "$PUBLIC_IP" ]; then
        CORS_VAL="[\"http://${PUBLIC_IP}\"]"
    else
        CORS_VAL="[\"http://localhost\"]"
    fi

    # --- 部署模式 ---
    echo ""
    echo -e "${CYAN}── 部署模式 ──${NC}"
    echo "  1. all     - 全量部署（开发测试，含所有功能）"
    echo "  2. external - 用户端（仅对外服务）"
    echo "  3. internal - 内部系统（管理员+负责人+承包商）"
    read -p "请选择 (1/2/3，默认 1): " MODE_CHOICE
    case "$MODE_CHOICE" in
        2) DEPLOY_MODE="external" ;;
        3) DEPLOY_MODE="internal" ;;
        *) DEPLOY_MODE="all" ;;
    esac
    info "部署模式: $DEPLOY_MODE"

    # 承包商邀请链接 URL（仅 internal/all 模式需要）
    CONTRACTOR_URL="http://localhost:3000"
    if [ "$DEPLOY_MODE" != "external" ]; then
        if [ -n "$PUBLIC_IP" ]; then
            CONTRACTOR_URL="http://${PUBLIC_IP}"
        fi
        if [ -n "$PROD_DOMAIN" ]; then
            CONTRACTOR_URL="https://${PROD_DOMAIN}"
        fi
        read -p "承包商邀请链接基础URL (默认 $CONTRACTOR_URL): " inp
        CONTRACTOR_URL="${inp:-$CONTRACTOR_URL}"
    fi

    # 写入
    cat > "$ENV_FILE" << ENVEOF
# ===== 自动生成于 $(date) =====
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8000
DEBUG=false
JWT_SECRET_KEY=${JWT_SECRET}

# 数据库
DB_TYPE=${DB_TYPE}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
AUDIT_DATABASE_URL=sqlite+aiosqlite:///./audit.db

# CORS
CORS_ORIGINS=${CORS_VAL}

# 管理员
INIT_ADMIN_USERNAME=${ADMIN_USER}
INIT_ADMIN_PASSWORD=${ADMIN_PASS}
INIT_ADMIN_PHONE=${ADMIN_PHONE}

# AI / 语音
AI_API_KEY=${AI_KEY}
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL_NAME=qwen-max

# 短信
SMS_ENABLED=$( [ -n "$SMS_AK_ID" ] && echo "true" || echo "false" )
SMS_ACCESS_KEY_ID=${SMS_AK_ID}
SMS_ACCESS_KEY_SECRET=${SMS_AK_SECRET}
SMS_SIGN_NAME=${SMS_SIGN}
SMS_TEMPLATE_CODE=${SMS_TPL}

# 部署模式: all=全量(开发), external=用户端, internal=内部系统
DEPLOYMENT_MODE=${DEPLOY_MODE}

# 承包商邀请链接基础URL
CONTRACTOR_BASE_URL=${CONTRACTOR_URL}

# 日志 & 限流
LOG_ENABLED=true
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
ENVEOF

    chmod 600 "$ENV_FILE"
    info ".env 已生成: $ENV_FILE"
}

if [ "$CMD" = "env" ]; then
    generate_env
    warn "请重启服务使配置生效: sudo bash scripts/deploy_system.sh restart"
    exit 0
fi

# ==============================================================
#  SSL 证书
# ==============================================================
setup_ssl() {
    title "配置 SSL 证书 (Let's Encrypt)"
    read -p "请输入域名 (如 example.com): " SSL_DOMAIN
    [ -z "$SSL_DOMAIN" ] && { err "域名不能为空"; }

    if ! command -v certbot &>/dev/null; then
        info "安装 certbot..."
        if command -v apt &>/dev/null; then
            apt install -y certbot python3-certbot-nginx
        else
            yum install -y certbot python3-certbot-nginx
        fi
    fi

    certbot --nginx -d "$SSL_DOMAIN" --non-interactive --agree-tos --email "admin@${SSL_DOMAIN}" || {
        warn "自动申请失败，尝试交互式..."
        certbot --nginx -d "$SSL_DOMAIN"
    }
    systemctl enable certbot.timer 2>/dev/null || true
    info "SSL 证书配置完成！已启用自动续期"
}

if [ "$CMD" = "ssl" ]; then
    setup_ssl
    exit 0
fi

# ==============================================================
#  全量部署流程开始
# ==============================================================
title "🚀 全栈系统一键部署"

# ---- 停止现有服务 ----
for svc in "$SERVICE_NAME" "$AI_SERVICE_NAME"; do
    if service_exists "$svc" && service_running "$svc"; then
        warn "停止 $svc..."
        systemctl stop "$svc" 2>/dev/null || true
    fi
done

# ==============================================================
#  步骤 1: 系统依赖
# ==============================================================
title "步骤 1/6: 安装系统依赖"

if command -v apt &>/dev/null; then
    PKG_MGR="apt"
    apt update -qq
else
    PKG_MGR="yum"
    yum makecache -q || true
fi

# Node.js
if ! command -v node &>/dev/null; then
    info "安装 Node.js 20..."
    if [ "$PKG_MGR" = "apt" ]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt install -y nodejs
    else
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
        yum install -y nodejs
    fi
else
    info "Node.js 已就绪: $(node --version)"
fi

# Nginx
if ! command -v nginx &>/dev/null; then
    info "安装 Nginx..."
    $PKG_MGR install -y nginx
    systemctl enable nginx
fi
info "Nginx 已就绪"

# Python (优先 3.9+)
if [ "$PKG_MGR" = "yum" ]; then
    yum install -y python3.9 python3.9-pip 2>/dev/null \
        || yum module install -y python39 2>/dev/null \
        || yum install -y python3 python3-pip 2>/dev/null || true
    if command -v python3.9 &>/dev/null; then PYTHON_CMD="python3.9"
    elif command -v python3.8 &>/dev/null; then PYTHON_CMD="python3.8"
    else PYTHON_CMD="python3"; fi
else
    if ! command -v python3 &>/dev/null; then
        apt install -y python3 python3-pip python3-venv
    fi
    python3 -m venv --help > /dev/null 2>&1 || apt install -y python3-venv
    PYTHON_CMD="python3"
fi
info "Python: $($PYTHON_CMD --version)"

# 中文字体（PDF 生成需要）
info "安装中文字体..."
if [ "$PKG_MGR" = "apt" ]; then
    apt install -y fonts-wqy-zenhei fonts-wqy-microhei 2>/dev/null || true
else
    yum install -y wqy-zenhei-fonts wqy-microhei-fonts 2>/dev/null \
        || yum install -y google-noto-sans-cjk-ttc-fonts 2>/dev/null || true
fi
fc-cache -f 2>/dev/null || true

mkdir -p "$DEPLOY_DIR"

# ==============================================================
#  步骤 2: 配置 .env
# ==============================================================
title "步骤 2/6: 配置后端环境"

if [ ! -f "$BACKEND_DIR/.env" ]; then
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        warn "未找到 .env，进入交互式配置..."
    fi
    generate_env
else
    info ".env 已存在（如需重新配置: sudo bash scripts/deploy_system.sh env）"
fi

# ==============================================================
#  步骤 3: 部署后端
# ==============================================================
title "步骤 3/6: 部署后端"

cd "$BACKEND_DIR"

# 虚拟环境
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    if venv/bin/python --version > /dev/null 2>&1; then
        info "虚拟环境已存在且有效"
    else
        warn "虚拟环境损坏，重新创建..."
        rm -rf venv
        $PYTHON_CMD -m venv venv
    fi
else
    info "创建虚拟环境..."
    $PYTHON_CMD -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q

info "安装 Python 依赖（可能需要几分钟）..."
pip install -r requirements.txt -q
pip install gunicorn uvicorn -q
info "Python 依赖安装完成"

# 日志目录
mkdir -p logs/{auth,workspace,order,ai,staff,notification,contractor,system,error,crash,ai_sessions}
# 上传目录
mkdir -p uploads
info "日志和上传目录已准备"

# Gunicorn 配置
cat > gunicorn_config.py << 'EOF'
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
EOF

# Systemd 服务
USER_TO_RUN=$(id -un)
GROUP_TO_RUN=$(id -gn)

cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=AI Design Platform Backend API
After=network.target

[Service]
Type=simple
User=$USER_TO_RUN
Group=$GROUP_TO_RUN
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/gunicorn app.main:app -c $BACKEND_DIR/gunicorn_config.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 3

if service_running "$SERVICE_NAME"; then
    info "后端服务启动成功"
else
    warn "后端服务启动可能有问题"
    journalctl -xeu "$SERVICE_NAME" --no-pager -n 15
fi

# ---- 独立 AI 后端（遗留兼容）----
if [ -d "$PROJECT_ROOT/ai_backend" ] && [ -f "$PROJECT_ROOT/ai_backend/requirements.txt" ]; then
    info "检测到独立 AI 后端，部署中..."
    cd "$PROJECT_ROOT/ai_backend"
    [ ! -d "venv" ] && $PYTHON_CMD -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    pip install gunicorn uvicorn -q

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
    systemctl enable "$AI_SERVICE_NAME"
    systemctl restart "$AI_SERVICE_NAME"
else
    info "AI 已集成在主后端，跳过独立 AI 部署"
fi

# ==============================================================
#  步骤 4: 构建前端
# ==============================================================
title "步骤 4/6: 构建前端 (官网 + 管理系统)"
# 自动获取公网 IP
PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || curl -s --connect-timeout 3 ip.sb 2>/dev/null || echo "")
[ -n "$PUBLIC_IP" ] && info "检测到公网 IP: $PUBLIC_IP"

# ---- 统一前端构建 (官网 + 管理系统已合并为单 Vue 应用) ----
info "构建前端应用（官网 + 管理系统）..."
cd "$PROJECT_ROOT/cursor_sh"
echo "VITE_API_BASE_URL=/api" > .env.production
echo "VITE_ENABLE_VOICE_INPUT=false" >> .env.production
npm install --legacy-peer-deps 2>/dev/null || npm install

BUILD_OK=false
if npm run build > /tmp/cursor-build.log 2>&1; then
    BUILD_OK=true
    info "前端构建成功"
elif npx vite build > /tmp/cursor-build.log 2>&1; then
    BUILD_OK=true
    info "前端构建成功（跳过类型检查）"
fi

if [ "$BUILD_OK" = true ] && [ -d "dist" ]; then
    cp -r dist/* "$DEPLOY_DIR/"
    chown -R www-data:www-data "$DEPLOY_DIR" 2>/dev/null || chown -R root:root "$DEPLOY_DIR"
    info "前端文件已部署到 $DEPLOY_DIR"
else
    err "前端构建失败！日志: tail -30 /tmp/cursor-build.log"
fi

# ==============================================================
#  步骤 5: Nginx 配置
# ==============================================================
title "步骤 5/6: 配置 Nginx"

# ---- 统一 Nginx 配置 (单端口 80) ----
cat > /etc/nginx/conf.d/unique-vision.conf << 'NGEOF'
server {
    listen 80;
    server_name _;
    root /var/www/unique-vision;
    index index.html;

    # 上传文件大小限制 (营业执照、初稿等)
    client_max_body_size 50m;

    # Vue Router SPA (官网 + 管理系统所有前端路由)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持 (语音识别等)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        client_max_body_size 50m;
    }

    # AI 聊天接口 (SSE 流式响应)
    location /ai/ {
        proxy_pass http://127.0.0.1:8000/ai/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE 必须关闭缓冲
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 用户上传文件 (营业执照、初稿预览等)
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
    }

    # 案例静态资源 (视频、封面图)
    location /static/cases/ {
        proxy_pass http://127.0.0.1:8000/static/cases/;
    }

    # 静态资源长缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|mp4|webm)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml+rss;
}
NGEOF

# 清理旧的双端口配置
rm -f /etc/nginx/conf.d/cursor-sh.conf 2>/dev/null || true
rm -f /etc/nginx/conf.d/unique-vision-website.conf 2>/dev/null || true

# 清理默认配置
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# 禁用 nginx.conf 中自带的默认 server 块（CentOS/RHEL 默认会监听 80 端口导致冲突）
if grep -q "listen.*80;" /etc/nginx/nginx.conf 2>/dev/null; then
    # 注释掉 nginx.conf 中的 server { ... } 块
    sed -i '/^    server {/,/^    }/s/^/#/' /etc/nginx/nginx.conf 2>/dev/null || true
    info "已禁用 nginx.conf 中的默认 server 块"
fi

if nginx -t 2>/dev/null; then
    systemctl restart nginx
    info "Nginx 配置完成并已重启"
else
    err "Nginx 配置有误，请检查: nginx -t"
fi

# ==============================================================
#  步骤 6: 防火墙 + SSL
# ==============================================================
title "步骤 6/6: 防火墙与 SSL"

# 防火墙
if command -v ufw &>/dev/null; then
    ufw allow 22/tcp > /dev/null 2>&1
    ufw allow 80/tcp > /dev/null 2>&1
    ufw allow 443/tcp > /dev/null 2>&1
    ufw --force enable > /dev/null 2>&1
    info "防火墙已配置 (22/80/443)"
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
    firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    info "firewalld 已配置 (80/443)"
fi

# SSL
echo ""
read -p "是否现在申请 SSL 证书？(语音功能需要 HTTPS) (y/N): " SSL_CHOICE
if [[ "${SSL_CHOICE,,}" = "y" ]]; then
    setup_ssl
else
    warn "跳过 SSL。语音录入功能在非 HTTPS 下无法使用"
    warn "之后可执行: sudo bash scripts/deploy_system.sh ssl"
fi

# ==============================================================
#  部署完成 🎉
# ==============================================================
echo ""
title "🎉 全栈部署完成！"
echo ""

echo -e "${GREEN}服务状态：${NC}"
systemctl status "$SERVICE_NAME" --no-pager -l 2>/dev/null | head -8
echo ""

echo -e "${CYAN}── 访问方式 ──${NC}"
if [ -n "$PUBLIC_IP" ]; then
    echo "  官网:         http://$PUBLIC_IP"
    echo "  用户登录:     http://$PUBLIC_IP/login"
    echo "  管理后台:     http://$PUBLIC_IP/admin/login"
    echo "  承包商注册:   通过管理后台生成邀请链接"
else
    echo "  官网:         http://服务器IP"
    echo "  用户登录:     http://服务器IP/login"
    echo "  管理后台:     http://服务器IP/admin/login"
    echo "  承包商注册:   通过管理后台生成邀请链接"
fi
echo ""

echo -e "${CYAN}── 常用命令 ──${NC}"
echo "  查看后端日志:    journalctl -fu $SERVICE_NAME"
echo "  重启服务:        sudo bash scripts/deploy_system.sh restart"
echo "  停止服务:        sudo bash scripts/deploy_system.sh stop"
echo "  重新配置:        sudo bash scripts/deploy_system.sh env"
echo "  申请 SSL:        sudo bash scripts/deploy_system.sh ssl"
echo ""

echo -e "${YELLOW}⚠️  重要提醒：${NC}"
echo "  1. 请前往阿里云安全组，放行 TCP 端口: 80, 443"
echo "  2. 语音录入需要 HTTPS，请尽快配置 SSL 证书"
echo "  3. 首次启动会自动建表、创建管理员账户、初始化工作流配置"
echo "  4. 承包商管理入口：管理后台 → 承包商管理 → 生成邀请链接"
echo ""
