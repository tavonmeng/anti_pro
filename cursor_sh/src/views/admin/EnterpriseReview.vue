<template>
  <div class="enterprise-review-page">
    <div class="page-header">
      <h1 class="page-title">企业认证审核</h1>
      <p class="page-subtitle">审核用户提交的企业认证申请</p>
    </div>

    <el-tabs v-model="activeTab" class="review-tabs">
      <el-tab-pane label="待审核" name="pending">
        <el-table :data="pendingList" v-loading="loading" empty-text="暂无待审核申请" stripe>
          <el-table-column label="用户名" prop="username" width="120" />
          <el-table-column label="手机号" prop="phone" width="140" />
          <el-table-column label="企业名称" prop="enterprise_name" min-width="180" />
          <el-table-column label="提交时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.submitted_at) }}
            </template>
          </el-table-column>
          <el-table-column label="营业执照" width="100">
            <template #default="{ row }">
              <el-button type="primary" link @click="previewLicense(row.business_license_url)">查看</el-button>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
              <el-button type="danger" size="small" @click="handleReject(row)">拒绝</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="已处理" name="processed">
        <el-table :data="processedList" v-loading="loading" empty-text="暂无已处理记录" stripe>
          <el-table-column label="用户名" prop="username" width="120" />
          <el-table-column label="手机号" prop="phone" width="140" />
          <el-table-column label="企业名称" prop="enterprise_name" min-width="180" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.enterprise_status === 'approved' ? 'success' : 'danger'" size="small">
                {{ row.enterprise_status === 'approved' ? '已通过' : '已拒绝' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="营业执照" width="100">
            <template #default="{ row }">
              <el-button v-if="row.business_license_url" type="primary" link @click="previewLicense(row.business_license_url)">查看</el-button>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="拒绝原因" min-width="200">
            <template #default="{ row }">
              {{ row.enterprise_reject_reason || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="审核时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.reviewed_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 营业执照预览弹窗 -->
    <el-dialog v-model="showLicensePreview" title="营业执照预览" width="600px" align-center>
      <div class="license-preview-wrap">
        <el-image :src="licensePreviewUrl" fit="contain" style="width: 100%; max-height: 500px;" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { enterpriseApi } from '@/utils/api'

const loading = ref(false)
const activeTab = ref('pending')
const allItems = ref<any[]>([])

const showLicensePreview = ref(false)
const licensePreviewUrl = ref('')

const pendingList = computed(() => allItems.value.filter(i => i.enterprise_status === 'pending'))
const processedList = computed(() => allItems.value.filter(i => i.enterprise_status !== 'pending'))

onMounted(async () => {
  await fetchList()
})

const fetchList = async () => {
  loading.value = true
  try {
    const res = await enterpriseApi.getPending()
    allItems.value = Array.isArray(res) ? res : (res as any).data || []
  } catch (error: any) {
    ElMessage.error(error.message || '获取列表失败')
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const previewLicense = (url: string) => {
  if (!url) {
    ElMessage.warning('暂无营业执照图片')
    return
  }
  licensePreviewUrl.value = url
  showLicensePreview.value = true
}

const handleApprove = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确认通过「${row.enterprise_name}」的企业认证？通过后用户名将更新为企业名称。`,
      '确认通过',
      { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'success' }
    )
    
    await enterpriseApi.review(row.user_id, 'approve')
    ElMessage.success('已通过企业认证')
    await fetchList()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '操作失败')
    }
  }
}

const handleReject = async (row: any) => {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请填写拒绝原因，用户将看到此原因并可据此修正后重新提交。',
      '拒绝认证',
      {
        confirmButtonText: '确认拒绝',
        cancelButtonText: '取消',
        inputPlaceholder: '例如：营业执照照片不清晰，请重新上传',
        inputValidator: (val: string) => {
          if (!val || !val.trim()) return '请填写拒绝原因'
          return true
        },
        type: 'warning'
      }
    )
    
    await enterpriseApi.review(row.user_id, 'reject', reason)
    ElMessage.success('已拒绝企业认证')
    await fetchList()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '操作失败')
    }
  }
}
</script>

<style lang="scss" scoped>
.enterprise-review-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #86868B;
  margin: 0;
}

.review-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }
}

.license-preview-wrap {
  display: flex;
  justify-content: center;
  padding: 16px;
}
</style>
