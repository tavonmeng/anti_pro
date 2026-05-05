#!/bin/bash
# ============================================================
#  本地构建 & 部署脚本
#  在 Mac 上构建 Docker 镜像，导出并上传到阿里云 ECS
#
#  用法：
#    bash scripts/local_build.sh              # 构建 + 上传到所有服务器
#    bash scripts/local_build.sh build        # 仅构建，不上传
#    bash scripts/local_build.sh deploy       # 仅上传已构建的镜像
#    bash scripts/local_build.sh frontend     # 仅构建前端 + 上传
# ============================================================

set -e

# ---- 颜色 ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓] $*${NC}"; }
warn()  { echo -e "${YELLOW}[!] $*${NC}"; }
err()   { echo -e "${RED}[✗] $*${NC}"; exit 1; }
title() { echo -e "\n${CYAN}════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}════════════════════════════════════════${NC}"; }

# ============================================================
#  配置区
# ============================================================

# 项目根目录（自动检测脚本所在位置的上一级）
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 镜像名称
FRONTEND_IMAGE="anti_pro-frontend"
BACKEND_IMAGE="anti_pro-backend"

# 导出文件路径
EXPORT_FILE="/tmp/images.tar.gz"

# ---- 服务器配置 ----
# External（用户端）—— 密码登录
EXTERNAL_SERVER="47.114.118.52"
EXTERNAL_SSH_USER="root"
EXTERNAL_SSH_OPTS=""
EXTERNAL_REMOTE_DIR="/root/workspace"

# Internal（管理端）—— SSH Key 登录
INTERNAL_SERVER="116.62.88.121"
INTERNAL_SSH_USER="root"
INTERNAL_SSH_KEY="$HOME/Downloads/ssh.pem"
INTERNAL_SSH_OPTS="-i ${INTERNAL_SSH_KEY}"
INTERNAL_REMOTE_DIR="/root/workspace"

# 服务器上 docker-compose.yml 所在目录
REMOTE_PROJECT_DIR="/root/service/anti_pro/cursor_sh"

# ============================================================
#  构建镜像
# ============================================================
build_frontend() {
    cd "$PROJECT_DIR"
    info "构建前端镜像..."
    
    # 提取 .env 变量供 Dockerfile 使用
    local BUILD_ARGS=""
    if [ -f ".env" ]; then
        info "加载 .env 配置..."
        while IFS='=' read -r key value || [ -n "$key" ]; do
            # 忽略空行和注释
            if [[ ! -z "$key" && "$key" != \#* ]]; then
                BUILD_ARGS="$BUILD_ARGS --build-arg ${key}=${value}"
            fi
        done < ".env"
    fi
    
    START=$(date +%s)
    docker build $BUILD_ARGS -t "$FRONTEND_IMAGE" -f Dockerfile .
    END=$(date +%s)
    info "前端构建完成！耗时 $((END - START)) 秒"
}

build_backend() {
    cd "$PROJECT_DIR"
    info "构建后端镜像..."
    START=$(date +%s)
    docker build -t "$BACKEND_IMAGE" -f backend/Dockerfile backend/
    END=$(date +%s)
    info "后端构建完成！耗时 $((END - START)) 秒"
}

export_images() {
    local images="$1"
    title "📦 导出镜像"
    info "正在打包镜像到 $EXPORT_FILE ..."
    docker save $images | gzip > "$EXPORT_FILE"
    FILE_SIZE=$(du -h "$EXPORT_FILE" | cut -f1)
    info "镜像导出完成！文件大小: $FILE_SIZE"
}

do_build() {
    title "🔨 开始本地构建 Docker 镜像"

    # 检查 Docker 是否可用
    if ! command -v docker &> /dev/null; then
        err "Docker 未安装！请先安装 Docker Desktop 或 Colima"
    fi
    if ! docker info &> /dev/null 2>&1; then
        err "Docker 未启动！请先打开 Docker Desktop 或执行 colima start"
    fi

    build_frontend
    build_backend
    export_images "$FRONTEND_IMAGE $BACKEND_IMAGE"
}

do_build_frontend_only() {
    title "🔨 仅构建前端镜像"

    if ! command -v docker &> /dev/null; then
        err "Docker 未安装！"
    fi
    if ! docker info &> /dev/null 2>&1; then
        err "Docker 未启动！"
    fi

    build_frontend
    export_images "$FRONTEND_IMAGE"
}

# ============================================================
#  部署到服务器
# ============================================================
deploy_to_server() {
    local SERVER_IP="$1"
    local SERVER_NAME="$2"
    local SSH_USER="$3"
    local SSH_OPTS="$4"
    local REMOTE_DIR="$5"

    if [ -z "$SERVER_IP" ]; then
        warn "跳过 ${SERVER_NAME}（未配置 IP）"
        return
    fi

    title "🚀 部署到 ${SERVER_NAME} (${SERVER_IP})"

    # 检查导出文件
    if [ ! -f "$EXPORT_FILE" ]; then
        err "镜像文件不存在: $EXPORT_FILE，请先执行 build"
    fi

    # 上传镜像
    info "正在上传镜像到 ${SERVER_IP}:${REMOTE_DIR}/ ..."
    scp $SSH_OPTS "$EXPORT_FILE" "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR}/images.tar.gz"
    info "上传完成！"

    # 远程导入并重启
    info "正在远程导入镜像并重启服务..."
    ssh $SSH_OPTS "${SSH_USER}@${SERVER_IP}" bash -s <<REMOTE_SCRIPT
        set -e
        echo ">>> 导入镜像..."
        docker load < ${REMOTE_DIR}/images.tar.gz
        echo ">>> 停止并清除旧容器..."
        cd ${REMOTE_PROJECT_DIR}
        docker compose down --remove-orphans 2>/dev/null || true
        # 强制清除可能残留的同名容器（防止 name conflict）
        docker rm -f anti-pro-backend anti-pro-frontend 2>/dev/null || true
        echo ">>> 启动新容器..."
        docker compose up -d
        echo ">>> 清理临时文件和悬空镜像..."
        rm -f ${REMOTE_DIR}/images.tar.gz
        docker image prune -f
        echo ">>> 部署完成！当前容器状态："
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
REMOTE_SCRIPT

    info "${SERVER_NAME} 部署成功！"
}

do_deploy() {
    deploy_to_server "$EXTERNAL_SERVER" "External（用户端）" "$EXTERNAL_SSH_USER" "$EXTERNAL_SSH_OPTS" "$EXTERNAL_REMOTE_DIR"
    deploy_to_server "$INTERNAL_SERVER" "Internal（管理端）" "$INTERNAL_SSH_USER" "$INTERNAL_SSH_OPTS" "$INTERNAL_REMOTE_DIR"
}

# ============================================================
#  主流程
# ============================================================
CMD="${1:-all}"

case "$CMD" in
    build)
        do_build
        ;;
    deploy)
        do_deploy
        ;;
    frontend)
        do_build_frontend_only
        do_deploy
        ;;
    all|"")
        do_build
        do_deploy
        ;;
    *)
        echo "用法: bash scripts/local_build.sh [build|deploy|frontend|all]"
        echo ""
        echo "  all       - 构建前后端 + 部署到所有服务器（默认）"
        echo "  build     - 仅构建镜像，不上传"
        echo "  deploy    - 仅部署已构建的镜像"
        echo "  frontend  - 仅构建前端 + 部署（适合只改了 nginx/前端代码）"
        exit 1
        ;;
esac

echo ""
title "🎉 全部完成！"
echo ""
info "External（用户端）: http://${EXTERNAL_SERVER}"
info "Internal（管理端）: http://${INTERNAL_SERVER}"
echo ""
