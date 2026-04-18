# AI设计任务管理系统 - 后端

基于 FastAPI 的高性能异步后端 API 服务。

## 技术栈

- **FastAPI 0.104+** - 现代化的异步 Web 框架
- **SQLAlchemy 2.0** - ORM 框架
- **SQLite / PostgreSQL** - 数据库
- **JWT** - 身份认证
- **Pydantic** - 数据验证
- **Uvicorn** - ASGI 服务器

## 功能特性

### ✅ 核心功能
- 用户认证（JWT Token）
- 三种订单类型管理
- 完整的订单状态机
- 基于角色的权限控制（RBAC）
- 文件上传（本地 + 阿里云 OSS）
- 邮件通知系统
- API 限流保护

### 🔐 安全特性
- 密码 bcrypt 加密
- JWT Token 认证
- CORS 跨域保护
- API 访问限流

### 📊 订单系统
- **裸眼3D成片购买适配** - 视频内容适配
- **AI裸眼3D内容定制** - 5-7天制作周期
- **数字艺术内容定制** - 3天初稿交付

### 🔄 订单状态流转
```
待分配 → 制作中 → 初稿预览 → 需要修改/继续制作 → 终稿预览 → 已完成
```

## 快速开始

### 1. 环境要求

- Python 3.11+
- pip 或 conda

### 2. 安装依赖

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，配置必要参数
# 特别注意：
# - JWT_SECRET_KEY（生产环境必须修改）
# - SMTP_USER 和 SMTP_PASSWORD（邮件功能）
# - CORS_ORIGINS（前端地址）
```

#### 重要配置说明

**邮件配置（QQ邮箱）：**
```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-qq-email@qq.com
SMTP_PASSWORD=your-qq-smtp-auth-code  # 注意：这是授权码，不是QQ密码
SMTP_FROM=your-qq-email@qq.com
```

**获取 QQ 邮箱授权码：**
1. 登录 QQ 邮箱
2. 设置 → 账户
3. 开启 SMTP 服务
4. 生成授权码

> **💡 邮件通知功能说明**: 
> 系统内置了完整的邮件自动化通知流程：
> - **订单状态流转通知**：订单状态变更（如进入制作中、终稿预览等）时自动发送邮件。
> - **预览审核通知**：管理员上传初稿/终稿后自动通知客户。
> - **需求确认函自动下发**：用户提交订单（含草稿转提交）后，系统会自动寄送一封带有**需求确认函 PDF 附件**的邮件至其预留的通知邮箱中，作为留档与核对凭证。
> 🚨 **注意**: 你只需在 `.env` 中按上述格式填写真实的 `SMTP_HOST`、`SMTP_USER` 和 `SMTP_PASSWORD`（授权码），所有自动化邮件通知和 PDF 下发功能就会**立即生效**，无需修改任何代码。

### 4. 初始化数据库

```bash
# 初始化数据库并创建管理员账户
python scripts/init_admin.py
```

默认管理员账户：
- 用户名：`admin`
- 密码：`123456`
- 邮箱：`admin@example.com`

示例负责人账户：
- `staff1` / `123456`（张设计）
- `staff2` / `123456`（李艺术）

### 5. 启动服务

```bash
# 开发模式（自动重载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 main.py
python app/main.py
```

服务启动后：
- API 地址：`http://localhost:8000`
- Swagger 文档：`http://localhost:8000/docs`
- ReDoc 文档：`http://localhost:8000/redoc`

## 项目结构

```
backend/
├── app/
│   ├── api/                 # API 路由
│   │   ├── auth.py          # 认证接口
│   │   ├── orders.py        # 订单接口
│   │   └── staff.py         # 负责人接口
│   ├── models/              # 数据库模型
│   │   ├── user.py          # 用户模型
│   │   ├── order.py         # 订单模型
│   │   ├── file.py          # 文件模型
│   │   └── feedback.py      # 反馈模型
│   ├── schemas/             # Pydantic 数据验证
│   │   ├── auth.py
│   │   ├── order.py
│   │   ├── user.py
│   │   ├── file.py
│   │   ├── feedback.py
│   │   └── response.py
│   ├── services/            # 业务逻辑层
│   │   ├── auth_service.py  # 认证服务
│   │   ├── order_service.py # 订单服务
│   │   ├── file_service.py  # 文件服务
│   │   └── email_service.py # 邮件服务
│   ├── utils/               # 工具函数
│   │   ├── security.py      # 安全工具
│   │   ├── dependencies.py  # 依赖注入
│   │   └── validators.py    # 验证器
│   ├── middleware/          # 中间件
│   │   ├── cors.py          # CORS 配置
│   │   └── rate_limit.py    # 限流配置
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   └── main.py              # 应用入口
├── scripts/                 # 工具脚本
│   ├── init_admin.py        # 初始化管理员
│   └── backup_db.py         # 数据库备份
├── uploads/                 # 上传文件目录
├── tests/                   # 测试
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量示例
├── Dockerfile               # Docker 配置
├── docker-compose.yml       # Docker Compose
└── README.md                # 本文档
```

## API 文档

### 认证 API

#### POST `/api/auth/login` - 用户登录
```json
{
  "username": "admin",
  "password": "123456",
  "role": "admin",
  "captcha": "1234"
}
```

#### POST `/api/auth/register` - 用户注册
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123",
  "role": "user"
}
```

### 订单 API

#### GET `/api/orders` - 获取订单列表
查询参数：
- `user_id` - 用户 ID（管理员可用）
- `order_type` - 订单类型
- `status` - 订单状态
- `assignee_id` - 负责人 ID

#### POST `/api/orders` - 创建订单
支持三种订单类型，详见 Swagger 文档。

#### GET `/api/orders/{order_id}` - 获取订单详情

#### PUT `/api/orders/{order_id}/status` - 更新订单状态

#### PUT `/api/orders/{order_id}/assign` - 分配负责人

#### POST `/api/orders/{order_id}/preview` - 上传预览文件

#### POST `/api/orders/{order_id}/feedback` - 提交反馈

### 负责人 API

#### GET `/api/staff` - 获取负责人列表

#### POST `/api/staff` - 添加负责人（管理员）

完整 API 文档请访问：`http://localhost:8000/docs`

## 数据库管理

### 备份数据库

```bash
python scripts/backup_db.py
```

备份文件保存在 `backups/` 目录，自动保留最近 10 个备份。

### 迁移到 PostgreSQL（生产环境）

1. 安装 PostgreSQL
2. 创建数据库：`createdb ai_design`
3. 修改 `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_design
   ```
4. 重新初始化数据库：`python scripts/init_admin.py`

## Docker 部署

### 使用 Docker Compose

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

### 单独使用 Docker

```bash
# 构建镜像
docker build -t ai-design-backend .

# 运行容器
docker run -d \
  --name ai-design-backend \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/app.db:/app/app.db \
  ai-design-backend
```

## 开发指南

### 添加新的 API 路由

1. 在 `app/schemas/` 创建数据验证模型
2. 在 `app/services/` 实现业务逻辑
3. 在 `app/api/` 创建路由
4. 在 `app/main.py` 注册路由

### 运行测试

```bash
pytest
```

### 代码风格

项目遵循 PEP 8 规范，建议使用以下工具：
```bash
pip install black flake8

# 格式化代码
black app/

# 检查代码规范
flake8 app/
```

## 常见问题

### Q: 邮件发送失败？
A: 
1. 检查 SMTP 配置是否正确
2. 确保使用的是授权码而非密码
3. 查看服务器日志获取详细错误信息

### Q: 数据库连接失败？
A: 
1. 检查 DATABASE_URL 配置
2. 确保数据库文件有写入权限
3. PostgreSQL 需确保服务已启动

### Q: CORS 错误？
A: 
在 `.env` 中正确配置前端地址：
```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Q: Token 过期？
A: 
默认 24 小时有效期，可在 `.env` 中修改：
```env
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

## 性能优化建议

### 生产环境

1. **使用 PostgreSQL**
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
   ```

2. **启用多进程**
   ```bash
   uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

3. **使用 Nginx 反向代理**

4. **开启文件缓存**（如使用 CDN）

5. **配置限流**
   ```env
   RATE_LIMIT_PER_MINUTE=100
   ```

## 部署到阿里云

### 1. 准备服务器

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 部署应用

```bash
# 克隆代码
git clone <your-repo>
cd cursor_sh/backend

# 配置环境变量
cp .env.example .env
vim .env  # 修改生产配置

# 启动服务
docker-compose up -d

# 初始化数据库
docker-compose exec backend python scripts/init_admin.py
```

### 3. 配置 Nginx（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads {
        alias /path/to/backend/uploads;
    }
}
```

## 许可证

MIT License

## 支持

如有问题，请提交 Issue 或联系技术支持。

