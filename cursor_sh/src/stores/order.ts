import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { orderApi } from '@/utils/api'
import type { Order, OrderStatus, OrderType } from '@/types'
import { ElMessage } from 'element-plus'
import { useAuthStore } from './auth'

export const useOrderStore = defineStore('order', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  const authStore = useAuthStore()

  // 获取订单列表
  const fetchOrders = async (params?: { 
    userId?: string
    orderType?: OrderType
    status?: OrderStatus
    assigneeId?: string
  }) => {
    loading.value = true
    try {
      const fetchParams: any = { ...params }
      
      // 如果是普通用户，只获取自己的订单
      if (authStore.isUser() && authStore.user) {
        fetchParams.userId = authStore.user.id
      }
      
      orders.value = await orderApi.getOrders(fetchParams)
    } catch (error: any) {
      ElMessage.error(error.message || '获取订单列表失败')
    } finally {
      loading.value = false
    }
  }

  // 创建订单
  const createOrder = async (orderData: any, isDraft: boolean = false) => {
    try {
      const newOrder = await orderApi.createOrder(orderData, isDraft)
      orders.value.unshift(newOrder)
      ElMessage.success(isDraft ? '草稿保存成功' : '订单创建成功')
      return newOrder
    } catch (error: any) {
      ElMessage.error(error.message || (isDraft ? '保存草稿失败' : '创建订单失败'))
      throw error
    }
  }

  // 获取订单详情
  const getOrderDetail = async (orderId: string): Promise<Order | null> => {
    try {
      return await orderApi.getOrderDetail(orderId)
    } catch (error: any) {
      ElMessage.error(error.message || '获取订单详情失败')
      return null
    }
  }

  // 更新订单状态
  const updateOrderStatus = async (orderId: string, status: OrderStatus) => {
    try {
      const updatedOrder = await orderApi.updateOrderStatus(orderId, status)
      const index = orders.value.findIndex(o => o.id === orderId)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }
      ElMessage.success('订单状态更新成功')
      return updatedOrder
    } catch (error: any) {
      ElMessage.error(error.message || '更新订单状态失败')
      throw error
    }
  }

  // 分配负责人
  const assignOrder = async (orderId: string, assignees: Array<{ id: string, name: string }>) => {
    try {
      const assigneeIds = assignees.map(a => a.id)
      const assigneeNames = assignees.map(a => a.name)
      const updatedOrder = await orderApi.assignOrder(orderId, assigneeIds, assigneeNames)
      const index = orders.value.findIndex(o => o.id === orderId)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }
      ElMessage.success('负责人分配成功')
      return updatedOrder
    } catch (error: any) {
      ElMessage.error(error.message || '分配负责人失败')
      throw error
    }
  }

  // 上传预览文件
  const uploadPreview = async (orderId: string, files: any[], previewType: 'initial' | 'final', note?: string) => {
    try {
      const updatedOrder = await orderApi.uploadPreview(orderId, files, previewType, note)
      const index = orders.value.findIndex(o => o.id === orderId)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }
      ElMessage.success('预览上传成功，等待管理员审核')
      return updatedOrder
    } catch (error: any) {
      ElMessage.error(error.message || '上传预览文件失败')
      throw error
    }
  }
  
  // 审核预览
  const reviewPreview = async (orderId: string, params: { previewId: string; action: 'approve' | 'reject'; note?: string }) => {
    try {
      const updatedOrder = await orderApi.reviewPreview(orderId, params)
      const index = orders.value.findIndex(o => o.id === orderId)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }
      ElMessage.success('预览审核完成')
      return updatedOrder
    } catch (error: any) {
      ElMessage.error(error.message || '预览审核失败')
      throw error
    }
  }

  // 修改订单
  const updateOrder = async (orderId: string, orderData: any) => {
    try {
      const updatedOrder = await orderApi.updateOrder(orderId, orderData)
      const index = orders.value.findIndex(o => o.id === orderId)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }
      ElMessage.success('订单修改成功')
      return updatedOrder
    } catch (error: any) {
      ElMessage.error(error.message || '修改订单失败')
      throw error
    }
  }

  // 提交反馈
  const submitFeedback = async (orderId: string, feedbackData: any) => {
    try {
      await orderApi.submitFeedback(orderId, feedbackData)
      // 刷新订单详情
      const updatedOrder = await orderApi.getOrderDetail(orderId)
      if (updatedOrder) {
        const index = orders.value.findIndex(o => o.id === orderId)
        if (index !== -1) {
          orders.value[index] = updatedOrder
        }
      }
      ElMessage.success('反馈提交成功')
    } catch (error: any) {
      ElMessage.error(error.message || '提交反馈失败')
      throw error
    }
  }

  // 统计数据
  const orderStats = computed(() => {
    const stats = {
      total: orders.value.length,
      draft: orders.value.filter(o => o.status === 'draft').length,
      pendingAssign: orders.value.filter(o => o.status === 'pending_assign').length,
      pendingContract: orders.value.filter(o => o.status === 'pending_contract').length,
      inProduction: orders.value.filter(o => o.status === 'in_production').length,
      pendingReview: orders.value.filter(o => o.status === 'pending_review').length,
      reviewRejected: orders.value.filter(o => o.status === 'review_rejected').length,
      preview: orders.value.filter(o => o.status === 'preview_ready' || o.status === 'final_preview').length,
      revisionNeeded: orders.value.filter(o => o.status === 'revision_needed').length,
      completed: orders.value.filter(o => o.status === 'completed').length,
      cancelled: orders.value.filter(o => o.status === 'cancelled').length
    }
    return stats
  })

  return {
    orders,
    loading,
    orderStats,
    fetchOrders,
    createOrder,
    getOrderDetail,
    updateOrder,
    updateOrderStatus,
    assignOrder,
    uploadPreview,
    reviewPreview,
    submitFeedback
  }
})

