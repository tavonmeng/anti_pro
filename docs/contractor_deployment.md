# 承包商角色系统 — 部署文档

> 版本: v1.0 · 最后更新: 2026-04-27

---

## 1. 环境要求

### 1.1 服务器配置

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| **操作系统** | CentOS 7+ / Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **CPU** | 2 核 | 4 核 |
| **内存** | 2 GB | 4 GB |
| **磁盘** | 40 GB SSD | 100 GB SSD (交付物存储) |
| **带宽** | 1 Mbps | 5 Mbps (视频文件传输) |

### 1.2 软件依赖

| 软件 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.9+ | 后端运行环境 |
| **Node.js** | 20+ | 前端构建 |
| **Nginx** | 1.18+ | 反向代理 + 静态文件 |
| **MySQL** | 5.7+ / 8.0 | 数据库 (可使用阿里云 RDS) |

> [!NOTE]
> 开发阶段可使用 SQLite 替代 MySQL，无需额外安装数据库服务。

---

## 2. 部署模式

系统支持三种部署模式，通过 `.env` 中的 `DEPLOYMENT_MODE` 控制：

### 2.1 模式对比

| 模式 | 值 | 说明 | 适用场景 |
|------|-----|------|---------|
| **全量** | `all` | 所有路由统一加载 | 本地开发、测试 |
| **用户端** | `external` | 仅加载用户相关路由 | 面向客户的生产服务器 |
| **内部系统** | `internal` | 仅加载管理/承包商路由 | 内部团队服务器 |

### 2.2 推荐拓扑

#### 方案 A：单机部署 (开发/测试)

```
[单台服务器]
├── Nginx :80
├── FastAPI (DEPLOYMENT_MODE=all) :8000
├── Vue SPA (dist/)
└── SQLite / 本地 MySQL
```

#### 方案 B：双机部署 (生产推荐)

```
[服务器 A - 用户端]                [服务器 B - 内部系统]
├── Nginx :80                      ├── Nginx :80
├── FastAPI (external) :8000       ├── FastAPI (internal) :8000
├── Vue SPA (dist/)                ├── Vue SPA (dist/)
└──────────┬───────────────────────└──────────┬────────
           └──────── 阿里云 RDS MySQL ────────┘
```

> [!IMPORTANT]
> 双机部署时两台服务器的 `.env` 需使用相同的 RDS 连接信息和 `JWT_SECRET_KEY`。

---

## 3. 环境变量参考

### 3.1 `.env` 完整配置项

```bash
# ===== 基础配置 =====
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8000
DEBUG=false
JWT_SECRET_KEY=<32位随机Hex>         # 重要：双机部署必须一致

# ===== 数据库 =====
DB_TYPE=mysql                        # sqlite 或 mysql
DB_HOST=rm-xxx.mysql.rds.aliyuncs.com
DB_PORT=3306
DB_NAME=anti_pro_db
DB_USER=admin
DB_PASSWORD=<密码>
AUDIT_DATABASE_URL=sqlite+aiosqlite:///./audit.db

# ===== CORS =====
CORS_ORIGINS=["https://your-domain.com","http://your-ip"]

# ===== 管理员账户 (首次启动自动创建) =====
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=<安全密码>
INIT_ADMIN_PHONE=138xxxxxxxx

# ===== AI 模型 =====
AI_API_KEY=<阿里云百炼 API Key>
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL_NAME=qwen-max

# ===== 短信验证码 =====
SMS_ENABLED=true
SMS_ACCESS_KEY_ID=<阿里云 AccessKey>
SMS_ACCESS_KEY_SECRET=<阿里云 Secret>
SMS_SIGN_NAME=<签名>
SMS_TEMPLATE_CODE=<模板CODE>

# ===== 部署模式 =====
DEPLOYMENT_MODE=all                  # all / external / internal

# ===== 承包商配置 =====
CONTRACTOR_BASE_URL=http://your-internal-ip  # 邀请链接使用的基础URL

# ===== 邮件 (可选) =====
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=<邮箱>
SMTP_PASSWORD=<授权码>
SMTP_FROM=<发送地址>

# ===== 阿里云 OSS (预留，默认关闭) =====
OSS_ENABLED=false

# ===== 日志 =====
LOG_ENABLED=true
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

### 3.2 关键配置说明

| 变量 | 重要性 | 说明 |
|------|:------:|------|
| `JWT_SECRET_KEY` | 🔴 关键 | 双机部署必须相同，否则 Token 互不认 |
| `DEPLOYMENT_MODE` | 🔴 关键 | 决定加载哪些 API 路由 |
| `CONTRACTOR_BASE_URL` | 🟡 重要 | 邀请链接的域名/IP，承包商点击后访问的地址 |
| `DB_TYPE` | 🟡 重要 | `sqlite` (开发) 或 `mysql` (生产) |
| `SMS_ENABLED` | 🟡 重要 | 关闭后承包商无法通过 SMS 注册/登录 |

---

## 4. 部署步骤

### 4.1 一键部署 (推荐)

```bash
# 克隆项目
git clone <repo-url> /opt/anti_pro
cd /opt/anti_pro

# 执行一键部署脚本
sudo bash scripts/deploy_system.sh
```

脚本将自动完成：
1. ✅ 安装 Node.js、Nginx、Python 等系统依赖
2. ✅ 交互式生成 `.env` 环境配置
3. ✅ 创建 Python 虚拟环境并安装依赖
4. ✅ 注册 Systemd 服务并启动后端
5. ✅ 构建 Vue 前端并部署到 Nginx
6. ✅ 配置 Nginx 反向代理
7. ✅ 配置防火墙规则

### 4.2 手动部署

#### Step 1: 配置环境变量

```bash
cp cursor_sh/backend/.env.example cursor_sh/backend/.env
vim cursor_sh/backend/.env
# 按照第 3 节配置所有变量
```

#### Step 2: 后端部署

```bash
cd cursor_sh/backend

# 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn uvicorn

# 创建必要目录
mkdir -p logs uploads

# 启动（测试）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 生产启动（Gunicorn + 4 workers）
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8000 \
  --timeout 120
```

#### Step 3: 前端构建

```bash
cd cursor_sh

# 配置生产环境变量
echo "VITE_API_BASE_URL=/api" > .env.production
echo "VITE_ENABLE_VOICE_INPUT=false" >> .env.production

# 安装依赖并构建
npm install --legacy-peer-deps
npm run build

# 复制到 Nginx 目录
sudo cp -r dist/* /var/www/unique-vision/
```

#### Step 4: 配置 Nginx

```nginx
# /etc/nginx/conf.d/unique-vision.conf
server {
    listen 80;
    server_name _;
    root /var/www/unique-vision;
    index index.html;

    client_max_body_size 50m;    # 交付物文件上传

    # Vue Router SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        client_max_body_size 50m;
    }

    # AI 聊天 SSE 流式
    location /ai/ {
        proxy_pass http://127.0.0.1:8000/ai/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 上传文件
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
    }

    # 静态资源长缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|mp4|webm)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    gzip on;
    gzip_types text/plain text/css text/javascript application/javascript application/json;
}
```

```bash
# 检查配置并重启
sudo nginx -t && sudo systemctl restart nginx
```

#### Step 5: 配置 Systemd 服务

```ini
# /etc/systemd/system/order-api.service
[Unit]
Description=AI Design Platform Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/anti_pro/cursor_sh/backend
Environment="PATH=/opt/anti_pro/cursor_sh/backend/venv/bin"
ExecStart=/opt/anti_pro/cursor_sh/backend/venv/bin/gunicorn app.main:app -c gunicorn_config.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable order-api
sudo systemctl start order-api
```

---

## 5. 首次启动后自动执行

应用首次启动时会自动完成以下初始化（幂等，重复启动不会重复执行）：

| 操作 | 说明 |
|------|------|
| **建表** | 所有 SQLAlchemy 模型自动 `CREATE TABLE IF NOT EXISTS` |
| **管理员账户** | 根据 `INIT_ADMIN_*` 配置创建初始管理员 |
| **工作流配置** | 写入默认 5 个环节 (方案/原画/模型/渲染/成片) |
| **目录创建** | 自动创建 `uploads/` 和 `logs/` 目录 |

> [!NOTE]
> 如果使用 MySQL RDS，请确保数据库已创建且用户有 `CREATE TABLE` 权限：
> ```sql
> CREATE DATABASE anti_pro_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> GRANT ALL PRIVILEGES ON anti_pro_db.* TO 'your_user'@'%';
> ```

---

## 6. 双机部署补充

### 6.1 服务器 A — 用户端

```bash
# .env 关键配置
DEPLOYMENT_MODE=external
DB_TYPE=mysql
DB_HOST=rm-xxx.mysql.rds.aliyuncs.com
JWT_SECRET_KEY=<和服务器B相同>
```

### 6.2 服务器 B — 内部系统

```bash
# .env 关键配置
DEPLOYMENT_MODE=internal
DB_TYPE=mysql
DB_HOST=rm-xxx.mysql.rds.aliyuncs.com
JWT_SECRET_KEY=<和服务器A相同>
CONTRACTOR_BASE_URL=http://<服务器B公网IP>
```

### 6.3 安全组规则

| 服务器 | 入站端口 | 来源 |
|--------|---------|------|
| 服务器 A (用户端) | 80, 443 | 0.0.0.0/0 |
| 服务器 B (内部系统) | 80, 443 | 公司 IP / VPN |
| RDS | 3306 | 服务器 A + B 的内网 IP |

> [!WARNING]
> 内部系统建议限制访问来源 IP，避免承包商管理页面暴露到公网。可通过安全组或 Nginx `allow/deny` 实现。

---

## 7. 常用运维命令

### 7.1 服务管理

```bash
# 查看服务状态
sudo systemctl status order-api

# 重启服务
sudo bash scripts/deploy_system.sh restart

# 停止服务
sudo bash scripts/deploy_system.sh stop

# 查看实时日志
journalctl -fu order-api
```

### 7.2 数据库操作

```bash
# 进入后端虚拟环境
cd /opt/anti_pro/cursor_sh/backend
source venv/bin/activate

# 检查数据库连接
python -c "
from app.config import settings
print(f'DB Type: {settings.DB_TYPE}')
print(f'DB URL: {settings.database_url[:50]}...')
"

# 手动初始化工作流
python -c "
import asyncio
from app.database import async_session_maker
from scripts.init_workflow import ensure_workflow_stages
async def main():
    async with async_session_maker() as db:
        await ensure_workflow_stages(db)
asyncio.run(main())
"
```

### 7.3 日志查看

```bash
# 后端应用日志
tail -f /opt/anti_pro/cursor_sh/backend/logs/system/*.log

# Nginx 访问日志
tail -f /var/log/nginx/access.log

# Nginx 错误日志
tail -f /var/log/nginx/error.log
```

### 7.4 前端重建

```bash
cd /opt/anti_pro/cursor_sh
npm run build
sudo cp -r dist/* /var/www/unique-vision/
```

### 7.5 数据备份

```bash
# MySQL 备份
mysqldump -h <RDS地址> -u <用户> -p anti_pro_db > backup_$(date +%Y%m%d).sql

# SQLite 备份
cp /opt/anti_pro/cursor_sh/backend/app.db backup_$(date +%Y%m%d).db

# 上传文件备份
tar czf uploads_$(date +%Y%m%d).tar.gz /opt/anti_pro/cursor_sh/backend/uploads/
```

---

## 8. SSL 证书配置

```bash
# 使用 Let's Encrypt 自动申请
sudo bash scripts/deploy_system.sh ssl

# 或手动执行
sudo certbot --nginx -d your-domain.com --agree-tos --email admin@domain.com
```

> [!IMPORTANT]
> 语音录入功能 (ASR) 依赖 WebSocket，必须通过 HTTPS 访问才能使用麦克风。

---

## 9. 故障排查

### 9.1 检查清单

| 问题 | 检查方法 |
|------|---------|
| 后端无法启动 | `journalctl -xeu order-api --no-pager -n 30` |
| 502 Bad Gateway | 确认后端 :8000 已启动：`curl http://127.0.0.1:8000/health` |
| 数据库连接失败 | 检查 RDS 安全组是否放行服务器 IP |
| 承包商无法注册 | 检查 `DEPLOYMENT_MODE` 是否为 `internal` 或 `all` |
| 邀请链接打不开 | 检查 `CONTRACTOR_BASE_URL` 是否正确指向内部系统 |
| 文件上传 413 | Nginx `client_max_body_size` 需 ≥ 50m |
| 短信发送失败 | 检查 `SMS_ENABLED=true` 且阿里云 AccessKey 正确 |
| 双机 Token 不通 | 确认两台 `.env` 中 `JWT_SECRET_KEY` 完全一致 |

### 9.2 健康检查

```bash
# 后端健康检查
curl -s http://127.0.0.1:8000/health
# 期望输出: {"status":"ok","app":"..."}

# API 文档（仅限内网）
curl -s http://127.0.0.1:8000/docs
```

---

## 10. 版本升级

```bash
# 1. 拉取最新代码
cd /opt/anti_pro
git pull

# 2. 后端依赖更新
cd cursor_sh/backend
source venv/bin/activate
pip install -r requirements.txt

# 3. 前端重建
cd ../
npm install --legacy-peer-deps
npm run build
sudo cp -r dist/* /var/www/unique-vision/

# 4. 重启服务（数据库会自动迁移新表）
sudo bash scripts/deploy_system.sh restart
```

> [!CAUTION]
> 升级前请务必做好数据库备份。含结构变更的升级可能需要手动 `ALTER TABLE`。
