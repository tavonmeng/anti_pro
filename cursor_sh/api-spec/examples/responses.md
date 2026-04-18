# API 响应示例

## 认证相关

### 登录成功响应

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJ1c2VyLTAwMSIsInVzZXJuYW1lIjoidXNlciIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzMwODgwMDAwLCJleHAiOjE3MzA5NjY0MDB9.abc123xyz",
    "user": {
      "id": "user-001",
      "username": "user",
      "role": "user",
      "email": "user@example.com"
    }
  }
}
```

### 登录失败响应

```json
{
  "code": 401,
  "message": "用户名或密码错误",
  "data": null
}
```

### 注册成功响应

```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "success": true
  }
}
```

### 注册失败（用户名已存在）

```json
{
  "code": 409,
  "message": "用户名已存在",
  "data": null
}
```

## 订单相关

### 获取订单列表响应

```json
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "id": "order-1730880000000",
      "orderNumber": "ORD-20251105-A1B2",
      "orderType": "video_purchase",
      "status": "in_production",
      "userId": "user-001",
      "userName": "user",
      "assignee": "张设计",
      "assigneeId": "staff-001",
      "createdAt": "2025-11-05T10:00:00Z",
      "updatedAt": "2025-11-05T14:30:00Z",
      "feedbacks": [],
      "revisionCount": 0,
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
    },
    {
      "id": "order-1730880001000",
      "orderNumber": "ORD-20251105-C3D4",
      "orderType": "ai_3d_custom",
      "status": "preview_ready",
      "userId": "user-001",
      "userName": "user",
      "assignee": "李艺术",
      "assigneeId": "staff-002",
      "createdAt": "2025-11-05T11:00:00Z",
      "updatedAt": "2025-11-05T16:00:00Z",
      "feedbacks": [],
      "revisionCount": 0,
      "configuration": "裸眼3D显示屏，分辨率4K，尺寸100英寸",
      "creativeIdea": "科幻主题的太空场景，需要展示星球和飞船",
      "scenePhotos": [
        {
          "id": "file-001",
          "name": "scene1.jpg",
          "size": 2048000,
          "type": "image/jpeg",
          "uploadTime": "2025-11-05T11:05:00Z",
          "url": "https://cdn.example.com/uploads/scene1.jpg"
        }
      ],
      "previewFiles": [
        {
          "id": "preview-001",
          "name": "preview_v1.mp4",
          "size": 10240000,
          "type": "video/mp4",
          "uploadTime": "2025-11-05T16:00:00Z",
          "url": "https://cdn.example.com/previews/preview_v1.mp4"
        }
      ]
    },
    {
      "id": "order-1730880002000",
      "orderNumber": "ORD-20251105-E5F6",
      "orderType": "digital_art",
      "status": "completed",
      "userId": "user-001",
      "userName": "user",
      "assignee": "王制作",
      "assigneeId": "staff-003",
      "createdAt": "2025-11-04T09:00:00Z",
      "updatedAt": "2025-11-05T18:00:00Z",
      "feedbacks": [
        {
          "id": "feedback-001",
          "orderId": "order-1730880002000",
          "content": "初稿颜色很棒，请继续",
          "type": "approval",
          "createdAt": "2025-11-04T15:00:00Z",
          "createdBy": "user-001",
          "createdByName": "user"
        },
        {
          "id": "feedback-002",
          "orderId": "order-1730880002000",
          "content": "完美，验收通过",
          "type": "approval",
          "createdAt": "2025-11-05T18:00:00Z",
          "createdBy": "user-001",
          "createdByName": "user"
        }
      ],
      "revisionCount": 0,
      "artDirection": "abstract",
      "description": "抽象风格的数字艺术作品，色彩鲜艳",
      "materials": [
        {
          "id": "file-002",
          "name": "reference.zip",
          "size": 5120000,
          "type": "application/zip",
          "uploadTime": "2025-11-04T09:10:00Z",
          "url": "https://cdn.example.com/uploads/reference.zip"
        }
      ],
      "previewFiles": [
        {
          "id": "preview-002",
          "name": "initial_draft.png",
          "size": 3072000,
          "type": "image/png",
          "uploadTime": "2025-11-04T14:00:00Z",
          "url": "https://cdn.example.com/previews/initial_draft.png"
        },
        {
          "id": "preview-003",
          "name": "final_artwork.png",
          "size": 4096000,
          "type": "image/png",
          "uploadTime": "2025-11-05T17:00:00Z",
          "url": "https://cdn.example.com/previews/final_artwork.png"
        }
      ]
    }
  ]
}
```

### 创建订单成功响应（裸眼3D成片购买）

```json
{
  "code": 201,
  "message": "订单创建成功",
  "data": {
    "id": "order-1730880000000",
    "orderNumber": "ORD-20251105-A1B2",
    "orderType": "video_purchase",
    "status": "pending_assign",
    "userId": "user-001",
    "userName": "user",
    "assignee": null,
    "assigneeId": null,
    "createdAt": "2025-11-05T10:00:00Z",
    "updatedAt": "2025-11-05T10:00:00Z",
    "feedbacks": [],
    "revisionCount": 0,
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
}
```

### 创建订单成功响应（AI裸眼3D定制）

```json
{
  "code": 201,
  "message": "订单创建成功，预计5-7个工作日完成制作",
  "data": {
    "id": "order-1730880001000",
    "orderNumber": "ORD-20251105-C3D4",
    "orderType": "ai_3d_custom",
    "status": "pending_assign",
    "userId": "user-001",
    "userName": "user",
    "assignee": null,
    "assigneeId": null,
    "createdAt": "2025-11-05T11:00:00Z",
    "updatedAt": "2025-11-05T11:00:00Z",
    "feedbacks": [],
    "revisionCount": 0,
    "configuration": "裸眼3D显示屏，分辨率4K，尺寸100英寸",
    "creativeIdea": "科幻主题的太空场景，需要展示星球和飞船",
    "scenePhotos": [
      {
        "id": "file-001",
        "name": "scene1.jpg",
        "size": 2048000,
        "type": "image/jpeg",
        "uploadTime": "2025-11-05T11:05:00Z",
        "url": "https://cdn.example.com/uploads/scene1.jpg"
      },
      {
        "id": "file-002",
        "name": "scene2.jpg",
        "size": 1856000,
        "type": "image/jpeg",
        "uploadTime": "2025-11-05T11:06:00Z",
        "url": "https://cdn.example.com/uploads/scene2.jpg"
      }
    ]
  }
}
```

### 创建订单成功响应（数字艺术定制）

```json
{
  "code": 201,
  "message": "订单创建成功，预计3个工作日交付初稿",
  "data": {
    "id": "order-1730880002000",
    "orderNumber": "ORD-20251105-E5F6",
    "orderType": "digital_art",
    "status": "pending_assign",
    "userId": "user-001",
    "userName": "user",
    "assignee": null,
    "assigneeId": null,
    "createdAt": "2025-11-05T12:00:00Z",
    "updatedAt": "2025-11-05T12:00:00Z",
    "feedbacks": [],
    "revisionCount": 0,
    "artDirection": "abstract",
    "description": "抽象风格的数字艺术作品，色彩鲜艳，充满科技感",
    "materials": [
      {
        "id": "file-003",
        "name": "reference.zip",
        "size": 5120000,
        "type": "application/zip",
        "uploadTime": "2025-11-05T12:05:00Z",
        "url": "https://cdn.example.com/uploads/reference.zip"
      }
    ]
  }
}
```

### 获取订单详情响应

```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "id": "order-1730880001000",
    "orderNumber": "ORD-20251105-C3D4",
    "orderType": "ai_3d_custom",
    "status": "preview_ready",
    "userId": "user-001",
    "userName": "user",
    "assignee": "李艺术",
    "assigneeId": "staff-002",
    "createdAt": "2025-11-05T11:00:00Z",
    "updatedAt": "2025-11-05T16:00:00Z",
    "feedbacks": [],
    "revisionCount": 0,
    "configuration": "裸眼3D显示屏，分辨率4K，尺寸100英寸",
    "creativeIdea": "科幻主题的太空场景，需要展示星球和飞船，强调科技感和未来感",
    "scenePhotos": [
      {
        "id": "file-001",
        "name": "scene1.jpg",
        "size": 2048000,
        "type": "image/jpeg",
        "uploadTime": "2025-11-05T11:05:00Z",
        "url": "https://cdn.example.com/uploads/scene1.jpg"
      }
    ],
    "previewFiles": [
      {
        "id": "preview-001",
        "name": "preview_v1.mp4",
        "size": 10240000,
        "type": "video/mp4",
        "uploadTime": "2025-11-05T16:00:00Z",
        "url": "https://cdn.example.com/previews/preview_v1.mp4"
      }
    ]
  }
}
```

### 更新订单状态成功响应

```json
{
  "code": 200,
  "message": "状态更新成功",
  "data": {
    "id": "order-1730880000000",
    "orderNumber": "ORD-20251105-A1B2",
    "orderType": "video_purchase",
    "status": "in_production",
    "userId": "user-001",
    "userName": "user",
    "assignee": "张设计",
    "assigneeId": "staff-001",
    "createdAt": "2025-11-05T10:00:00Z",
    "updatedAt": "2025-11-05T14:30:00Z",
    "feedbacks": [],
    "revisionCount": 0,
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
}
```

### 分配负责人成功响应

```json
{
  "code": 200,
  "message": "负责人分配成功",
  "data": {
    "id": "order-1730880000000",
    "orderNumber": "ORD-20251105-A1B2",
    "orderType": "video_purchase",
    "status": "in_production",
    "userId": "user-001",
    "userName": "user",
    "assignee": "张设计",
    "assigneeId": "staff-001",
    "createdAt": "2025-11-05T10:00:00Z",
    "updatedAt": "2025-11-05T14:00:00Z",
    "feedbacks": [],
    "revisionCount": 0,
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
}
```

### 上传预览文件成功响应

```json
{
  "code": 200,
  "message": "预览文件上传成功",
  "data": {
    "id": "order-1730880001000",
    "orderNumber": "ORD-20251105-C3D4",
    "orderType": "ai_3d_custom",
    "status": "preview_ready",
    "userId": "user-001",
    "userName": "user",
    "assignee": "李艺术",
    "assigneeId": "staff-002",
    "createdAt": "2025-11-05T11:00:00Z",
    "updatedAt": "2025-11-05T16:00:00Z",
    "feedbacks": [],
    "revisionCount": 0,
    "configuration": "裸眼3D显示屏，分辨率4K，尺寸100英寸",
    "creativeIdea": "科幻主题的太空场景",
    "scenePhotos": [
      {
        "id": "file-001",
        "name": "scene1.jpg",
        "size": 2048000,
        "type": "image/jpeg",
        "uploadTime": "2025-11-05T11:05:00Z",
        "url": "https://cdn.example.com/uploads/scene1.jpg"
      }
    ],
    "previewFiles": [
      {
        "id": "preview-001",
        "name": "preview_v1.mp4",
        "size": 10240000,
        "type": "video/mp4",
        "uploadTime": "2025-11-05T16:00:00Z",
        "url": "https://cdn.example.com/previews/preview_v1.mp4"
      }
    ]
  }
}
```

### 提交反馈成功响应

```json
{
  "code": 200,
  "message": "反馈提交成功",
  "data": {
    "id": "feedback-1730880003000",
    "orderId": "order-1730880001000",
    "content": "初稿效果很好，请继续制作终稿",
    "type": "approval",
    "createdAt": "2025-11-05T17:00:00Z",
    "createdBy": "user-001",
    "createdByName": "user"
  }
}
```

### 提交修改反馈响应

```json
{
  "code": 200,
  "message": "修改意见已提交，订单状态已更新为\"需要修改\"",
  "data": {
    "id": "feedback-1730880004000",
    "orderId": "order-1730880001000",
    "content": "背景颜色需要调整为蓝色调，太空飞船的细节需要更精致",
    "type": "revision",
    "createdAt": "2025-11-05T17:30:00Z",
    "createdBy": "user-001",
    "createdByName": "user"
  }
}
```

## 负责人管理

### 获取负责人列表响应

```json
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "id": "staff-001",
      "username": "staff1",
      "role": "staff",
      "email": "staff1@example.com",
      "realName": "张设计"
    },
    {
      "id": "staff-002",
      "username": "staff2",
      "role": "staff",
      "email": "staff2@example.com",
      "realName": "李艺术"
    },
    {
      "id": "staff-003",
      "username": "staff3",
      "role": "staff",
      "email": "staff3@example.com",
      "realName": "王制作"
    }
  ]
}
```

### 添加负责人成功响应

```json
{
  "code": 201,
  "message": "负责人添加成功",
  "data": {
    "id": "staff-004",
    "username": "staff4",
    "role": "staff",
    "email": "staff4@example.com",
    "realName": "赵创意"
  }
}
```

## 错误响应

### 400 - 请求参数错误

```json
{
  "code": 400,
  "message": "请求参数错误: orderType 是必填项",
  "data": {
    "field": "orderType",
    "error": "required"
  }
}
```

### 401 - 未授权

```json
{
  "code": 401,
  "message": "未授权，请先登录",
  "data": null
}
```

### 403 - 权限不足

```json
{
  "code": 403,
  "message": "权限不足，只有管理员可以执行此操作",
  "data": {
    "requiredRole": "admin",
    "currentRole": "user"
  }
}
```

### 404 - 资源不存在

```json
{
  "code": 404,
  "message": "订单不存在",
  "data": {
    "orderId": "order-invalid-id"
  }
}
```

### 409 - 资源冲突

```json
{
  "code": 409,
  "message": "用户名已存在",
  "data": {
    "username": "existinguser"
  }
}
```

### 500 - 服务器内部错误

```json
{
  "code": 500,
  "message": "服务器内部错误，请稍后重试",
  "data": null
}
```

