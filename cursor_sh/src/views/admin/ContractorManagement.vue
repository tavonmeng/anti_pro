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
    <el-dialog v-model="inviteDialogVisible" :title="inviteType === 'user' ? '生成用户邀请链接' : '生成承包商邀请链接'" width="520px" class="admin-form-dialog">
      <el-form label-position="top">
        <template v-if="inviteType === 'user'">
          <el-form-item label="公司名称">
            <el-input v-model="inviteCompanyName" placeholder="注册后写入用户公司名称，可后续修改" />
          </el-form-item>
          <el-form-item label="绑定用户 Memory（选填）">
            <template v-if="isMobile">
              <button
                type="button"
                class="mobile-memory-trigger"
                @click="openMemoryPicker"
              >
                <span :class="{ placeholder: !selectedMemoryLabel }">
                  {{ selectedMemoryLabel || '选择已 ingest 的客户 Memory' }}
                </span>
                <el-icon><ArrowRight /></el-icon>
              </button>
              <div v-if="inviteMemoryUserId" class="mobile-memory-clear">
                <el-button link type="primary" size="small" @click="clearMemorySelection">清除绑定</el-button>
              </div>
            </template>
            <el-select
              v-else
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
    <el-dialog
      v-model="resultDialogVisible"
      title="邀请链接已生成"
      width="500px"
      class="admin-form-dialog invite-result-dialog"
      :show-close="true"
    >
      <div class="result-content">
        <p class="result-lead">请将以下链接发送给{{ inviteType === 'user' ? '受邀用户' : '承包商' }}：</p>
        <button type="button" class="generated-link-card" @click="copyGeneratedLink">
          <code>{{ generatedUrl }}</code>
        </button>
        <p class="result-tip">该链接仅可使用一次，{{ inviteDays }} 天后过期</p>
      </div>
      <template #footer>
        <el-button class="result-action" @click="resultDialogVisible = false">关闭</el-button>
        <el-button class="result-action" type="primary" @click="copyGeneratedLink">复制链接</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="memoryPickerVisible"
      direction="btt"
      size="82%"
      :with-header="false"
      append-to-body
      class="memory-picker-drawer"
    >
      <div class="memory-picker">
        <div class="memory-picker-header">
          <div>
            <h3>选择用户 Memory</h3>
            <p>用于生成邀请后绑定客户资料</p>
          </div>
          <el-button :icon="Close" circle plain aria-label="关闭" @click="memoryPickerVisible = false" />
        </div>

        <el-input
          v-model="memorySearch"
          class="memory-picker-search"
          placeholder="搜索公司、联系人或手机号"
          clearable
          :prefix-icon="Search"
        />

        <div class="memory-picker-list" v-loading="memoryOptionsLoading">
          <button
            type="button"
            class="memory-picker-option no-memory"
            :class="{ selected: !inviteMemoryUserId }"
            @click="clearMemorySelection"
          >
            <span class="memory-company">不绑定 Memory</span>
            <span class="memory-meta">生成普通邀请链接</span>
          </button>

          <button
            v-for="item in filteredMemoryOptions"
            :key="item.userId"
            type="button"
            class="memory-picker-option"
            :class="{ selected: inviteMemoryUserId === item.userId }"
            @click="selectMemoryOption(item)"
          >
            <span class="memory-option-main">
              <span class="memory-company">{{ item.company || '未命名客户' }}</span>
              <el-tag size="small" :type="item.isProspect ? 'warning' : 'success'">
                {{ item.isProspect ? '未注册' : '已注册' }}
              </el-tag>
            </span>
            <span class="memory-meta">{{ [item.username, item.phone].filter(Boolean).join(' / ') || item.userId }}</span>
          </button>

          <div v-if="!memoryOptionsLoading && filteredMemoryOptions.length === 0" class="memory-empty">
            没有匹配的 Memory
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onBeforeUnmount, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, Close, Search } from '@element-plus/icons-vue'
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
const memoryPickerVisible = ref(false)
const memorySearch = ref('')
const isMobile = ref(false)
const contractorBaseUrl = (import.meta.env.VITE_CONTRACTOR_BASE_URL || 'https://contractor.uniquevisionx.com').replace(/\/$/, '')
let mobileQuery: MediaQueryList | undefined

const formatTime = (iso: string) => {
  return formatServerTime(iso, '—')
}

const getInviteUrl = (token: string) => {
  return `${contractorBaseUrl}/contractor/register?invite=${token}`
}

const copyText = async (text: string) => {
  if (!text) return false

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    // Fall through to the textarea fallback for mobile HTTP/LAN previews.
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.top = '0'
  textarea.style.left = '-9999px'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)

  const selection = document.getSelection()
  const previousRange = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null

  textarea.focus()
  textarea.select()
  textarea.setSelectionRange(0, textarea.value.length)

  let copied = false
  try {
    copied = document.execCommand('copy')
  } catch {
    copied = false
  }

  document.body.removeChild(textarea)
  if (selection) {
    selection.removeAllRanges()
    if (previousRange) selection.addRange(previousRange)
  }
  return copied
}

const copyLink = async (row: any) => {
  const url = row?.inviteUrl || (row?.token ? getInviteUrl(row.token) : '')
  const copied = await copyText(url)
  if (copied) ElMessage.success('链接已复制')
  else ElMessage.warning('复制失败，请长按链接手动复制')
}

const copyGeneratedLink = async () => {
  const copied = await copyText(generatedUrl.value)
  if (copied) ElMessage.success('链接已复制')
  else ElMessage.warning('复制失败，请长按链接手动复制')
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

const selectedMemoryLabel = computed(() => {
  const selected = memoryOptions.value.find((item) => item.userId === inviteMemoryUserId.value)
  return selected ? memoryOptionLabel(selected) : ''
})

const filteredMemoryOptions = computed(() => {
  const keyword = memorySearch.value.trim().toLowerCase()
  if (!keyword) return memoryOptions.value
  return memoryOptions.value.filter((item) => memoryOptionLabel(item).toLowerCase().includes(keyword))
})

const syncMobileState = () => {
  isMobile.value = window.matchMedia('(max-width: 768px)').matches
}

const openMemoryPicker = async () => {
  await fetchMemoryOptions()
  memorySearch.value = ''
  memoryPickerVisible.value = true
}

const selectMemoryOption = (item: any) => {
  inviteMemoryUserId.value = item.userId
  memoryPickerVisible.value = false
}

const clearMemorySelection = () => {
  inviteMemoryUserId.value = ''
  memoryPickerVisible.value = false
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
  syncMobileState()
  mobileQuery = window.matchMedia('(max-width: 768px)')
  mobileQuery.addEventListener('change', syncMobileState)
  fetchUserInvitations()
  fetchInvitations()
  fetchContractors()
})

onBeforeUnmount(() => {
  mobileQuery?.removeEventListener('change', syncMobileState)
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
.result-lead { margin: 0 0 12px; color: #515154; font-size: 14px; }
.generated-link-card {
  width: 100%;
  min-height: 76px;
  padding: 12px;
  border: 1px solid #D2D2D7;
  border-radius: 8px;
  background: #F8FAFC;
  text-align: left;
  cursor: pointer;

  code {
    display: block;
    color: #2563EB;
    font-size: 12px;
    line-height: 1.45;
    word-break: break-all;
    white-space: normal;
  }
}
.result-tip { font-size: 12px; color: #86868B; margin-top: 12px; }
.mobile-memory-trigger {
  width: 100%;
  min-height: 40px;
  padding: 8px 12px;
  border: 1px solid #D2D2D7;
  border-radius: 8px;
  background: #fff;
  color: #1D1D1F;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font: inherit;
  text-align: left;

  span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .placeholder {
    color: #A1A1A6;
  }
}
.mobile-memory-clear {
  margin-top: 4px;
  display: flex;
  justify-content: flex-start;
}

:deep(.memory-picker-drawer.el-drawer.is-bottom) {
  width: 100% !important;
  max-width: none;
  border-radius: 14px 14px 0 0;
}

:deep(.memory-picker-drawer .el-drawer__body) {
  padding: 0;
}

.memory-picker {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #F5F7FA;
}

.memory-picker-header {
  padding: 16px 16px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;

  h3 {
    font-size: 17px;
    line-height: 1.2;
    margin: 0 0 4px;
    color: #1D1D1F;
  }

  p {
    margin: 0;
    font-size: 12px;
    color: #86868B;
  }
}

.memory-picker-search {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;
}

.memory-picker-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  -webkit-overflow-scrolling: touch;
}

.memory-picker-option {
  width: 100%;
  min-height: 68px;
  padding: 12px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 7px;
  text-align: left;

  &.selected {
    border-color: #A0522D;
    background: #FDF7F3;
  }

  &.no-memory {
    min-height: 56px;
  }
}

.memory-option-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.memory-company {
  min-width: 0;
  font-size: 15px;
  font-weight: 650;
  color: #1D1D1F;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memory-meta {
  font-size: 12px;
  color: #86868B;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memory-empty {
  padding: 28px 12px;
  text-align: center;
  color: #86868B;
  font-size: 13px;
}

@media (max-width: 768px) {
  .contractor-mgmt {
    max-width: none;
  }

  .page-header {
    margin-bottom: 14px;
  }

  .section-card {
    margin-bottom: 14px;
  }

  .section-header {
    align-items: stretch;

    :deep(.el-input) {
      width: 100% !important;
    }
  }

  .invite-tabs {
    :deep(.el-tabs__nav-wrap) {
      overflow: hidden;
    }
  }

  .invite-table {
    :deep(.el-table__cell) {
      padding: 8px 0;
    }
  }

  .invite-url {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;

    code {
      max-width: 220px;
      line-height: 1.35;
    }
  }

  .pagination {
    justify-content: flex-start;
  }

  .result-content {
    text-align: left;
  }

  :deep(.admin-form-dialog .el-dialog__header) {
    padding: 16px 48px 8px 16px;
    margin-right: 0;
  }

  :deep(.admin-form-dialog .el-dialog__title) {
    display: block;
    font-size: 17px;
    font-weight: 700;
    line-height: 1.25;
  }

  :deep(.admin-form-dialog .el-dialog__headerbtn) {
    top: 10px;
    right: 10px;
    width: 36px;
    height: 36px;
  }

  :deep(.admin-form-dialog .el-dialog__footer) {
    display: flex;
    gap: 8px;

    .el-button {
      flex: 1;
      margin-left: 0;
    }
  }

  :deep(.invite-result-dialog .el-dialog__footer) {
    padding-top: 0;
  }

  .result-lead {
    margin-bottom: 10px;
    font-size: 13px;
  }

  .generated-link-card {
    min-height: 96px;
    padding: 12px;
  }

  .result-action {
    min-height: 40px;
  }
}
</style>
