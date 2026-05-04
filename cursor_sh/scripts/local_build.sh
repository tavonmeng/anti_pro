#!/bin/bash
# ============================================================
#  本地构建 & 部署脚本
#  在 Mac 上构建 Docker 镜像，导出并上传到阿里云 ECS
#
#  用法：
#    bash local_build.sh              # 构建 + 上传到所有服务器
#    bash local_build.sh build        # 仅构建，不上传
#    bash local_build.sh deploy       # 仅上传已构建的镜像
# ============================================================

set -e

# ---- 颜色 ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓] $*${NC}"; }
warn()  { echo -e "${YELLOW}[!] $*${NC}"; }
err()   { echo -e "${RED}[✗] $*${NC}"; exit 1; }
title() { echo -e "\n${CYAN}════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}════════════════════════════════════════${NC}"; }

# ============================================================
#  配置区（根据你的实际情况修改）
# ============================================================

# 项目根目录（自动检测脚本所在位置）
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 镜像名称
FRONTEND_IMAGE="anti_pro-frontend"
BACKEND_IMAGE="anti_pro-backend"

# 导出文件路径
EXPORT_FILE="/tmp/anti_pro_images.tar.gz"

# 服务器列表（IP 地址，用空格分隔）
# ⚠️ 请替换为你的真实服务器 IP
INTERNAL_SERVER="116.62.88.121"
EXTERNAL_SERVER=""  # 填入 external 服务器的 IP

# 服务器上的项目路径（docker-compose.yml 所在目录）
REMOTE_PROJECT_DIR="/root/service/anti_pro/cursor_sh"

# SSH 用户
SSH_USER="root"

# ============================================================
#  构建镜像
# ============================================================
do_build() {
    title "🔨 开始本地构建 Docker 镜像"

    # 检查 Docker 是否可用
    if ! command -v docker &> /dev/null; then
        err "Docker 未安装！请先安装 Docker Desktop 或 Colima"
    fi

    if ! docker info &> /dev/null; then
        err "Docker 未启动！请先打开 Docker Desktop 或执行 colima start"
    fi

    cd "$PROJECT_DIR"

    # 构建前端
    info "构建前端镜像..."
    START=$(date +%s)
    docker build -t "$FRONTEND_IMAGE" -f Dockerfile .
    END=$(date +%s)
    info "前端构建完成！耗时 $((END - START)) 秒"

    # 构建后端
    info "构建后端镜像..."
    START=$(date +%s)
    docker build -t "$BACKEND_IMAGE" -f backend/Dockerfile backend/
    END=$(date +%s)
    info "后端构建完成！耗时 $((END - START)) 秒"

    # 导出镜像
    title "📦 导出镜像"
    info "正在打包镜像到 $EXPORT_FILE ..."
    docker save "$FRONTEND_IMAGE" "$BACKEND_IMAGE" | gzip > "$EXPORT_FILE"
    FILE_SIZE=$(du -h "$EXPORT_FILE" | cut -f1)
    info "镜像导出完成！文件大小: $FILE_SIZE"
}

# ============================================================
#  部署到服务器
# ============================================================
deploy_to_server() {
    local SERVER_IP="$1"
    local SERVER_NAME="$2"

    if [ -z "$SERVER_IP" ]; then
        warn "跳过 ${SERVER_NAME}（未配置 IP）"
        return
    fi

    title "🚀 部署到 ${SERVER_NAME} (${SERVER_IP})"

    # 检查导出文件是否存在
    if [ ! -f "$EXPORT_FILE" ]; then
        err "镜像文件不存在: $EXPORT_FILE，请先执行 build"
    fi

    # 上传镜像
    info "正在上传镜像到 ${SERVER_IP}..."
    scp "$EXPORT_FILE" "${SSH_USER}@${SERVER_IP}:/tmp/images.tar.gz"
    info "上传完成！"

    # 远程导入并重启
    info "正在远程导入镜像并重启服务..."
    ssh "${SSH_USER}@${SERVER_IP}" bash -s <<REMOTE_SCRIPT
        set -e
        echo ">>> 导入镜像..."
        docker load < /tmp/images.tar.gz
        echo ">>> 重启服务..."
        cd ${REMOTE_PROJECT_DIR}
        docker compose up -d
        echo ">>> 清理临时文件..."
        rm -f /tmp/images.tar.gz
        echo ">>> 部署完成！"
        docker ps
REMOTE_SCRIPT

    info "${SERVER_NAME} 部署成功！"
}

do_deploy() {
    deploy_to_server "$INTERNAL_SERVER" "Internal（管理员端）"
    deploy_to_server "$EXTERNAL_SERVER" "External（客户端）"
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
    all|"")
        do_build
        do_deploy
        ;;
    *)
        echo "用法: bash local_build.sh [build|deploy|all]"
        echo "  build   - 仅构建镜像"
        echo "  deploy  - 仅部署到服务器"
        echo "  all     - 构建 + 部署（默认）"
        exit 1
        ;;
esac

echo ""
title "🎉 全部完成！"
echo ""
info "Internal: http://${INTERNAL_SERVER}"
[ -n "$EXTERNAL_SERVER" ] && info "External: http://${EXTERNAL_SERVER}"
echo ""
