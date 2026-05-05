#!/bin/sh
# 根据 DEPLOYMENT_MODE 环境变量选择对应的 Nginx 配置文件
# 配置模板在 /etc/nginx/templates/，仅将选中的复制到 conf.d/

MODE="${DEPLOYMENT_MODE:-all}"

# 清除 conf.d 中可能残留的配置
rm -f /etc/nginx/conf.d/*.conf

case "$MODE" in
    internal)
        echo ">>> 使用 Internal 模式 Nginx 配置"
        cp /etc/nginx/templates/nginx.internal.conf /etc/nginx/conf.d/default.conf
        ;;
    external)
        echo ">>> 使用 External 模式 Nginx 配置"
        cp /etc/nginx/templates/nginx.external.conf /etc/nginx/conf.d/default.conf
        ;;
    *)
        echo ">>> 使用默认（All）模式 Nginx 配置"
        cp /etc/nginx/templates/nginx.internal.conf /etc/nginx/conf.d/default.conf
        ;;
esac

# 继续执行 Nginx 官方的启动流程
exec /docker-entrypoint.sh "$@"
