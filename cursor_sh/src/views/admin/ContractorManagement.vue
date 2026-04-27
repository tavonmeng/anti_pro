<template>
  <div class="contractor-mgmt">
    <div class="page-header">
      <h1 class="page-title">承包商管理</h1>
      <p class="page-desc">管理邀请链接和承包商列表</p>
    </div>

    <!-- 邀请链接区 -->
    <div class="section-card">
      <div class="section-header">
        <h2 class="section-title">邀请链接</h2>
        <el-button type="primary" size="small" @click="generateInvite">生成邀请链接</el-button>
      </div>

      <el-table :data="invitations" border size="small" class="invite-table">
        <el-table-column label="邀请链接" min-width="280">
          <template #default="{ row }">
            <div class="invite-url" v-if="!row.isUsed && !row.isExpired">
              <code>{{ getInviteUrl(row.token) }}</code>
              <el-button link size="small" @click="copyLink(row.token)">复制</el-button>
            </div>
            <span v-else class="token-masked">{{ row.token.substring(0, 8) }}...</span>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="note" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.isUsed" type="success" size="small">已使用</el-tag>
            <el-tag v-else-if="row.isExpired" type="info" size="small">已过期</el-tag>
            <el-tag v-else type="warning" size="small">待使用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="使用者" prop="usedByName" width="100" />
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button
              v-if="!row.isUsed"
              type="danger"
              link
              size="small"
              @click="revokeInvite(row.id)"
            >撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 承包商列表 -->
    <div class="section-card">
      <div class="section-header">
        <h2 class="section-title">承包商列表</h2>
        <el-input v-model="keyword" placeholder="搜索用户名/公司" size="small" style="width:200px" clearable @change="fetchContractors" />
      </div>

      <el-table :data="contractors" border size="small">
        <el-table-column label="用户名" prop="username" width="120" />
        <el-table-column label="公司" prop="company" width="140" />
        <el-table-column label="手机" prop="phone" width="130" />
        <el-table-column label="专业方向" prop="specialty" width="140" />
        <el-table-column label="在手订单" prop="activeOrders" width="90" align="center" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.isActive ? 'success' : 'danger'" size="small">
              {{ row.isActive ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="150">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              :type="row.isActive ? 'danger' : 'success'"
              link
              size="small"
              @click="toggleActive(row)"
            >{{ row.isActive ? '禁用' : '启用' }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        layout="prev, pager, next"
        class="pagination"
        @current-change="(p: number) => { currentPage = p; fetchContractors() }"
      />
    </div>

    <!-- 生成邀请对话框 -->
    <el-dialog v-model="inviteDialogVisible" title="生成邀请链接" width="420px">
      <el-form label-position="top">
        <el-form-item label="备注（选填）">
          <el-input v-model="inviteNote" placeholder="如：给XX公司的邀请" />
        </el-form-item>
        <el-form-item label="有效天数">
          <el-input-number v-model="inviteDays" :min="1" :max="30" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inviteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="confirmGenerate">确认生成</el-button>
      </template>
    </el-dialog>

    <!-- 生成结果对话框 -->
    <el-dialog v-model="resultDialogVisible" title="邀请链接已生成" width="500px">
      <div class="result-content">
        <p>请将以下链接发送给承包商：</p>
        <el-input :model-value="generatedUrl" readonly>
          <template #append>
            <el-button @click="copyGeneratedLink">复制</el-button>
          </template>
        </el-input>
        <p class="result-tip">该链接仅可使用一次，{{ inviteDays }} 天后过期</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const invitations = ref<any[]>([])
const contractors = ref<any[]>([])
const keyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

const inviteDialogVisible = ref(false)
const resultDialogVisible = ref(false)
const inviteNote = ref('')
const inviteDays = ref(7)
const generating = ref(false)
const generatedUrl = ref('')

const formatTime = (iso: string) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const getInviteUrl = (token: string) => {
  const base = window.location.origin
  return `${base}/contractor/register?invite=${token}`
}

const copyLink = async (token: string) => {
  const url = getInviteUrl(token)
  await navigator.clipboard.writeText(url)
  ElMessage.success('链接已复制')
}

const copyGeneratedLink = async () => {
  await navigator.clipboard.writeText(generatedUrl.value)
  ElMessage.success('链接已复制')
}

const fetchInvitations = async () => {
  try {
    const res = await request.get('/api/contractor-admin/invitations')
    invitations.value = res.data || []
  } catch { /* ignore */ }
}

const fetchContractors = async () => {
  try {
    const res = await request.get('/api/contractor-admin/list', {
      params: { page: currentPage.value, pageSize, keyword: keyword.value || undefined },
    })
    contractors.value = res.data?.data || []
    total.value = res.data?.total || 0
  } catch { /* ignore */ }
}

const generateInvite = () => {
  inviteNote.value = ''
  inviteDays.value = 7
  inviteDialogVisible.value = true
}

const confirmGenerate = async () => {
  generating.value = true
  try {
    const res = await request.post('/api/contractor-admin/invitations', {
      note: inviteNote.value,
      expires_days: inviteDays.value,
    })
    inviteDialogVisible.value = false
    generatedUrl.value = res.data?.inviteUrl || ''
    resultDialogVisible.value = true
    fetchInvitations()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

const revokeInvite = async (id: string) => {
  try {
    await ElMessageBox.confirm('撤销后该邀请链接将无法使用', '确认撤销')
    await request.delete(`/api/contractor-admin/invitations/${id}`)
    ElMessage.success('已撤销')
    fetchInvitations()
  } catch { /* cancelled */ }
}

const toggleActive = async (row: any) => {
  try {
    const action = row.isActive ? '禁用' : '启用'
    await ElMessageBox.confirm(`确认${action}该承包商？`, '确认操作')
    await request.put(`/api/contractor-admin/${row.id}`, { isActive: !row.isActive })
    ElMessage.success(`已${action}`)
    fetchContractors()
  } catch { /* cancelled */ }
}

onMounted(() => {
  fetchInvitations()
  fetchContractors()
})
</script>

<style lang="scss" scoped>
.contractor-mgmt { max-width: 1100px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #1D1D1F; margin: 0 0 4px; }
.page-desc { font-size: 14px; color: #86868B; margin: 0; }
.section-card {
  background: #fff; border-radius: 12px; padding: 24px;
  border: 1px solid #E5E7EB; margin-bottom: 24px;
}
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.section-title { font-size: 16px; font-weight: 600; color: #1D1D1F; margin: 0; }
.invite-url { display: flex; align-items: center; gap: 8px;
  code { font-size: 12px; color: #409eff; word-break: break-all; }
}
.token-masked { font-size: 12px; color: #86868B; font-family: monospace; }
.pagination { margin-top: 16px; display: flex; justify-content: center; }
.result-content { text-align: center; }
.result-tip { font-size: 12px; color: #86868B; margin-top: 12px; }
</style>
