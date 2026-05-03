# 阶段1：构建（slim 比 alpine 快 3-5 倍，因为 esbuild 原生支持 glibc）
FROM node:20-slim AS builder

WORKDIR /app
COPY package.json package-lock.json ./

# 使用淘宝镜像 + 挂载缓存，依赖包只需下载一次
RUN --mount=type=cache,target=/root/.npm \
    npm ci --legacy-peer-deps --registry=https://registry.npmmirror.com

COPY . .

# 构建时注入环境变量
ARG VITE_API_BASE_URL=/api
ARG VITE_ENABLE_VOICE_INPUT=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_ENABLE_VOICE_INPUT=$VITE_ENABLE_VOICE_INPUT

# 挂载 Vite 编译缓存，增量构建飞快
RUN --mount=type=cache,target=/app/node_modules/.vite \
    npm run build

# 阶段2：仅保留产物，不含 node_modules（镜像从 ~1GB 缩到 ~30MB）
FROM nginx:alpine

# 自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080
