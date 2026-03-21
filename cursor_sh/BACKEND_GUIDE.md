# 后端开发完成指南 ✅

## 🎉 恭喜！后端代码已全部生成

基于 **FastAPI** 的完整后端系统已经创建完成，包含所有核心功能。

---

## 📦 生成的文件清单

### 核心应用文件
```
backend/
├── app/
│   ├── main.py                  # FastAPI 应用入口 ⭐
│   ├── config.py                # 配置管理
│   ├── database.py              # 数据库连接
│   │
│   ├── models/                  # 数据库模型（SQLAlchemy）
│   │   ├── user.py              # 用户模型
│   │   ├── order.py             # 订单模型
│   │   ├── file.py              # 文件模型
│   │   └── feedback.py          # 反馈模型
│   │
│   ├── schemas/                 # 数据验证（Pydantic）
│   │   ├── auth.py              # 认证相关
│   │   ├── user.py              # 用户相关
│   │   ├── order.py             # 订单相关
│   │   ├── file.py              # 文件相关
│   │   ├── feedback.py          # 反馈相关
│   │   └── response.py          # 统一响应格式
│   │
│   ├── api/                     # API 路由
│   │   ├── auth.py              # 认证 API
│   │   ├── orders.py            # 订单 API
│   │   └── staff.py             # 负责人 API
│   │
│   ├── services/                # 业务逻辑层
│   │   ├── auth_service.py      # 认证服务
│   │   ├── order_service.py     # 订单服务（含状态机）
│   │   ├── file_service.py      # 文件服务
│   │   └── email_service.py     # 邮件服务
│   │
│   ├── utils/                   # 工具函数
│   │   ├── security.py          # JWT、密码加密
│   │   ├── dependencies.py      # 依赖注入、权限控制
│   │   └── validators.py        # 数据验证
│   │
│   └── middleware/              # 中间件
│       ├── cors.py              # CORS 配置
│       └── rate_limit.py        # API 限流
│
├── scripts/                     # 工具脚本
│   ├── init_admin.py            # 初始化管理员账户
│   └── backup_db.py             # 数据库备份脚本
│
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量示例
├── Dockerfile                   # Docker 配置
├── docker-compose.yml           # Docker Compose
├── run.sh                       # 快速启动脚本 ⭐
└── README.md                    # 完整文档
```

---

## 🚀 快速开始（3 步）

### 方式 1: 使用启动脚本（推荐）

```bash
cd backend
./run.sh
```

脚本会自动：
1. 创建虚拟环境
2. 安装依赖
3. 初始化数据库
4. 启动服务器

### 方式 2: 手动启动

```bash
cd backend

# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置邮件等参数

# 4. 初始化数据库
python scripts/init_admin.py

# 5. 启动服务器
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔐 默认账户

系统会自动创建以下测试账户：

### 管理员
- **用户名**: `admin`
- **密码**: `123456`
- **角色**: admin

### 普通用户（需自行注册）
- 使用注册接口创建

### 负责人（示例）
- `staff1` / `123456` （张设计）
- `staff2` / `123456` （李艺术）

---

## 📚 访问地址

启动后，访问以下地址：

- **API 服务**: http://localhost:8000
- **Swagger 文档**: http://localhost:8000/docs ⭐
- **ReDoc 文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

---

## ⚙️ 重要配置

### 邮件配置（必需）

编辑 `.env` 文件：

```env
# QQ 邮箱 SMTP 配置
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-qq-email@qq.com
SMTP_PASSWORD=your-qq-smtp-auth-code  # ⚠️ 这是授权码，不是密码！
SMTP_FROM=your-qq-email@qq.com
```

**获取 QQ 邮箱授权码：**
1. 登录 QQ 邮箱
2. 设置 → 账户
3. 开启 SMTP 服务
4. 生成授权码

### CORS 配置

```env
# 允许的前端地址（逗号分隔）
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### JWT 配置

```env
# ⚠️ 生产环境必须修改为随机密钥！
JWT_SECRET_KEY=your-random-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # Token 有效期（24小时）
```

---

## 🔧 核心功能清单

### ✅ 已实现功能

#### 1. 认证系统
- [x] 用户登录（JWT）
- [x] 用户注册
- [x] Token 验证
- [x] 密码加密（bcrypt）
- [x] 简化验证码验证

#### 2. 用户管理
- [x] 三种角色（admin、user、staff）
- [x] 基于角色的权限控制
- [x] 用户信息查询
- [x] 负责人管理

#### 3. 订单系统
- [x] 三种订单类型创建
  - 裸眼3D成片购买适配
  - AI裸眼3D内容定制（5-7天）
  - 数字艺术内容定制（3天初稿）
- [x] 订单列表查询（支持筛选）
- [x] 订单详情查询
- [x] 订单状态更新
- [x] 负责人分配
- [x] 预览文件上传
- [x] 客户反馈系统

#### 4. 订单状态机
- [x] 7 种订单状态
- [x] 状态转换验证
- [x] 修改次数统计
- [x] 状态变更历史

#### 5. 文件管理
- [x] 本地文件上传
- [x] 文件类型验证
- [x] 文件大小限制
- [x] 阿里云 OSS 接口预留

#### 6. 权限控制
- [x] 用户只能查看自己的订单
- [x] 负责人只能查看分配给自己的订单
- [x] 管理员查看所有订单
- [x] API 路由权限装饰器

#### 7. 邮件通知
- [x] 订单状态变更通知
- [x] 预览文件就绪通知
- [x] HTML 邮件模板
- [x] 异步发送

#### 8. API 限流
- [x] 基于 IP 的请求限流
- [x] 防止暴力破解
- [x] 可配置限流策略

#### 9. 其他功能
- [x] CORS 跨域支持
- [x] 统一响应格式
- [x] 异常处理
- [x] 数据库备份脚本
- [x] Docker 容器化
- [x] 完整 API 文档

---

## 📊 订单状态流转图

```
创建订单
    ↓
待分配 (pending_assign)
    ↓ [管理员分配负责人]
制作中 (in_production)
    ↓ [负责人上传初稿]
初稿预览 (preview_ready)
    ↓ [客户反馈]
    ├─ 确认通过 → 制作中（制作终稿）
    └─ 需要修改 → 需要修改 (revision_needed) → 制作中
    
制作中 (in_production)
    ↓ [负责人上传终稿]
终稿预览 (final_preview)
    ↓ [客户最终确认]
    ├─ 确认通过 → 已完成 (completed) ✅
    └─ 需要修改 → 需要修改 (revision_needed) → 制作中
```

---

## 🧪 测试 API

### 1. 使用 Swagger UI（推荐）

访问 http://localhost:8000/docs

- 可视化 API 文档
- 在线测试所有接口
- 自动 Token 管理

### 2. 使用 Postman

导入前端项目中的 `api-spec/postman_collection.json`

### 3. 使用 curl

```bash
# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin"
  }'

# 获取订单列表（需要 Token）
curl -X GET http://localhost:8000/api/orders \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔄 数据库管理

### 备份数据库

```bash
python scripts/backup_db.py
```

备份文件保存在 `backups/` 目录，自动保留最近 10 个备份。

### 重新初始化

```bash
# 删除现有数据库
rm app.db

# 重新初始化
python scripts/init_admin.py
```

---

## 🐳 Docker 部署

### 快速启动

```bash
cd backend

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 初始化数据库
docker-compose exec backend python scripts/init_admin.py

# 停止服务
docker-compose down
```

---

## 🔌 前后端联调

### 1. 确保后端运行

```bash
cd backend
./run.sh
```

后端地址：`http://localhost:8000`

### 2. 配置前端 API 地址

修改前端 `src/utils/request.ts`：

```typescript
const request = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000
})
```

### 3. 更新前端 mock API

将前端 `src/utils/api.ts` 中的 `ENABLE_MOCK` 改为 `false`：

```typescript
const ENABLE_MOCK = false  // 使用真实后端
```

### 4. 启动前端

```bash
cd ../  # 返回项目根目录
npm run dev
```

前端地址：`http://localhost:5173`

---

## 📖 API 接口概览

### 认证模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/logout` | 用户登出 |

### 订单模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/orders` | 获取订单列表 |
| POST | `/api/orders` | 创建订单 |
| GET | `/api/orders/{order_id}` | 获取订单详情 |
| PUT | `/api/orders/{order_id}/status` | 更新订单状态 |
| PUT | `/api/orders/{order_id}/assign` | 分配负责人 |
| POST | `/api/orders/{order_id}/preview` | 上传预览文件 |
| POST | `/api/orders/{order_id}/feedback` | 提交反馈 |

### 负责人模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/staff` | 获取负责人列表 |
| POST | `/api/staff` | 添加负责人 |

完整文档：http://localhost:8000/docs

---

## 🚨 常见问题

### Q1: 启动失败？

**检查清单：**
- [ ] Python 版本 3.11+
- [ ] 依赖是否安装完整
- [ ] 端口 8000 是否被占用
- [ ] .env 文件是否存在

### Q2: 邮件发送失败？

**解决方案：**
1. 确认使用的是 QQ 邮箱授权码，不是密码
2. 检查 SMTP 配置是否正确
3. 查看后端日志获取详细错误

### Q3: 前端连接失败？

**检查：**
1. 后端是否正常运行
2. CORS 配置是否包含前端地址
3. 前端 API baseURL 是否正确

### Q4: Token 无效？

**可能原因：**
1. Token 已过期（默认 24 小时）
2. JWT_SECRET_KEY 被修改
3. 用户已被禁用

---

## 📈 性能优化建议

### 生产环境

1. **切换到 PostgreSQL**
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
   ```

2. **启用多进程**
   ```bash
   uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

3. **配置 Nginx 反向代理**

4. **使用阿里云 OSS 存储文件**
   ```env
   OSS_ENABLED=True
   OSS_ACCESS_KEY_ID=your_key
   OSS_ACCESS_KEY_SECRET=your_secret
   OSS_BUCKET_NAME=your_bucket
   OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
   ```

---

## 📝 下一步

### 立即开始

1. ✅ 启动后端服务
2. ✅ 访问 API 文档测试接口
3. ✅ 配置前端连接后端
4. ✅ 进行完整功能测试

### 可选增强

- [ ] 实现阿里云 OSS 文件上传
- [ ] 添加单元测试
- [ ] 实现 WebSocket 实时通知
- [ ] 添加操作日志记录
- [ ] 实现数据导出功能

---

## 🎓 技术文档

- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Pydantic**: https://docs.pydantic.dev/
- **JWT**: https://jwt.io/

---

## 📞 技术支持

如遇到问题：

1. 查看后端日志
2. 检查 API 文档
3. 查看 backend/README.md
4. 提交 Issue

---

**🎉 后端开发完成，祝开发顺利！**

