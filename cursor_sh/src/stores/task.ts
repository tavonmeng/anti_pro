import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '@/utils/api'
import type { Task, TaskStatus } from '@/types'
import { ElMessage } from 'element-plus'
import { useAuthStore } from './auth'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const loading = ref(false)
  const statusFilter = ref<TaskStatus | 'all'>('all')
  const authStore = useAuthStore()

  // 获取任务列表
  const fetchTasks = async (forceRefresh = false) => {
    if (loading.value && !forceRefresh) return
    
    loading.value = true
    try {
      const params: any = {}
      
      // 如果是普通用户，只获取自己的任务
      if (authStore.isUser() && authStore.user) {
        params.userId = authStore.user.id
      }
      
      // 如果有状态筛选
      if (statusFilter.value !== 'all') {
        params.status = statusFilter.value
      }
      
      tasks.value = await taskApi.getTasks(params)
    } catch (error: any) {
      ElMessage.error(error.message || '获取任务列表失败')
    } finally {
      loading.value = false
    }
  }

  // 创建任务
  const createTask = async (taskData: { 
    title: string
    description: string
    images?: string[]
    designShape?: string
    customShapeText?: string
    designSize?: string
    customWidth?: number
    customHeight?: number
    is3D?: boolean
    isCurved?: boolean
  }) => {
    try {
      const newTask = await taskApi.createTask(taskData)
      tasks.value.unshift(newTask)
      ElMessage.success('任务创建成功')
      return newTask
    } catch (error: any) {
      ElMessage.error(error.message || '创建任务失败')
      throw error
    }
  }

  // 更新任务
  const updateTask = async (id: string, taskData: Partial<Task>) => {
    try {
      const updatedTask = await taskApi.updateTask(id, taskData)
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index] = updatedTask
      }
      ElMessage.success('任务更新成功')
      return updatedTask
    } catch (error: any) {
      ElMessage.error(error.message || '更新任务失败')
      throw error
    }
  }

  // 删除任务
  const deleteTask = async (id: string) => {
    try {
      await taskApi.deleteTask(id)
      tasks.value = tasks.value.filter(t => t.id !== id)
      ElMessage.success('任务删除成功')
    } catch (error: any) {
      ElMessage.error(error.message || '删除任务失败')
      throw error
    }
  }

  // 更新任务状态
  const updateTaskStatus = async (id: string, status: TaskStatus) => {
    try {
      const updatedTask = await taskApi.updateTaskStatus(id, status)
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index] = updatedTask
      }
      ElMessage.success('任务状态更新成功')
      return updatedTask
    } catch (error: any) {
      ElMessage.error(error.message || '更新任务状态失败')
      throw error
    }
  }

  // 筛选后的任务列表
  const filteredTasks = computed(() => {
    if (statusFilter.value === 'all') {
      return tasks.value
    }
    return tasks.value.filter(task => task.status === statusFilter.value)
  })

  // 统计数据
  const taskStats = computed(() => {
    const stats = {
      total: tasks.value.length,
      pending: tasks.value.filter(t => t.status === 'pending').length,
      inProgress: tasks.value.filter(t => t.status === 'in_progress').length,
      completed: tasks.value.filter(t => t.status === 'completed').length,
      rejected: tasks.value.filter(t => t.status === 'rejected').length
    }
    return stats
  })

  // 设置状态筛选
  const setStatusFilter = (status: TaskStatus | 'all') => {
    statusFilter.value = status
  }

  return {
    tasks,
    loading,
    statusFilter,
    filteredTasks,
    taskStats,
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    updateTaskStatus,
    setStatusFilter
  }
})

