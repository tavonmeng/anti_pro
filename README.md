# Unique Video AI — 全栈系统

裸眼3D视觉内容与数字艺术创意技术服务平台，包含官网、业务管理系统（订单/AI 助手/企业认证）和后端 API。

## 项目结构

```
anti_pro/
├── website/              # 官网（Vite + Vue 3）
├── cursor_sh/            # 业务管理系统
│   ├── src/              #   前端（Vue 3 + TypeScript + Element Plus）
│   ├── backend/          #   后端（FastAPI + SQLAlchemy）
│   │   ├── app/          #     应用代码
│   │   ├── .env          #     环境变量（不入库）
│   │   └── Dockerfile    #     后端镜像
│   ├── Dockerfile        #   前端镜像
│   └── nginx.conf        #   前端 Nginx 配置
├── scripts/              # 部署脚本
│   └── deploy_system.sh  #   裸机一键部署
├── docker-compose.yml    # Docker 编排
└── README.md             # ← 你在这里
```

---

## 🐳 Docker 部署（推荐）

### 前置条件

- 一台阿里云 ECS 服务器（CentOS 7/8 或 AliOS）
- 服务器安全组已开放 **8080** 端口

---

### Step 1：服务器安装 Docker

SSH 登录服务器，执行一次即可：

```bash
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

# 验证
docker --version
docker compose version
```

---

### Step 2：同步代码到服务器

在**本地开发机**上执行：

```bash
rsync -avz --progress \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='.git' \
  --exclude='dist' \
  --exclude='__pycache__' \
  /Users/menghongtao/Documents/anti_pro/ \
  root@你的服务器IP:/root/service/anti_pro/
```

---

### Step 3：配置后端环境变量

在**服务器**上：

```bash
cd /root/service/anti_pro/cursor_sh/backend
vi .env
```

核心配置项：

```dotenv
# 安全（必须修改）
DEBUG=false
SECRET_KEY=你的随机密钥          # openssl rand -hex 32

# AI 功能（留空则降级为规则匹配）
AI_API_KEY=你的阿里云百炼API_Key
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL_NAME=qwen-max

# 数据库（默认 SQLite，无需额外配置）
DB_TYPE=sqlite
```

---

### Step 4：一键构建并启动

```bash
cd /root/service/anti_pro
docker compose up -d --build
```

首次构建约 3~5 分钟。完成后：

```bash
docker compose ps
```

预期输出：
```
NAME                  STATUS    PORTS
anti-pro-backend      Up        8000/tcp
anti-pro-frontend     Up        0.0.0.0:8080->8080/tcp
```

访问 `http://你的服务器IP:8080` 即可使用。

---

### Step 5：验证部署

```bash
# 后端健康检查
curl http://localhost:8080/api/health

# 查看实时日志
docker compose logs -f

# 只看后端日志
docker compose logs -f backend
```

---

### 常用运维操作

| 操作 | 命令 |
|---|---|
| 启动 | `docker compose up -d` |
| 停止 | `docker compose down` |
| 重启 | `docker compose restart` |
| 更新代码后重新部署 | `docker compose up -d --build` |
| 查看日志 | `docker compose logs -f` |
| 进入后端容器调试 | `docker exec -it anti-pro-backend bash` |
| 进入前端容器调试 | `docker exec -it anti-pro-frontend sh` |

### 数据持久化

以下数据通过 Docker Volume 持久化，删除容器不会丢失：

| 数据 | Volume |
|---|---|
| SQLite 数据库 | `backend-data` |
| 用户上传文件 | `backend-uploads` |
| 运行日志 | `backend-logs` |

### 故障排查

```bash
docker compose logs backend --tail 50   # 查看详细日志
docker stats                            # 检查资源占用
docker compose up -d --build backend    # 重建某个服务
```

---

## 裸机部署（备选）

不使用 Docker 时，可通过脚本直接部署到宿主机：

```bash
sudo bash scripts/deploy_system.sh              # 全量部署
sudo bash scripts/deploy_system.sh restart       # 仅重启后端
sudo bash scripts/deploy_system.sh env           # 重新配置 .env
sudo bash scripts/deploy_system.sh ssl           # 申请 SSL 证书
```

---

## 本地开发

```bash
# 前端
cd cursor_sh
npm install
npm run dev

# 后端
cd cursor_sh/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## 许可证

MIT
