<template>
  <div class="contractor-mgmt">
    <div class="page-header">
      <h1 class="page-title">承包商和用户邀请管理</h1>
      <p class="page-desc">管理用户邀请、承包商邀请和承包商列表</p>
    </div>

    <!-- 邀请链接区 -->
    <div class="section-card">
      <div class="section-header">
        <h2 class="section-title">用户和承包商邀请链接</h2>
        <el-button type="primary" size="small" @click="generateInvite(invitationTab)">生成邀请链接</el-button>
      </div>

      <el-tabs v-model="invitationTab" class="invite-tabs">
        <el-tab-pane label="用户邀请" name="user">
          <el-table :data="userInvitations" border size="small" class="invite-table">
            <el-table-column label="邀请链接" min-width="280">
              <template #default="{ row }">
                <div class="invite-url" v-if="!row.isUsed && !row.isExpired">
                  <code>{{ row.inviteUrl }}</code>
                  <el-button link size="small" @click="copyLink(row)">复制</el-button>
                </div>
                <span v-else class="token-masked">{{ row.token?.substring(0, 8) }}...</span>
              </template>
            </el-table-column>
            <el-table-column label="公司" prop="companyName" width="140" />
            <el-table-column label="绑定 Memory" width="150">
              <template #default="{ row }">{{ row.memoryLabel || row.memoryUserId || '-' }}</template>
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
                  @click="revokeInvite(row.id, 'user')"
                >撤销</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="承包商邀请" name="contractor">
          <el-table :data="invitations" border size="small" class="invite-table">
            <el-table-column label="邀请链接" min-width="280">
              <template #default="{ row }">
                <div class="invite-url" v-if="!row.isUsed && !row.isExpired">
                  <code>{{ row.token ? getInviteUrl(row.token) : row.inviteUrl }}</code>
                  <el-button link size="small" @click="copyLink(row)">复制</el-button>
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
                  @click="revokeInvite(row.id, 'contractor')"
                >撤销</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
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
    <el-dialog v-model="inviteDialogVisible" :title="inviteType === 'user' ? '生成用户邀请链接' : '生成承包商邀请链接'" width="520px">
      <el-form label-position="top">
        <template v-if="inviteType === 'user'">
          <el-form-item label="公司名称">
            <el-input v-model="inviteCompanyName" placeholder="注册后写入用户公司名称，可后续修改" />
          </el-form-item>
          <el-form-item label="绑定用户 Memory（选填）">
            <el-select
              v-model="inviteMemoryUserId"
              placeholder="选择已 ingest 的客户 Memory"
              clearable
              filterable
              style="width: 100%"
              @visible-change="(open: boolean) => open && fetchMemoryOptions()"
            >
              <el-option
                v-for="item in memoryOptions"
                :key="item.userId"
                :label="memoryOptionLabel(item)"
                :value="item.userId"
              />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="备注（选填）">
          <el-input v-model="inviteNote" placeholder="如：给XX公司的邀请" />
        </el-form-item>
        <el-form-item label="有效天数">
          <el-input-number v-model="inviteDays" :min="1" :max="inviteType === 'user' ? 7 : 30" :disabled="inviteType === 'user'" />
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
        <p>请将以下链接发送给{{ inviteType === 'user' ? '受邀用户' : '承包商' }}：</p>
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
import { formatServerTime } from '@/utils/time'

type InvitationTab = 'user' | 'contractor'

const invitationTab = ref<InvitationTab>('user')
const userInvitations = ref<any[]>([])
const invitations = ref<any[]>([])
const contractors = ref<any[]>([])
const keyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

const inviteDialogVisible = ref(false)
const resultDialogVisible = ref(false)
const inviteType = ref<InvitationTab>('user')
const inviteNote = ref('')
const inviteDays = ref(7)
const inviteCompanyName = ref('')
const inviteMemoryUserId = ref('')
const generating = ref(false)
const generatedUrl = ref('')
const memoryOptions = ref<any[]>([])
const memoryOptionsLoading = ref(false)
const contractorBaseUrl = (import.meta.env.VITE_CONTRACTOR_BASE_URL || 'https://contractor.uniquevisionx.com').replace(/\/$/, '')

const formatTime = (iso: string) => {
  return formatServerTime(iso, '—')
}

const getInviteUrl = (token: string) => {
  return `${contractorBaseUrl}/contractor/register?invite=${token}`
}

const copyLink = async (row: any) => {
  const url = row?.inviteUrl || (row?.token ? getInviteUrl(row.token) : '')
  await navigator.clipboard.writeText(url)
  ElMessage.success('链接已复制')
}

const copyGeneratedLink = async () => {
  await navigator.clipboard.writeText(generatedUrl.value)
  ElMessage.success('链接已复制')
}

const fetchInvitations = async () => {
  try {
    const res: any = await request.get('/contractor-admin/invitations')
    invitations.value = Array.isArray(res) ? res : (res?.data || [])
  } catch { /* ignore */ }
}

const fetchUserInvitations = async () => {
  try {
    const res: any = await request.get('/user-admin/invitations')
    userInvitations.value = Array.isArray(res) ? res : (res?.data || [])
  } catch { /* ignore */ }
}

const fetchMemoryOptions = async () => {
  if (memoryOptionsLoading.value) return
  memoryOptionsLoading.value = true
  try {
    const res: any = await request.get('/admin/memory/customers', {
      params: { page: 1, pageSize: 100 },
    })
    memoryOptions.value = res?.data || []
  } catch { /* ignore */ }
  finally { memoryOptionsLoading.value = false }
}

const memoryOptionLabel = (item: any) => {
  const parts = [
    item.company || '',
    item.username || '',
    item.phone || '',
    item.isProspect ? '未注册' : '已注册',
  ].filter(Boolean)
  return parts.join(' / ')
}

const fetchContractors = async () => {
  try {
    const res: any = await request.get('/contractor-admin/list', {
      params: { page: currentPage.value, pageSize, keyword: keyword.value || undefined },
    })
    // res is already the inner data object from ApiResponse
    if (Array.isArray(res)) {
      contractors.value = res
      total.value = res.length
    } else {
      contractors.value = res?.data || res?.items || []
      total.value = res?.total || contractors.value.length
    }
  } catch { /* ignore */ }
}

const generateInvite = (type: InvitationTab) => {
  inviteType.value = type
  inviteNote.value = ''
  inviteDays.value = 7
  inviteCompanyName.value = ''
  inviteMemoryUserId.value = ''
  if (type === 'user') fetchMemoryOptions()
  inviteDialogVisible.value = true
}

const confirmGenerate = async () => {
  generating.value = true
  try {
    const payload: any = {
      note: inviteNote.value,
      expires_days: inviteDays.value,
    }
    let res: any
    if (inviteType.value === 'user') {
      payload.company_name = inviteCompanyName.value
      payload.memory_user_id = inviteMemoryUserId.value || undefined
      res = await request.post('/user-admin/invitations', payload)
    } else {
      res = await request.post('/contractor-admin/invitations', payload)
    }
    inviteDialogVisible.value = false
    // res is already the inner data from ApiResponse
    const token = res?.token || ''
    generatedUrl.value = res?.inviteUrl || (token ? getInviteUrl(token) : '')
    resultDialogVisible.value = true
    if (inviteType.value === 'user') fetchUserInvitations()
    else fetchInvitations()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

const revokeInvite = async (id: string, type: InvitationTab) => {
  try {
    await ElMessageBox.confirm('撤销后该邀请链接将无法使用', '确认撤销')
    if (type === 'user') await request.delete(`/user-admin/invitations/${id}`)
    else await request.delete(`/contractor-admin/invitations/${id}`)
    ElMessage.success('已撤销')
    if (type === 'user') fetchUserInvitations()
    else fetchInvitations()
  } catch { /* cancelled */ }
}

const toggleActive = async (row: any) => {
  try {
    const action = row.isActive ? '禁用' : '启用'
    await ElMessageBox.confirm(`确认${action}该承包商？`, '确认操作')
    await request.put(`/contractor-admin/${row.id}`, { isActive: !row.isActive })
    ElMessage.success(`已${action}`)
    fetchContractors()
  } catch { /* cancelled */ }
}

onMounted(() => {
  fetchUserInvitations()
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
