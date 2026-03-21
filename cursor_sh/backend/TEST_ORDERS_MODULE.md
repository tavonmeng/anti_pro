# 订单模块后端调试指南

## 📋 目录

1. [Swagger UI 文档页面介绍](#1-swagger-ui-文档页面介绍)
2. [订单模块 API 接口列表](#2-订单模块-api-接口列表)
3. [使用 Swagger UI 测试订单接口](#3-使用-swagger-ui-测试订单接口)
4. [订单模块测试用例](#4-订单模块测试用例)
5. [常见问题排查](#5-常见问题排查)

---

## 1. Swagger UI 文档页面介绍

### 访问地址

**Swagger UI**: http://localhost:8000/docs  
**ReDoc**: http://localhost:8000/redoc

### 页面功能

Swagger UI 是一个交互式的 API 文档界面，提供以下功能：

1. **API 文档浏览**
   - 按模块分组显示所有 API 接口
   - 每个接口都有详细的说明、参数、请求示例

2. **在线测试**
   - 可以直接在页面上测试 API 接口
   - 无需使用 Postman 或其他工具

3. **认证管理**
   - 可以设置 JWT Token
   - 所有需要认证的接口会自动带上 Token

4. **响应查看**
   - 实时查看 API 响应
   - 查看响应状态码、响应体、响应头

### 页面布局

```
┌─────────────────────────────────────────────────────┐
│  AI设计任务管理系统 API          [Authorize] [🔍]    │
├─────────────────────────────────────────────────────┤
│                                                       │
│  📦 订单                                             │
│    GET    /api/orders             获取订单列表       │
│    POST   /api/orders             创建订单           │
│    GET    /api/orders/{orderId}   获取订单详情       │
│    PUT    /api/orders/{orderId}/status  更新状态     │
│    PUT    /api/orders/{orderId}/assign  分配负责人   │
│    POST   /api/orders/{orderId}/preview 上传预览    │
│    POST   /api/orders/{orderId}/feedback 提交反馈    │
│                                                       │
│  🔐 认证                                             │
│    POST   /api/auth/login         登录               │
│    POST   /api/auth/register     注册               │
│                                                       │
│  👥 负责人                                           │
│    GET    /api/staff              获取负责人列表     │
│    ...                                               │
└─────────────────────────────────────────────────────┘
```

---

## 2. 订单模块 API 接口列表

### 2.1 获取订单列表

**接口**: `GET /api/orders`

**功能**: 获取订单列表，支持筛选和分页

**查询参数**:
- `user_id` (可选): 用户ID，筛选特定用户的订单
- `order_type` (可选): 订单类型 (`video_purchase`, `ai_3d_custom`, `digital_art`)
- `status` (可选): 订单状态 (`pending_assign`, `in_production`, `preview_ready`, 等)
- `assignee_id` (可选): 负责人ID，筛选分配给特定负责人的订单

**权限**: 需要登录（普通用户只能查看自己的订单，管理员和负责人可以查看所有订单）

---

### 2.2 创建订单

**接口**: `POST /api/orders`

**功能**: 创建新订单，支持三种订单类型

**请求体**: 根据订单类型不同，请求体结构不同

**订单类型**:

1. **裸眼3D成片购买** (`video_purchase`)
   ```json
   {
     "orderType": "video_purchase",
     "industryType": "movie",
     "visualStyle": "scifi",
     "duration": 120,
     "priceRange": {
       "min": 5000,
       "max": 10000
     },
     "resolution": "3840x2160",
     "size": "55英寸",
     "curvature": "1800R"
   }
   ```

2. **AI裸眼3D定制** (`ai_3d_custom`)
   ```json
   {
     "orderType": "ai_3d_custom",
     "configuration": "裸眼3D显示屏，分辨率4K，尺寸100英寸",
     "creativeIdea": "科幻主题的太空场景，需要展示星球和飞船",
     "scenePhotos": [
       {
         "id": "file-001",
         "name": "scene1.jpg",
         "size": 2048000,
         "type": "image/jpeg",
         "uploadTime": "2025-11-05T10:30:00Z"
       }
     ]
   }
   ```

3. **数字艺术定制** (`digital_art`)
   ```json
   {
     "orderType": "digital_art",
     "artDirection": "abstract",
     "description": "抽象风格的数字艺术作品，色彩鲜艳，充满科技感",
     "materials": [
       {
         "id": "file-002",
         "name": "reference.zip",
         "size": 5120000,
         "type": "application/zip",
         "uploadTime": "2025-11-05T10:35:00Z"
       }
     ]
   }
   ```

**权限**: 需要登录（普通用户）

---

### 2.3 获取订单详情

**接口**: `GET /api/orders/{orderId}`

**功能**: 根据订单ID获取订单完整信息

**路径参数**:
- `orderId`: 订单ID

**权限**: 需要登录（普通用户只能查看自己的订单）

---

### 2.4 更新订单状态

**接口**: `PUT /api/orders/{orderId}/status`

**功能**: 更新订单状态（仅管理员和负责人可操作）

**路径参数**:
- `orderId`: 订单ID

**请求体**:
```json
{
  "status": "in_production"
}
```

**订单状态流转**:
```
pending_assign (待分配)
  ↓
in_production (制作中)
  ↓
preview_ready (初稿预览)
  ↓ (客户反馈)
├─ revision_needed (需要修改) → in_production
└─ in_production → final_preview (终稿预览) → completed (已完成)
```

**权限**: 需要管理员或负责人权限

---

### 2.5 分配订单负责人

**接口**: `PUT /api/orders/{orderId}/assign`

**功能**: 为订单分配或更改负责人（仅管理员可操作）

**路径参数**:
- `orderId`: 订单ID

**请求体**:
```json
{
  "assigneeId": "staff-001",
  "assigneeName": "张设计"
}
```

**权限**: 需要管理员权限

---

### 2.6 上传预览文件

**接口**: `POST /api/orders/{orderId}/preview`

**功能**: 上传订单预览文件（仅管理员和负责人可操作）

**路径参数**:
- `orderId`: 订单ID

**请求体**:
```json
{
  "files": [
    {
      "id": "file-003",
      "name": "preview.mp4",
      "size": 10485760,
      "type": "video/mp4",
      "uploadTime": "2025-11-05T14:30:00Z"
    }
  ]
}
```

**权限**: 需要管理员或负责人权限

---

### 2.7 提交订单反馈

**接口**: `POST /api/orders/{orderId}/feedback`

**功能**: 提交订单反馈（客户可以提交反馈）

**路径参数**:
- `orderId`: 订单ID

**请求体**:
```json
{
  "content": "需要调整颜色，更鲜艳一些",
  "type": "revision"
}
```

**反馈类型**:
- `approval`: 通过/同意
- `revision`: 需要修改

**权限**: 需要登录（订单创建者或负责人）

---

## 3. 使用 Swagger UI 测试订单接口

### 步骤 1: 打开 Swagger UI

访问: http://localhost:8000/docs

### 步骤 2: 登录获取 Token

1. 找到 `🔐 认证` 模块
2. 展开 `POST /api/auth/login`
3. 点击 "Try it out"
4. 填写请求体:
   ```json
   {
     "username": "admin",
     "password": "123456",
     "role": "admin",
     "captcha": "1234"
   }
   ```
5. 点击 "Execute"
6. 复制响应中的 `token` 值

### 步骤 3: 设置认证 Token

1. 点击页面右上角的 "Authorize" 🔒 按钮
2. 在弹出的对话框中输入: `Bearer <你的token>`
   - 例如: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
3. 点击 "Authorize"
4. 点击 "Close"

现在所有需要认证的接口都会自动带上 Token。

### 步骤 4: 测试订单接口

#### 测试 1: 获取订单列表

1. 找到 `📦 订单` 模块
2. 展开 `GET /api/orders`
3. 点击 "Try it out"
4. 可选：填写查询参数（如 `status`, `order_type`）
5. 点击 "Execute"
6. 查看响应结果

#### 测试 2: 创建订单

1. 展开 `POST /api/orders`
2. 点击 "Try it out"
3. 在请求体中选择订单类型示例，或手动填写：
   ```json
   {
     "orderType": "video_purchase",
     "industryType": "movie",
     "visualStyle": "scifi",
     "duration": 120,
     "priceRange": {
       "min": 5000,
       "max": 10000
     },
     "resolution": "3840x2160",
     "size": "55英寸",
     "curvature": "1800R"
   }
   ```
4. 点击 "Execute"
5. 查看响应，复制订单ID

#### 测试 3: 获取订单详情

1. 展开 `GET /api/orders/{orderId}`
2. 点击 "Try it out"
3. 在 `orderId` 参数中输入刚才创建的订单ID
4. 点击 "Execute"
5. 查看订单详情

#### 测试 4: 更新订单状态

1. 展开 `PUT /api/orders/{orderId}/status`
2. 点击 "Try it out"
3. 输入订单ID
4. 填写请求体:
   ```json
   {
     "status": "in_production"
   }
   ```
5. 点击 "Execute"

---

## 4. 订单模块测试用例

### 测试用例 1: 创建裸眼3D成片购买订单

**请求**:
```json
POST /api/orders
{
  "orderType": "video_purchase",
  "industryType": "movie",
  "visualStyle": "scifi",
  "duration": 120,
  "priceRange": {
    "min": 5000,
    "max": 10000
  },
  "resolution": "3840x2160",
  "size": "55英寸",
  "curvature": "1800R"
}
```

**预期响应**:
- HTTP 201
- `code`: 201
- `message`: "订单创建成功"
- `data`: 包含订单信息的对象

---

### 测试用例 2: 创建 AI 裸眼3D定制订单

**请求**:
```json
POST /api/orders
{
  "orderType": "ai_3d_custom",
  "configuration": "裸眼3D显示屏，分辨率4K，尺寸100英寸",
  "creativeIdea": "科幻主题的太空场景，需要展示星球和飞船",
  "scenePhotos": []
}
```

**预期响应**:
- HTTP 201
- `message`: "订单创建成功，预计5-7个工作日完成制作"

---

### 测试用例 3: 获取订单列表（筛选）

**请求**:
```
GET /api/orders?status=pending_assign&order_type=video_purchase
```

**预期响应**:
- HTTP 200
- `data`: 订单数组，只包含符合条件的订单

---

### 测试用例 4: 更新订单状态

**请求**:
```json
PUT /api/orders/{orderId}/status
{
  "status": "in_production"
}
```

**预期响应**:
- HTTP 200
- `message`: "状态更新成功"
- `data.status`: "in_production"

---

### 测试用例 5: 分配负责人

**请求**:
```json
PUT /api/orders/{orderId}/assign
{
  "assigneeId": "staff-001",
  "assigneeName": "张设计"
}
```

**预期响应**:
- HTTP 200
- `message`: "负责人分配成功"
- `data.assigneeId`: "staff-001"
- `data.status`: "in_production" (自动更新)

---

## 5. 常见问题排查

### 问题 1: 401 未授权错误

**原因**: 未设置 Token 或 Token 已过期

**解决**:
1. 重新登录获取新 Token
2. 在 Swagger UI 中点击 "Authorize" 设置 Token
3. 确认 Token 格式正确: `Bearer <token>`

### 问题 2: 403 禁止访问

**原因**: 权限不足（例如普通用户尝试更新订单状态）

**解决**:
- 使用管理员或负责人账户登录
- 确认当前用户有相应权限

### 问题 3: 404 订单不存在

**原因**: 订单ID错误或订单已被删除

**解决**:
- 确认订单ID正确
- 使用获取订单列表接口查看所有订单ID

### 问题 4: 400 请求参数错误

**原因**: 请求体格式不正确或缺少必需字段

**解决**:
- 查看 Swagger UI 中的请求示例
- 确认所有必需字段都已填写
- 检查字段类型是否正确

### 问题 5: 500 服务器错误

**原因**: 后端处理请求时出现异常

**解决**:
1. 查看后端服务控制台的错误日志
2. 检查数据库连接是否正常
3. 确认所有依赖服务都在运行

---

## 6. 快速测试脚本

### 使用 curl 测试

```bash
# 1. 登录获取 Token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin",
    "captcha": "1234"
  }' | jq -r '.data.token')

# 2. 创建订单
curl -X POST "http://localhost:8000/api/orders" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "orderType": "video_purchase",
    "industryType": "movie",
    "visualStyle": "scifi",
    "duration": 120,
    "priceRange": {"min": 5000, "max": 10000},
    "resolution": "3840x2160",
    "size": "55英寸",
    "curvature": "1800R"
  }' | jq .

# 3. 获取订单列表
curl -X GET "http://localhost:8000/api/orders" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## 7. 数据库验证

### 查看订单数据

```bash
cd backend
sqlite3 app.db "SELECT id, order_number, order_type, status, user_id, assignee_id, created_at FROM orders ORDER BY created_at DESC LIMIT 10;"
```

### 查看订单详情

```bash
sqlite3 app.db "SELECT * FROM orders WHERE id = 'order-xxx';"
```

---

**提示**: Swagger UI 是最方便的测试工具，建议优先使用它来测试订单模块！


