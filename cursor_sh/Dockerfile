# 阶段1：构建（slim 比 alpine 快 3-5 倍，因为 esbuild 原生支持 glibc）
FROM node:20-slim AS builder

WORKDIR /app
COPY package.json package-lock.json ./

# 优先使用国内镜像；网络抖动或镜像异常时回退到官方 registry
RUN --mount=type=cache,target=/root/.npm \
    npm ci --legacy-peer-deps --registry=https://registry.npmmirror.com --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000 \
    || npm ci --legacy-peer-deps --registry=https://registry.npmjs.org --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000

COPY . .

# 构建时注入环境变量
ARG VITE_API_BASE_URL=/api
ARG VITE_ENABLE_VOICE_INPUT=false
ARG VITE_AGENT_MODE=media
ARG VITE_DEPLOYMENT_MODE=all
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_ENABLE_VOICE_INPUT=$VITE_ENABLE_VOICE_INPUT
ENV VITE_AGENT_MODE=$VITE_AGENT_MODE
ENV VITE_DEPLOYMENT_MODE=$VITE_DEPLOYMENT_MODE

# 挂载 Vite 编译缓存，增量构建飞快
RUN --mount=type=cache,target=/app/node_modules/.vite \
    npm run build

# 阶段2：仅保留产物，不含 node_modules（镜像从 ~1GB 缩到 ~30MB）
FROM nginx:alpine

# 复制 Nginx 配置到暂存目录（启动时由 entrypoint 选择一个复制到 conf.d）
COPY nginx.internal.conf /etc/nginx/templates/nginx.internal.conf
COPY nginx.external.conf /etc/nginx/templates/nginx.external.conf

# 自定义启动脚本（根据环境变量选择配置）
COPY docker-entrypoint-custom.sh /docker-entrypoint-custom.sh
RUN chmod +x /docker-entrypoint-custom.sh

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080
ENTRYPOINT ["/docker-entrypoint-custom.sh"]
CMD ["nginx", "-g", "daemon off;"]
