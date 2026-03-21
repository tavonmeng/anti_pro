# AI设计任务管理系统 - 技术文档

## 📐 架构设计

### 总体架构

系统采用 **前后端分离** 的架构模式，通过 RESTful API 进行通信。

```
┌─────────────────────────────────────────────────────────┐
│                      用户/浏览器                          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     ↓
┌─────────────────────────────────────────────────────────┐
│                   前端应用 (Vue 3)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Components  │  │    Router    │  │    Pinia     │  │
│  │   UI 组件    │  │   路由管理    │  │   状态管理    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Axios (HTTP Client)                  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/JSON
                     ↓
┌─────────────────────────────────────────────────────────┐
│                  后端 API (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  API Routes  │  │   Services   │  │  Middleware  │  │
│  │   路由层      │  │   业务逻辑    │  │   中间件      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Models    │  │   Schemas    │  │    Utils     │  │
│  │  数据模型     │  │  数据验证     │  │   工具函数    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ SQLAlchemy ORM
                     ↓
┌─────────────────────────────────────────────────────────┐
│              数据库 (SQLite / PostgreSQL)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  users   │ │  orders  │ │  files   │ │feedbacks │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 前端技术栈

### 核心框架

#### 1. Vue 3 (Composition API)

**选型理由：**
- **组合式 API** - 更好的逻辑复用和代码组织
- **TypeScript 友好** - 完整的类型支持
- **性能优异** - Virtual DOM diff 优化
- **生态成熟** - 丰富的第三方库

**关键特性使用：**
```typescript
// Composition API 示例
import { ref, computed, onMounted } from 'vue'

export default {
  setup() {
    const count = ref(0)
    const doubled = computed(() => count.value * 2)
    
    onMounted(() => {
      console.log('组件已挂载')
    })
    
    return { count, doubled }
  }
}
```

#### 2. Vite 5.x

**选型理由：**
- **极速冷启动** - 基于 ES modules
- **即时热更新** - 毫秒级 HMR
- **优化构建** - Rollup 打包，产物小
- **零配置** - 开箱即用

**配置示例：**
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

#### 3. TypeScript 5.x

**选型理由：**
- **类型安全** - 编译时错误检测
- **智能提示** - 更好的开发体验
- **代码重构** - 安全的重命名和重构
- **文档性** - 类型即文档

**类型定义示例：**
```typescript
// types/index.ts
export interface Order {
  id: string
  orderNumber: string
  orderType: OrderType
  status: OrderStatus
  userId: string
  createdAt: string
}

export type OrderType = 'video_purchase' | 'ai_3d_custom' | 'digital_art'
```

### UI 框架

#### Element Plus 2.x

**选型理由：**
- **组件丰富** - 60+ 高质量组件
- **Vue 3 原生** - 专为 Vue 3 设计
- **定制性强** - 主题、尺寸可配置
- **中文友好** - 国内主流，文档全

**常用组件：**
- 表单：`el-form`, `el-input`, `el-select`
- 布局：`el-container`, `el-card`, `el-menu`
- 数据：`el-table`, `el-pagination`
- 反馈：`el-message`, `el-dialog`, `el-loading`

### 状态管理

#### Pinia 2.x

**选型理由：**
- **Vue 3 官方推荐** - 替代 Vuex
- **TypeScript 完美支持** - 类型推导
- **组合式 API 风格** - 更简洁
- **模块化** - 自动代码分割

**Store 示例：**
```typescript
// stores/order.ts
export const useOrderStore = defineStore('order', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  
  async function fetchOrders() {
    loading.value = true
    try {
      orders.value = await orderApi.getOrders()
    } finally {
      loading.value = false
    }
  }
  
  return { orders, loading, fetchOrders }
})
```

### 路由管理

#### Vue Router 4.x

**选型理由：**
- **嵌套路由** - 支持复杂页面结构
- **路由守卫** - 权限控制
- **动态路由** - 参数传递
- **懒加载** - 按需加载组件

**路由配置：**
```typescript
// router/index.ts
const routes = [
  {
    path: '/user',
    component: UserDashboard,
    meta: { requiresAuth: true, role: 'user' },
    children: [
      { path: 'workspace', component: Workspace },
      { path: 'orders', component: Orders },
      { path: 'orders/:id', component: OrderDetail }
    ]
  }
]
```

### HTTP 客户端

#### Axios 1.x

**选型理由：**
- **拦截器** - 请求/响应统一处理
- **取消请求** - 避免重复请求
- **超时控制** - 防止长时间等待
- **错误处理** - 统一错误提示

**拦截器配置：**
```typescript
// utils/request.ts
request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      router.push('/login')
    }
    return Promise.reject(error)
  }
)
```

### 样式方案

#### SCSS

**选型理由：**
- **变量和混入** - 样式复用
- **嵌套语法** - 结构清晰
- **模块化** - 易于维护
- **兼容性** - 广泛支持

**样式组织：**
```
src/styles/
├── variables.scss    # 全局变量
├── mixins.scss       # 混入
├── common.scss       # 公共样式
└── main.scss         # 主样式文件
```

---

## ⚙️ 后端技术栈

### 核心框架

#### FastAPI 0.104+

**选型理由：**
- **高性能** - 基于 Starlette，性能媲美 Go
- **异步原生** - async/await 支持
- **自动文档** - OpenAPI 3.0 (Swagger)
- **类型检查** - Pydantic 数据验证
- **易学易用** - Python 语法简洁

**性能对比：**
| 框架 | 吞吐量 (req/s) | 响应时间 (ms) |
|------|---------------|--------------|
| FastAPI | 20,000+ | < 10 |
| Flask | 8,000 | 20-30 |
| Django | 5,000 | 30-50 |

**API 定义示例：**
```python
@router.post("/orders", response_model=ApiResponse[dict])
async def create_order(
    order_data: Union[VideoPurchaseOrderCreate, AI3DCustomOrderCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    order = await OrderService.create_order(db, order_data, current_user)
    return ApiResponse(code=201, message="订单创建成功", data=order)
```

### ORM 框架

#### SQLAlchemy 2.0

**选型理由：**
- **异步支持** - asyncio 兼容
- **功能强大** - 复杂查询、关系映射
- **数据库无关** - 支持多种数据库
- **成熟稳定** - Python 事实标准

**模型定义：**
```python
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String(50), primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING_ASSIGN)
    user_id = Column(String(50), ForeignKey("users.id"))
    
    # 关系
    files = relationship("File", back_populates="order")
    feedbacks = relationship("Feedback", back_populates="order")
```

### 数据验证

#### Pydantic 2.5+

**选型理由：**
- **类型安全** - 运行时验证
- **自动序列化** - JSON 转换
- **错误提示** - 详细的验证信息
- **性能优异** - Rust 核心，快速

**Schema 定义：**
```python
class OrderCreate(BaseModel):
    orderType: OrderType
    industryType: str
    duration: int = Field(gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "orderType": "video_purchase",
                "duration": 120
            }
        }
```

### 认证方案

#### JWT (JSON Web Token)

**选型理由：**
- **无状态** - 服务器不存储 session
- **跨域友好** - 适合前后端分离
- **信息携带** - token 包含用户信息
- **易扩展** - 微服务架构友好

**Token 结构：**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": "user-001",
    "username": "admin",
    "role": "admin",
    "exp": 1730966400
  },
  "signature": "..."
}
```

**实现：**
```python
# 生成 Token
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

# 验证 Token
def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
```

#### 密码加密 - bcrypt

**选型理由：**
- **安全性高** - 自适应哈希
- **防彩虹表** - 加盐处理
- **计算成本** - 可调整难度
- **行业标准** - 广泛使用

### 数据库

#### 开发环境：SQLite

**选型理由：**
- **零配置** - 无需安装数据库服务
- **轻量级** - 单文件，易备份
- **完整功能** - 支持事务、外键
- **快速开发** - 适合原型和测试

#### 生产环境：PostgreSQL

**选型理由：**
- **性能强劲** - 支持高并发
- **功能丰富** - JSON、全文检索
- **可靠性** - ACID 保证
- **扩展性** - 易于扩展

**数据库对比：**
| 特性 | SQLite | PostgreSQL |
|------|--------|-----------|
| 部署复杂度 | ⭐ | ⭐⭐⭐ |
| 并发能力 | 低 | 高 |
| 适用场景 | 开发测试 | 生产环境 |
| 数据量 | < 1GB | TB 级 |

### 文件存储

#### 本地文件系统 (开发)

**优点：**
- 零成本，无需配置
- 开发调试方便
- 速度快

**缺点：**
- 不支持分布式
- 难以扩展
- 备份麻烦

#### 阿里云 OSS (生产)

**选型理由：**
- **可靠性** - 99.9999999% 数据持久性
- **性能** - CDN 加速
- **成本低** - 按量付费
- **易扩展** - 无限容量

**接口预留：**
```python
class FileService:
    @staticmethod
    async def save_file(file: UploadFile, order_id: str):
        if settings.OSS_ENABLED:
            return await FileService.save_file_oss(file, order_id)
        else:
            return await FileService.save_file_local(file, order_id)
```

### 邮件服务

#### SMTP (QQ 邮箱)

**配置：**
```python
# 开发环境：QQ 邮箱
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "your-qq-email@qq.com"
SMTP_PASSWORD = "授权码"  # 不是密码！

# 生产环境：阿里云邮件推送（推荐）
```

**异步发送：**
```python
async def send_email(to: str, subject: str, html: str):
    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=True
    )
```

### API 限流

#### SlowAPI

**选型理由：**
- **简单易用** - 装饰器模式
- **灵活配置** - 多种限流策略
- **性能好** - 内存存储

**配置：**
```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"]
)

@limiter.limit("10/minute")
@router.post("/login")
async def login():
    pass
```

---

## 🗄️ 数据库设计

### ER 图

```
┌─────────────┐
│    Users    │
│─────────────│
│ id (PK)     │
│ username    │◄─────┐
│ password    │      │
│ role        │      │
│ email       │      │
│ real_name   │      │
└─────────────┘      │
                     │
                     │ user_id (FK)
                     │
┌─────────────┐      │
│   Orders    │◄─────┤
│─────────────│      │
│ id (PK)     │      │
│ order_num   │      │
│ order_type  │      │
│ status      │      │
│ user_id (FK)│──────┘
│ assignee_id │──────┐
│ order_data  │      │ assignee_id (FK)
└──────┬──────┘      │
       │             │
       │ order_id    │
       │             │
   ┌───┴────┐    ┌───┴────┐
   │        │    │        │
┌──▼──────┐ │ ┌──▼──────┐ │
│  Files  │ │ │Feedbacks│ │
│─────────│ │ │─────────│ │
│ id (PK) │ │ │ id (PK) │ │
│order_id │ │ │order_id │ │
│ name    │ │ │ content │ │
│ url     │ │ │ type    │ │
└─────────┘ │ │created_ │ │
            │ │  by (FK)│─┘
            │ └─────────┘
            └─────┘
```

### 表结构详解

#### 1. users 表

```sql
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'user', 'staff') NOT NULL,
    real_name VARCHAR(50),
    avatar VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_username (username),
    INDEX idx_role (role)
);
```

**字段说明：**
- `id`: 主键，格式如 `user-{timestamp}{random}`
- `password_hash`: bcrypt 加密后的密码
- `role`: 角色类型（admin/user/staff）
- `is_active`: 软删除标记

#### 2. orders 表

```sql
CREATE TABLE orders (
    id VARCHAR(50) PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_type ENUM('video_purchase', 'ai_3d_custom', 'digital_art') NOT NULL,
    status ENUM('pending_assign', 'in_production', 'preview_ready', 
                'revision_needed', 'final_preview', 'completed', 'cancelled') NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    assignee_id VARCHAR(50),
    revision_count INT DEFAULT 0,
    order_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (assignee_id) REFERENCES users(id),
    INDEX idx_order_number (order_number),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC)
);
```

**字段说明：**
- `order_data`: JSON 字段，存储订单类型特定数据
- `revision_count`: 修改次数统计
- 使用索引优化查询性能

#### 3. files 表

```sql
CREATE TABLE files (
    id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    file_type ENUM('scene_photo', 'material', 'preview') NOT NULL,
    name VARCHAR(255) NOT NULL,
    size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    INDEX idx_order_id (order_id),
    INDEX idx_file_type (file_type)
);
```

**字段说明：**
- `file_type`: 文件类型（现场照片/素材/预览）
- `ON DELETE CASCADE`: 订单删除时自动删除文件记录

#### 4. feedbacks 表

```sql
CREATE TABLE feedbacks (
    id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    type ENUM('approval', 'revision') NOT NULL,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_order_id (order_id),
    INDEX idx_created_at (created_at DESC)
);
```

### 数据关系

- **一对多**: 
  - 一个用户 → 多个订单
  - 一个订单 → 多个文件
  - 一个订单 → 多个反馈

- **多对一**:
  - 多个订单 → 一个负责人
  - 多个反馈 → 一个创建者

---

## 🔐 安全设计

### 认证流程

```
1. 用户登录
   ├─ 输入用户名、密码、角色
   ├─ 后端验证用户名/密码
   └─ 生成 JWT Token

2. Token 包含信息
   ├─ user_id
   ├─ username  
   ├─ role
   └─ exp (过期时间)

3. 后续请求
   ├─ 前端携带 Token (Authorization: Bearer {token})
   ├─ 后端验证 Token
   │   ├─ 解密 Token
   │   ├─ 检查是否过期
   │   └─ 提取用户信息
   └─ 执行业务逻辑
```

### 权限控制

#### 路由级别

```python
# 依赖注入实现权限控制
async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user

@router.post("/staff", dependencies=[Depends(require_admin)])
async def add_staff():
    # 只有管理员可以访问
    pass
```

#### 数据级别

```python
# 服务层权限过滤
async def get_orders(db, current_user):
    query = select(Order)
    
    if current_user.role == UserRole.USER:
        # 用户只能看自己的订单
        query = query.where(Order.user_id == current_user.id)
    elif current_user.role == UserRole.STAFF:
        # 负责人只能看分配的订单
        query = query.where(Order.assignee_id == current_user.id)
    # 管理员可以看所有订单
    
    return await db.execute(query)
```

### 安全措施

1. **密码安全**
   - bcrypt 加密（成本因子 12）
   - 加盐处理
   - 不存储明文密码

2. **Token 安全**
   - 24小时过期
   - 仅 HTTPS 传输（生产环境）
   - 存储在 localStorage（XSS 防护需注意）

3. **API 安全**
   - CORS 配置
   - 请求限流（60次/分钟）
   - 参数验证（Pydantic）

4. **SQL 注入防护**
   - 使用 ORM（SQLAlchemy）
   - 参数化查询
   - 不拼接 SQL

5. **XSS 防护**
   - Vue 自动转义
   - Content Security Policy
   - HTTP Only Cookie（可选）

---

## 📡 API 设计规范

### RESTful 设计

遵循 RESTful 最佳实践：

| 操作 | HTTP 方法 | 路径 | 说明 |
|------|-----------|------|------|
| 获取列表 | GET | `/api/orders` | 查询参数筛选 |
| 获取详情 | GET | `/api/orders/{id}` | 路径参数 |
| 创建 | POST | `/api/orders` | Body 传参 |
| 更新 | PUT/PATCH | `/api/orders/{id}` | 部分/全部更新 |
| 删除 | DELETE | `/api/orders/{id}` | - |

### 统一响应格式

```typescript
interface ApiResponse<T> {
  code: number      // 状态码
  message: string   // 提示信息
  data: T | null    // 业务数据
}
```

**成功响应：**
```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... }
}
```

**错误响应：**
```json
{
  "code": 400,
  "message": "请求参数错误",
  "data": null
}
```

### 状态码规范

| 状态码 | 含义 | 使用场景 |
|--------|------|---------|
| 200 | 成功 | GET, PUT 成功 |
| 201 | 创建成功 | POST 创建资源 |
| 400 | 请求错误 | 参数验证失败 |
| 401 | 未认证 | Token 无效/过期 |
| 403 | 权限不足 | 无权访问资源 |
| 404 | 不存在 | 资源未找到 |
| 409 | 冲突 | 用户名已存在等 |
| 429 | 限流 | 请求过于频繁 |
| 500 | 服务器错误 | 未预期的错误 |

---

## 🎯 性能优化

### 前端优化

#### 1. 代码分割

```typescript
// 路由懒加载
const routes = [
  {
    path: '/admin',
    component: () => import('@/views/AdminDashboard.vue')
  }
]
```

#### 2. 组件缓存

```vue
<keep-alive>
  <router-view />
</keep-alive>
```

#### 3. 图片优化

- 使用 WebP 格式
- 懒加载（Intersection Observer）
- 压缩和缩略图

#### 4. 请求优化

- 防抖/节流
- 请求合并
- 缓存策略

### 后端优化

#### 1. 数据库优化

```python
# 添加索引
Index('idx_order_status', 'status')
Index('idx_created_at', 'created_at')

# 预加载关联数据
query = query.options(
    selectinload(Order.files),
    selectinload(Order.feedbacks)
)

# 分页查询
query = query.limit(20).offset(offset)
```

#### 2. 异步处理

```python
# 所有 I/O 操作都使用 async/await
async def fetch_orders(db: AsyncSession):
    result = await db.execute(query)
    return result.scalars().all()
```

#### 3. 缓存策略

```python
# Redis 缓存（可选）
@cache(expire=300)  # 5分钟缓存
async def get_order_stats():
    return await calculate_stats()
```

---

## 🧪 测试策略

### 前端测试

#### 单元测试 (Vitest)

```typescript
import { describe, it, expect } from 'vitest'
import { useOrderStore } from '@/stores/order'

describe('OrderStore', () => {
  it('should fetch orders', async () => {
    const store = useOrderStore()
    await store.fetchOrders()
    expect(store.orders.length).toBeGreaterThan(0)
  })
})
```

#### E2E 测试 (Playwright)

```typescript
test('user can create order', async ({ page }) => {
  await page.goto('/login')
  await page.fill('input[name="username"]', 'user')
  await page.fill('input[name="password"]', '123456')
  await page.click('button[type="submit"]')
  
  await page.goto('/user/create-order/video_purchase')
  // ... 填写表单
  await page.click('button[type="submit"]')
  
  await expect(page).toHaveURL('/user/orders')
})
```

### 后端测试

#### 单元测试 (pytest)

```python
@pytest.mark.asyncio
async def test_create_order():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/orders", json={
            "orderType": "video_purchase",
            # ...
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        assert "order_number" in response.json()["data"]
```

#### API 测试 (Swagger UI)

- 访问 `/docs`
- 手动测试所有接口
- 导出为 Postman 集合

---

## 📈 监控和日志

### 日志系统

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 记录关键操作
logger.info(f"Order created: {order.order_number}")
logger.error(f"Failed to send email: {e}")
```

### 性能监控

```python
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {process_time:.2f}s")
    return response
```

---

## 🔧 开发工具

### 前端工具

- **VSCode** - IDE
- **Vue Devtools** - 调试工具
- **ESLint** - 代码检查
- **Prettier** - 代码格式化

### 后端工具

- **PyCharm / VSCode** - IDE
- **Black** - 代码格式化
- **Flake8** - 代码检查
- **pytest** - 测试框架

### 协作工具

- **Git** - 版本控制
- **GitHub / GitLab** - 代码托管
- **Swagger UI** - API 文档
- **Postman** - API 测试

---

## 📚 技术文档

### 参考资料

- **Vue 3**: https://vuejs.org/
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Element Plus**: https://element-plus.org/
- **Pydantic**: https://docs.pydantic.dev/

### 命名规范

#### 前端

- 组件：PascalCase (`OrderCard.vue`)
- 函数：camelCase (`fetchOrders`)
- 常量：UPPER_SNAKE_CASE (`API_BASE_URL`)
- 类型：PascalCase (`interface User`)

#### 后端

- 文件：snake_case (`order_service.py`)
- 类：PascalCase (`class OrderService`)
- 函数：snake_case (`def create_order`)
- 常量：UPPER_SNAKE_CASE (`MAX_FILE_SIZE`)

---

**版本**: v1.0.0  
**更新日期**: 2025-11-05  
**文档维护**: 技术团队

