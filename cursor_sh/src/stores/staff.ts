import { defineStore } from 'pinia'
import { ref } from 'vue'
import { staffApi } from '@/utils/api'
import type { User } from '@/types'
import { ElMessage } from 'element-plus'

export const useStaffStore = defineStore('staff', () => {
  const staffList = ref<User[]>([])
  const loading = ref(false)

  // 获取负责人列表
  const fetchStaff = async () => {
    loading.value = true
    try {
      const result = await staffApi.getStaff()
      staffList.value = result.data
    } catch (error: any) {
      ElMessage.error(error.message || '获取负责人列表失败')
    } finally {
      loading.value = false
    }
  }

  // 添加负责人
  const addStaff = async (userData: Partial<User>) => {
    try {
      const newStaff = await staffApi.addStaff(userData)
      staffList.value.push(newStaff)
      ElMessage.success('负责人添加成功')
      return newStaff
    } catch (error: any) {
      ElMessage.error(error.message || '添加负责人失败')
      throw error
    }
  }

  return {
    staffList,
    loading,
    fetchStaff,
    addStaff
  }
})

