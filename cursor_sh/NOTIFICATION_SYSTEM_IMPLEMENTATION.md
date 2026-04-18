# 系统内红点消息提醒功能 - 实施完成文档

## 实施概述

已成功实现完整的系统内红点消息提醒功能，包括后端消息通知系统和前端红点提醒UI。

## 实施的功能场景

### 1. 用户侧消息通知
- ✅ 订单状态改变时收到通知
- ✅ 预览文件就绪时收到通知
- ✅ 订单完成时收到通知
- ✅ 订单取消时收到通知

### 2. Staff侧消息通知
- ✅ 被分配订单时收到通知
- ✅ 订单被重新分配时收到通知（原负责人和新负责人都会收到）
- ✅ 订单状态改变时收到通知
- ✅ 收到新的用户反馈时收到通知
- ✅ 订单需要修改时收到通知

## 后端实施详情

### 1. 数据库模型
**文件**: `backend/app/models/notification.py`

- 创建了 `Notification` 模型
- 字段包括：id, user_id, order_id, type, title, content, is_read, created_at, read_at
- 使用枚举类型 `NotificationType` 定义8种消息类型

### 2. 消息服务类
**文件**: `backend/app/services/notification_service.py`

实现的核心方法：
- `create_notification` - 创建单个消息通知
- `create_notification_for_multiple_users` - 批量创建消息（用于通知多个staff）
- `get_user_notifications` - 获取用户消息列表（支持分页和未读筛选）
- `get_unread_count` - 获取未读消息数量
- `mark_as_read` - 标记单个消息为已读
- `mark_all_as_read` - 标记所有消息为已读
- `delete_notification` - 删除消息

### 3. API路由
**文件**: `backend/app/api/notifications.py`

实现的API端点：
- `GET /api/notifications` - 获取消息列表
- `GET /api/notifications/unread-count` - 获取未读数量
- `PUT /api/notifications/{id}/read` - 标记消息为已读
- `PUT /api/notifications/read-all` - 标记所有消息为已读
- `DELETE /api/notifications/{id}` - 删除消息

### 4. 订单服务集成
**文件**: `backend/app/services/order_service.py`

在以下方法中集成了消息通知：

#### update_order_status
- 通知订单用户状态变更
- 通知所有负责该订单的staff状态变更

#### assign_order
- 首次分配：通知所有新负责人
- 重新分配：通知新增的负责人，通知被移除的旧负责人

#### upload_preview
- 通知订单用户预览文件已就绪

#### submit_feedback
- 通知所有负责该订单的staff收到新反馈

### 5. Schema定义
**文件**: `backend/app/schemas/notification.py`

- `NotificationCreate` - 创建消息请求
- `NotificationResponse` - 消息响应
- `NotificationList` - 消息列表响应
- `UnreadCountResponse` - 未读数量响应

## 前端实施详情

### 1. 类型定义
**文件**: `src/types/index.ts`

添加了：
- `NotificationType` - 消息类型枚举
- `Notification` - 消息接口
- `NotificationList` - 消息列表接口

### 2. API客户端
**文件**: `src/utils/api.ts`

添加了 `notificationApi` 对象，包含所有消息相关的API调用方法。

### 3. 消息Store
**文件**: `src/stores/notification.ts`

使用 Pinia 实现状态管理：
- `notifications` - 消息列表
- `unreadCount` - 未读消息数量
- `fetchNotifications` - 获取消息列表
- `fetchUnreadCount` - 获取未读数量
- `markAsRead` - 标记为已读
- `markAllAsRead` - 标记全部为已读
- `deleteNotification` - 删除消息
- `startPolling` - 启动轮询（30秒间隔）
- `stopPolling` - 停止轮询

### 4. 消息铃铛组件
**文件**: `src/components/NotificationBell.vue`

功能特性：
- 显示红点徽章（未读消息数量）
- 点击显示消息列表下拉菜单
- 消息列表显示最新10条
- 未读消息以蓝色背景高亮
- 点击消息自动标记为已读并跳转到订单详情
- 支持"全部已读"和单条删除
- 相对时间显示（刚刚、X分钟前、X小时前等）
- 组件挂载时自动启动轮询

### 5. 布局集成
**文件**: `src/components/Sidebar.vue`

- 在侧边栏头部添加了消息铃铛图标
- 适用于所有用户角色（user、staff、admin）

## 数据库变更

### 新增表：notifications

```sql
CREATE TABLE notifications (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_order_id ON notifications(order_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
```

## 消息类型定义

| 类型 | 值 | 说明 |
|------|-----|------|
| 订单状态变更 | order_status_changed | 订单状态发生改变 |
| 订单分配 | order_assigned | Staff被分配新订单 |
| 订单重新分配 | order_reassigned | Staff被移除或重新分配 |
| 新反馈 | new_feedback | 用户提交了新反馈 |
| 预览就绪 | preview_ready | 预览文件已上传 |
| 订单完成 | order_completed | 订单已完成 |
| 订单取消 | order_cancelled | 订单已取消 |
| 需要修改 | revision_needed | 订单需要修改 |

## 技术特点

### 1. 实时性
- 使用轮询机制（30秒间隔）自动更新未读消息数量
- 可轻松扩展为WebSocket实现真正的实时推送

### 2. 用户体验
- 红点徽章醒目显示未读数量
- 未读消息蓝色高亮
- 相对时间显示更人性化
- 点击消息自动跳转相关订单
- 支持批量标记已读

### 3. 性能优化
- 消息列表支持分页
- 未读数量单独查询，减少数据传输
- 本地状态更新减少API调用
- 数据库索引优化查询性能

### 4. 权限控制
- 用户只能看到自己的消息
- 服务端验证消息所有权
- 防止越权操作

## 部署说明

### 1. 数据库迁移

如果使用 `init_db()`，会自动创建 notifications 表。

或手动运行迁移脚本：
```bash
python -m backend.migrations.add_notifications_table
```

### 2. 启动后端
```bash
cd backend
python -m app.main
```

### 3. 启动前端
```bash
cd frontend
npm run dev
```

## 测试场景

### 用户测试场景
1. 登录用户账号
2. 创建订单 → 无消息（订单刚创建）
3. Admin分配负责人 → 无消息（用户不关心分配）
4. Staff上传预览 → 收到"预览文件已就绪"消息
5. 用户查看消息 → 红点消失，消息标记已读
6. 点击消息 → 跳转到订单详情页

### Staff测试场景
1. 登录Staff账号
2. Admin分配订单给该Staff → 收到"新订单分配"消息
3. 订单状态变更 → 收到"订单状态更新"消息
4. 用户提交反馈 → 收到"新反馈提交"消息
5. Admin重新分配负责人 → 收到"订单负责人变更"消息（如果被移除）

### Admin测试场景
1. 登录Admin账号
2. 更改订单状态 → Staff和用户都收到相应消息
3. 分配负责人 → Staff收到分配消息

## 扩展建议

### 1. WebSocket实时推送
可以使用 FastAPI 的 WebSocket 支持替换轮询机制：
```python
# backend/app/api/websocket.py
@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str):
    # 实现WebSocket连接和消息推送
    pass
```

### 2. 消息模板
可以创建消息模板系统，便于统一管理消息内容格式。

### 3. 消息设置
允许用户配置哪些类型的消息需要接收。

### 4. 推送通知
集成浏览器推送通知API，即使页面不在前台也能收到提醒。

### 5. 消息分类
添加消息分类筛选，如"订单消息"、"系统消息"等。

## 总结

✅ 成功实现了完整的系统内红点消息提醒功能
✅ 涵盖了所有用户要求的场景和扩展场景
✅ 后端API完整，前端UI美观实用
✅ 代码结构清晰，易于维护和扩展
✅ 性能优化到位，用户体验良好

系统现在具备了完善的消息通知能力，用户和staff可以及时收到订单相关的各种通知，大大提升了系统的交互性和用户体验。

