<template>
  <div class="profile-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人设置</h1>
        <p class="page-subtitle">管理账号资料、企业认证和安全联系方式</p>
      </div>
    </div>

    <div class="settings-shell">
      <section class="account-panel">
        <div class="identity-strip">
          <div class="avatar-stack">
            <el-avatar :size="72" class="profile-avatar" :src="avatarUrl">{{ userInitial }}</el-avatar>
            <el-upload
              v-if="authStore.isEnterprise()"
              :auto-upload="false"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/webp"
              :on-change="handleAvatarChange"
            >
              <el-button class="avatar-action" :icon="Upload" :loading="uploadingAvatar">更换头像</el-button>
            </el-upload>
          </div>

          <div class="identity-main">
            <div class="identity-title-row">
              <h2>{{ authStore.user?.username || '用户' }}</h2>
              <el-tag :type="enterpriseStatusTag.type" effect="plain">{{ enterpriseStatusTag.text }}</el-tag>
            </div>
            <div class="identity-meta">
              <span>账户ID {{ profileForm.userId || '-' }}</span>
              <span>{{ maskedPhone }}</span>
              <span v-if="roleText">{{ roleText }}</span>
            </div>
          </div>

          <div class="account-status">
            <span class="summary-label">账号状态</span>
            <strong :class="{ 'is-unverified': enterpriseStatus !== 'approved' }">{{ enterpriseStatusTag.text }}</strong>
          </div>
        </div>

        <div class="profile-sections">
          <div class="info-section">
            <div class="section-heading">
              <div>
                <h3>个人信息</h3>
                <p>企业认证通过后可修改头像和用户名</p>
              </div>
            </div>

            <el-form :model="profileForm" label-position="top" class="profile-form">
              <div class="form-grid">
                <el-form-item label="用户名">
                  <div class="inline-edit">
                    <el-input v-model="profileForm.username" :disabled="!authStore.isEnterprise() || !editingUsername" />
                    <el-button v-if="authStore.isEnterprise() && !editingUsername" text type="primary" :icon="EditPen" @click="editingUsername = true">
                      修改
                    </el-button>
                    <template v-if="authStore.isEnterprise() && editingUsername">
                      <el-button type="primary" :loading="savingUsername" @click="handleUpdateUsername">保存</el-button>
                      <el-button @click="cancelEditUsername">取消</el-button>
                    </template>
                  </div>
                </el-form-item>

                <el-form-item label="手机号">
                  <div class="inline-edit">
                    <el-input :model-value="profileForm.phone" disabled />
                    <el-button text type="primary" :icon="Iphone" @click="openPhoneDialog">更改</el-button>
                  </div>
                </el-form-item>

                <el-form-item label="邮箱">
                  <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
                </el-form-item>

                <el-form-item label="联系人姓名">
                  <el-input v-model="profileForm.realName" placeholder="请输入联系人姓名" />
                </el-form-item>

                <el-form-item label="联系地址" class="wide-field">
                  <el-input v-model="profileForm.address" placeholder="请输入常用联系地址" />
                </el-form-item>
              </div>

              <div class="form-actions">
                <el-button type="primary" :loading="saving" @click="handleSave">
                  保存修改
                </el-button>
                <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
              </div>
            </el-form>
          </div>

          <div class="enterprise-section" data-onboarding-target="enterprise-auth-section">
            <div class="section-heading">
              <div>
                <h3>企业认证</h3>
                <p>{{ enterpriseHint }}</p>
              </div>
              <el-icon class="section-icon" :class="`is-${enterpriseStatus}`">
                <CircleCheckFilled v-if="enterpriseStatus === 'approved'" />
                <Clock v-else-if="enterpriseStatus === 'pending'" />
                <WarningFilled v-else-if="enterpriseStatus === 'rejected'" />
                <OfficeBuilding v-else />
              </el-icon>
            </div>

            <div v-if="enterpriseStatus === 'approved'" class="approved-box">
              <div>
                <span class="summary-label">已认证企业</span>
                <strong>{{ enterpriseDisplayName }}</strong>
              </div>
              <p>认证已通过。敏感材料已隐藏，如需变更企业主体请联系管理员。</p>
            </div>

            <div v-else>
              <el-alert
                v-if="enterpriseStatus === 'rejected'"
                type="warning"
                title="认证被退回"
                :description="(authStore.user as any)?.enterprise_reject_reason || '请补充相关材料后重新提交'"
                show-icon
                :closable="false"
                class="enterprise-alert"
              />

              <el-form :model="enterpriseForm" label-position="top" class="enterprise-form">
                <el-form-item label="企业名称" required>
                  <el-input v-model="enterpriseForm.name" placeholder="请输入企业全称" :disabled="enterpriseStatus === 'pending'" />
                </el-form-item>

                <el-form-item v-if="enterpriseStatus !== 'pending'" label="营业执照" required>
                  <el-upload
                    :auto-upload="false"
                    :limit="1"
                    accept="image/jpeg,image/png,image/webp"
                    :on-change="handleLicenseChange"
                    :file-list="licenseFileList"
                    list-type="picture-card"
                    class="license-uploader"
                  >
                    <el-icon><Plus /></el-icon>
                    <template #tip>
                      <div class="el-upload__tip">支持 JPG/PNG/WEBP，不超过 5MB{{ enterpriseLicenseUrl ? '，不重新上传则沿用原文件' : '' }}</div>
                    </template>
                  </el-upload>
                </el-form-item>

                <div v-if="enterpriseStatus === 'pending'" class="pending-box">
                  <span>审核中</span>
                  <p>我们已收到您的企业认证申请，通过后会自动解锁企业用户能力。</p>
                </div>

                <el-button
                  v-if="enterpriseStatus !== 'pending'"
                  type="primary"
                  :loading="submittingAuth"
                  @click="handleSubmitAuth"
                >
                  {{ enterpriseStatus === 'rejected' ? '重新提交认证' : '提交企业认证' }}
                </el-button>
              </el-form>
            </div>
          </div>
        </div>
      </section>

      <section class="danger-panel">
        <div>
          <h3>账号操作</h3>
          <p>退出后需要重新登录才能访问工作台。</p>
        </div>
        <el-button type="danger" plain :icon="SwitchButton" @click="handleLogout">
          退出登录
        </el-button>
      </section>
    </div>

    <el-dialog v-model="phoneDialogVisible" title="更改手机号" width="440px" align-center>
      <el-form :model="phoneForm" label-position="top" class="phone-form">
        <el-form-item label="当前手机号">
          <div class="inline-edit">
            <el-input :model-value="profileForm.phone" disabled />
            <el-button :disabled="smsCooldown > 0 || sendingSms" :loading="sendingSms" @click="sendOldPhoneCode">
              {{ smsCooldown > 0 ? `${smsCooldown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="旧手机号验证码" required>
          <el-input v-model="phoneForm.oldCode" maxlength="8" placeholder="请输入验证码" />
        </el-form-item>
        <el-form-item label="新手机号" required>
          <el-input v-model="phoneForm.newPhone" maxlength="11" placeholder="请输入新的11位手机号" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="phoneDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="changingPhone" @click="handleChangePhone">确认更改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CircleCheckFilled,
  Clock,
  EditPen,
  Iphone,
  OfficeBuilding,
  Plus,
  RefreshLeft,
  SwitchButton,
  Upload,
  WarningFilled
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi, userApi, enterpriseApi } from '@/utils/api'
import type { UploadFile } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const saving = ref(false)
const submittingAuth = ref(false)
const editingUsername = ref(false)
const savingUsername = ref(false)
const uploadingAvatar = ref(false)
const licenseFile = ref<File | null>(null)
const licenseFileList = ref<any[]>([])
const phoneDialogVisible = ref(false)
const sendingSms = ref(false)
const changingPhone = ref(false)
const smsCooldown = ref(0)
let smsTimer: ReturnType<typeof setInterval> | null = null

const profileForm = reactive({
  username: '',
  phone: '',
  email: '',
  realName: '',
  company: '',
  address: '',
  userId: ''
})

const enterpriseForm = reactive({ name: '' })
const phoneForm = reactive({ oldCode: '', newPhone: '' })

const enterpriseStatus = computed(() => authStore.user?.enterprise_status || 'none')
const avatarUrl = computed(() => authStore.user?.avatar || '')
const userInitial = computed(() => (authStore.user?.username || 'U').charAt(0).toUpperCase())

const enterpriseLicenseUrl = computed(() => {
  if (enterpriseStatus.value === 'approved') return ''
  return (authStore.user as any)?.business_license_url || ''
})

const enterpriseStatusTag = computed(() => {
  const map: Record<string, { text: string; type: 'success' | 'warning' | 'danger' | 'info' }> = {
    approved: { text: '已认证', type: 'success' },
    pending: { text: '审核中', type: 'warning' },
    rejected: { text: '已退回', type: 'danger' },
    none: { text: '未认证', type: 'info' }
  }
  return map[enterpriseStatus.value] || map.none
})

const roleText = computed(() => {
  if (authStore.isAdmin()) return '管理员'
  if (authStore.isStaff()) return '负责人'
  return authStore.isEnterprise() ? '企业用户' : ''
})

const maskedPhone = computed(() => {
  const phone = profileForm.phone || authStore.user?.phone || ''
  if (!phone || phone.length < 7) return '未绑定手机号'
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
})

const enterpriseDisplayName = computed(() => {
  return authStore.user?.enterprise_name || profileForm.company || '暂未认证'
})

const enterpriseHint = computed(() => {
  const map: Record<string, string> = {
    approved: '仅展示企业名称，营业执照等敏感材料不在此处显示',
    pending: '认证材料已提交，请等待管理员审核',
    rejected: '认证被退回后可在此修改企业名称并重新提交材料',
    none: '完成认证后可使用完整下单能力'
  }
  return map[enterpriseStatus.value] || map.none
})

onMounted(async () => {
  syncFormFromUser()
  await refreshEnterpriseStatus()
})

onUnmounted(() => {
  if (smsTimer) clearInterval(smsTimer)
})

const getUserRealName = () => {
  return authStore.user?.realName || (authStore.user as any)?.real_name || ''
}

const syncFormFromUser = () => {
  if (!authStore.user) return
  profileForm.username = authStore.user.username
  profileForm.phone = authStore.user.phone || ''
  profileForm.email = authStore.user.email || ''
  profileForm.realName = getUserRealName()
  profileForm.company = authStore.user.company || ''
  profileForm.address = authStore.user.address || ''
  profileForm.userId = authStore.user.id
  enterpriseForm.name = authStore.user.enterprise_name || authStore.user.company || ''
}

const applyUserPatch = (data: any) => {
  if (!authStore.user || !data) return
  Object.assign(authStore.user, {
    email: data.email ?? authStore.user.email,
    phone: data.phone ?? authStore.user.phone,
    avatar: data.avatar ?? authStore.user.avatar,
    realName: data.realName ?? data.real_name ?? authStore.user.realName,
    company: data.company ?? authStore.user.company,
    address: data.address ?? authStore.user.address,
    enterprise_status: data.enterprise_status ?? authStore.user.enterprise_status,
    enterprise_name: data.enterprise_name ?? authStore.user.enterprise_name,
    enterprise_reject_reason: data.enterprise_reject_reason ?? authStore.user.enterprise_reject_reason
  })
  if (data.username) authStore.user.username = data.username
  if (enterpriseStatus.value === 'approved') {
    ;(authStore.user as any).business_license_url = ''
  } else if (data.business_license_url !== undefined) {
    ;(authStore.user as any).business_license_url = data.business_license_url
  }
  localStorage.setItem('user', JSON.stringify(authStore.user))
  syncFormFromUser()
}

const refreshEnterpriseStatus = async () => {
  if (!authStore.user) return
  try {
    const data = await enterpriseApi.getStatus()
    applyUserPatch(data)
    if (data?.enterprise_name) enterpriseForm.name = data.enterprise_name
  } catch (e) {
    // 使用本地缓存即可。
  }
}

const handleAvatarChange = async (file: UploadFile) => {
  if (!file.raw) return
  if (file.raw.size > 5 * 1024 * 1024) {
    ElMessage.error('头像不能超过 5MB')
    return
  }

  uploadingAvatar.value = true
  try {
    const formData = new FormData()
    formData.append('avatar', file.raw)
    const data = await userApi.updateAvatar(formData)
    applyUserPatch(data)
    ElMessage.success('头像已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '头像上传失败')
  } finally {
    uploadingAvatar.value = false
  }
}

const handleLicenseChange = (file: UploadFile) => {
  if (!file.raw) return
  if (file.raw.size > 5 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 5MB')
    licenseFileList.value = []
    return
  }
  licenseFile.value = file.raw
  licenseFileList.value = [file]
}

const handleSubmitAuth = async () => {
  if (!enterpriseForm.name.trim()) {
    ElMessage.warning('请输入企业名称')
    return
  }
  if (!licenseFile.value && !enterpriseLicenseUrl.value) {
    ElMessage.warning('请上传营业执照')
    return
  }

  submittingAuth.value = true
  try {
    const formData = new FormData()
    formData.append('enterprise_name', enterpriseForm.name.trim())
    if (licenseFile.value) formData.append('business_license', licenseFile.value)

    const data = await enterpriseApi.submit(formData)
    applyUserPatch(data)
    licenseFile.value = null
    licenseFileList.value = []
    ElMessage.success('企业认证申请已提交')
  } catch (error: any) {
    ElMessage.error(error.message || '提交失败')
  } finally {
    submittingAuth.value = false
  }
}

const handleUpdateUsername = async () => {
  if (!profileForm.username.trim() || profileForm.username.trim().length < 2) {
    ElMessage.warning('用户名至少2个字符')
    return
  }
  savingUsername.value = true
  try {
    const data = await enterpriseApi.updateUsername(profileForm.username.trim())
    applyUserPatch(data || { username: profileForm.username.trim() })
    ElMessage.success('用户名修改成功')
    editingUsername.value = false
  } catch (error: any) {
    ElMessage.error(error.message || '修改失败')
  } finally {
    savingUsername.value = false
  }
}

const cancelEditUsername = () => {
  editingUsername.value = false
  if (authStore.user) profileForm.username = authStore.user.username
}

const handleSave = async () => {
  saving.value = true
  try {
    const data = await userApi.updateProfile({
      email: profileForm.email || null,
      realName: profileForm.realName,
      company: profileForm.company,
      address: profileForm.address
    })
    applyUserPatch(data || profileForm)
    ElMessage.success('保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  syncFormFromUser()
}

const openPhoneDialog = () => {
  phoneForm.oldCode = ''
  phoneForm.newPhone = ''
  phoneDialogVisible.value = true
}

const startSmsCooldown = () => {
  smsCooldown.value = 60
  if (smsTimer) clearInterval(smsTimer)
  smsTimer = setInterval(() => {
    smsCooldown.value -= 1
    if (smsCooldown.value <= 0 && smsTimer) {
      clearInterval(smsTimer)
      smsTimer = null
    }
  }, 1000)
}

const sendOldPhoneCode = async () => {
  if (!profileForm.phone) {
    ElMessage.warning('当前账号未绑定手机号')
    return
  }
  sendingSms.value = true
  try {
    await authApi.sendSms(profileForm.phone)
    startSmsCooldown()
    ElMessage.success('验证码已发送至旧手机号')
  } catch (error: any) {
    ElMessage.error(error.message || '验证码发送失败')
  } finally {
    sendingSms.value = false
  }
}

const handleChangePhone = async () => {
  if (!phoneForm.oldCode.trim()) {
    ElMessage.warning('请输入旧手机号验证码')
    return
  }
  if (!/^1[3-9]\d{9}$/.test(phoneForm.newPhone)) {
    ElMessage.warning('请输入有效的11位手机号')
    return
  }

  changingPhone.value = true
  try {
    const data = await userApi.changePhone({
      new_phone: phoneForm.newPhone,
      old_phone_code: phoneForm.oldCode.trim()
    })
    applyUserPatch(data)
    phoneDialogVisible.value = false
    ElMessage.success('手机号已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '手机号修改失败')
  } finally {
    changingPhone.value = false
  }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出当前账号吗？', '退出登录', {
      confirmButtonText: '确定退出',
      cancelButtonText: '暂不退出',
      type: 'warning'
    })
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    // 用户取消。
  }
}
</script>

<style lang="scss" scoped>
.profile-page {
  min-height: 100%;
  padding: 32px 24px 40px;
  box-sizing: border-box;
  color: #1b1b1c;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0;
}

.page-subtitle {
  margin: 0;
  color: #6f737c;
  font-size: 14px;
}

.settings-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account-panel,
.danger-panel {
  background: #ffffff;
  border: 1px solid rgba(27, 27, 28, 0.08);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(27, 27, 28, 0.04);
}

.identity-strip {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(160px, 220px);
  gap: 20px;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid rgba(27, 27, 28, 0.08);
  background: #f7f7f8;
  border-radius: 8px 8px 0 0;
}

.avatar-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.profile-avatar {
  background: #A0522D;
  color: #fff;
  font-size: 24px;
  font-weight: 700;
}

.avatar-action {
  height: 30px;
  border-radius: 6px;
}

.identity-main {
  min-width: 0;
}

.identity-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;

  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0;
  }
}

.identity-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-top: 10px;
  color: #6f737c;
  font-size: 13px;
}

.account-status,
.approved-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.summary-label {
  color: #6f737c;
  font-size: 12px;
}

.account-status strong,
.approved-box strong {
  color: #1b1b1c;
  font-size: 16px;
  line-height: 1.4;
}

.account-status strong.is-unverified {
  color: #c84444;
}

.profile-sections {
  display: flex;
  flex-direction: column;
}

.info-section,
.enterprise-section {
  padding: 24px;
}

.info-section {
  border-bottom: 1px solid rgba(27, 27, 28, 0.08);
}

.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;

  h3 {
    margin: 0 0 5px;
    font-size: 16px;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: #6f737c;
    font-size: 13px;
    line-height: 1.5;
  }
}

.section-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(160, 82, 45, 0.12);
  color: #A0522D;
  font-size: 20px;

  &.is-approved {
    background: #edf8f1;
    color: #2f8f4e;
  }

  &.is-pending {
    background: #fff7e8;
    color: #b87618;
  }

  &.is-rejected {
    background: #fff0f0;
    color: #c84444;
  }
}

.profile-form {
  :deep(.el-form-item__label) {
    color: #414754;
    font-weight: 600;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 16px;
}

.wide-field {
  grid-column: 1 / -1;
}

.inline-edit {
  display: flex;
  width: 100%;
  gap: 8px;
  align-items: center;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.approved-box,
.pending-box {
  padding: 16px;
  border: 1px solid rgba(27, 27, 28, 0.08);
  border-radius: 8px;
  background: #f7f7f8;

  p {
    margin: 8px 0 0;
    color: #6f737c;
    font-size: 13px;
    line-height: 1.6;
  }
}

.approved-box {
  max-width: 680px;
}

.enterprise-form {
  max-width: 680px;
}

.pending-box {
  margin-bottom: 16px;

  span {
    color: #b87618;
    font-weight: 700;
    font-size: 14px;
  }
}

.enterprise-alert {
  margin-bottom: 16px;
}

.enterprise-form {
  :deep(.el-form-item__label) {
    color: #414754;
    font-weight: 600;
  }
}

.license-uploader {
  :deep(.el-upload--picture-card),
  :deep(.el-upload-list__item) {
    width: 120px;
    height: 120px;
    border-radius: 8px;
  }
}

.danger-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;

  h3 {
    margin: 0 0 4px;
    font-size: 15px;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: #6f737c;
    font-size: 13px;
  }
}

.phone-form {
  :deep(.el-form-item__label) {
    font-weight: 600;
  }
}

@media (max-width: 1100px) {
  .identity-strip {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .account-status {
    grid-column: 1 / -1;
  }
}

@media (max-width: 720px) {
  .profile-page {
    padding: 20px 16px 32px;
  }

  .identity-strip {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .identity-title-row,
  .identity-meta {
    justify-content: center;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .inline-edit,
  .danger-panel {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
