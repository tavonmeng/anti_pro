# AI设计任务管理系统 API 文档

## 概述

本项目是一个基于 VR+AI 的裸眼3D内容定制管理系统的后端 API 接口规范，采用 OpenAPI 3.0 标准定义。

## 文件说明

- `openapi.yaml` - OpenAPI 3.0 规范文件
- `examples/` - API 请求响应示例
- `postman_collection.json` - Postman 导入集合

## 快速开始

### 1. 查看 API 文档

#### 使用 Swagger UI（在线）

访问 [Swagger Editor](https://editor.swagger.io/)，将 `openapi.yaml` 内容粘贴进去即可查看可交互的 API 文档。

#### 使用本地工具

```bash
# 安装 swagger-ui-watcher（需要 Node.js）
npm install -g swagger-ui-watcher

# 启动本地文档服务器
swagger-ui-watcher api-spec/openapi.yaml
```

然后访问 `http://localhost:8000` 查看文档。

#### 使用 Redoc

```bash
# 安装 redoc-cli
npm install -g redoc-cli

# 生成 HTML 文档
redoc-cli bundle api-spec/openapi.yaml -o api-docs.html

# 或启动本地服务器
redoc-cli serve api-spec/openapi.yaml
```

### 2. 导入 Postman

1. 打开 Postman
2. 点击 `Import` 按钮
3. 选择 `postman_collection.json` 文件
4. 导入后即可使用预定义的 API 请求

### 3. 验证规范文件

```bash
# 安装 openapi-cli
npm install -g @redocly/cli

# 验证 OpenAPI 规范
openapi lint api-spec/openapi.yaml
```

## API 模块说明

### 1. 认证模块 (Authentication)

- **POST /api/auth/login** - 用户登录
- **POST /api/auth/register** - 用户注册
- **POST /api/auth/logout** - 用户登出

### 2. 订单模块 (Orders)

- **GET /api/orders** - 获取订单列表
- **POST /api/orders** - 创建订单
- **GET /api/orders/{orderId}** - 获取订单详情
- **PUT /api/orders/{orderId}/status** - 更新订单状态
- **PUT /api/orders/{orderId}/assign** - 分配负责人
- **POST /api/orders/{orderId}/preview** - 上传预览文件
- **POST /api/orders/{orderId}/feedback** - 提交反馈

### 3. 负责人模块 (Staff)

- **GET /api/staff** - 获取负责人列表
- **POST /api/staff** - 添加负责人

## 订单类型

系统支持三种订单类型：

### 1. 裸眼3D成片购买适配 (video_purchase)

客户选择现有3D视频内容进行屏幕适配。

**主要参数：**
- 行业类型 (industryType)
- 视觉风格 (visualStyle)
- 时长 (duration)
- 价格范围 (priceRange)
- 分辨率 (resolution)
- 屏幕尺寸 (size)
- 曲率 (curvature)

### 2. AI裸眼3D内容定制 (ai_3d_custom)

使用 AI 技术定制裸眼3D内容。

**主要参数：**
- 配置信息 (configuration)
- 创意说明 (creativeIdea)
- 现场实拍图 (scenePhotos)

**制作周期：** 5-7 个工作日

### 3. 数字艺术内容定制 (digital_art)

定制数字艺术作品。

**主要参数：**
- 艺术方向 (artDirection)
- 说明文字 (description)
- 相关材料 (materials)

**制作周期：** 3 个工作日（初稿）

## 订单状态流转

```
pending_assign (待分配)
    ↓
in_production (制作中)
    ↓
preview_ready (初稿预览)
    ↓ 
    ├─ 客户反馈 = approval → in_production (继续制作终稿)
    └─ 客户反馈 = revision → revision_needed (需要修改) → in_production
    
    ↓ (终稿完成)
final_preview (终稿预览)
    ↓
    ├─ 客户确认 → completed (已完成)
    └─ 客户要求修改 → revision_needed → in_production
```

## 权限说明

系统有三种用户角色：

### 1. 普通用户 (user)
- 创建订单
- 查看自己的订单
- 提交反馈
- 查看预览文件

### 2. 负责人 (staff)
- 查看分配给自己的订单
- 上传预览文件
- 更新订单状态

### 3. 管理员 (admin)
- 查看所有订单
- 分配负责人
- 上传预览文件
- 更新订单状态
- 管理负责人账户

## 认证方式

API 使用 JWT (JSON Web Token) 进行认证。

### 获取 Token

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user",
    "password": "123456",
    "role": "user",
    "captcha": "1234"
  }'
```

### 使用 Token

在后续请求的 Header 中添加：

```
Authorization: Bearer {your_token}
```

示例：

```bash
curl -X GET http://localhost:3000/api/orders \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 响应格式

所有 API 响应都遵循统一格式：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    // 具体数据
  }
}
```

### 状态码说明

- **200** - 请求成功
- **201** - 创建成功
- **400** - 请求参数错误
- **401** - 未授权，需要登录
- **403** - 权限不足
- **404** - 资源不存在
- **409** - 资源冲突（如用户名已存在）
- **500** - 服务器内部错误

## 测试账户

开发环境提供以下测试账户：

### 普通用户
- 用户名: `user`
- 密码: `123456`
- 角色: `user`

### 管理员
- 用户名: `admin`
- 密码: `123456`
- 角色: `admin`

## 开发建议

### 1. 文件上传

当前前端使用模拟上传（localStorage），后端实现时建议：

- 使用对象存储服务（如 AWS S3、阿里云 OSS）
- 实现分片上传支持大文件
- 生成预签名 URL 供客户端直传
- 实现文件类型和大小验证

### 2. 实时通知

建议实现以下通知机制：

- 订单状态变更时通知用户
- 新反馈提交时通知负责人
- 预览文件上传完成时通知用户

技术选型：
- WebSocket
- Server-Sent Events (SSE)
- 或第三方推送服务

### 3. 订单编号生成

建议格式：`ORD-{日期}-{随机码}`

示例实现：

```javascript
function generateOrderNumber() {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const random = Math.random().toString(36).substring(2, 6).toUpperCase();
  return `ORD-${date}-${random}`;
}
```

### 4. 数据库设计建议

#### 用户表 (users)
```sql
CREATE TABLE users (
  id VARCHAR(50) PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(100),
  role ENUM('admin', 'user', 'staff') NOT NULL,
  real_name VARCHAR(50),
  avatar VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### 订单表 (orders)
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
  order_data JSON NOT NULL, -- 存储订单类型特定的数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (assignee_id) REFERENCES users(id)
);
```

#### 文件表 (files)
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
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
```

#### 反馈表 (feedbacks)
```sql
CREATE TABLE feedbacks (
  id VARCHAR(50) PRIMARY KEY,
  order_id VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  type ENUM('approval', 'revision') NOT NULL,
  created_by VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id)
);
```

## 常见问题

### Q: 如何处理大文件上传？

A: 建议使用以下方案：
1. 前端获取预签名 URL
2. 直接上传到对象存储
3. 上传完成后通知后端保存文件记录

### Q: 订单状态变更的权限控制？

A: 
- 只有管理员和订单负责人可以更新状态
- 用户只能通过提交反馈间接影响状态
- 某些状态转换有严格的流程限制

### Q: 如何实现订单搜索？

A: 建议实现以下搜索维度：
- 订单编号
- 订单类型
- 订单状态
- 创建时间范围
- 负责人
- 客户名称

可以使用 Elasticsearch 等搜索引擎提升性能。

## 更新日志

### v1.0.0 (2025-11-05)
- 初始版本发布
- 完整的订单管理功能
- 支持三种订单类型
- 完整的状态流转机制

## 许可证

MIT License

## 联系方式

如有问题，请联系：
- Email: support@example.com
- 文档问题: 提交 Issue

