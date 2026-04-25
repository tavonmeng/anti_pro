# 阶段1：构建
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .

# 构建时注入环境变量
ARG VITE_API_BASE_URL=/api
ARG VITE_ENABLE_VOICE_INPUT=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_ENABLE_VOICE_INPUT=$VITE_ENABLE_VOICE_INPUT

RUN npm run build

# 阶段2：仅保留产物，不含 node_modules（镜像从 ~1GB 缩到 ~30MB）
FROM nginx:alpine

# 自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080
