<template>
  <div class="assignment-list">
    <div class="page-header">
      <h1 class="page-title">我的派单</h1>
      <p class="page-desc">查看和管理您收到的项目派单</p>
    </div>

    <!-- 资料未完善提示 -->
    <div v-if="profileIncomplete" class="profile-alert" @click="router.push('/contractor/profile')">
      <span class="alert-icon">⚠️</span>
      <span class="alert-text">您的资料尚未完善，请前往<strong>个人设置</strong>补充公司信息和专业方向，以便接收派单</span>
      <span class="alert-arrow">→</span>
    </div>

    <!-- 状态筛选 Tabs -->
    <el-tabs v-model="activeTab" class="status-tabs" @tab-change="fetchAssignments">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="待处理" name="pending" />
      <el-tab-pane label="进行中" name="in_progress" />
      <el-tab-pane label="已完成" name="completed" />
      <el-tab-pane label="已拒绝" name="rejected" />
    </el-tabs>

    <!-- 列表 -->
    <div v-if="loading" class="loading-state">
      <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <div v-else-if="assignments.length === 0" class="empty-state">
      <el-empty description="暂无派单记录" />
    </div>

    <div v-else class="assignment-cards">
      <div
        v-for="item in assignments"
        :key="item.id"
        class="assignment-card"
        @click="goToDetail(item.id)"
      >
        <div class="card-header">
          <div class="order-number">{{ item.order?.orderNumber || '—' }}</div>
          <el-tag :type="statusTagType(item.status)" size="small" effect="dark">
            {{ statusLabel(item.status) }}
          </el-tag>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="label">品牌</span>
            <span class="value">{{ item.order?.brand || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="label">城市</span>
            <span class="value">{{ item.order?.city || '—' }}</span>
          </div>
          <div class="info-row" v-if="item.order?.orderType">
            <span class="label">类型</span>
            <span class="value">{{ item.order?.orderType || '—' }}</span>
          </div>
          <div class="info-row" v-if="item.schedule">
            <span class="label">总排期</span>
            <span class="value">{{ totalDays(item.schedule) }} 天</span>
          </div>
        </div>

        <div class="card-footer">
          <span class="time">派单时间：{{ formatTime(item.assignedAt) }}</span>
          <div class="actions" v-if="item.status === 'pending'" @click.stop>
            <el-button size="small" type="primary" @click="handleAccept(item.id)">接单</el-button>
            <el-button size="small" @click="showRejectDialog(item.id)">拒绝</el-button>
          </div>
          <div class="actions" v-else>
            <el-button size="small" type="primary" plain>查看详情</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 拒绝对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="拒绝派单" width="400px" :append-to-body="true">
      <el-form>
        <el-form-item label="拒绝理由">
          <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写拒绝理由（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejecting" @click="handleReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()
const activeTab = ref('all')
const loading = ref(false)
const assignments = ref<any[]>([])
const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const rejectingId = ref('')
const rejecting = ref(false)
const profileIncomplete = ref(false)

const checkProfile = async () => {
  try {
    const d: any = await request.get('/contractor/profile')
    const missing = !d?.realName && !d?.real_name || !d?.company || !d?.specialty || !d?.expertise
    profileIncomplete.value = !!missing
  } catch { /* ignore */ }
}

const statusLabel = (s: string) => ({
  pending: '待处理', accepted: '已接单', in_progress: '进行中',
  completed: '已完成', rejected: '已拒绝', cancelled: '已取消',
}[s] || s)

const statusTagType = (s: string) => ({
  pending: 'warning', in_progress: '', accepted: 'success',
  completed: 'success', rejected: 'danger', cancelled: 'info',
}[s] || 'info')

const totalDays = (schedule: any[]) => schedule?.reduce((sum: number, s: any) => sum + (s.days || 0), 0) || 0

const formatTime = (iso: string) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const fetchAssignments = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (activeTab.value !== 'all') params.status = activeTab.value
    const res: any = await request.get('/contractor/assignments', { params })
    assignments.value = Array.isArray(res) ? res : (res?.data || res?.items || [])
  } catch (e: any) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const goToDetail = (id: string) => {
  router.push(`/contractor/assignments/${id}`)
}

const handleAccept = async (id: string) => {
  try {
    await request.put(`/contractor/assignments/${id}/accept`)
    ElMessage.success('接单成功')
    fetchAssignments()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const showRejectDialog = (id: string) => {
  rejectingId.value = id
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

const handleReject = async () => {
  rejecting.value = true
  try {
    await request.put(`/contractor/assignments/${rejectingId.value}/reject`, {
      reject_reason: rejectReason.value,
    })
    ElMessage.success('已拒绝')
    rejectDialogVisible.value = false
    fetchAssignments()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    rejecting.value = false
  }
}

onMounted(() => {
  fetchAssignments()
  checkProfile()
})
</script>

<style lang="scss" scoped>
.assignment-list { max-width: 960px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #1D1D1F; margin: 0 0 4px; }
.page-desc { font-size: 14px; color: #86868B; margin: 0; }
.status-tabs { margin-bottom: 20px; }
.loading-state {
  text-align: center; padding: 60px 0; color: #86868B;
  .loading-icon { animation: spin 1s linear infinite; }
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { padding: 60px 0; }
.assignment-cards { display: flex; flex-direction: column; gap: 16px; }
.profile-alert {
  display: flex; align-items: center; gap: 10px;
  background: #FFF8E6; border: 1px solid #FFD666;
  border-radius: 10px; padding: 12px 16px; margin-bottom: 16px;
  cursor: pointer; transition: all 0.2s;
  &:hover { background: #FFF3CC; transform: translateY(-1px); }
}
.alert-icon { font-size: 18px; flex-shrink: 0; }
.alert-text { flex: 1; font-size: 13px; color: #1D1D1F; line-height: 1.5;
  strong { color: #E6770F; }
}
.alert-arrow { font-size: 16px; color: #E6770F; font-weight: 600; }
.assignment-card {
  background: #fff; border-radius: 12px; padding: 20px;
  border: 1px solid #E5E7EB; cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #409eff; box-shadow: 0 4px 12px rgba(0,0,0,0.08); transform: translateY(-1px); }
}
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.order-number { font-size: 16px; font-weight: 600; color: #1D1D1F; }
.card-body { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; margin-bottom: 16px; }
.info-row { display: flex; gap: 8px; }
.info-row .label { color: #86868B; font-size: 13px; min-width: 40px; }
.info-row .value { color: #1D1D1F; font-size: 13px; }
.card-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 12px; border-top: 1px solid #F0F0F0;
}
.card-footer .time { font-size: 12px; color: #86868B; }
.actions { display: flex; gap: 8px; }
</style>
