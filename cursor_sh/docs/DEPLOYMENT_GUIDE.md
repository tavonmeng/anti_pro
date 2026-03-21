# AI设计任务管理系统 - 部署指南

## 📋 目录

- [一、开发环境搭建](#一开发环境搭建)
- [二、本地测试](#二本地测试)
- [三、生产环境部署](#三生产环境部署)
- [四、运维指南](#四运维指南)
- [五、故障排查](#五故障排查)

---

## 一、开发环境搭建

### 1.1 系统要求

#### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 双核 2.0GHz | 四核 2.5GHz+ |
| 内存 | 4GB | 8GB+ |
| 硬盘 | 10GB 可用空间 | 20GB+ SSD |
| 网络 | 宽带连接 | - |

#### 操作系统

- ✅ **macOS** 10.15+
- ✅ **Linux** Ubuntu 20.04+, CentOS 7+
- ✅ **Windows** 10/11 (WSL2 推荐)

### 1.2 环境准备

#### 前端环境

**1. 安装 Node.js**

```bash
# macOS (使用 Homebrew)
brew install node

# Linux (Ubuntu)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证安装
node --version  # 应显示 v18.x 或更高
npm --version   # 应显示 9.x 或更高
```

**2. 安装项目依赖**

```bash
cd /Users/hongtaomeng/cursor_sh

# 安装依赖
npm install

# 或使用 yarn
yarn install

# 或使用 pnpm（更快）
pnpm install
```

#### 后端环境

**1. 安装 Python**

```bash
# macOS (使用 Homebrew)
brew install python@3.11

# Linux (Ubuntu)
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# 验证安装
python3 --version  # 应显示 3.11.x
pip3 --version
```

**2. 创建虚拟环境**

```bash
cd /Users/hongtaomeng/cursor_sh/backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows (WSL2):
source venv/bin/activate

# Windows (PowerShell):
# .\venv\Scripts\Activate.ps1
```

**3. 安装依赖**

```bash
# 确保虚拟环境已激活
pip install -r requirements.txt

# 验证安装
pip list | grep fastapi  # 应显示 fastapi 0.104.x
```

### 1.3 配置文件

#### 前端配置

编辑 `vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

#### 后端配置

```bash
cd /Users/hongtaomeng/cursor_sh/backend

# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用你喜欢的编辑器
```

**必需配置项：**

```env
# 应用基础配置
APP_NAME=AI设计任务管理系统
DEBUG=True

# JWT 密钥（必须修改！）
JWT_SECRET_KEY=your-random-secret-key-here-change-in-production

# 数据库（开发环境使用 SQLite）
DATABASE_URL=sqlite+aiosqlite:///./app.db

# CORS（前端地址）
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# 邮件配置（QQ邮箱）
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-qq-email@qq.com
SMTP_PASSWORD=your-qq-smtp-auth-code  # 授权码，不是密码！
SMTP_FROM=your-qq-email@qq.com
```

**QQ 邮箱授权码获取：**
1. 登录 QQ 邮箱 (mail.qq.com)
2. 设置 → 账户
3. 开启 SMTP 服务
4. 生成授权码（16位）
5. 将授权码填入 `SMTP_PASSWORD`

### 1.4 初始化数据库

```bash
cd /Users/hongtaomeng/cursor_sh/backend

# 确保虚拟环境已激活
source venv/bin/activate

# 运行初始化脚本
python scripts/init_admin.py
```

**预期输出：**
```
🔧 初始化数据库...
✅ 数据库表创建完成
✅ 管理员账户创建成功
   用户名: admin
   密码: 123456
   邮箱: admin@example.com
✅ 示例负责人账户创建完成（默认密码: 123456）

🎉 数据库初始化完成！
```

---

## 二、本地测试

### 2.1 启动开发服务器

#### 方式 A: 快速启动（推荐）

**启动后端：**
```bash
cd /Users/hongtaomeng/cursor_sh/backend
./run.sh
```

**启动前端：**
```bash
cd /Users/hongtaomeng/cursor_sh
npm run dev
```

#### 方式 B: 手动启动

**终端 1 - 后端：**
```bash
cd /Users/hongtaomeng/cursor_sh/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 - 前端：**
```bash
cd /Users/hongtaomeng/cursor_sh
npm run dev
```

### 2.2 验证服务

#### 后端验证

**1. 健康检查：**
```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "ok",
  "app": "AI设计任务管理系统"
}
```

**2. API 文档：**

访问 http://localhost:8000/docs

- 应该看到完整的 Swagger UI
- 测试登录接口

**3. 测试登录：**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin"
  }'
```

预期响应：
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "admin-...",
      "username": "admin",
      "role": "admin"
    }
  }
}
```

#### 前端验证

**1. 访问首页：**

打开浏览器访问 http://localhost:3000

- 应该看到轮播图和登录按钮
- 页面无错误

**2. 测试登录：**

- 点击右上角"登录"
- 输入 `admin` / `123456`
- 选择"管理员"角色
- 点击登录
- 应该跳转到工作台

**3. 检查浏览器控制台：**

按 F12 打开开发者工具：
- Console 无错误
- Network 可以看到 API 请求
- Application → Local Storage 有 token

### 2.3 功能测试

#### 测试用例 1: 创建订单

```
1. 以 user 身份登录 (user/123456)
2. 进入工作台
3. 点击"裸眼3D成片购买适配"
4. 填写表单：
   - 行业类型: 电影
   - 视觉风格: 科幻
   - 时长: 120 秒
   - 价格: 5000-10000
   - 分辨率: 3840x2160
   - 尺寸: 55英寸
5. 点击"确认提交"
6. 验证：
   ✓ 显示成功提示
   ✓ 跳转到订单列表
   ✓ 能看到新创建的订单
```

#### 测试用例 2: 分配负责人

```
1. 以 admin 身份登录 (admin/123456)
2. 进入订单管理
3. 找到状态为"待分配"的订单
4. 点击"分配负责人"
5. 选择一个负责人
6. 点击确认
7. 验证：
   ✓ 订单状态变为"制作中"
   ✓ 显示负责人信息
   ✓ 负责人收到邮件通知（如已配置）
```

#### 测试用例 3: 上传预览

```
1. 以 staff1 身份登录 (staff1/123456)
2. 进入"我的订单"
3. 找到分配给自己的订单
4. 点击"上传预览文件"
5. 选择并上传文件（模拟）
6. 点击"提交预览"
7. 验证：
   ✓ 订单状态变为"初稿预览"
   ✓ 客户可以看到预览文件
   ✓ 客户收到邮件通知
```

#### 测试用例 4: 客户反馈

```
1. 以 user 身份登录
2. 进入"我的订单"
3. 找到"初稿预览"状态的订单
4. 查看预览文件
5. 点击"需要修改"
6. 填写修改意见
7. 提交反馈
8. 验证：
   ✓ 订单状态变为"需要修改"
   ✓ 修改次数 +1
   ✓ 负责人收到通知
```

### 2.4 性能测试

#### 响应时间测试

```bash
# 安装 Apache Bench
brew install apache-bench  # macOS
sudo apt install apache2-utils  # Linux

# 测试登录接口
ab -n 100 -c 10 -p login.json -T application/json \
   http://localhost:8000/api/auth/login

# 测试订单列表接口（需要 token）
ab -n 100 -c 10 -H "Authorization: Bearer {token}" \
   http://localhost:8000/api/orders
```

**期望指标：**
- 平均响应时间 < 100ms
- 95% 请求 < 200ms
- 错误率 0%

#### 并发测试

```python
# 使用 locust 进行压力测试
from locust import HttpUser, task, between

class SystemUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # 登录获取 token
        response = self.client.post("/api/auth/login", json={
            "username": "admin",
            "password": "123456",
            "role": "admin"
        })
        self.token = response.json()["data"]["token"]
    
    @task
    def get_orders(self):
        self.client.get("/api/orders", headers={
            "Authorization": f"Bearer {self.token}"
        })
```

运行测试：
```bash
locust -f locustfile.py --host=http://localhost:8000
```

---

## 三、生产环境部署

### 3.1 服务器准备

#### 云服务器选择

**推荐配置（阿里云）：**
- **实例类型**: ecs.c6.large
- **CPU**: 2核
- **内存**: 4GB
- **硬盘**: 40GB SSD
- **带宽**: 5Mbps
- **操作系统**: Ubuntu 20.04 LTS

#### 服务器初始化

```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 安装基础工具
sudo apt install -y git curl wget vim build-essential

# 3. 配置防火墙
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# 4. 创建部署用户
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG sudo deploy
sudo passwd deploy

# 5. 配置 SSH 密钥
ssh-copy-id deploy@your-server-ip
```

### 3.2 Docker 部署（推荐）

#### 安装 Docker

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. 验证安装
docker --version
docker-compose --version
```

#### 部署应用

```bash
# 1. 克隆代码
cd /home/deploy
git clone https://github.com/your-repo/cursor_sh.git
cd cursor_sh

# 2. 配置环境变量
cd backend
cp .env.example .env
nano .env  # 修改生产配置

# 重要配置：
# DEBUG=False
# JWT_SECRET_KEY=生成一个随机密钥
# DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/dbname
# CORS_ORIGINS=https://your-domain.com

# 3. 启动服务
docker-compose up -d

# 4. 初始化数据库
docker-compose exec backend python scripts/init_admin.py

# 5. 查看日志
docker-compose logs -f backend
```

#### Docker Compose 配置

编辑 `backend/docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    container_name: ai-design-postgres
    environment:
      POSTGRES_USER: aidesign
      POSTGRES_PASSWORD: your-secure-password
      POSTGRES_DB: ai_design
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - app-network

  # 后端 API
  backend:
    build: .
    container_name: ai-design-backend
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=postgresql+asyncpg://aidesign:your-secure-password@postgres:5432/ai_design
      - DEBUG=False
    depends_on:
      - postgres
    restart: always
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
```

### 3.3 前端部署

#### 构建生产版本

```bash
cd /Users/hongtaomeng/cursor_sh

# 1. 修改 API 地址
# 编辑 src/utils/request.ts
# baseURL: 'https://api.your-domain.com/api'

# 2. 构建
npm run build

# 输出目录: dist/
```

#### 部署到 Nginx

```bash
# 1. 安装 Nginx
sudo apt install nginx

# 2. 配置 Nginx
sudo nano /etc/nginx/sites-available/aidesign

# 粘贴以下配置：
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    root /var/www/aidesign/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 上传文件
    location /uploads {
        alias /home/deploy/cursor_sh/backend/uploads;
        expires 30d;
    }
}

# 3. 启用站点
sudo ln -s /etc/nginx/sites-available/aidesign /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 4. 上传前端文件
scp -r dist/* deploy@your-server:/var/www/aidesign/dist/
```

#### 配置 HTTPS (Let's Encrypt)

```bash
# 1. 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 2. 获取证书
sudo certbot --nginx -d your-domain.com

# 3. 自动续期
sudo certbot renew --dry-run

# Certbot 会自动修改 Nginx 配置，添加 HTTPS
```

### 3.4 数据库迁移

#### 从 SQLite 迁移到 PostgreSQL

```bash
# 1. 导出 SQLite 数据
cd /Users/hongtaomeng/cursor_sh/backend
python scripts/export_data.py > data.sql

# 2. 在服务器上创建 PostgreSQL 数据库
psql -U postgres
CREATE DATABASE ai_design;
CREATE USER aidesign WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE ai_design TO aidesign;

# 3. 导入数据
psql -U aidesign -d ai_design < data.sql

# 4. 验证数据
psql -U aidesign -d ai_design
\dt  # 查看表
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM orders;
```

### 3.5 配置阿里云 OSS

```bash
# 1. 编辑后端 .env
OSS_ENABLED=True
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_BUCKET_NAME=your-bucket-name
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com

# 2. 重启后端服务
docker-compose restart backend
```

### 3.6 配置进程守护

#### 使用 systemd (非 Docker 部署)

创建 `/etc/systemd/system/aidesign-backend.service`:

```ini
[Unit]
Description=AI Design Backend Service
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/cursor_sh/backend
Environment="PATH=/home/deploy/cursor_sh/backend/venv/bin"
ExecStart=/home/deploy/cursor_sh/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable aidesign-backend
sudo systemctl start aidesign-backend
sudo systemctl status aidesign-backend
```

---

## 四、运维指南

### 4.1 日常维护

#### 监控服务状态

```bash
# Docker 方式
docker-compose ps
docker-compose logs -f backend

# Systemd 方式
sudo systemctl status aidesign-backend
sudo journalctl -u aidesign-backend -f
```

#### 数据库备份

**自动备份脚本：**

创建 `/home/deploy/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/home/deploy/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T postgres pg_dump -U aidesign ai_design \
  > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# 备份上传文件
tar -czf "$BACKUP_DIR/uploads_$TIMESTAMP.tar.gz" ./backend/uploads

# 清理 7 天前的备份
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
```

设置定时任务：
```bash
chmod +x /home/deploy/backup.sh

# 编辑 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /home/deploy/backup.sh >> /home/deploy/backup.log 2>&1
```

#### 日志管理

```bash
# 查看后端日志
docker-compose logs --tail=100 backend

# 查看 Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 日志轮转配置
sudo nano /etc/logrotate.d/aidesign
```

### 4.2 性能监控

#### 安装监控工具

```bash
# 1. 安装 Prometheus
docker run -d -p 9090:9090 \
  -v /home/deploy/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# 2. 安装 Grafana
docker run -d -p 3001:3000 grafana/grafana

# 3. 配置数据源
# 访问 http://your-server:3001
# 添加 Prometheus 数据源
```

#### 监控指标

- **系统指标**: CPU、内存、磁盘、网络
- **应用指标**: 请求数、响应时间、错误率
- **数据库指标**: 连接数、查询时间、慢查询
- **业务指标**: 订单数、用户数、完成率

### 4.3 扩容方案

#### 垂直扩容

```bash
# 阿里云控制台升级配置
# 4核8GB → 8核16GB

# 重启服务
docker-compose restart
```

#### 水平扩容

```yaml
# docker-compose.yml
services:
  backend:
    # ...
    deploy:
      replicas: 3  # 运行 3 个实例
  
  nginx:
    image: nginx
    # 配置负载均衡
```

---

## 五、故障排查

### 5.1 常见问题

#### 问题 1: 后端启动失败

**症状：**
```
Error: Address already in use
```

**解决方案：**
```bash
# 查找占用 8000 端口的进程
lsof -i:8000

# 杀死进程
kill -9 <PID>

# 或更换端口
python -m uvicorn app.main:app --port 8001
```

#### 问题 2: 数据库连接失败

**症状：**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**检查清单：**
```bash
# 1. 检查数据库服务
docker-compose ps postgres
sudo systemctl status postgresql

# 2. 检查连接字符串
echo $DATABASE_URL

# 3. 测试连接
psql -U aidesign -d ai_design -h localhost

# 4. 检查防火墙
sudo ufw status
```

#### 问题 3: 前端 API 请求失败

**症状：**
```
Network Error
CORS Error
```

**解决方案：**
```bash
# 1. 检查后端 CORS 配置
# backend/.env
CORS_ORIGINS=https://your-domain.com

# 2. 检查 Nginx 配置
sudo nginx -t
sudo systemctl reload nginx

# 3. 检查浏览器控制台
# F12 → Network → 查看请求详情
```

#### 问题 4: 文件上传失败

**症状：**
```
File size exceeds limit
Permission denied
```

**解决方案：**
```bash
# 1. 检查文件大小限制
# backend/.env
MAX_FILE_SIZE=52428800  # 50MB

# 2. 检查上传目录权限
ls -la backend/uploads
chmod 755 backend/uploads

# 3. 检查 Nginx 配置
# /etc/nginx/nginx.conf
client_max_body_size 50M;
```

#### 问题 5: 邮件发送失败

**症状：**
```
SMTP Authentication Error
Connection refused
```

**解决方案：**
```bash
# 1. 检查 SMTP 配置
# backend/.env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-auth-code  # 确认是授权码！

# 2. 测试 SMTP 连接
telnet smtp.qq.com 465

# 3. 查看日志
docker-compose logs backend | grep smtp
```

### 5.2 性能问题

#### 问题: 响应慢

**诊断：**
```bash
# 1. 检查系统资源
top
htop
free -m
df -h

# 2. 检查数据库
# 慢查询日志
docker-compose exec postgres psql -U aidesign -d ai_design
\x
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;

# 3. 检查应用日志
docker-compose logs backend | grep "process_time"
```

**优化方案：**
```python
# 1. 添加数据库索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

# 2. 启用查询缓存
# 3. 增加数据库连接池
# 4. 使用 Redis 缓存热点数据
```

### 5.3 安全问题

#### 定期安全检查

```bash
# 1. 更新系统和软件包
sudo apt update && sudo apt upgrade -y

# 2. 检查开放端口
sudo netstat -tuln

# 3. 检查失败的登录尝试
sudo grep "Failed password" /var/log/auth.log

# 4. 扫描恶意软件
sudo apt install clamav
sudo clamscan -r /home/deploy/cursor_sh
```

#### 安全加固

```bash
# 1. 禁用 root SSH 登录
sudo nano /etc/ssh/sshd_config
# PermitRootLogin no

# 2. 启用防火墙
sudo ufw enable
sudo ufw default deny incoming
sudo ufw allow 22,80,443/tcp

# 3. 安装 fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

---

## 六、回滚方案

### 6.1 代码回滚

```bash
# 1. 查看提交历史
git log --oneline

# 2. 回滚到指定版本
git checkout <commit-hash>

# 3. 重新部署
docker-compose down
docker-compose up -d --build

# 4. 验证
curl http://localhost:8000/health
```

### 6.2 数据库回滚

```bash
# 1. 停止服务
docker-compose stop backend

# 2. 恢复备份
docker-compose exec -T postgres psql -U aidesign -d ai_design \
  < /home/deploy/backups/db_backup_YYYYMMDD_HHMMSS.sql

# 3. 重启服务
docker-compose start backend
```

---

## 七、发布检查清单

### 上线前检查

- [ ] 代码已合并到主分支
- [ ] 所有测试通过
- [ ] 配置文件已更新（.env）
- [ ] 数据库已备份
- [ ] SSL 证书已配置
- [ ] 监控和告警已设置
- [ ] 负载均衡已配置（如需要）
- [ ] 邮件通知已测试
- [ ] 文件上传已测试
- [ ] 性能测试通过
- [ ] 安全扫描通过
- [ ] 文档已更新

### 上线步骤

```bash
# 1. 备份当前版本
./backup.sh

# 2. 拉取最新代码
git pull origin main

# 3. 构建新版本
docker-compose build

# 4. 平滑重启
docker-compose up -d --no-deps --build backend

# 5. 验证
curl http://localhost:8000/health

# 6. 监控日志
docker-compose logs -f backend
```

### 上线后验证

- [ ] 服务正常启动
- [ ] API 接口可访问
- [ ] 前端页面正常
- [ ] 登录功能正常
- [ ] 创建订单正常
- [ ] 邮件发送正常
- [ ] 监控数据正常
- [ ] 无异常错误日志

---

## 八、联系支持

### 技术支持渠道

- **邮件**: support@example.com
- **文档**: https://docs.your-domain.com
- **问题跟踪**: https://github.com/your-repo/issues

### 紧急联系

- **系统管理员**: admin@example.com
- **开发负责人**: dev@example.com
- **值班电话**: 123-4567-8901（工作时间）

---

**版本**: v1.0.0  
**更新日期**: 2025-11-05  
**文档维护**: 运维团队

