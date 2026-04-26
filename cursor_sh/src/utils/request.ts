import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '@/types'

// 扩展 AxiosRequestConfig 以支持 silent 标记
declare module 'axios' {
  export interface AxiosRequestConfig {
    silent?: boolean
  }
}

// 创建axios实例
const request: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    // 调试日志
    console.log('Response received:', response.data)
    
    const { code, message, data } = response.data
    
    // 200 和 201 都视为成功（201 是创建成功）
    if (code === 200 || code === 201 || code === 0) {
      return data
    } else {
      const errorMsg = message || '请求失败'
      console.error('API Error:', { code, message, data })
      
      // 检查请求配置中是否有 silent 标记
      const isSilent = response.config?.silent === true
      if (!isSilent) {
        ElMessage.error(errorMsg)
      }
      
      return Promise.reject(new Error(errorMsg))
    }
  },
  (error) => {
    // 调试日志
    console.error('Request error:', error)
    
    // 检查请求配置中是否有 silent 标记（静默模式，不显示错误消息）
    const isSilent = error.config?.silent === true
    
    // 处理HTTP错误
    if (error.response) {
      const { status, data } = error.response
      console.error('Error response:', { status, data })
      
      // 获取错误信息，优先使用 detail，其次使用 message
      const errorMessage = data?.detail || data?.message || '请求失败'
      
      // 如果是静默模式，不显示错误消息
      if (isSilent) {
        return Promise.reject(error)
      }
      
      switch (status) {
        case 401:
          // 登录页面或弹窗中的401错误不跳转，只显示错误信息
          const currentPath = window.location.pathname
          const isAuthModalOpen = !!document.querySelector('.auth-modal-overlay')
          if (currentPath !== '/login' && currentPath !== '/admin/login' && currentPath !== '/register' && !isAuthModalOpen) {
            ElMessage.error('未授权，请重新登录')
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            window.location.href = '/login'
          } else {
            ElMessage.error(errorMessage)
          }
          break
        case 403:
          ElMessage.error(errorMessage || '拒绝访问')
          break
        case 404:
          ElMessage.error(errorMessage || '请求地址不存在')
          break
        case 409:
          ElMessage.error(errorMessage || '资源冲突')
          break
        case 500:
          ElMessage.error(errorMessage || '服务器内部错误')
          break
        default:
          ElMessage.error(errorMessage || `请求失败 (${status})`)
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('No response received:', error.request)
      if (!isSilent) {
        ElMessage.error('网络连接失败，请检查后端服务是否启动')
      }
    } else {
      // 请求配置错误
      console.error('Request config error:', error.message)
      if (!isSilent) {
        ElMessage.error('请求配置错误: ' + (error.message || '未知错误'))
      }
    }
    return Promise.reject(error)
  }
)

export default request

