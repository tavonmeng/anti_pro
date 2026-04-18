# AI设计任务管理系统 - 代码结构指南

## 📋 文档目的

本文档详细说明项目的代码结构、文件职责、模块关系，以及如何进行代码修改和功能扩展。

---

## 🎨 前端代码结构

### 一、核心入口文件

#### 1. `src/main.ts` - 应用入口

**作用**: 创建 Vue 应用，挂载全局配置

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import ElementPlus from 'element-plus'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())      // 状态管理
app.use(router)              // 路由
app.use(ElementPlus)         // UI 组件库
app.mount('#app')
```

**修改场景**:
- 添加全局插件
- 配置全局组件
- 设置全局错误处理

#### 2. `src/App.vue` - 根组件

**作用**: 应用根容器，包含路由出口

```vue
<template>
  <router-view />
</template>
```

**很少需要修改**

---

### 二、类型定义 (`src/types/index.ts`)

#### 核心类型定义

```typescript
// 用户角色
export type UserRole = 'admin' | 'user' | 'staff'

// 订单类型
export type OrderType = 'video_purchase' | 'ai_3d_custom' | 'digital_art'

// 订单状态
export type OrderStatus = 
  | 'pending_assign'      // 待分配
  | 'in_production'       // 制作中
  | 'preview_ready'       // 预览就绪
  | 'revision_needed'     // 需要修改
  | 'final_preview'       // 终稿预览
  | 'completed'           // 已完成
  | 'cancelled'           // 已取消

// 用户接口
export interface User {
  id: string
  username: string
  role: UserRole
  email?: string
  realName?: string
  avatar?: string
}

// 订单接口
export interface Order {
  id: string
  orderNumber: string
  orderType: OrderType
  status: OrderStatus
  userId: string
  userName?: string
  assignee?: string
  assigneeId?: string
  createdAt: string
  updatedAt: string
  feedbacks: OrderFeedback[]
  revisionCount: number
  // ... 订单特定字段
}
```

**修改指南**:

**场景 1: 添加新的订单类型**
```typescript
// 1. 添加类型
export type OrderType = 
  | 'video_purchase' 
  | 'ai_3d_custom' 
  | 'digital_art'
  | 'new_type'  // 新增

// 2. 添加对应的接口
export interface NewTypeOrder extends BaseOrder {
  newField1: string
  newField2: number
}

// 3. 更新 Order 类型
export type Order = 
  | VideoPurchaseOrder 
  | AI3DCustomOrder 
  | DigitalArtOrder
  | NewTypeOrder  // 新增
```

**场景 2: 添加新的订单状态**
```typescript
export type OrderStatus = 
  | 'pending_assign'
  | 'in_production'
  | 'new_status'  // 新增
  // ...
```

---

### 三、API 层 (`src/utils/`)

#### 1. `src/utils/request.ts` - HTTP 客户端

**作用**: Axios 实例配置，请求/响应拦截

```typescript
// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器 - 添加 Token
request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - 统一处理
request.interceptors.response.use(
  response => response.data,
  error => {
    // 错误处理
    if (error.response?.status === 401) {
      router.push('/login')
    }
    return Promise.reject(error)
  }
)
```

**修改场景**:

**添加新的全局错误处理**:
```typescript
// 在响应拦截器中添加
case 403:
  ElMessage.error('权限不足')
  break
case 429:
  ElMessage.error('请求过于频繁')
  break
```

**修改 API 地址**:
```typescript
const request = axios.create({
  baseURL: 'http://localhost:8000/api',  // 修改这里
  timeout: 10000
})
```

#### 2. `src/utils/api.ts` - API 接口定义

**结构**:
```typescript
// Mock 开关
const ENABLE_MOCK = true  // 开发时用 mock，生产改为 false

// 认证 API
export const authApi = {
  login: (data: LoginRequest) => request.post('/auth/login', data),
  register: (data: RegisterRequest) => request.post('/auth/register', data),
  logout: () => request.post('/auth/logout')
}

// 订单 API
export const orderApi = {
  getOrders: (params?: any) => request.get('/orders', { params }),
  createOrder: (data: any) => request.post('/orders', data),
  getOrderDetail: (id: string) => request.get(`/orders/${id}`),
  updateStatus: (id: string, status: OrderStatus) => 
    request.put(`/orders/${id}/status`, { status }),
  assignOrder: (id: string, assigneeId: string, assigneeName: string) =>
    request.put(`/orders/${id}/assign`, { assigneeId, assigneeName }),
  uploadPreview: (id: string, files: UploadedFile[]) =>
    request.post(`/orders/${id}/preview`, { files }),
  submitFeedback: (id: string, feedback: OrderFeedback) =>
    request.post(`/orders/${id}/feedback`, feedback)
}

// 负责人 API
export const staffApi = {
  getStaff: () => request.get('/staff'),
  addStaff: (data: any) => request.post('/staff', data)
}
```

**修改指南**:

**场景 1: 添加新的 API 接口**
```typescript
// 在对应的 API 组中添加
export const orderApi = {
  // ... 现有接口
  
  // 新增接口
  deleteOrder: (id: string) => request.delete(`/orders/${id}`),
  exportOrders: (params?: any) => request.get('/orders/export', { params })
}
```

**场景 2: 修改接口路径**
```typescript
// 如果后端路径改变，修改这里
getOrders: () => request.get('/api/v2/orders'),  // 添加版本号
```

**场景 3: 关闭 Mock**
```typescript
const ENABLE_MOCK = false  // 使用真实后端
```

---

### 四、状态管理 (`src/stores/`)

#### 1. `src/stores/auth.ts` - 认证状态

**结构**:
```typescript
export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const isLoggedIn = computed(() => !!token.value)

  // 动作
  async function login(credentials: LoginRequest) {
    const response = await authApi.login(credentials)
    token.value = response.token
    user.value = response.user
    localStorage.setItem('token', response.token)
    localStorage.setItem('user', JSON.stringify(response.user))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isLoggedIn, login, logout }
})
```

**修改场景**:

**添加新的状态**:
```typescript
const userProfile = ref<UserProfile | null>(null)

async function fetchProfile() {
  userProfile.value = await userApi.getProfile()
}

return { 
  // ... 现有
  userProfile, 
  fetchProfile 
}
```

#### 2. `src/stores/order.ts` - 订单状态

**核心方法**:
```typescript
export const useOrderStore = defineStore('order', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  const currentOrder = ref<Order | null>(null)
  
  // 获取订单列表
  async function fetchOrders(filters?: any) {
    loading.value = true
    try {
      orders.value = await orderApi.getOrders(filters)
    } finally {
      loading.value = false
    }
  }
  
  // 创建订单
  async function createOrder(orderData: any) {
    const newOrder = await orderApi.createOrder(orderData)
    orders.value.unshift(newOrder)
    return newOrder
  }
  
  // 更新订单状态
  async function updateOrderStatus(id: string, status: OrderStatus) {
    const updated = await orderApi.updateStatus(id, status)
    const index = orders.value.findIndex(o => o.id === id)
    if (index !== -1) {
      orders.value[index] = updated
    }
  }
  
  return { 
    orders, 
    loading, 
    currentOrder, 
    fetchOrders, 
    createOrder, 
    updateOrderStatus 
  }
})
```

**修改指南**:

**添加筛选功能**:
```typescript
const statusFilter = ref<OrderStatus | null>(null)

const filteredOrders = computed(() => {
  if (!statusFilter.value) return orders.value
  return orders.value.filter(o => o.status === statusFilter.value)
})

function setStatusFilter(status: OrderStatus | null) {
  statusFilter.value = status
}

return { 
  // ...
  filteredOrders, 
  statusFilter, 
  setStatusFilter 
}
```

**添加统计功能**:
```typescript
const orderStats = computed(() => ({
  total: orders.value.length,
  pending: orders.value.filter(o => o.status === 'pending_assign').length,
  inProgress: orders.value.filter(o => o.status === 'in_production').length,
  completed: orders.value.filter(o => o.status === 'completed').length
}))

return { 
  // ...
  orderStats 
}
```

---

### 五、路由配置 (`src/router/index.ts`)

**结构**:
```typescript
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/user',
    component: () => import('@/views/UserDashboard.vue'),
    meta: { requiresAuth: true, role: 'user' },
    children: [
      {
        path: 'workspace',
        name: 'Workspace',
        component: () => import('@/views/user/Workspace.vue')
      },
      {
        path: 'create-order/:type',
        name: 'CreateOrder',
        component: () => import('@/views/user/CreateOrder.vue')
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/user/Orders.vue')
      }
    ]
  },
  {
    path: '/admin',
    component: () => import('@/views/AdminDashboard.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      {
        path: 'orders',
        name: 'AdminOrders',
        component: () => import('@/views/admin/OrderManagement.vue')
      }
    ]
  }
]

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})
```

**修改指南**:

**添加新路由**:
```typescript
{
  path: '/user/new-page',
  name: 'NewPage',
  component: () => import('@/views/user/NewPage.vue'),
  meta: { requiresAuth: true, role: 'user' }
}
```

**添加权限检查**:
```typescript
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth) {
    if (!authStore.isLoggedIn) {
      next('/login')
      return
    }
    
    // 角色检查
    if (to.meta.role && authStore.user?.role !== to.meta.role) {
      next('/403')  // 权限不足页面
      return
    }
  }
  
  next()
})
```

---

### 六、组件层

#### 1. 页面组件 (`src/views/`)

**结构说明**:
```
views/
├── Home.vue              # 首页
├── Login.vue             # 登录
├── Register.vue          # 注册
├── UserDashboard.vue     # 用户主布局
├── AdminDashboard.vue    # 管理员主布局
├── user/                 # 用户子页面
│   ├── Workspace.vue     # 工作台
│   ├── CreateOrder.vue   # 创建订单
│   ├── Orders.vue        # 订单列表
│   └── OrderDetail.vue   # 订单详情
└── admin/                # 管理员子页面
    ├── OrderManagement.vue
    └── AdminOrderDetail.vue
```

**典型页面结构** (`src/views/user/Workspace.vue`):
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOrderStore } from '@/stores/order'

const router = useRouter()
const orderStore = useOrderStore()

// 数据
const services = ref([
  {
    type: 'video_purchase',
    title: '裸眼3D成片购买适配',
    description: '现有视频内容适配到裸眼3D设备'
  },
  // ...
])

// 方法
function goToService(type: string) {
  router.push(`/user/create-order/${type}`)
}

// 生命周期
onMounted(() => {
  orderStore.fetchOrders()
})
</script>

<template>
  <div class="workspace">
    <div class="service-cards">
      <div 
        v-for="service in services" 
        :key="service.type"
        class="service-card"
        @click="goToService(service.type)"
      >
        <h3>{{ service.title }}</h3>
        <p>{{ service.description }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.workspace {
  padding: 20px;
}
</style>
```

**修改指南**:

**添加新页面**:
1. 创建 `.vue` 文件
2. 在 `router/index.ts` 添加路由
3. 在导航菜单添加链接

#### 2. 可复用组件 (`src/components/`)

**组件分类**:

**表单组件**:
- `VideoPurchaseForm.vue` - 成片购买表单
- `AI3DCustomForm.vue` - AI定制表单
- `DigitalArtForm.vue` - 数字艺术表单
- `FileUpload.vue` - 文件上传

**展示组件**:
- `OrderCard.vue` - 订单卡片
- `OrderStatusBadge.vue` - 状态标签
- `Sidebar.vue` - 侧边栏

**对话框组件**:
- `AssigneeDialog.vue` - 分配负责人
- `UploadPreviewDialog.vue` - 上传预览

**典型组件结构** (`src/components/OrderCard.vue`):
```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { Order } from '@/types'

// Props
const props = defineProps<{
  order: Order
}>()

// Emits
const emit = defineEmits<{
  'view-detail': [id: string]
  'update-status': [id: string, status: string]
}>()

// 计算属性
const statusColor = computed(() => {
  const colors = {
    'pending_assign': 'warning',
    'in_production': 'primary',
    'completed': 'success'
  }
  return colors[props.order.status] || 'info'
})

// 方法
function handleViewDetail() {
  emit('view-detail', props.order.id)
}
</script>

<template>
  <el-card class="order-card">
    <div class="order-header">
      <span class="order-number">{{ order.orderNumber }}</span>
      <el-tag :type="statusColor">{{ order.status }}</el-tag>
    </div>
    <div class="order-content">
      <p>类型: {{ order.orderType }}</p>
      <p>创建时间: {{ order.createdAt }}</p>
    </div>
    <div class="order-actions">
      <el-button @click="handleViewDetail">查看详情</el-button>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.order-card {
  margin-bottom: 16px;
}
</style>
```

**修改指南**:

**创建新组件**:
```vue
<!-- src/components/NewComponent.vue -->
<script setup lang="ts">
// 定义 Props
interface Props {
  title: string
  count?: number
}

const props = withDefaults(defineProps<Props>(), {
  count: 0
})

// 定义 Emits
const emit = defineEmits<{
  'update': [value: string]
  'delete': []
}>()
</script>

<template>
  <div>{{ title }} ({{ count }})</div>
</template>
```

**使用组件**:
```vue
<script setup>
import NewComponent from '@/components/NewComponent.vue'
</script>

<template>
  <NewComponent 
    title="标题" 
    :count="10"
    @update="handleUpdate"
    @delete="handleDelete"
  />
</template>
```

---

## ⚙️ 后端代码结构

### 一、应用入口 (`backend/app/main.py`)

**结构**:
```python
from fastapi import FastAPI
from app.api import auth, orders, staff
from app.middleware.cors import setup_cors

app = FastAPI(
    title="AI设计任务管理系统",
    version="1.0.0"
)

# 配置 CORS
setup_cors(app)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(staff.router, prefix="/api")

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/")
async def root():
    return {"app": "AI设计任务管理系统"}
```

**修改指南**:

**添加新的路由模块**:
```python
from app.api import new_module

app.include_router(new_module.router, prefix="/api")
```

**添加中间件**:
```python
from app.middleware.logging import LoggingMiddleware

app.add_middleware(LoggingMiddleware)
```

---

### 二、数据模型层 (`backend/app/models/`)

#### 1. `models/user.py` - 用户模型

```python
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    STAFF = "staff"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(50), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    email = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
```

**修改指南**:

**添加新字段**:
```python
class User(Base):
    # ... 现有字段
    phone = Column(String(20))  # 新增
    department = Column(String(50))  # 新增
```

**添加索引**:
```python
from sqlalchemy import Index

class User(Base):
    # ... 字段定义
    
    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_email', 'email'),
    )
```

#### 2. `models/order.py` - 订单模型

```python
class OrderType(str, enum.Enum):
    VIDEO_PURCHASE = "video_purchase"
    AI_3D_CUSTOM = "ai_3d_custom"
    DIGITAL_ART = "digital_art"

class OrderStatus(str, enum.Enum):
    PENDING_ASSIGN = "pending_assign"
    IN_PRODUCTION = "in_production"
    # ...

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String(50), primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING_ASSIGN)
    user_id = Column(String(50), ForeignKey("users.id"))
    order_data = Column(JSON, nullable=False)
    
    # 关系
    files = relationship("File", back_populates="order")
    feedbacks = relationship("Feedback", back_populates="order")
```

**修改指南**:

**添加新的订单类型**:
```python
class OrderType(str, enum.Enum):
    VIDEO_PURCHASE = "video_purchase"
    AI_3D_CUSTOM = "ai_3d_custom"
    DIGITAL_ART = "digital_art"
    NEW_TYPE = "new_type"  # 新增
```

**添加新的订单状态**:
```python
class OrderStatus(str, enum.Enum):
    # ... 现有状态
    NEW_STATUS = "new_status"  # 新增
```

---

### 三、数据验证层 (`backend/app/schemas/`)

#### 1. `schemas/order.py` - 订单 Schema

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class VideoPurchaseOrderCreate(BaseModel):
    orderType: str = "video_purchase"
    industryType: str
    visualStyle: str
    duration: int
    priceRange: dict
    resolution: str
    size: str

class OrderResponse(BaseModel):
    id: str
    orderNumber: str
    orderType: str
    status: str
    userId: str
    createdAt: datetime
    
    class Config:
        from_attributes = True
```

**修改指南**:

**添加新的订单类型 Schema**:
```python
class NewTypeOrderCreate(BaseModel):
    orderType: str = "new_type"
    field1: str
    field2: int
    field3: Optional[str] = None
```

**添加验证规则**:
```python
from pydantic import validator

class OrderCreate(BaseModel):
    duration: int
    
    @validator('duration')
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError('时长必须大于0')
        if v > 3600:
            raise ValueError('时长不能超过3600秒')
        return v
```

---

### 四、业务逻辑层 (`backend/app/services/`)

#### 1. `services/order_service.py` - 订单服务

**核心类**:
```python
class OrderStateMachine:
    """订单状态机"""
    
    ALLOWED_TRANSITIONS = {
        OrderStatus.PENDING_ASSIGN: [
            OrderStatus.IN_PRODUCTION, 
            OrderStatus.CANCELLED
        ],
        OrderStatus.IN_PRODUCTION: [
            OrderStatus.PREVIEW_READY,
            OrderStatus.FINAL_PREVIEW,
            OrderStatus.CANCELLED
        ],
        # ...
    }
    
    @classmethod
    def can_transition(cls, from_status, to_status) -> bool:
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def validate_transition(cls, from_status, to_status):
        if not cls.can_transition(from_status, to_status):
            raise HTTPException(
                status_code=400,
                detail=f"非法的状态转换: {from_status} -> {to_status}"
            )

class OrderService:
    """订单服务"""
    
    @staticmethod
    async def create_order(db: AsyncSession, order_data, user: User):
        order_id = generate_id("order")
        order_number = generate_order_number()
        
        new_order = Order(
            id=order_id,
            order_number=order_number,
            order_type=order_data.orderType,
            status=OrderStatus.PENDING_ASSIGN,
            user_id=user.id,
            order_data=order_data.model_dump()
        )
        
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)
        
        return new_order
    
    @staticmethod
    async def update_order_status(
        db: AsyncSession, 
        order_id: str, 
        new_status: OrderStatus,
        current_user: User
    ):
        order = await db.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 验证状态转换
        OrderStateMachine.validate_transition(order.status, new_status)
        
        # 权限检查
        if current_user.role not in [UserRole.ADMIN, UserRole.STAFF]:
            raise HTTPException(status_code=403, detail="权限不足")
        
        old_status = order.status
        order.status = new_status
        
        await db.commit()
        
        # 发送邮件通知
        await EmailService.send_status_notification(...)
        
        return order
```

**修改指南**:

**添加新的业务方法**:
```python
class OrderService:
    # ... 现有方法
    
    @staticmethod
    async def batch_update_status(
        db: AsyncSession,
        order_ids: List[str],
        new_status: OrderStatus,
        current_user: User
    ):
        """批量更新订单状态"""
        updated_orders = []
        
        for order_id in order_ids:
            order = await OrderService.update_order_status(
                db, order_id, new_status, current_user
            )
            updated_orders.append(order)
        
        return updated_orders
```

**修改状态转换规则**:
```python
class OrderStateMachine:
    ALLOWED_TRANSITIONS = {
        OrderStatus.PENDING_ASSIGN: [
            OrderStatus.IN_PRODUCTION,
            OrderStatus.CANCELLED,
            OrderStatus.NEW_STATUS  # 新增允许的转换
        ],
        # ...
    }
```

---

### 五、API 路由层 (`backend/app/api/`)

#### 1. `api/orders.py` - 订单 API

```python
from fastapi import APIRouter, Depends, HTTPException
from app.services.order_service import OrderService
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/orders", tags=["订单"])

@router.get("")
async def get_orders(
    order_type: Optional[OrderType] = None,
    status: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取订单列表"""
    orders = await OrderService.get_orders(
        db, current_user, order_type, status
    )
    return ApiResponse(code=200, message="获取成功", data=orders)

@router.post("")
async def create_order(
    order_data: Union[VideoPurchaseOrderCreate, ...],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建订单"""
    order = await OrderService.create_order(db, order_data, current_user)
    return ApiResponse(code=201, message="创建成功", data=order)

@router.put("/{order_id}/status")
async def update_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(require_admin_or_staff),
    db: AsyncSession = Depends(get_db)
):
    """更新订单状态"""
    order = await OrderService.update_order_status(
        db, order_id, status_update.status, current_user
    )
    return ApiResponse(code=200, message="更新成功", data=order)
```

**修改指南**:

**添加新的 API 端点**:
```python
@router.get("/{order_id}/history")
async def get_order_history(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取订单历史"""
    history = await OrderService.get_order_history(db, order_id, current_user)
    return ApiResponse(code=200, message="获取成功", data=history)

@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除订单（仅管理员）"""
    await OrderService.delete_order(db, order_id)
    return ApiResponse(code=200, message="删除成功")
```

**添加查询参数**:
```python
@router.get("")
async def get_orders(
    order_type: Optional[OrderType] = None,
    status: Optional[OrderStatus] = None,
    start_date: Optional[str] = None,  # 新增
    end_date: Optional[str] = None,    # 新增
    page: int = 1,                     # 新增
    page_size: int = 20,               # 新增
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取订单列表（支持分页和日期筛选）"""
    orders = await OrderService.get_orders(
        db, current_user, 
        order_type, status, start_date, end_date, 
        page, page_size
    )
    return ApiResponse(code=200, message="获取成功", data=orders)
```

---

### 六、工具函数层 (`backend/app/utils/`)

#### 1. `utils/security.py` - 安全工具

```python
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """加密密码"""
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    """解码 JWT Token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
```

#### 2. `utils/dependencies.py` - 依赖注入

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前用户"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="无效的 Token")
    
    user_id = payload.get("user_id")
    user = await db.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return user

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """要求管理员权限"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user
```

---

## 🔧 常见开发场景

### 场景 1: 添加新的订单类型

#### 前端修改

**1. 更新类型定义** (`src/types/index.ts`):
```typescript
export type OrderType = 
  | 'video_purchase' 
  | 'ai_3d_custom' 
  | 'digital_art'
  | 'new_order_type'  // 新增

export interface NewOrderType extends BaseOrder {
  customField1: string
  customField2: number
}

export type Order = 
  | VideoPurchaseOrder 
  | AI3DCustomOrder 
  | DigitalArtOrder
  | NewOrderType  // 新增
```

**2. 创建表单组件** (`src/components/NewOrderTypeForm.vue`):
```vue
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const formData = ref({
  customField1: '',
  customField2: 0
})

const emit = defineEmits<{
  'submit': [data: any]
  'cancel': []
}>()

function handleSubmit() {
  emit('submit', {
    orderType: 'new_order_type',
    ...formData.value
  })
}
</script>

<template>
  <el-form :model="formData">
    <el-form-item label="字段1">
      <el-input v-model="formData.customField1" />
    </el-form-item>
    <el-form-item label="字段2">
      <el-input-number v-model="formData.customField2" />
    </el-form-item>
    <div class="form-actions">
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="primary" @click="handleSubmit">提交</el-button>
    </div>
  </el-form>
</template>
```

**3. 更新创建订单页面** (`src/views/user/CreateOrder.vue`):
```vue
<script setup>
import NewOrderTypeForm from '@/components/NewOrderTypeForm.vue'

const orderType = route.params.type

const formComponents = {
  'video_purchase': VideoPurchaseForm,
  'ai_3d_custom': AI3DCustomForm,
  'digital_art': DigitalArtForm,
  'new_order_type': NewOrderTypeForm  // 新增
}
</script>

<template>
  <component 
    :is="formComponents[orderType]"
    @submit="handleSubmit"
    @cancel="handleCancel"
  />
</template>
```

**4. 更新工作台** (`src/views/user/Workspace.vue`):
```vue
<script setup>
const services = ref([
  // ... 现有服务
  {
    type: 'new_order_type',
    title: '新订单类型',
    description: '新订单类型的描述',
    icon: 'Document'
  }
])
</script>
```

#### 后端修改

**1. 更新枚举** (`backend/app/models/order.py`):
```python
class OrderType(str, enum.Enum):
    VIDEO_PURCHASE = "video_purchase"
    AI_3D_CUSTOM = "ai_3d_custom"
    DIGITAL_ART = "digital_art"
    NEW_ORDER_TYPE = "new_order_type"  # 新增
```

**2. 创建 Schema** (`backend/app/schemas/order.py`):
```python
class NewOrderTypeCreate(BaseModel):
    orderType: str = "new_order_type"
    customField1: str
    customField2: int

class NewOrderTypeResponse(BaseOrderResponse):
    customField1: str
    customField2: int
```

**3. 更新服务** (`backend/app/services/order_service.py`):
```python
class OrderService:
    @staticmethod
    async def create_order(db, order_data, user):
        order_type_map = {
            "video_purchase": OrderType.VIDEO_PURCHASE,
            "ai_3d_custom": OrderType.AI_3D_CUSTOM,
            "digital_art": OrderType.DIGITAL_ART,
            "new_order_type": OrderType.NEW_ORDER_TYPE  # 新增
        }
        # ... 其余逻辑
```

**4. 更新 API** (`backend/app/api/orders.py`):
```python
@router.post("")
async def create_order(
    order_data: Union[
        VideoPurchaseOrderCreate, 
        AI3DCustomOrderCreate, 
        DigitalArtOrderCreate,
        NewOrderTypeCreate  # 新增
    ],
    # ...
):
    pass
```

---

### 场景 2: 添加新的 API 端点

#### 后端实现

**1. 在 Service 添加方法**:
```python
# backend/app/services/order_service.py
class OrderService:
    @staticmethod
    async def export_orders(
        db: AsyncSession,
        filters: dict,
        current_user: User
    ) -> bytes:
        """导出订单为 Excel"""
        orders = await OrderService.get_orders(db, current_user, **filters)
        
        # 生成 Excel
        import pandas as pd
        df = pd.DataFrame([order.dict() for order in orders])
        
        # 转换为 bytes
        from io import BytesIO
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        
        return output.getvalue()
```

**2. 在 API 添加端点**:
```python
# backend/app/api/orders.py
from fastapi.responses import StreamingResponse

@router.get("/export")
async def export_orders(
    order_type: Optional[OrderType] = None,
    status: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出订单"""
    excel_data = await OrderService.export_orders(
        db, 
        {"order_type": order_type, "status": status},
        current_user
    )
    
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=orders.xlsx"}
    )
```

#### 前端调用

**1. 在 API 层添加方法**:
```typescript
// src/utils/api.ts
export const orderApi = {
  // ... 现有方法
  
  exportOrders: (params?: any) => {
    return request.get('/orders/export', { 
      params,
      responseType: 'blob'  // 重要！
    })
  }
}
```

**2. 在组件中调用**:
```vue
<script setup>
import { orderApi } from '@/utils/api'

async function handleExport() {
  try {
    const blob = await orderApi.exportOrders({
      orderType: 'video_purchase',
      status: 'completed'
    })
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'orders.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}
</script>

<template>
  <el-button @click="handleExport">导出订单</el-button>
</template>
```

---

### 场景 3: 添加新的订单状态

**1. 后端 - 更新枚举**:
```python
# backend/app/models/order.py
class OrderStatus(str, enum.Enum):
    PENDING_ASSIGN = "pending_assign"
    IN_PRODUCTION = "in_production"
    PREVIEW_READY = "preview_ready"
    REVISION_NEEDED = "revision_needed"
    FINAL_PREVIEW = "final_preview"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NEW_STATUS = "new_status"  # 新增
```

**2. 后端 - 更新状态机**:
```python
# backend/app/services/order_service.py
class OrderStateMachine:
    ALLOWED_TRANSITIONS = {
        # ... 现有转换规则
        OrderStatus.NEW_STATUS: [
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED
        ]
    }
```

**3. 前端 - 更新类型**:
```typescript
// src/types/index.ts
export type OrderStatus = 
  | 'pending_assign'
  | 'in_production'
  | 'preview_ready'
  | 'revision_needed'
  | 'final_preview'
  | 'completed'
  | 'cancelled'
  | 'new_status'  // 新增
```

**4. 前端 - 更新状态显示**:
```vue
<!-- src/components/OrderStatusBadge.vue -->
<script setup>
const statusMap = {
  'pending_assign': { label: '待分配', type: 'warning' },
  'in_production': { label: '制作中', type: 'primary' },
  'new_status': { label: '新状态', type: 'info' }  // 新增
}
</script>
```

---

### 场景 4: 添加权限控制

**1. 后端 - 创建权限装饰器**:
```python
# backend/app/utils/dependencies.py
async def require_permission(
    permission: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """检查用户权限"""
    user_permissions = get_user_permissions(current_user.role)
    
    if permission not in user_permissions:
        raise HTTPException(status_code=403, detail="权限不足")
    
    return current_user

def get_user_permissions(role: UserRole) -> List[str]:
    """获取角色权限"""
    permissions = {
        UserRole.ADMIN: [
            "order:create", "order:view", "order:update", "order:delete",
            "staff:create", "staff:view", "staff:update", "staff:delete"
        ],
        UserRole.STAFF: [
            "order:view", "order:update"
        ],
        UserRole.USER: [
            "order:create", "order:view"
        ]
    }
    return permissions.get(role, [])
```

**2. 后端 - 在 API 中使用**:
```python
# backend/app/api/orders.py
@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    current_user: User = Depends(
        lambda: require_permission("order:delete")
    ),
    db: AsyncSession = Depends(get_db)
):
    """删除订单（需要 order:delete 权限）"""
    await OrderService.delete_order(db, order_id)
    return ApiResponse(code=200, message="删除成功")
```

**3. 前端 - 权限判断**:
```vue
<script setup>
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// 权限映射
const permissions = {
  'admin': ['order:create', 'order:view', 'order:update', 'order:delete'],
  'staff': ['order:view', 'order:update'],
  'user': ['order:create', 'order:view']
}

function hasPermission(permission: string) {
  const userPerms = permissions[authStore.user?.role] || []
  return userPerms.includes(permission)
}
</script>

<template>
  <div>
    <el-button 
      v-if="hasPermission('order:create')"
      @click="createOrder"
    >
      创建订单
    </el-button>
    
    <el-button 
      v-if="hasPermission('order:delete')"
      @click="deleteOrder"
      type="danger"
    >
      删除订单
    </el-button>
  </div>
</template>
```

---

## 📝 代码风格规范

### 前端规范

**命名约定**:
- 组件: PascalCase (`OrderCard.vue`)
- 函数: camelCase (`fetchOrders`)
- 常量: UPPER_SNAKE_CASE (`API_BASE_URL`)
- 文件: kebab-case 或 PascalCase

**Vue 组件结构顺序**:
```vue
<script setup lang="ts">
// 1. 导入
import { ref } from 'vue'

// 2. Props
const props = defineProps<{}>()

// 3. Emits
const emit = defineEmits<{}>()

// 4. 数据
const data = ref()

// 5. 计算属性
const computed = computed(() => {})

// 6. 方法
function method() {}

// 7. 生命周期
onMounted(() => {})
</script>

<template>
  <!-- 模板 -->
</template>

<style scoped lang="scss">
/* 样式 */
</style>
```

### 后端规范

**命名约定**:
- 文件: snake_case (`order_service.py`)
- 类: PascalCase (`class OrderService`)
- 函数: snake_case (`def create_order()`)
- 常量: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`)

**代码结构顺序**:
```python
# 1. 标准库导入
import os
from datetime import datetime

# 2. 第三方库导入
from fastapi import APIRouter
from sqlalchemy import select

# 3. 本地导入
from app.models import Order
from app.schemas import OrderCreate

# 4. 常量定义
MAX_ORDERS = 100

# 5. 类和函数定义
class OrderService:
    pass
```

---

## 🎯 总结

### 代码修改流程

1. **确定需求** - 明确要添加/修改什么功能
2. **修改类型定义** - 更新 TypeScript/Python 类型
3. **修改数据模型** - 更新数据库模型（如需要）
4. **修改业务逻辑** - 在 Service 层实现逻辑
5. **修改 API 层** - 添加/修改 API 端点
6. **修改前端 API** - 更新 API 调用
7. **修改 UI 组件** - 更新界面展示
8. **测试验证** - 测试新功能

### 关键文件速查

| 想做什么 | 修改的文件 |
|---------|-----------|
| 添加新的订单类型 | `types/index.ts`, `models/order.py`, `schemas/order.py`, 新建表单组件 |
| 添加新的 API | `services/*.py`, `api/*.py`, `utils/api.ts` |
| 添加新页面 | `views/` 创建组件, `router/index.ts` 添加路由 |
| 添加新的状态 | `types/index.ts`, `models/order.py`, `services/order_service.py` |
| 修改权限 | `utils/dependencies.py`, 路由守卫 |
| 添加新字段 | 数据模型、Schema、表单组件 |

---

_文档版本: v1.0.0_  
_最后更新: 2025-11-05_  
_维护: 开发团队_

