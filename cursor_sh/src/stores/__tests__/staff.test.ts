import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useStaffStore } from '../staff'
import { staffApi } from '@/utils/api'
import type { User } from '@/types'

// Mock staffApi
vi.mock('@/utils/api', () => ({
  staffApi: {
    getStaff: vi.fn(),
    addStaff: vi.fn()
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('useStaffStore', () => {
  beforeEach(() => {
    // 每次测试前创建新的 pinia 实例
    setActivePinia(createPinia())
    // 清除所有 mock
    vi.clearAllMocks()
  })

  describe('fetchStaff', () => {
    it('应该正确提取 data 字段并设置到 staffList', async () => {
      const store = useStaffStore()
      
      // Mock API 返回的数据结构
      const mockApiResponse = {
        data: [
          {
            id: 'staff-001',
            username: 'staff1',
            role: 'staff' as const,
            email: 'staff1@example.com',
            realName: '张设计',
            isActive: true,
            orderCount: 5
          },
          {
            id: 'staff-002',
            username: 'staff2',
            role: 'staff' as const,
            email: 'staff2@example.com',
            realName: '李艺术',
            isActive: true,
            orderCount: 3
          }
        ],
        total: 2
      }

      vi.mocked(staffApi.getStaff).mockResolvedValue(mockApiResponse)

      // 执行 fetchStaff
      await store.fetchStaff()

      // 验证 staffList 是正确的数组，包含正确的数据
      expect(store.staffList).toEqual(mockApiResponse.data)
      expect(store.staffList).toHaveLength(2)
      expect(store.staffList[0].id).toBe('staff-001')
      expect(store.staffList[0].realName).toBe('张设计')
      expect(store.staffList[1].id).toBe('staff-002')
      expect(store.staffList[1].realName).toBe('李艺术')
      
      // 验证 loading 状态
      expect(store.loading).toBe(false)
      
      // 验证 API 被调用
      expect(staffApi.getStaff).toHaveBeenCalledTimes(1)
    })

    it('应该正确处理空列表', async () => {
      const store = useStaffStore()
      
      const mockApiResponse = {
        data: [],
        total: 0
      }

      vi.mocked(staffApi.getStaff).mockResolvedValue(mockApiResponse)

      await store.fetchStaff()

      expect(store.staffList).toEqual([])
      expect(store.staffList).toHaveLength(0)
      expect(store.loading).toBe(false)
    })

    it('应该在 API 调用失败时处理错误', async () => {
      const store = useStaffStore()
      const errorMessage = '网络错误'
      
      vi.mocked(staffApi.getStaff).mockRejectedValue(new Error(errorMessage))

      await store.fetchStaff()

      // 验证 staffList 没有被修改（保持初始状态）
      expect(store.staffList).toEqual([])
      expect(store.loading).toBe(false)
    })

    it('应该在加载时设置 loading 状态', async () => {
      const store = useStaffStore()
      
      const mockApiResponse = {
        data: [],
        total: 0
      }

      // 创建一个延迟的 Promise
      let resolvePromise: (value: any) => void
      const delayedPromise = new Promise((resolve) => {
        resolvePromise = resolve
      })

      vi.mocked(staffApi.getStaff).mockReturnValue(delayedPromise as any)

      // 开始 fetchStaff（不等待完成）
      const fetchPromise = store.fetchStaff()

      // 验证 loading 状态为 true
      expect(store.loading).toBe(true)

      // 完成 Promise
      resolvePromise!(mockApiResponse)
      await fetchPromise

      // 验证 loading 状态为 false
      expect(store.loading).toBe(false)
    })
  })

  describe('addStaff', () => {
    it('应该正确添加负责人到列表', async () => {
      const store = useStaffStore()
      
      // 初始化一些现有数据
      store.staffList = [
        {
          id: 'staff-001',
          username: 'staff1',
          role: 'staff' as const,
          realName: '张设计'
        }
      ]

      const newStaff: User = {
        id: 'staff-002',
        username: 'staff2',
        role: 'staff' as const,
        email: 'staff2@example.com',
        realName: '李艺术',
        isActive: true,
        orderCount: 0
      }

      vi.mocked(staffApi.addStaff).mockResolvedValue(newStaff)

      const result = await store.addStaff({
        username: 'staff2',
        realName: '李艺术',
        email: 'staff2@example.com'
      })

      // 验证返回的新负责人
      expect(result).toEqual(newStaff)
      
      // 验证新负责人被添加到列表
      expect(store.staffList).toHaveLength(2)
      expect(store.staffList[1]).toEqual(newStaff)
      
      // 验证 API 被调用
      expect(staffApi.addStaff).toHaveBeenCalledTimes(1)
    })

    it('应该在添加失败时抛出错误', async () => {
      const store = useStaffStore()
      
      const errorMessage = '用户名已存在'
      vi.mocked(staffApi.addStaff).mockRejectedValue(new Error(errorMessage))

      await expect(
        store.addStaff({
          username: 'existing',
          realName: '测试'
        })
      ).rejects.toThrow(errorMessage)

      // 验证列表没有被修改
      expect(store.staffList).toEqual([])
    })

    it('应该正确处理没有初始数据的添加', async () => {
      const store = useStaffStore()
      
      const newStaff: User = {
        id: 'staff-001',
        username: 'staff1',
        role: 'staff' as const,
        realName: '张设计'
      }

      vi.mocked(staffApi.addStaff).mockResolvedValue(newStaff)

      await store.addStaff({
        username: 'staff1',
        realName: '张设计'
      })

      expect(store.staffList).toHaveLength(1)
      expect(store.staffList[0]).toEqual(newStaff)
    })
  })

  describe('数据结构验证', () => {
    it('staffList 应该始终是数组类型', async () => {
      const store = useStaffStore()
      
      // 初始状态应该是空数组
      expect(Array.isArray(store.staffList)).toBe(true)
      expect(store.staffList).toEqual([])

      // 获取数据后也应该是数组
      const mockApiResponse = {
        data: [
          {
            id: 'staff-001',
            username: 'staff1',
            role: 'staff' as const,
            realName: '张设计'
          }
        ],
        total: 1
      }

      vi.mocked(staffApi.getStaff).mockResolvedValue(mockApiResponse)
      await store.fetchStaff()

      expect(Array.isArray(store.staffList)).toBe(true)
      expect(store.staffList).toHaveLength(1)
    })

    it('不应该将整个 API 响应对象赋值给 staffList', async () => {
      const store = useStaffStore()
      
      const mockApiResponse = {
        data: [
          {
            id: 'staff-001',
            username: 'staff1',
            role: 'staff' as const,
            realName: '张设计'
          }
        ],
        total: 1
      }

      vi.mocked(staffApi.getStaff).mockResolvedValue(mockApiResponse)
      await store.fetchStaff()

      // 验证 staffList 不是整个响应对象
      expect(store.staffList).not.toHaveProperty('total')
      expect(store.staffList).not.toHaveProperty('data')
      
      // 验证 staffList 是数组
      expect(Array.isArray(store.staffList)).toBe(true)
      
      // 验证第一个元素是正确的 User 对象
      expect(store.staffList[0]).toHaveProperty('id')
      expect(store.staffList[0]).toHaveProperty('username')
      expect(store.staffList[0]).toHaveProperty('role')
    })
  })
})

