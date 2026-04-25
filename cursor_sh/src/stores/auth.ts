import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/utils/api'
import type { User, LoginRequest, UserRole } from '@/types'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const userStr = localStorage.getItem('user')
  const user = ref<User | null>(userStr ? JSON.parse(userStr) : null)

  // 登录
  const login = async (loginData: LoginRequest, silent = false) => {
    try {
      const response = await authApi.login(loginData, silent)
      token.value = response.token
      user.value = response.user
      
      // 保存到localStorage
      localStorage.setItem('token', response.token)
      localStorage.setItem('user', JSON.stringify(response.user))
      
      if (!silent) {
        ElMessage.success('登录成功')
      }
      return true
    } catch (error: any) {
      // 错误消息已经在 request 拦截器中处理（如果不是静默模式）
      // 我们把 error 抛出，方便调用端拦截并定制交互（比如提示去注册）
      throw error
    }
  }

  // 登出
  const logout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('登出失败:', error)
    } finally {
      token.value = null
      user.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      ElMessage.success('已退出登录')
    }
  }

  // 检查是否已登录
  const isAuthenticated = () => {
    return !!token.value && !!user.value
  }

  // 检查是否为管理员
  const isAdmin = () => {
    return user.value?.role === 'admin'
  }

  // 检查是否为普通用户
  const isUser = () => {
    return user.value?.role === 'user'
  }

  // 检查是否为负责人
  const isStaff = () => {
    return user.value?.role === 'staff'
  }

  // 检查是否为管理员或负责人
  const isAdminOrStaff = () => {
    return user.value?.role === 'admin' || user.value?.role === 'staff'
  }

  // 检查是否为已通过企业认证的用户
  const isEnterprise = () => {
    return user.value?.enterprise_status === 'approved'
  }

  return {
    token,
    user,
    login,
    logout,
    isAuthenticated,
    isAdmin,
    isUser,
    isStaff,
    isAdminOrStaff,
    isEnterprise
  }
})

