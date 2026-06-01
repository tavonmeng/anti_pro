#!/bin/bash
# ============================================================
#  服务器构建 & 部署脚本
#  从 Mac 同步代码到阿里云 ECS，然后在服务器上构建 Docker 镜像并重启服务
#
#  用法：
#    bash scripts/local_build.sh              # 同步代码 + 在所有服务器构建并重启前后端
#    bash scripts/local_build.sh deploy       # 同上
#    bash scripts/local_build.sh frontend     # 仅同步代码 + 在所有服务器构建并重启前端
#    bash scripts/local_build.sh backend      # 仅同步代码 + 在所有服务器构建并重启后端
#    bash scripts/local_build.sh build        # 仅在所有服务器构建，不重启
#    bash scripts/local_build.sh status       # 查看所有服务器容器状态
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

# cursor_sh 目录（自动检测脚本所在位置的上一级）
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"

# ---- 服务器配置 ----
# External（用户端）—— 密码登录
EXTERNAL_SERVER="8.141.111.94"
EXTERNAL_SSH_USER="root"
EXTERNAL_SSH_OPTS=""
EXTERNAL_DEPLOYMENT_MODE="external"
EXTERNAL_BACKEND_ENV_FILE="./cursor_sh/backend/.env.external"

# Internal（管理端）—— 密码登录
INTERNAL_SERVER="101.201.58.68"
INTERNAL_SSH_USER="root"
INTERNAL_SSH_OPTS=""
INTERNAL_DEPLOYMENT_MODE="internal"
INTERNAL_BACKEND_ENV_FILE="./cursor_sh/backend/.env.internal"

# 服务器上 docker-compose.yml 所在目录
REMOTE_PROJECT_DIR="/root/service/anti_pro"

sync_code_to_server() {
    local SERVER_IP="$1"
    local SERVER_NAME="$2"
    local SSH_USER="$3"
    local SSH_OPTS="$4"

    if [ -z "$SERVER_IP" ]; then
        warn "跳过 ${SERVER_NAME}（未配置 IP）"
        return
    fi

    title "同步代码到 ${SERVER_NAME} (${SERVER_IP})"
    local SSH_RSH="ssh"
    if [ -n "$SSH_OPTS" ]; then
        SSH_RSH="ssh $SSH_OPTS"
    fi
    rsync -az --delete \
        -e "$SSH_RSH" \
        --exclude ".git/" \
        --exclude ".DS_Store" \
        --exclude "node_modules/" \
        --exclude "dist/" \
        --exclude ".vite/" \
        --exclude "backend/.env*" \
        --exclude "backend/app.db" \
        --exclude "backend/audit.db" \
        --exclude "backend/logs/" \
        --exclude "backend/uploads/" \
        "$PROJECT_DIR/" "${SSH_USER}@${SERVER_IP}:${REMOTE_PROJECT_DIR}/cursor_sh/"

    if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
        rsync -az -e "$SSH_RSH" "$ROOT_DIR/docker-compose.yml" "${SSH_USER}@${SERVER_IP}:${REMOTE_PROJECT_DIR}/docker-compose.yml"
    fi
}

remote_compose() {
    local SERVER_IP="$1"
    local SERVER_NAME="$2"
    local SSH_USER="$3"
    local SSH_OPTS="$4"
    local DEPLOYMENT_MODE="$5"
    local BACKEND_ENV_FILE="$6"
    local ACTION="$7"
    shift 7
    local SERVICES="$*"

    if [ -z "$SERVER_IP" ]; then
        return
    fi

    title "${SERVER_NAME} (${SERVER_IP}) ${ACTION}: ${SERVICES:-all services}"
    ssh $SSH_OPTS "${SSH_USER}@${SERVER_IP}" bash -s -- "$REMOTE_PROJECT_DIR" "$DEPLOYMENT_MODE" "$BACKEND_ENV_FILE" "$ACTION" "$SERVICES" <<'REMOTE_SCRIPT'
        set -e
        REMOTE_PROJECT_DIR="$1"
        DEPLOYMENT_MODE="$2"
        BACKEND_ENV_FILE="$3"
        ACTION="$4"
        SERVICES="$5"

        cd "$REMOTE_PROJECT_DIR"
        export DEPLOYMENT_MODE
        export BACKEND_ENV_FILE

        if [ "$ACTION" = "build" ]; then
            echo ">>> docker compose build ${SERVICES}"
            docker compose build ${SERVICES}
        elif [ "$ACTION" = "up" ]; then
            echo ">>> docker compose up -d --build ${SERVICES}"
            docker compose up -d --build ${SERVICES}
        elif [ "$ACTION" = "status" ]; then
            true
        else
            echo "未知动作: $ACTION"
            exit 1
        fi

        echo ">>> 当前容器状态："
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
REMOTE_SCRIPT
}

deploy_to_server() {
    local SERVER_IP="$1"
    local SERVER_NAME="$2"
    local SSH_USER="$3"
    local SSH_OPTS="$4"
    local DEPLOYMENT_MODE="$5"
    local BACKEND_ENV_FILE="$6"
    local ACTION="$7"
    shift 7
    local SERVICES="$*"

    sync_code_to_server "$SERVER_IP" "$SERVER_NAME" "$SSH_USER" "$SSH_OPTS"
    remote_compose "$SERVER_IP" "$SERVER_NAME" "$SSH_USER" "$SSH_OPTS" "$DEPLOYMENT_MODE" "$BACKEND_ENV_FILE" "$ACTION" $SERVICES
    info "${SERVER_NAME} 完成！"
}

run_all_servers() {
    local ACTION="$1"
    shift
    local SERVICES="$*"
    deploy_to_server "$EXTERNAL_SERVER" "External（用户端）" "$EXTERNAL_SSH_USER" "$EXTERNAL_SSH_OPTS" "$EXTERNAL_DEPLOYMENT_MODE" "$EXTERNAL_BACKEND_ENV_FILE" "$ACTION" $SERVICES
    deploy_to_server "$INTERNAL_SERVER" "Internal（管理端）" "$INTERNAL_SSH_USER" "$INTERNAL_SSH_OPTS" "$INTERNAL_DEPLOYMENT_MODE" "$INTERNAL_BACKEND_ENV_FILE" "$ACTION" $SERVICES
}

show_status() {
    remote_compose "$EXTERNAL_SERVER" "External（用户端）" "$EXTERNAL_SSH_USER" "$EXTERNAL_SSH_OPTS" "$EXTERNAL_DEPLOYMENT_MODE" "$EXTERNAL_BACKEND_ENV_FILE" "status"
    remote_compose "$INTERNAL_SERVER" "Internal（管理端）" "$INTERNAL_SSH_USER" "$INTERNAL_SSH_OPTS" "$INTERNAL_DEPLOYMENT_MODE" "$INTERNAL_BACKEND_ENV_FILE" "status"
}

# ============================================================
#  主流程
# ============================================================
CMD="${1:-all}"

case "$CMD" in
    build)
        run_all_servers build backend frontend
        ;;
    deploy|all|"")
        run_all_servers up backend frontend
        ;;
    frontend)
        run_all_servers up frontend
        ;;
    backend)
        run_all_servers up backend
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: bash scripts/local_build.sh [deploy|build|frontend|backend|status|all]"
        echo ""
        echo "  all/deploy - 同步代码 + 在所有服务器构建并重启前后端（默认）"
        echo "  build      - 同步代码 + 仅在所有服务器构建，不重启"
        echo "  frontend   - 同步代码 + 仅构建并重启前端"
        echo "  backend    - 同步代码 + 仅构建并重启后端"
        echo "  status     - 查看所有服务器容器状态"
        exit 1
        ;;
esac

echo ""
title "🎉 全部完成！"
echo ""
info "External（用户端）: ${EXTERNAL_SERVER}"
info "Internal（管理端）: ${INTERNAL_SERVER}"
echo ""
