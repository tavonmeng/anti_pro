<template>
  <el-popover
    v-model:visible="visible"
    placement="bottom-end"
    :width="400"
    trigger="click"
    :teleported="true"
    @show="handleShow"
    @hide="handleHide"
  >
    <template #reference>
      <div class="notification-bell">
        <el-badge :value="unreadCount" :max="99">
          <el-icon :size="24" class="bell-icon">
            <Bell />
          </el-icon>
        </el-badge>
      </div>
    </template>

    <div class="notification-panel">
      <div class="notification-header">
        <span class="title">消息通知</span>
        <el-button 
          v-if="hasUnread" 
          link 
          size="small" 
          @click="handleMarkAllRead"
        >
          全部已读
        </el-button>
      </div>

      <el-divider class="divider" />

      <div class="notification-list" v-loading="loading">
        <template v-if="notifications.length > 0">
          <div
            v-for="notification in notifications"
            :key="notification.id"
            class="notification-item"
            :class="{ unread: !notification.isRead }"
            @click="handleNotificationClick(notification)"
          >
            <div class="notification-content">
              <div class="notification-title">
                <span class="title-text">{{ notification.title }}</span>
                <span v-if="!notification.isRead" class="unread-dot"></span>
              </div>
              <div class="notification-message">{{ notification.content }}</div>
              <div class="notification-time">{{ formatTime(notification.createdAt) }}</div>
            </div>
            <div class="notification-actions">
              <el-button
                link
                size="small"
                @click.stop="handleDelete(notification.id)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </template>
        <el-empty v-else description="暂无消息" :image-size="80" />
      </div>

      <el-divider class="divider" />

      <div class="notification-footer">
        <el-button link size="small" @click="handleViewAll">
          查看全部
        </el-button>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, Delete } from '@element-plus/icons-vue'
import { useNotificationStore } from '@/stores/notification'
import type { Notification } from '@/types'

const router = useRouter()
const notificationStore = useNotificationStore()

const visible = ref(false)

// Computed
const notifications = computed(() => notificationStore.notifications.slice(0, 10)) // 只显示最新10条
const unreadCount = computed(() => notificationStore.unreadCount)
const hasUnread = computed(() => notificationStore.hasUnread)
const loading = computed(() => notificationStore.loading)

// 切换弹出层
const togglePopover = () => {
  visible.value = !visible.value
}

// 显示弹出层时加载消息
const handleShow = () => {
  notificationStore.fetchNotifications({ limit: 10 })
}

// 隐藏弹出层
const handleHide = () => {
  visible.value = false
}

// 格式化时间（转换为北京时间）
const formatTime = (timeString: string) => {
  if (!timeString) return '-'
  
  // 解析时间字符串
  const date = new Date(timeString)
  if (isNaN(date.getTime())) {
    return timeString
  }
  
  // 获取当前时间（UTC时间戳）
  const now = new Date()
  
  // 计算时间差（毫秒）
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 1) {
    return '刚刚'
  } else if (minutes < 60) {
    return `${minutes}分钟前`
  } else if (hours < 24) {
    return `${hours}小时前`
  } else if (days < 7) {
    return `${days}天前`
  } else {
    // 显示完整的北京时间（使用 toLocaleString 自动转换为北京时间）
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }
}

// 点击消息
const handleNotificationClick = async (notification: Notification) => {
  // 标记为已读
  if (!notification.isRead) {
    await notificationStore.markAsRead(notification.id)
  }
  
  // 如果有关联订单，跳转到订单详情
  if (notification.orderId) {
    visible.value = false
    router.push(`/user/orders/${notification.orderId}`)
  }
}

// 标记所有消息为已读
const handleMarkAllRead = async () => {
  await notificationStore.markAllAsRead()
}

// 删除消息
const handleDelete = async (notificationId: string) => {
  await notificationStore.deleteNotification(notificationId)
}

// 查看全部消息（可扩展）
const handleViewAll = () => {
  visible.value = false
  // 可以跳转到完整的消息列表页面
  // router.push('/notifications')
}

// 组件挂载时启动轮询
onMounted(() => {
  // 立即获取未读数量
  notificationStore.fetchUnreadCount()
  // 启动轮询，每30秒更新一次未读数量
  notificationStore.startPolling(30000)
})

// 组件卸载时停止轮询
onUnmounted(() => {
  notificationStore.stopPolling()
})
</script>

<style lang="scss" scoped>
.notification-bell {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  
  .bell-icon {
    color: #606266;
    transition: color 0.3s;
    
    &:hover {
      color: #409EFF;
    }
  }
  
  :deep(.el-badge__content) {
    background-color: #F56C6C;
    border: none;
  }
}

.notification-panel {
  .notification-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    
    .title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .divider {
    margin: 0;
  }
  
  .notification-list {
    max-height: 400px;
    overflow-y: auto;
    
    .notification-item {
      display: flex;
      padding: 12px 16px;
      cursor: pointer;
      transition: background-color 0.3s;
      border-bottom: 1px solid #F0F0F0;
      
      &:last-child {
        border-bottom: none;
      }
      
      &:hover {
        background-color: #F5F7FA;
      }
      
      &.unread {
        background-color: #F0F9FF;
      }
      
      .notification-content {
        flex: 1;
        min-width: 0;
        
        .notification-title {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 4px;
          
          .title-text {
            font-size: 14px;
            font-weight: 500;
            color: #303133;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          
          .unread-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #409EFF;
            flex-shrink: 0;
            display: inline-block;
          }
        }
        
        .notification-message {
          font-size: 13px;
          color: #606266;
          line-height: 1.5;
          margin-bottom: 4px;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }
        
        .notification-time {
          font-size: 12px;
          color: #909399;
        }
      }
      
      .notification-actions {
        display: flex;
        align-items: center;
        margin-left: 8px;
      }
    }
  }
  
  .notification-footer {
    display: flex;
    justify-content: center;
    padding: 8px 16px;
  }
}
</style>

