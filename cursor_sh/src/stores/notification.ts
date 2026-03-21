import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationApi } from '@/utils/api'
import type { Notification, NotificationList } from '@/types'
import { ElMessage } from 'element-plus'

export const useNotificationStore = defineStore('notification', () => {
  // 状态
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)
  const total = ref(0)
  const loading = ref(false)

  // Computed
  const hasUnread = computed(() => unreadCount.value > 0)

  // 获取消息列表
  const fetchNotifications = async (params?: {
    skip?: number
    limit?: number
    unreadOnly?: boolean
  }) => {
    loading.value = true
    try {
      const result: NotificationList = await notificationApi.getNotifications(params)
      const resultAny = result as any
      
      // 转换消息列表中的字段名（从下划线转为驼峰）
      notifications.value = (resultAny.items || []).map((item: any) => ({
        id: item.id,
        userId: item.user_id || item.userId,
        orderId: item.order_id || item.orderId,
        type: item.type,
        title: item.title,
        content: item.content,
        isRead: item.is_read !== undefined ? item.is_read : (item.isRead !== undefined ? item.isRead : false),
        createdAt: item.created_at || item.createdAt,
        readAt: item.read_at || item.readAt
      }))
      
      // 处理未读数量，支持两种命名方式
      let count = 0
      if (result && typeof result === 'object') {
        if ('unreadCount' in resultAny) {
          count = Number(resultAny.unreadCount) || 0
        } else if ('unread_count' in resultAny) {
          count = Number(resultAny.unread_count) || 0
        }
      }
      
      // 优先使用API返回的未读数量（从数据库直接查询，更准确）
      // 如果API返回的数量为0，也使用它（可能是真的没有未读消息）
      unreadCount.value = count
      
      // 本地计算用于验证（调试用）
      const localUnreadCount = notifications.value.filter(n => !n.isRead).length
      console.log('API返回的未读数量:', count, '本地计算的未读数量:', localUnreadCount)
      
      // 如果两者不一致，记录警告（可能是数据同步问题）
      if (count !== localUnreadCount) {
        console.warn('未读数量不一致！API返回:', count, '本地计算:', localUnreadCount)
      }
      
      total.value = Number(resultAny.total) || 0
      console.log('最终设置的未读数量:', unreadCount.value, '总数量:', total.value)
    } catch (error: any) {
      console.error('获取消息列表失败:', error)
      ElMessage.error(error.message || '获取消息列表失败')
    } finally {
      loading.value = false
    }
  }

  // 获取未读消息数量
  const fetchUnreadCount = async () => {
    try {
      const result = await notificationApi.getUnreadCount()
      const resultAny = result as any
      console.log('API返回的完整数据:', JSON.stringify(result))
      console.log('检查 unreadCount:', resultAny?.unreadCount)
      console.log('检查 unread_count:', resultAny?.unread_count)
      
      // 处理不同的数据格式
      let count = 0
      if (result !== null && result !== undefined) {
        const resultAny = result as any
        // 如果 result 直接是数字
        if (typeof resultAny === 'number') {
          count = resultAny
        } 
        // 如果 result 是对象
        else if (typeof resultAny === 'object') {
          // 优先检查 unreadCount (驼峰命名)
          if ('unreadCount' in resultAny) {
            count = Number(resultAny.unreadCount) || 0
          }
          // 检查 unread_count (下划线命名)
          else if ('unread_count' in resultAny) {
            count = Number(resultAny.unread_count) || 0
          }
          // 如果 result 有 data 字段（嵌套结构）
          else if ('data' in resultAny && resultAny.data && typeof resultAny.data === 'object') {
            if ('unreadCount' in resultAny.data) {
              count = Number(resultAny.data.unreadCount) || 0
            } else if ('unread_count' in resultAny.data) {
              count = Number(resultAny.data.unread_count) || 0
            }
          }
        }
      }
      
      unreadCount.value = count
      console.log('最终设置的未读数量:', count, '类型:', typeof count)
    } catch (error: any) {
      console.error('获取未读消息数量失败:', error)
      console.error('错误详情:', error.response?.data || error.message)
      // 确保即使出错也保持为有效数字
      unreadCount.value = Number(unreadCount.value) || 0
    }
  }

  // 标记消息为已读
  const markAsRead = async (notificationId: string) => {
    try {
      await notificationApi.markAsRead(notificationId)
      
      // 更新本地状态
      const notification = notifications.value.find(n => n.id === notificationId)
      if (notification && !notification.isRead) {
        notification.isRead = true
        notification.readAt = new Date().toISOString()
        const currentCount = Number(unreadCount.value) || 0
        unreadCount.value = Math.max(0, currentCount - 1)
      }
    } catch (error: any) {
      console.error('标记消息已读失败:', error)
      ElMessage.error(error.message || '标记消息已读失败')
    }
  }

  // 标记所有消息为已读
  const markAllAsRead = async () => {
    try {
      await notificationApi.markAllAsRead()
      
      // 更新本地状态
      notifications.value.forEach(notification => {
        notification.isRead = true
        notification.readAt = new Date().toISOString()
      })
      unreadCount.value = 0
      
      ElMessage.success('已标记所有消息为已读')
    } catch (error: any) {
      console.error('标记所有消息已读失败:', error)
      ElMessage.error(error.message || '标记所有消息已读失败')
    }
  }

  // 删除消息
  const deleteNotification = async (notificationId: string) => {
    try {
      await notificationApi.deleteNotification(notificationId)
      
      // 更新本地状态
      const index = notifications.value.findIndex(n => n.id === notificationId)
      if (index !== -1) {
        const notification = notifications.value[index]
        if (!notification.isRead) {
          const currentCount = Number(unreadCount.value) || 0
          unreadCount.value = Math.max(0, currentCount - 1)
        }
        notifications.value.splice(index, 1)
        const currentTotal = Number(total.value) || 0
        total.value = Math.max(0, currentTotal - 1)
      }
      
      ElMessage.success('消息已删除')
    } catch (error: any) {
      console.error('删除消息失败:', error)
      ElMessage.error(error.message || '删除消息失败')
    }
  }

  // 启动轮询（可选）
  let pollTimer: number | null = null
  const startPolling = (interval = 30000) => {
    if (pollTimer) {
      return
    }
    
    // 立即获取一次
    fetchUnreadCount()
    
    // 设置定时器
    pollTimer = window.setInterval(() => {
      fetchUnreadCount()
    }, interval)
  }

  // 停止轮询
  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    notifications,
    unreadCount,
    total,
    loading,
    hasUnread,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    startPolling,
    stopPolling
  }
})

