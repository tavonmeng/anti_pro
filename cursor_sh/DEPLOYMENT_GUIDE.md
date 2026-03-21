# 阿里云部署指南

本指南将帮助您将整个订单管理系统部署到阿里云服务器上。

## 目录

1. [服务器准备](#1-服务器准备)
2. [环境安装](#2-环境安装)
3. [数据库配置](#3-数据库配置)
4. [后端部署](#4-后端部署)
5. [前端部署](#5-前端部署)
6. [Nginx 配置](#6-nginx-配置)
7. [域名和SSL证书](#7-域名和ssl证书)
8. [进程管理](#8-进程管理)
9. [安全配置](#9-安全配置)
10. [监控和维护](#10-监控和维护)

---

## 1. 服务器准备

### 1.1 购买阿里云ECS实例

**推荐配置：**
- **CPU**: 2核或以上
- **内存**: 4GB或以上
- **系统盘**: 40GB SSD
- **操作系统**: Ubuntu 22.04 LTS 或 CentOS 7/8
- **网络**: 公网IP（带宽建议5Mbps以上）

### 1.2 安全组配置

在阿里云控制台配置安全组规则，开放以下端口：

| 端口 | 协议 | 说明 |
|------|------|------|
| 22 | TCP | SSH远程连接 |
| 80 | TCP | HTTP |
| 443 | TCP | HTTPS |
| 8000 | TCP | 后端API（可选，生产环境建议只通过Nginx访问） |

### 1.3 连接服务器

```bash
ssh root@your-server-ip
```

---

## 2. 环境安装

### 2.1 更新系统

```bash
# Ubuntu
apt update && apt upgrade -y

# CentOS
yum update -y
```

### 2.2 安装基础工具

```bash
# Ubuntu
apt install -y git curl wget vim

# CentOS
yum install -y git curl wget vim
```

### 2.3 安装 Python 3.10+

```bash
# Ubuntu
apt install -y python3 python3-pip python3-venv

# CentOS
yum install -y python3 python3-pip
```

验证安装：
```bash
python3 --version
pip3 --version
```

### 2.4 安装 Node.js 18+

```bash
# 使用 NodeSource 安装
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# 或使用 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
```

验证安装：
```bash
node --version
npm --version
```

### 2.5 安装 PostgreSQL（推荐）或 SQLite

#### PostgreSQL（生产环境推荐）

```bash
# Ubuntu
apt install -y postgresql postgresql-contrib

# CentOS
yum install -y postgresql-server postgresql-contrib
postgresql-setup initdb
systemctl enable postgresql
systemctl start postgresql
```

配置PostgreSQL：
```bash
sudo -u postgres psql
```

```sql
-- 创建数据库和用户
CREATE DATABASE order_management;
CREATE USER order_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE order_management TO order_user;
\q
```

#### SQLite（开发/小规模使用）

```bash
# Ubuntu
apt install -y sqlite3

# CentOS
yum install -y sqlite
```

### 2.6 安装 Nginx

```bash
# Ubuntu
apt install -y nginx

# CentOS
yum install -y nginx

# 启动并设置开机自启
systemctl enable nginx
systemctl start nginx
```

---

## 3. 数据库配置

### 3.1 配置数据库连接

编辑后端配置文件 `backend/app/config.py` 或环境变量：

```python
# 使用 PostgreSQL
DATABASE_URL = "postgresql://order_user:your_secure_password@localhost:5432/order_management"

# 或使用 SQLite
DATABASE_URL = "sqlite:///./order_management.db"
```

### 3.2 初始化数据库

```bash
cd /path/to/your/project/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 运行数据库迁移
python -m app.database init_db
```

---

## 4. 后端部署

### 4.1 上传代码到服务器

```bash
# 在本地打包代码
cd /path/to/your/project
tar -czf order-management.tar.gz backend/ frontend/

# 上传到服务器
scp order-management.tar.gz root@your-server-ip:/opt/

# 在服务器上解压
ssh root@your-server-ip
cd /opt
tar -xzf order-management.tar.gz
```

或使用 Git：

```bash
# 在服务器上
cd /opt
git clone your-repository-url order-management
cd order-management
```

### 4.2 安装后端依赖

```bash
cd /opt/order-management/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.3 配置环境变量

创建 `.env` 文件：

```bash
cd /opt/order-management/backend
cat > .env << EOF
DATABASE_URL=postgresql://order_user:your_secure_password@localhost:5432/order_management
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
EOF
```

### 4.4 使用 Gunicorn 运行后端

```bash
# 安装 Gunicorn
pip install gunicorn

# 创建 Gunicorn 配置文件
cat > /opt/order-management/backend/gunicorn_config.py << EOF
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
EOF
```

### 4.5 使用 systemd 管理后端服务

创建服务文件：

```bash
cat > /etc/systemd/system/order-api.service << EOF
[Unit]
Description=Order Management API
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/order-management/backend
Environment="PATH=/opt/order-management/backend/venv/bin"
ExecStart=/opt/order-management/backend/venv/bin/gunicorn app.main:app -c gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

启动服务：

```bash
systemctl daemon-reload
systemctl enable order-api
systemctl start order-api
systemctl status order-api
```

---

## 5. 前端部署

### 5.1 安装前端依赖

```bash
cd /opt/order-management/frontend
npm install
```

### 5.2 配置环境变量

创建 `.env.production` 文件：

```bash
cat > /opt/order-management/frontend/.env.production << EOF
VITE_API_BASE_URL=https://your-domain.com/api
EOF
```

### 5.3 构建前端

```bash
npm run build
```

构建完成后，静态文件在 `dist/` 目录中。

### 5.4 部署静态文件

```bash
# 将构建好的文件复制到 Nginx 目录
cp -r /opt/order-management/frontend/dist/* /var/www/html/

# 或创建专门的目录
mkdir -p /var/www/order-management
cp -r /opt/order-management/frontend/dist/* /var/www/order-management/
chown -R www-data:www-data /var/www/order-management
```

---

## 6. Nginx 配置

### 6.1 配置 Nginx

创建配置文件：

```bash
cat > /etc/nginx/sites-available/order-management << EOF
# 前端静态文件
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    root /var/www/order-management;
    index index.html;

    # 前端路由支持（SPA）
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
}
EOF
```

启用配置：

```bash
# Ubuntu
ln -s /etc/nginx/sites-available/order-management /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default  # 可选，删除默认配置

# CentOS
# 配置文件在 /etc/nginx/conf.d/order-management.conf
```

测试配置：

```bash
nginx -t
```

重启 Nginx：

```bash
systemctl restart nginx
```

---

## 7. 域名和SSL证书

### 7.1 配置域名解析

在阿里云域名控制台，将域名A记录指向服务器公网IP。

### 7.2 安装 SSL 证书（Let's Encrypt）

```bash
# 安装 Certbot
apt install -y certbot python3-certbot-nginx

# 或 CentOS
yum install -y certbot python3-certbot-nginx
```

申请证书：

```bash
certbot --nginx -d your-domain.com -d www.your-domain.com
```

证书会自动配置到 Nginx，并设置自动续期。

### 7.3 更新 Nginx 配置支持 HTTPS

Certbot 会自动更新配置，或手动配置：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... 其他配置
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://\$server_name\$request_uri;
}
```

---

## 8. 进程管理

### 8.1 使用 PM2 管理前端构建（可选）

如果需要 Node.js 服务端渲染：

```bash
npm install -g pm2
pm2 start npm --name "order-frontend" -- run serve
pm2 save
pm2 startup
```

### 8.2 监控服务状态

```bash
# 检查后端服务
systemctl status order-api

# 检查 Nginx
systemctl status nginx

# 检查数据库
systemctl status postgresql
```

### 8.3 查看日志

```bash
# 后端日志
journalctl -u order-api -f

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## 9. 安全配置

### 9.1 防火墙配置

```bash
# Ubuntu (UFW)
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# CentOS (firewalld)
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

### 9.2 禁用 root 登录（推荐）

```bash
# 创建新用户
adduser deploy
usermod -aG sudo deploy

# 配置 SSH 密钥登录
su - deploy
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# 将你的公钥复制到 ~/.ssh/authorized_keys

# 编辑 SSH 配置
sudo vim /etc/ssh/sshd_config
# 设置：
# PermitRootLogin no
# PasswordAuthentication no

sudo systemctl restart sshd
```

### 9.3 定期备份

创建备份脚本：

```bash
cat > /opt/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
pg_dump -U order_user order_management > $BACKUP_DIR/db_$DATE.sql

# 备份代码
tar -czf $BACKUP_DIR/code_$DATE.tar.gz /opt/order-management

# 删除7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/backup.sh

# 设置定时任务（每天凌晨2点备份）
crontab -e
# 添加：
# 0 2 * * * /opt/backup.sh
```

---

## 10. 监控和维护

### 10.1 安装监控工具（可选）

```bash
# 安装 htop
apt install -y htop

# 安装 netdata（实时监控）
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
```

### 10.2 日志轮转

配置 logrotate：

```bash
cat > /etc/logrotate.d/order-api << EOF
/opt/order-management/backend/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
}
EOF
```

### 10.3 性能优化

- **数据库优化**：定期执行 `VACUUM` 和 `ANALYZE`
- **Nginx 缓存**：配置适当的缓存策略
- **CDN**：使用阿里云CDN加速静态资源
- **负载均衡**：如果流量大，考虑使用阿里云SLB

---

## 快速部署脚本

创建一个自动化部署脚本：

```bash
cat > /opt/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "开始部署..."

# 拉取最新代码
cd /opt/order-management
git pull origin main

# 更新后端
cd backend
source venv/bin/activate
pip install -r requirements.txt
systemctl restart order-api

# 更新前端
cd ../frontend
npm install
npm run build
cp -r dist/* /var/www/order-management/

echo "部署完成！"
EOF

chmod +x /opt/deploy.sh
```

---

## 常见问题

### Q: 如何查看后端API日志？
A: `journalctl -u order-api -f`

### Q: 如何重启服务？
A: 
```bash
systemctl restart order-api
systemctl restart nginx
```

### Q: 如何更新代码？
A: 使用上面的 `deploy.sh` 脚本，或手动执行部署步骤。

### Q: 数据库连接失败？
A: 检查：
1. PostgreSQL 服务是否运行：`systemctl status postgresql`
2. 数据库配置是否正确
3. 防火墙是否允许连接

---

## 总结

部署完成后，访问 `https://your-domain.com` 即可使用系统。

**重要提醒：**
- 定期备份数据库和代码
- 保持系统和依赖包更新
- 监控服务器资源使用情况
- 定期检查日志文件

如有问题，请查看日志文件或联系技术支持。


