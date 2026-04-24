import request from './request'
import type { 
  LoginRequest, 
  LoginResponse, 
  RegisterRequest, 
  Task, 
  TaskStatus,
  Order,
  OrderType,
  OrderStatus,
  OrderFeedback,
  UploadedFile,
  User,
  NotificationList,
  Notification
} from '@/types'

// 模拟用户数据
const MOCK_USERS = {
  user: {
    id: 'user-001',
    username: 'user',
    password: '123456',
    role: 'user' as const,
    email: 'user@example.com'
  },
  admin: {
    id: 'admin-001',
    username: 'admin',
    password: '123456',
    role: 'admin' as const,
    email: 'admin@example.com'
  }
}

// 是否启用模拟模式（可以根据环境变量控制）
const ENABLE_MOCK = false // 关闭模拟模式，使用真实后端API

// 模拟登录
const mockLogin = (data: LoginRequest): Promise<LoginResponse> => {
  return new Promise((resolve, reject) => {
    // 模拟网络延迟
    setTimeout(() => {
      const userKey = data.role === 'admin' ? 'admin' : 'user'
      const mockUser = MOCK_USERS[userKey]
      
      // 验证用户名和密码
      if (data.username === mockUser.username && data.password === mockUser.password) {
        const token = `mock-token-${mockUser.id}-${Date.now()}`
        resolve({
          token,
          user: {
            id: mockUser.id,
            username: mockUser.username,
            role: mockUser.role,
            email: mockUser.email
          }
        })
      } else {
        reject(new Error('用户名或密码错误'))
      }
    }, 500) // 模拟 500ms 延迟
  })
}

// 模拟注册
const mockRegister = (data: RegisterRequest): Promise<{ success: boolean }> => {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      // 检查用户名是否已存在
      const existingUsers = JSON.parse(localStorage.getItem('mockUsers') || '[]')
      const userExists = existingUsers.some((u: any) => u.username === data.username)
      
      if (userExists) {
        reject(new Error('用户名已存在'))
      } else {
        // 创建新用户
        const newUser = {
          id: `user-${Date.now()}`,
          username: data.username,
          password: data.password,
          role: data.role,
          email: data.email
        }
        
        existingUsers.push(newUser)
        localStorage.setItem('mockUsers', JSON.stringify(existingUsers))
        
        resolve({ success: true })
      }
    }, 500)
  })
}

// 认证相关API
export interface Announcement {
  id: string
  title: string
  content: string
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string
}

export const authApi = {
  // 登录
  async login(data: LoginRequest, silent = false): Promise<LoginResponse> {
    if (ENABLE_MOCK) {
      try {
        // 先尝试真实API，如果失败则使用模拟数据
        return await request.post('/auth/login', data, { silent })
      } catch (error) {
        // API 请求失败，使用模拟登录
        console.log('使用模拟登录功能')
        
        // 从localStorage获取用户列表
        const mockUsers = JSON.parse(localStorage.getItem('mockUsers') || '[]')
        const defaultUsers = [
          { id: 'user-001', username: 'user', password: '123456', role: 'user', email: 'user@example.com' },
          { id: 'admin-001', username: 'admin', password: '123456', role: 'admin', email: 'admin@example.com' }
        ]
        const allUsers = [...defaultUsers, ...mockUsers]
        
        const user = allUsers.find((u: any) => 
          u.username === data.username && 
          u.password === data.password && 
          u.role === data.role
        )
        
        if (user) {
          const token = `mock-token-${user.id}-${Date.now()}`
          return {
            token,
            user: {
              id: user.id,
              username: user.username,
              role: user.role,
              email: user.email
            }
          }
        } else {
          throw new Error('用户名或密码错误')
        }
      }
    } else {
      // 生产环境，只使用真实API
      return request.post('/auth/login', data, { silent })
    }
  },
  
  // 注册
  async register(data: RegisterRequest): Promise<boolean> {
    if (ENABLE_MOCK) {
      try {
        await request.post('/auth/register', data)
        return true
      } catch (error) {
        console.log('使用模拟注册功能')
        await mockRegister(data)
        return true
      }
    } else {
      await request.post('/auth/register', data)
      return true
    }
  },
  
  // 发送短信验证码
  async sendSms(phone: string): Promise<any> {
    return request.post('/auth/send-sms', { phone })
  },
  
  // 验证短信验证码
  async verifySms(phone: string, code: string): Promise<boolean> {
    if (ENABLE_MOCK) return true
    return request.post('/auth/verify-sms', { phone, code })
  },
  
  // 重置密码（忘记密码）
  async resetPassword(phone: string, sms_code: string, new_password: string): Promise<any> {
    return request.post('/auth/reset-password', { phone, sms_code, new_password })
  },
  
  // 登出
  logout(): Promise<void> {
    if (ENABLE_MOCK) {
      // 模拟登出，直接返回成功
      return Promise.resolve()
    }
    return request.post('/auth/logout')
  },
  
  // 修改密码
  async changePassword(data: { oldPassword: string; newPassword: string }): Promise<void> {
    return request.put('/auth/change-password', {
      oldPassword: data.oldPassword,
      newPassword: data.newPassword
    })
  }
}

// 任务相关API
export const taskApi = {
  // 获取任务列表
  async getTasks(params?: { userId?: string; status?: TaskStatus }): Promise<Task[]> {
    if (ENABLE_MOCK) {
      try {
        return await request.get('/tasks', { params })
      } catch (error) {
        // 使用模拟数据
        const { mockTasks, mockDelay } = await import('./mockData')
        await mockDelay(300)
        
        // 合并localStorage中的任务和初始模拟任务
        const storedTasks = localStorage.getItem('mockTasks')
        const storedTasksList: Task[] = storedTasks ? JSON.parse(storedTasks) : []
        
        // 合并任务列表：storedTasks优先，然后添加不在storedTasks中的mockTasks
        const storedTaskIds = new Set(storedTasksList.map((t: Task) => t.id))
        const allTasks: Task[] = [
          ...storedTasksList,
          ...mockTasks.filter(t => !storedTaskIds.has(t.id))
        ]
        
        let tasks = [...allTasks]
        
        // 根据用户ID筛选
        if (params?.userId) {
          tasks = tasks.filter(task => task.userId === params.userId)
        }
        
        // 根据状态筛选（注意：这里不过滤，让前端筛选）
        // 状态筛选由前端store处理
        
        return tasks
      }
    }
    return request.get('/tasks', { params })
  },
  
  // 获取任务详情
  async getTaskById(id: string): Promise<Task> {
    if (ENABLE_MOCK) {
      try {
        return await request.get(`/tasks/${id}`)
      } catch (error) {
        const { mockTasks, mockDelay } = await import('./mockData')
        await mockDelay(200)
        const task = mockTasks.find(t => t.id === id)
        if (!task) {
          throw new Error('任务不存在')
        }
        return task
      }
    }
    return request.get(`/tasks/${id}`)
  },
  
  // 创建任务
  async createTask(data: { 
    title: string
    description: string
    images?: string[]
    designShape?: string
    designSize?: string
    is3D?: boolean
    isCurved?: boolean
  }): Promise<Task> {
    if (ENABLE_MOCK) {
      try {
        return await request.post('/tasks', data)
      } catch (error) {
        const { mockDelay } = await import('./mockData')
        await mockDelay(400)
        
        const user = localStorage.getItem('user') 
          ? JSON.parse(localStorage.getItem('user')!) 
          : { id: 'user-001', username: 'user' }
        
        const newTask: Task = {
          id: `task-${Date.now()}`,
          title: data.title,
          description: data.description,
          images: data.images,
          designShape: data.designShape as any,
          customShapeText: (data as any).customShapeText,
          designSize: data.designSize as any,
          customWidth: (data as any).customWidth,
          customHeight: (data as any).customHeight,
          is3D: data.is3D,
          isCurved: data.isCurved,
          status: 'pending',
          userId: user.id,
          userName: user.username,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }
        
        // 保存到localStorage
        const storedTasks = localStorage.getItem('mockTasks')
        const allTasks = storedTasks ? JSON.parse(storedTasks) : []
        allTasks.unshift(newTask)
        localStorage.setItem('mockTasks', JSON.stringify(allTasks))
        
        return newTask
      }
    }
    return request.post('/tasks', data)
  },
  
  // 更新任务
  async updateTask(id: string, data: Partial<Task>): Promise<Task> {
    if (ENABLE_MOCK) {
      try {
        return await request.put(`/tasks/${id}`, data)
      } catch (error) {
        const { mockTasks, mockDelay } = await import('./mockData')
        await mockDelay(300)
        
        const task = mockTasks.find(t => t.id === id)
        if (!task) {
          throw new Error('任务不存在')
        }
        
        return {
          ...task,
          ...data,
          updatedAt: new Date().toISOString()
        }
      }
    }
    return request.put(`/tasks/${id}`, data)
  },
  
  // 删除任务
  async deleteTask(id: string): Promise<void> {
    if (ENABLE_MOCK) {
      try {
        return await request.delete(`/tasks/${id}`)
      } catch (error) {
        const { mockDelay } = await import('./mockData')
        await mockDelay(300)
        
        // 从localStorage删除任务
        const storedTasks = localStorage.getItem('mockTasks')
        if (storedTasks) {
          const allTasks = JSON.parse(storedTasks)
          const filteredTasks = allTasks.filter((t: Task) => t.id !== id)
          localStorage.setItem('mockTasks', JSON.stringify(filteredTasks))
        }
        
        return Promise.resolve()
      }
    }
    return request.delete(`/tasks/${id}`)
  },
  
  // 更新任务状态
  async updateTaskStatus(id: string, status: TaskStatus): Promise<Task> {
    if (ENABLE_MOCK) {
      try {
        return await request.patch(`/tasks/${id}/status`, { status })
      } catch (error) {
        const { mockDelay } = await import('./mockData')
        await mockDelay(300)
        
        // 从localStorage获取任务
        const storedTasks = localStorage.getItem('mockTasks')
        const allTasks = storedTasks ? JSON.parse(storedTasks) : []
        const task = allTasks.find((t: Task) => t.id === id)
        
        if (!task) {
          throw new Error('任务不存在')
        }
        
        const updatedTask = {
          ...task,
          status,
          updatedAt: new Date().toISOString()
        }
        
        // 更新localStorage中的任务
        const updatedTasks = allTasks.map((t: Task) => 
          t.id === id ? updatedTask : t
        )
        localStorage.setItem('mockTasks', JSON.stringify(updatedTasks))
        
        return updatedTask
      }
    }
    return request.patch(`/tasks/${id}/status`, { status })
  }
}

// 用户相关API
export const userApi = {
  // 获取用户列表（管理员）
  getUsers(): Promise<any[]> {
    return request.get('/users')
  },
  
  // 获取用户详情
  getUserById(id: string): Promise<any> {
    return request.get(`/users/${id}`)
  },
  
  // 更新个人信息
  updateProfile(data: any): Promise<any> {
    if (ENABLE_MOCK) {
      return Promise.resolve({ success: true })
    }
    return request.put('/auth/profile', data)
  }
}

// ========== 订单相关API ==========

// 生成订单编号
const generateOrderNumber = (): string => {
  const now = new Date()
  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '')
  const randomStr = Math.random().toString(36).substr(2, 4).toUpperCase()
  return `ORD-${dateStr}-${randomStr}`
}

// 订单相关API
export const orderApi = {
  // 获取订单列表
  async getOrders(params?: { 
    userId?: string
    orderType?: OrderType
    status?: OrderStatus
    assigneeId?: string
  }): Promise<Order[]> {
    if (ENABLE_MOCK) {
      try {
        return await request.get('/orders', { params })
      } catch (error) {
        console.log('使用模拟订单数据')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        
        let filteredOrders = allOrders
        
        if (params?.userId) {
          filteredOrders = filteredOrders.filter((o: Order) => o.userId === params.userId)
        }
        if (params?.orderType) {
          filteredOrders = filteredOrders.filter((o: Order) => o.orderType === params.orderType)
        }
        if (params?.status) {
          filteredOrders = filteredOrders.filter((o: Order) => o.status === params.status)
        }
        if (params?.assigneeId) {
          filteredOrders = filteredOrders.filter((o: Order) => 
            o.assignees && o.assignees.some((a: { id: string }) => a.id === params.assigneeId)
          )
        }
        
        return filteredOrders
      }
    } else {
      return request.get('/orders', { params })
    }
  },
  
  // 创建订单
  async createOrder(data: any, isDraft: boolean = false): Promise<Order> {
    if (ENABLE_MOCK) {
      try {
        return await request.post(`/orders?is_draft=${isDraft}`, data)
      } catch (error) {
        console.log('使用模拟创建订单')
        const authStore = JSON.parse(localStorage.getItem('auth') || '{}')
        const user = authStore.user
        
        const baseOrder = {
          id: `order-${Date.now()}`,
          orderNumber: generateOrderNumber(),
          status: (isDraft ? 'draft' : 'pending_contract') as OrderStatus,
          userId: user?.id || 'unknown',
          userName: user?.username || 'Unknown',
          assignee: undefined,
          assignees: undefined,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          feedbacks: [],
          revisionCount: 0
        }
        
        const newOrder: Order = {
          ...baseOrder,
          ...data
        }
        
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        allOrders.unshift(newOrder)
        localStorage.setItem('mockOrders', JSON.stringify(allOrders))
        
        return newOrder
      }
    } else {
      return request.post(`/orders?is_draft=${isDraft}`, data)
    }
  },
  
  // 获取订单详情
  async getOrderDetail(orderId: string): Promise<Order> {
    if (ENABLE_MOCK) {
      try {
        return await request.get(`/orders/${orderId}`)
      } catch (error) {
        console.log('使用模拟获取订单详情')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        const order = allOrders.find((o: Order) => o.id === orderId)
        if (!order) {
          throw new Error('订单不存在')
        }
        return order
      }
    } else {
      return request.get(`/orders/${orderId}`)
    }
  },
  
  // 修改订单
  async updateOrder(orderId: string, data: any): Promise<Order> {
    if (ENABLE_MOCK) {
      try {
        return await request.put(`/orders/${orderId}`, data)
      } catch (error) {
        console.log('使用模拟修改订单')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        const orderIndex = allOrders.findIndex((o: Order) => o.id === orderId)
        if (orderIndex === -1) {
          throw new Error('订单不存在')
        }
        
        allOrders[orderIndex] = {
          ...allOrders[orderIndex],
          ...data,
          updatedAt: new Date().toISOString()
        }
        localStorage.setItem('mockOrders', JSON.stringify(allOrders))
        return allOrders[orderIndex]
      }
    } else {
      return request.put(`/orders/${orderId}`, data)
    }
  },
  
  // 更新订单状态
  async updateOrderStatus(orderId: string, status: OrderStatus): Promise<Order> {
    if (ENABLE_MOCK) {
      try {
        return await request.put(`/orders/${orderId}/status`, { status })
      } catch (error) {
        console.log('使用模拟更新订单状态')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        const orderIndex = allOrders.findIndex((o: Order) => o.id === orderId)
        if (orderIndex === -1) {
          throw new Error('订单不存在')
        }
        
        allOrders[orderIndex].status = status
        allOrders[orderIndex].updatedAt = new Date().toISOString()
        
        localStorage.setItem('mockOrders', JSON.stringify(allOrders))
        return allOrders[orderIndex]
      }
    } else {
      return request.put(`/orders/${orderId}/status`, { status })
    }
  },
  
  // 分配负责人
  async assignOrder(orderId: string, assigneeIds: string[], assigneeNames: string[]): Promise<Order> {
    if (ENABLE_MOCK) {
      try {
        return await request.put(`/orders/${orderId}/assign`, { assigneeIds, assigneeNames })
      } catch (error) {
        console.log('使用模拟分配负责人')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        const orderIndex = allOrders.findIndex((o: Order) => o.id === orderId)
        if (orderIndex === -1) {
          throw new Error('订单不存在')
        }
        
        allOrders[orderIndex].assignees = assigneeIds.map((id, index) => ({
          id,
          name: assigneeNames[index]
        }))
        allOrders[orderIndex].status = 'in_production'
        allOrders[orderIndex].updatedAt = new Date().toISOString()
        
        localStorage.setItem('mockOrders', JSON.stringify(allOrders))
        return allOrders[orderIndex]
      }
    } else {
      return request.put(`/orders/${orderId}/assign`, { assigneeIds, assigneeNames })
    }
  },
  
  // 上传预览文件
  async uploadPreview(orderId: string, files: UploadedFile[], previewType: 'initial' | 'final', note?: string): Promise<Order> {
    if (ENABLE_MOCK) {
      try {
        return await request.post(`/orders/${orderId}/preview`, { files, note, previewType })
      } catch (error) {
        console.log('使用模拟上传预览')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        const orderIndex = allOrders.findIndex((o: Order) => o.id === orderId)
        if (orderIndex === -1) {
          throw new Error('订单不存在')
        }
        
        const order = allOrders[orderIndex] as Order & { previewHistory?: any[]; pendingReviewPreviewIds?: string[] }
        if (!order.previewHistory) {
          order.previewHistory = []
        }
        if (!order.pendingReviewPreviewIds) {
          order.pendingReviewPreviewIds = []
        }
        const previewId = `preview-${Date.now()}`
        const historyEntry = {
          id: previewId,
          files,
          note: note || '',
          createdAt: new Date().toISOString(),
          createdBy: 'mock-staff',
          createdByName: 'Mock Staff',
          previewType,
          reviewStatus: 'pending' as const,
          reviewNote: '',
          reviewedAt: null,
          reviewedBy: null,
          reviewedByName: null
        }
        order.previewHistory.push(historyEntry)
        order.pendingReviewPreviewIds.push(previewId)
        order.status = 'pending_review'
        order.updatedAt = new Date().toISOString()
        localStorage.setItem('mockOrders', JSON.stringify(allOrders))
        return order
      }
    } else {
      return request.post(`/orders/${orderId}/preview`, { files, note, previewType })
    }
  },
  
  // 审核预览
  async reviewPreview(orderId: string, data: { previewId: string; action: 'approve' | 'reject'; note?: string }): Promise<Order> {
    if (ENABLE_MOCK) {
      try {
        return await request.post(`/orders/${orderId}/preview/review`, data)
      } catch (error) {
        console.log('使用模拟审核预览')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        const orderIndex = allOrders.findIndex((o: Order) => o.id === orderId)
        if (orderIndex === -1) {
          throw new Error('订单不存在')
        }
        const order = allOrders[orderIndex] as Order & { previewHistory?: any[]; pendingReviewPreviewIds?: string[]; previewFiles?: UploadedFile[] }
        const history = order.previewHistory || []
        const entry = history.find((item: any) => item.id === data.previewId)
        if (!entry) {
          throw new Error('预览记录不存在')
        }
        entry.reviewStatus = data.action === 'approve' ? 'approved' : 'rejected'
        entry.reviewNote = data.note || ''
        entry.reviewedAt = new Date().toISOString()
        entry.reviewedBy = 'mock-admin'
        entry.reviewedByName = 'Mock Admin'
        order.pendingReviewPreviewIds = (order.pendingReviewPreviewIds || []).filter(id => id !== data.previewId)
        if (data.action === 'approve') {
          order.previewFiles = [...(order.previewFiles || []), ...entry.files]
          order.status = entry.previewType === 'final' ? 'final_preview' : 'preview_ready'
        } else {
          order.status = 'review_rejected'
        }
        order.updatedAt = new Date().toISOString()
        localStorage.setItem('mockOrders', JSON.stringify(allOrders))
        return order
      }
    } else {
      return request.post(`/orders/${orderId}/preview/review`, data)
    }
  },
  
  // 提交反馈
  async submitFeedback(orderId: string, feedbackData: Partial<OrderFeedback>): Promise<OrderFeedback> {
    if (ENABLE_MOCK) {
      try {
        return await request.post(`/orders/${orderId}/feedback`, feedbackData)
      } catch (error) {
        console.log('使用模拟提交反馈')
        const allOrders = JSON.parse(localStorage.getItem('mockOrders') || '[]')
        const orderIndex = allOrders.findIndex((o: Order) => o.id === orderId)
        if (orderIndex === -1) {
          throw new Error('订单不存在')
        }
        
        const authStore = JSON.parse(localStorage.getItem('auth') || '{}')
        const user = authStore.user
        
        const feedback: OrderFeedback = {
          id: `feedback-${Date.now()}`,
          orderId,
          content: feedbackData.content || '',
          type: feedbackData.type || 'approval',
          createdAt: new Date().toISOString(),
          createdBy: user?.id || 'unknown',
          createdByName: user?.username || 'Unknown'
        }
        
        allOrders[orderIndex].feedbacks.push(feedback)
        
        // 根据反馈类型更新订单状态
        if (feedback.type === 'revision') {
          allOrders[orderIndex].status = 'revision_needed'
          allOrders[orderIndex].revisionCount += 1
        } else if (feedback.type === 'approval') {
          if (allOrders[orderIndex].status === 'preview_ready') {
            allOrders[orderIndex].status = 'in_production'
          } else if (allOrders[orderIndex].status === 'final_preview') {
            allOrders[orderIndex].status = 'completed'
          }
        }
        
        allOrders[orderIndex].updatedAt = new Date().toISOString()
        localStorage.setItem('mockOrders', JSON.stringify(allOrders))
        
        return feedback
      }
    } else {
      return request.post(`/orders/${orderId}/feedback`, feedbackData)
    }
  },
  
  // 下载需求告知函 PDF
  async downloadConfirmationPdf(orderId: string): Promise<void> {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/orders/${orderId}/pdf/confirmation`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    if (!response.ok) {
      throw new Error('下载 PDF 失败')
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const disposition = response.headers.get('Content-Disposition')
    const filename = disposition?.match(/filename="(.+)"/)?.[1] || `confirmation_${orderId}.pdf`
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },
  
  // 下载订单详情 PDF（管理员）
  async downloadDetailPdf(orderId: string): Promise<void> {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/orders/${orderId}/pdf/detail`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    if (!response.ok) {
      throw new Error('下载 PDF 失败')
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const disposition = response.headers.get('Content-Disposition')
    const filename = disposition?.match(/filename="(.+)"/)?.[1] || `order_detail_${orderId}.pdf`
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  // 推进合同流程（管理员）
  async advanceContract(orderId: string, data: { contractNumber: string; paymentAmount: number; note?: string }): Promise<Order> {
    return request.post(`/orders/${orderId}/contract/advance`, data)
  },

  // 管理员取消订单（需 SMS 验证）
  async adminCancelOrder(orderId: string, data: { phone: string; smsCode: string; reason?: string }): Promise<Order> {
    return request.post(`/orders/${orderId}/cancel`, data)
  }
}

// 负责人相关API
export const staffApi = {
  // 获取负责人列表
  async getStaff(params?: { 
    page?: number
    pageSize?: number
    keyword?: string
    role?: string
    isActive?: boolean
  }): Promise<{ data: User[], total: number }> {
    if (ENABLE_MOCK) {
      try {
        return await request.get('/staff', { params })
      } catch (error) {
        console.log('使用模拟获取负责人列表')
        const { mockDelay } = await import('./mockData')
        await mockDelay(300)
        
        let mockStaff = JSON.parse(localStorage.getItem('mockStaff') || '[]')
        
        // 如果没有负责人，创建一些默认的
        if (mockStaff.length === 0) {
          const defaultStaff = [
            {
              id: 'staff-001',
              username: 'staff1',
              role: 'staff' as const,
              email: 'staff1@example.com',
              realName: '张设计',
              isActive: true,
              orderCount: 5,
              createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
            },
            {
              id: 'staff-002',
              username: 'staff2',
              role: 'staff' as const,
              email: 'staff2@example.com',
              realName: '李艺术',
              isActive: true,
              orderCount: 3,
              createdAt: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString()
            },
            {
              id: 'staff-003',
              username: 'staff3',
              role: 'staff' as const,
              email: 'staff3@example.com',
              realName: '王制作',
              isActive: true,
              orderCount: 7,
              createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString()
            },
            {
              id: 'admin-001',
              username: 'admin',
              role: 'admin' as const,
              email: 'admin@example.com',
              realName: '系统管理员',
              isActive: true,
              orderCount: 0,
              createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString()
            }
          ]
          localStorage.setItem('mockStaff', JSON.stringify(defaultStaff))
          mockStaff = defaultStaff
        }
        
        // 筛选
        let filteredStaff = [...mockStaff]
        
        if (params?.keyword) {
          const keyword = params.keyword.toLowerCase()
          filteredStaff = filteredStaff.filter(s => 
            s.username.toLowerCase().includes(keyword) ||
            (s.realName && s.realName.toLowerCase().includes(keyword)) ||
            (s.email && s.email.toLowerCase().includes(keyword))
          )
        }
        
        if (params?.role) {
          filteredStaff = filteredStaff.filter(s => s.role === params.role)
        }
        
        if (params?.isActive !== undefined) {
          filteredStaff = filteredStaff.filter(s => s.isActive === params.isActive)
        }
        
        // 分页
        const page = params?.page || 1
        const pageSize = params?.pageSize || 20
        const start = (page - 1) * pageSize
        const end = start + pageSize
        const paginatedStaff = filteredStaff.slice(start, end)
        
        return {
          data: paginatedStaff,
          total: filteredStaff.length
        }
      }
    } else {
      return request.get('/staff', { params })
    }
  },
  
  // 添加负责人
  async addStaff(userData: Partial<User> & { password?: string }): Promise<User> {
    if (ENABLE_MOCK) {
      try {
        return await request.post('/staff', userData)
      } catch (error) {
        console.log('使用模拟添加负责人')
        const { mockDelay } = await import('./mockData')
        await mockDelay(400)
        
        // 检查用户名是否已存在
        const mockStaff = JSON.parse(localStorage.getItem('mockStaff') || '[]')
        const exists = mockStaff.find((s: User) => s.username === userData.username)
        if (exists) {
          throw new Error('用户名已存在')
        }
        
        const newStaff: User = {
          id: `staff-${Date.now()}`,
          username: userData.username || '',
          role: userData.role || 'staff',
          email: userData.email,
          realName: userData.realName,
          isActive: userData.isActive ?? true,
          orderCount: 0,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }
        
        mockStaff.push(newStaff)
        localStorage.setItem('mockStaff', JSON.stringify(mockStaff))
        
        return newStaff
      }
    } else {
      return request.post('/staff', userData)
    }
  },
  
  // 更新负责人
  async updateStaff(id: string, userData: Partial<User>): Promise<User> {
    if (ENABLE_MOCK) {
      try {
        return await request.put(`/staff/${id}`, userData)
      } catch (error) {
        console.log('使用模拟更新负责人')
        const { mockDelay } = await import('./mockData')
        await mockDelay(400)
        
        const mockStaff = JSON.parse(localStorage.getItem('mockStaff') || '[]')
        const index = mockStaff.findIndex((s: User) => s.id === id)
        
        if (index === -1) {
          throw new Error('负责人不存在')
        }
        
        mockStaff[index] = {
          ...mockStaff[index],
          ...userData,
          updatedAt: new Date().toISOString()
        }
        
        localStorage.setItem('mockStaff', JSON.stringify(mockStaff))
        return mockStaff[index]
      }
    } else {
      return request.put(`/staff/${id}`, userData)
    }
  },
  
  // 删除负责人
  async deleteStaff(id: string): Promise<void> {
    if (ENABLE_MOCK) {
      try {
        return await request.delete(`/staff/${id}`)
      } catch (error) {
        console.log('使用模拟删除负责人')
        const { mockDelay } = await import('./mockData')
        await mockDelay(300)
        
        const mockStaff = JSON.parse(localStorage.getItem('mockStaff') || '[]')
        const staff = mockStaff.find((s: User) => s.id === id)
        
        if (!staff) {
          throw new Error('负责人不存在')
        }
        
        if (staff.orderCount && staff.orderCount > 0) {
          throw new Error('该负责人还有进行中的订单，无法删除')
        }
        
        const filteredStaff = mockStaff.filter((s: User) => s.id !== id)
        localStorage.setItem('mockStaff', JSON.stringify(filteredStaff))
      }
    } else {
      return request.delete(`/staff/${id}`)
    }
  }
}

// 消息通知相关API
export const notificationApi = {
  // 获取消息列表
  async getNotifications(params?: { 
    skip?: number
    limit?: number
    unreadOnly?: boolean
  }): Promise<NotificationList> {
    return request.get('/notifications', { params })
  },

  // 获取未读消息数量
  async getUnreadCount(): Promise<{ unreadCount: number }> {
    return request.get('/notifications/unread-count')
  },

  // 标记消息为已读
  async markAsRead(notificationId: string): Promise<Notification> {
    return request.put(`/notifications/${notificationId}/read`)
  },

  // 标记所有消息为已读
  async markAllAsRead(): Promise<{ count: number }> {
    return request.put('/notifications/read-all')
  },

  // 删除消息
  async deleteNotification(notificationId: string): Promise<void> {
    return request.delete(`/notifications/${notificationId}`)
  }
}

// 公告 API 接口
export const announcementApi = {
  // 获取公告列表 (activeOnly 为 true 时仅获取展示中的)
  async getAnnouncements(activeOnly: boolean = true): Promise<Announcement[]> {
    const res = await request.get('/announcements', { params: { active_only: activeOnly } })
    return res.data
  },
  
  // 创建公告
  async createAnnouncement(data: { title: string; content: string; is_active: boolean }): Promise<Announcement> {
    const res = await request.post('/announcements', data)
    return res.data
  },
  
  // 更新公告
  async updateAnnouncement(id: string, data: Partial<{ title: string; content: string; is_active: boolean }>): Promise<Announcement> {
    const res = await request.put(`/announcements/${id}`, data)
    return res.data
  },
  
  // 删除公告
  async deleteAnnouncement(id: string): Promise<void> {
    await request.delete(`/announcements/${id}`)
  }
}
