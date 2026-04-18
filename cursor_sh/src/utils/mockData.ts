import type { Task, TaskStatus } from '@/types'

// 模拟任务数据
export const mockTasks: Task[] = [
  {
    id: 'task-001',
    title: '实现用户登录功能',
    description: '需要实现用户登录界面，包括用户名、密码输入和角色选择功能。界面要简洁美观，符合苹果设计风格。',
    images: [
      'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=400&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&auto=format&fit=crop'
    ],
    status: 'pending',
    userId: 'user-001',
    userName: 'user',
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'task-002',
    title: '开发任务管理界面',
    description: '创建任务管理界面，支持任务的创建、编辑、删除操作。使用卡片式布局展示任务列表，支持状态筛选。',
    status: 'in_progress',
    userId: 'user-001',
    userName: 'user',
    createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'task-003',
    title: '优化系统性能',
    description: '对系统进行性能优化，包括代码优化、图片懒加载、路由懒加载等。目标是提升页面加载速度和用户体验。',
    images: [
      'https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=400&auto=format&fit=crop'
    ],
    status: 'completed',
    userId: 'user-001',
    userName: 'user',
    createdAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'task-004',
    title: '添加图片上传功能',
    description: '实现图片上传功能，支持多图片上传、预览、删除。限制图片大小和数量，提供良好的用户体验。',
    status: 'pending',
    userId: 'admin-001',
    userName: 'admin',
    createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'task-005',
    title: '实现数据统计功能',
    description: '为管理员添加数据统计功能，包括任务数量统计、状态分布图表等。使用现代化图表库展示数据。',
    status: 'in_progress',
    userId: 'admin-001',
    userName: 'admin',
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
  }
]

// 模拟API响应延迟
export const mockDelay = (ms: number = 500) => {
  return new Promise(resolve => setTimeout(resolve, ms))
}




