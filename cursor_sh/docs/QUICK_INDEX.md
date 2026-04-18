# 快速代码索引

> 这是一个快速查找表，帮助你在 3 秒内找到需要修改的代码位置。

---

## 🎯 我想做什么？

### 📝 添加/修改功能

| 我想... | 去哪里 | 文件路径 |
|---------|--------|----------|
| **添加新的订单类型** | 类型定义 | `src/types/index.ts` |
| | 后端模型 | `backend/app/models/order.py` |
| | 后端 Schema | `backend/app/schemas/order.py` |
| | 创建表单组件 | `src/components/NewOrderForm.vue` |
| | 更新工作台 | `src/views/user/Workspace.vue` |
| **添加新的订单状态** | 类型定义 | `src/types/index.ts` |
| | 后端模型 | `backend/app/models/order.py` |
| | 状态机逻辑 | `backend/app/services/order_service.py` |
| | 状态显示 | `src/components/OrderStatusBadge.vue` |
| **添加新的 API 端点** | 后端服务层 | `backend/app/services/*.py` |
| | 后端路由 | `backend/app/api/*.py` |
| | 前端 API 调用 | `src/utils/api.ts` |
| **添加新页面** | 创建组件 | `src/views/NewPage.vue` |
| | 添加路由 | `src/router/index.ts` |
| | 添加导航 | `src/components/Sidebar.vue` |
| **修改数据库表结构** | 后端模型 | `backend/app/models/*.py` |
| | Schema | `backend/app/schemas/*.py` |
| | 前端类型 | `src/types/index.ts` |
| **修改权限控制** | 后端依赖 | `backend/app/utils/dependencies.py` |
| | 路由守卫 | `src/router/index.ts` |

---

## 🔍 按文件类型查找

### 前端文件

#### 页面组件 (`src/views/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `Home.vue` | 首页 | 修改首页内容、轮播图 |
| `Login.vue` | 登录页 | 修改登录界面、验证逻辑 |
| `Register.vue` | 注册页 | 修改注册表单、验证规则 |
| `UserDashboard.vue` | 用户主布局 | 修改用户界面整体布局 |
| `AdminDashboard.vue` | 管理员主布局 | 修改管理员界面整体布局 |
| `user/Workspace.vue` | 用户工作台 | 添加/修改服务入口 |
| `user/CreateOrder.vue` | 创建订单 | 修改订单创建流程 |
| `user/Orders.vue` | 订单列表 | 修改订单展示、筛选 |
| `user/OrderDetail.vue` | 订单详情 | 修改订单详情展示 |
| `admin/OrderManagement.vue` | 订单管理 | 修改管理员订单管理界面 |

#### 可复用组件 (`src/components/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `OrderCard.vue` | 订单卡片 | 修改订单卡片样式、内容 |
| `OrderStatusBadge.vue` | 状态标签 | 添加新状态、修改状态样式 |
| `Sidebar.vue` | 侧边栏 | 修改导航菜单 |
| `FileUpload.vue` | 文件上传 | 修改文件上传逻辑、限制 |
| `VideoPurchaseForm.vue` | 成片购买表单 | 修改成片购买表单字段 |
| `AI3DCustomForm.vue` | AI定制表单 | 修改AI定制表单字段 |
| `DigitalArtForm.vue` | 数字艺术表单 | 修改数字艺术表单字段 |
| `AssigneeDialog.vue` | 分配负责人 | 修改分配逻辑 |
| `UploadPreviewDialog.vue` | 上传预览 | 修改预览上传界面 |

#### 状态管理 (`src/stores/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `auth.ts` | 认证状态 | 修改登录/登出逻辑、用户信息 |
| `order.ts` | 订单状态 | 添加订单相关方法、筛选逻辑 |
| `staff.ts` | 负责人状态 | 修改负责人管理逻辑 |

#### 工具函数 (`src/utils/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `request.ts` | HTTP 客户端 | 修改请求拦截、错误处理 |
| `api.ts` | API 接口定义 | 添加新的 API 调用 |
| `validators.ts` | 数据验证 | 添加新的验证规则 |

#### 类型定义 (`src/types/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `index.ts` | 全局类型 | 添加新类型、修改现有接口 |

---

### 后端文件

#### API 路由 (`backend/app/api/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `auth.py` | 认证接口 | 修改登录/注册逻辑 |
| `orders.py` | 订单接口 | 添加订单相关 API |
| `staff.py` | 负责人接口 | 修改负责人管理 API |

#### 数据模型 (`backend/app/models/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `user.py` | 用户模型 | 修改用户表结构、添加字段 |
| `order.py` | 订单模型 | 修改订单表结构、添加字段 |
| `file.py` | 文件模型 | 修改文件存储逻辑 |
| `feedback.py` | 反馈模型 | 修改反馈表结构 |

#### 数据验证 (`backend/app/schemas/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `auth.py` | 认证 Schema | 修改登录/注册请求格式 |
| `user.py` | 用户 Schema | 修改用户数据格式 |
| `order.py` | 订单 Schema | 添加新订单类型、修改字段 |
| `file.py` | 文件 Schema | 修改文件数据格式 |
| `feedback.py` | 反馈 Schema | 修改反馈数据格式 |

#### 业务逻辑 (`backend/app/services/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `auth_service.py` | 认证服务 | 修改认证逻辑 |
| `order_service.py` | 订单服务 | **核心业务逻辑**，状态机在这里 |
| `file_service.py` | 文件服务 | 修改文件存储、OSS 逻辑 |
| `email_service.py` | 邮件服务 | 修改邮件发送逻辑 |

#### 工具函数 (`backend/app/utils/`)

| 文件 | 用途 | 什么时候修改 |
|------|------|-------------|
| `security.py` | 安全工具 | 修改 JWT、密码加密 |
| `dependencies.py` | 依赖注入 | **权限控制在这里** |
| `validators.py` | 验证器 | 添加数据验证函数 |

---

## 🎨 按业务场景查找

### 场景 1: 订单相关

| 要做什么 | 前端文件 | 后端文件 |
|---------|---------|---------|
| 创建订单 | `views/user/CreateOrder.vue`<br>`components/*Form.vue`<br>`utils/api.ts` | `api/orders.py:create_order`<br>`services/order_service.py:create_order`<br>`models/order.py` |
| 订单列表 | `views/user/Orders.vue`<br>`views/admin/OrderManagement.vue`<br>`components/OrderCard.vue` | `api/orders.py:get_orders`<br>`services/order_service.py:get_orders` |
| 订单详情 | `views/user/OrderDetail.vue`<br>`views/admin/AdminOrderDetail.vue` | `api/orders.py:get_order_detail`<br>`services/order_service.py:get_order_by_id` |
| 更新状态 | `stores/order.ts:updateOrderStatus`<br>`components/OrderStatusBadge.vue` | `api/orders.py:update_status`<br>`services/order_service.py:update_order_status`<br>**状态机在这里** ⭐ |
| 分配负责人 | `components/AssigneeDialog.vue`<br>`stores/order.ts:assignOrder` | `api/orders.py:assign_order`<br>`services/order_service.py:assign_order` |
| 上传预览 | `components/UploadPreviewDialog.vue`<br>`components/FileUpload.vue` | `api/orders.py:upload_preview`<br>`services/order_service.py:upload_order_preview`<br>`services/file_service.py` |
| 提交反馈 | `views/user/OrderDetail.vue`<br>`views/admin/AdminOrderDetail.vue` | `api/orders.py:submit_feedback`<br>`services/order_service.py:submit_order_feedback` |

### 场景 2: 用户认证

| 要做什么 | 前端文件 | 后端文件 |
|---------|---------|---------|
| 用户登录 | `views/Login.vue`<br>`stores/auth.ts:login` | `api/auth.py:login_for_access_token`<br>`services/auth_service.py:authenticate_user` |
| 用户注册 | `views/Register.vue`<br>`stores/auth.ts:register` | `api/auth.py:register_new_user`<br>`services/auth_service.py:register_user` |
| 退出登录 | `stores/auth.ts:logout` | `api/auth.py:logout_user` |
| 权限验证 | `router/index.ts:beforeEach` | `utils/dependencies.py:get_current_user`<br>`utils/dependencies.py:require_admin` |

### 场景 3: 文件上传

| 要做什么 | 前端文件 | 后端文件 |
|---------|---------|---------|
| 上传文件 | `components/FileUpload.vue` | `api/orders.py:upload_preview`<br>`services/file_service.py:save_file_local` |
| 文件预览 | `views/user/OrderDetail.vue`<br>`views/admin/AdminOrderDetail.vue` | `services/file_service.py:get_file_url` |
| OSS 存储 | - | `services/file_service.py:upload_file_oss` |

### 场景 4: 邮件通知

| 要做什么 | 后端文件 |
|---------|---------|
| 状态更新通知 | `services/email_service.py:send_order_status_update_email` |
| 预览就绪通知 | `services/email_service.py:send_preview_ready_email` |
| 邮件配置 | `config.py:Settings`<br>`.env:SMTP_*` |

---

## 🔧 按修改类型查找

### 修改 UI 样式

| 要修改的样式 | 文件位置 |
|-------------|----------|
| 全局样式 | `src/styles/main.scss` |
| 全局变量 | `src/styles/variables.scss` |
| 组件样式 | 组件内的 `<style scoped>` |
| Element Plus 主题 | `src/main.ts` + Element Plus 主题配置 |

### 修改业务逻辑

| 业务逻辑 | 文件位置 |
|---------|----------|
| **订单状态机** | `backend/app/services/order_service.py:OrderStateMachine` ⭐ |
| 订单创建 | `backend/app/services/order_service.py:create_order` |
| 订单查询 | `backend/app/services/order_service.py:get_orders` |
| 状态更新 | `backend/app/services/order_service.py:update_order_status` |
| 文件上传 | `backend/app/services/file_service.py` |
| 邮件发送 | `backend/app/services/email_service.py` |

### 修改数据库

| 要做什么 | 文件位置 |
|---------|----------|
| 添加表 | `backend/app/models/` 新建文件 |
| 修改表结构 | `backend/app/models/*.py` 对应模型 |
| 修改关系 | `backend/app/models/*.py` relationship 定义 |
| 数据库配置 | `backend/app/database.py`<br>`backend/.env:DATABASE_URL` |

### 修改权限

| 要做什么 | 文件位置 |
|---------|----------|
| 添加角色 | `backend/app/models/user.py:UserRole` |
| 权限检查 | `backend/app/utils/dependencies.py` |
| 路由守卫 | `src/router/index.ts:beforeEach` |
| API 权限 | `backend/app/api/*.py` 的 `Depends()` |

---

## 📊 核心数据流

### 创建订单流程

```
用户操作                     前端                          后端
  │                          │                             │
  ├─> 填写表单                │                             │
  │   (CreateOrder.vue)      │                             │
  │                          │                             │
  ├─> 点击提交 ──────────────> 调用 API                     │
  │                          (api.ts:createOrder)          │
  │                          │                             │
  │                          ├─> 发送请求 ───────────────> 路由接收
  │                          │   (request.ts)             (api/orders.py:create_order)
  │                          │                             │
  │                          │                             ├─> 业务处理
  │                          │                             │   (services/order_service.py:create_order)
  │                          │                             │
  │                          │                             ├─> 生成订单号
  │                          │                             │   (utils/validators.py:generate_order_number)
  │                          │                             │
  │                          │                             ├─> 保存数据库
  │                          │                             │   (models/order.py)
  │                          │                             │
  │                          │   <─────────────────────── 返回结果
  │                          │                             │
  │   <─────────────────────┤ 更新状态                     │
  │                          (stores/order.ts:createOrder) │
  │                          │                             │
  └─> 显示成功 ───────────────┤                             │
      跳转到订单列表          │                             │
```

### 状态更新流程

```
管理员/负责人               前端                          后端
  │                          │                             │
  ├─> 选择新状态              │                             │
  │   (AdminOrderDetail.vue) │                             │
  │                          │                             │
  ├─> 点击确认 ──────────────> 调用 API                     │
  │                          (api.ts:updateStatus)         │
  │                          │                             │
  │                          ├─> 发送请求 ───────────────> 路由接收
  │                          │                             (api/orders.py:update_status)
  │                          │                             │
  │                          │                             ├─> 业务处理
  │                          │                             │   (services/order_service.py:update_order_status)
  │                          │                             │
  │                          │                             ├─> ⭐ 状态机验证
  │                          │                             │   (OrderStateMachine.validate_transition)
  │                          │                             │   - 检查状态转换是否合法
  │                          │                             │   - 不合法抛出异常
  │                          │                             │
  │                          │                             ├─> 权限检查
  │                          │                             │   (dependencies.py:require_admin_or_staff)
  │                          │                             │
  │                          │                             ├─> 更新数据库
  │                          │                             │   (models/order.py)
  │                          │                             │
  │                          │                             ├─> 发送邮件通知
  │                          │                             │   (services/email_service.py:send_status_notification)
  │                          │                             │
  │                          │   <─────────────────────── 返回结果
  │                          │                             │
  │   <─────────────────────┤ 更新状态                     │
  │                          (stores/order.ts)             │
  │                          │                             │
  └─> 显示成功 ───────────────┤                             │
      界面刷新                │                             │
```

---

## 🎯 快速修改模板

### 添加新的 API 端点（完整示例）

#### 步骤 1: 后端 Service (业务逻辑)
```python
# backend/app/services/order_service.py
class OrderService:
    @staticmethod
    async def new_method(db: AsyncSession, param1: str, current_user: User):
        """新的业务方法"""
        # 实现逻辑
        result = await db.execute(...)
        return result
```

#### 步骤 2: 后端 API (路由)
```python
# backend/app/api/orders.py
@router.post("/new-endpoint")
async def new_endpoint(
    request_data: NewSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """新的 API 端点"""
    result = await OrderService.new_method(db, request_data.param1, current_user)
    return ApiResponse(code=200, message="成功", data=result)
```

#### 步骤 3: 前端 API (接口定义)
```typescript
// src/utils/api.ts
export const orderApi = {
  // ... 现有方法
  newEndpoint: (data: any) => request.post('/orders/new-endpoint', data)
}
```

#### 步骤 4: 前端调用 (在组件中使用)
```vue
<script setup>
import { orderApi } from '@/utils/api'

async function handleAction() {
  const result = await orderApi.newEndpoint({ param1: 'value' })
  console.log(result)
}
</script>
```

---

## 💡 开发技巧

### 调试技巧

| 要调试什么 | 怎么做 | 在哪里 |
|-----------|--------|--------|
| 前端 API 请求 | 打开浏览器开发者工具 > Network | Chrome DevTools |
| 前端状态 | 安装 Vue DevTools 扩展 | Chrome/Firefox |
| 后端日志 | 查看终端输出 | 运行 `uvicorn` 的终端 |
| 后端调试 | 在代码中添加 `print()` 或使用调试器 | VS Code / PyCharm |
| 数据库查询 | 使用 SQLite Browser | DB Browser for SQLite |

### 快捷操作

| 要做什么 | 命令 | 备注 |
|---------|------|------|
| 快速启动前端 | `npm run dev` | 默认端口 3000 |
| 快速启动后端 | `cd backend && bash run.sh` | 自动创建虚拟环境 |
| 重置数据库 | `rm backend/app.db && python backend/scripts/init_admin.py` | 删除后重新初始化 |
| 备份数据库 | `python backend/scripts/backup_db.py` | 备份到 backups/ |
| 查看 API 文档 | 访问 `http://localhost:8000/docs` | 后端需要运行 |
| 测试 API | 导入 Postman 集合 | `api-spec/postman_collection.json` |

---

## 📞 需要帮助？

| 问题类型 | 查看文档 |
|---------|---------|
| 不知道代码在哪 | 本文档（快速索引） |
| 不知道怎么修改 | [代码结构指南](./CODE_STRUCTURE.md) |
| 不了解业务流程 | [产品文档](./PRODUCT_GUIDE.md) |
| 不了解技术架构 | [技术文档](./TECHNICAL_GUIDE.md) |
| 需要部署上线 | [部署文档](./DEPLOYMENT_GUIDE.md) |

---

_更新时间: 2025-11-05_  
_维护: 开发团队_

