<template>
  <div class="staff-management">
    <div class="page-header">
      <h1>负责人管理</h1>
      <el-button type="primary" @click="handleAddStaff">
        <el-icon><Plus /></el-icon>
        添加负责人
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #E3F2FD;">
            <el-icon color="#1976D2" :size="24"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总负责人数</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #E8F5E9;">
            <el-icon color="#388E3C" :size="24"><SuccessFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.active }}</div>
            <div class="stat-label">活跃负责人</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #FFF3E0;">
            <el-icon color="#F57C00" :size="24"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalOrders }}</div>
            <div class="stat-label">负责订单总数</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #FCE4EC;">
            <el-icon color="#C2185B" :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.avgOrdersPerStaff }}</div>
            <div class="stat-label">人均订单数</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="搜索">
          <el-input 
            v-model="filterForm.keyword" 
            placeholder="搜索用户名/姓名/邮箱"
            clearable
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="角色">
          <el-select v-model="filterForm.role" placeholder="全部" clearable>
            <el-option label="全部" value="" />
            <el-option label="管理员" value="admin" />
            <el-option label="负责人" value="staff" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="filterForm.isActive" placeholder="全部" clearable>
            <el-option label="全部" value="" />
            <el-option label="活跃" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 负责人列表 -->
    <el-card class="table-card">
      <el-table 
        v-loading="loading"
        :data="staffList" 
        stripe
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" width="150" />
        
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            {{ row.realName || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="邮箱" min-width="200">
          <template #default="{ row }">
            {{ row.email || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'admin'" type="danger">管理员</el-tag>
            <el-tag v-else-if="row.role === 'staff'" type="primary">负责人</el-tag>
            <el-tag v-else type="info">用户</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.isActive" type="success">活跃</el-tag>
            <el-tag v-else type="info">禁用</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="负责订单数" width="120" align="center">
          <template #default="{ row }">
            <span class="order-count">{{ row.orderCount || 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              link 
              type="primary" 
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button 
              link 
              :type="row.isActive ? 'warning' : 'success'"
              size="small"
              @click="handleToggleStatus(row)"
            >
              {{ row.isActive ? '禁用' : '启用' }}
            </el-button>
            <el-button 
              link 
              type="danger" 
              size="small"
              @click="handleDelete(row)"
              :disabled="row.orderCount > 0"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <StaffDialog
      v-model="dialogVisible"
      :staff="currentStaff"
      :is-edit="isEdit"
      @success="handleDialogSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, 
  User, 
  SuccessFilled, 
  Document, 
  TrendCharts,
  Search
} from '@element-plus/icons-vue'
import StaffDialog from '@/components/StaffDialog.vue'
import { staffApi } from '@/utils/api'
import type { User as StaffUser } from '@/types'

// 数据
const loading = ref(false)
const staffList = ref<StaffUser[]>([])
const dialogVisible = ref(false)
const currentStaff = ref<StaffUser | null>(null)
const isEdit = ref(false)

// 筛选表单
const filterForm = ref({
  keyword: '',
  role: '',
  isActive: '' as boolean | ''
})

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 统计数据
const stats = computed(() => {
  const total = staffList.value.length
  const active = staffList.value.filter(s => s.isActive).length
  const totalOrders = staffList.value.reduce((sum, s) => sum + (s.orderCount || 0), 0)
  const avgOrdersPerStaff = total > 0 ? Math.round(totalOrders / total) : 0

  return {
    total,
    active,
    totalOrders,
    avgOrdersPerStaff
  }
})

// 方法
async function fetchStaffList() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      keyword: filterForm.value.keyword || undefined,
      role: filterForm.value.role || undefined,
      isActive: filterForm.value.isActive !== '' ? filterForm.value.isActive : undefined
    }
    
    const response = await staffApi.getStaff(params)
    staffList.value = response.data || []
    pagination.value.total = response.total || staffList.value.length
  } catch (error) {
    console.error('获取负责人列表失败:', error)
    ElMessage.error('获取负责人列表失败')
  } finally {
    loading.value = false
  }
}

function handleAddStaff() {
  currentStaff.value = null
  isEdit.value = false
  dialogVisible.value = true
}

function handleEdit(staff: StaffUser) {
  currentStaff.value = { ...staff }
  isEdit.value = true
  dialogVisible.value = true
}

async function handleToggleStatus(staff: StaffUser) {
  const action = staff.isActive ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}负责人 ${staff.realName || staff.username} 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await staffApi.updateStaff(staff.id, {
      isActive: !staff.isActive
    })

    ElMessage.success(`${action}成功`)
    fetchStaffList()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`${action}失败`)
    }
  }
}

async function handleDelete(staff: StaffUser) {
  if (staff.orderCount && staff.orderCount > 0) {
    ElMessage.warning('该负责人还有进行中的订单，无法删除')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除负责人 ${staff.realName || staff.username} 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'error'
      }
    )

    await staffApi.deleteStaff(staff.id)
    ElMessage.success('删除成功')
    fetchStaffList()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function handleSearch() {
  pagination.value.page = 1
  fetchStaffList()
}

function handleReset() {
  filterForm.value = {
    keyword: '',
    role: '',
    isActive: ''
  }
  pagination.value.page = 1
  fetchStaffList()
}

function handlePageChange(page: number) {
  pagination.value.page = page
  fetchStaffList()
}

function handleSizeChange(size: number) {
  pagination.value.pageSize = size
  pagination.value.page = 1
  fetchStaffList()
}

function handleDialogSuccess() {
  dialogVisible.value = false
  fetchStaffList()
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchStaffList()
})
</script>

<style lang="scss" scoped>
.staff-management {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  h1 {
    font-size: 28px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 0;
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  :deep(.el-card__body) {
    padding: 20px;
  }
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1D1D1F;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #86868B;
  margin-top: 4px;
}

.filter-card {
  margin-bottom: 16px;

  :deep(.el-card__body) {
    padding: 16px 20px;
  }

  :deep(.el-form) {
    margin: 0;
  }

  :deep(.el-form-item) {
    margin-bottom: 0;
  }
}

.table-card {
  :deep(.el-card__body) {
    padding: 0;
  }

  :deep(.el-table) {
    th {
      background-color: #F5F5F7;
      color: #1D1D1F;
      font-weight: 600;
    }
  }
}

.order-count {
  display: inline-block;
  padding: 4px 12px;
  background: #F5F5F7;
  border-radius: 12px;
  font-weight: 600;
  color: #1D1D1F;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  padding: 20px;
  border-top: 1px solid #E5E5E7;
}
</style>

