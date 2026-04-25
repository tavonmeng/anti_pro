<template>
  <div class="profile-page">
    <div class="page-header">
      <div class="header-text">
        <h1 class="page-title">个人设置</h1>
        <p class="page-subtitle">管理您的个人信息和企业认证</p>
      </div>
    </div>
    
    <div class="profile-columns">
      <!-- 左栏：企业认证（放在个人信息前面） -->
      <el-card class="profile-card enterprise-card">
        <template #header>
          <div class="card-header">
            <span>企业认证</span>
            <el-tag 
              :type="enterpriseStatusTag.type" 
              size="small"
              effect="plain"
            >{{ enterpriseStatusTag.text }}</el-tag>
          </div>
        </template>
        
        <!-- 已通过认证（不可修改） -->
        <div v-if="enterpriseStatus === 'approved'" class="enterprise-approved">
          <div class="approved-icon">
            <el-icon :size="48" color="#67C23A"><CircleCheckFilled /></el-icon>
          </div>
          <h3>企业认证已通过</h3>
          <el-form label-width="100px" class="enterprise-form enterprise-readonly">
            <el-form-item label="企业名称">
              <el-input :model-value="authStore.user?.enterprise_name" disabled />
            </el-form-item>
            <el-form-item label="营业执照">
              <div v-if="enterpriseLicenseUrl" class="license-preview-inline" @click="showLicenseDialog = true">
                <el-image :src="enterpriseLicenseUrl" fit="cover" style="width: 120px; height: 90px; border-radius: 6px; cursor: pointer;" />
                <span class="preview-hint">点击放大</span>
              </div>
              <el-tag v-else type="success" size="small">已提交</el-tag>
            </el-form-item>
          </el-form>
          <p class="enterprise-info-sub" style="margin-top: 12px;">认证信息不可修改。如需变更，请联系管理员。</p>
        </div>

        <!-- 审核中（不可修改） -->
        <div v-else-if="enterpriseStatus === 'pending'" class="enterprise-pending">
          <div class="pending-icon">
            <el-icon :size="48" color="#E6A23C"><Clock /></el-icon>
          </div>
          <h3>企业认证审核中</h3>
          <el-form label-width="100px" class="enterprise-form enterprise-readonly">
            <el-form-item label="企业名称">
              <el-input :model-value="authStore.user?.enterprise_name" disabled />
            </el-form-item>
            <el-form-item label="营业执照">
              <div v-if="enterpriseLicenseUrl" class="license-preview-inline" @click="showLicenseDialog = true">
                <el-image :src="enterpriseLicenseUrl" fit="cover" style="width: 120px; height: 90px; border-radius: 6px; cursor: pointer;" />
                <span class="preview-hint">点击放大</span>
              </div>
              <el-tag v-else type="warning" size="small">待审核</el-tag>
            </el-form-item>
          </el-form>
          <p class="enterprise-info-sub" style="margin-top: 12px;">审核通过后，您将解锁下单等更多功能。</p>
        </div>

        <!-- 被拒绝（可重新修改提交） -->
        <div v-else-if="enterpriseStatus === 'rejected'" class="enterprise-rejected">
          <el-alert 
            type="warning" 
            :title="'认证被退回'" 
            :description="(authStore.user as any)?.enterprise_reject_reason || '请补充相关材料后重新提交'" 
            show-icon 
            :closable="false"
            style="margin-bottom: 20px;"
          />
          <el-form :model="enterpriseForm" label-width="100px" class="enterprise-form">
            <el-form-item label="企业名称" required>
              <el-input v-model="enterpriseForm.name" placeholder="请输入企业全称" />
            </el-form-item>
            <el-form-item label="已上传执照" v-if="enterpriseLicenseUrl">
              <div class="license-preview-inline" @click="showLicenseDialog = true">
                <el-image :src="enterpriseLicenseUrl" fit="cover" style="width: 120px; height: 90px; border-radius: 6px; cursor: pointer;" />
                <span class="preview-hint">当前已上传（点击放大）</span>
              </div>
            </el-form-item>
            <el-form-item label="重新上传" :required="!enterpriseLicenseUrl">
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
                  <div class="el-upload__tip">支持 JPG/PNG/WEBP，不超过 5MB{{ enterpriseLicenseUrl ? '（不选则沿用已上传的）' : '' }}</div>
                </template>
              </el-upload>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="submittingAuth" @click="handleSubmitAuth">
                重新提交认证
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 未提交（可填写） -->
        <div v-else class="enterprise-none">
          <p class="enterprise-info-sub" style="margin-bottom: 20px;">完成企业认证后可使用全部功能，包括下单、修改用户名等。</p>
          <el-form :model="enterpriseForm" label-width="100px" class="enterprise-form">
            <el-form-item label="企业名称" required>
              <el-input v-model="enterpriseForm.name" placeholder="请输入企业全称" />
            </el-form-item>
            <el-form-item label="营业执照" required>
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
                  <div class="el-upload__tip">支持 JPG/PNG/WEBP，不超过 5MB</div>
                </template>
              </el-upload>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="submittingAuth" @click="handleSubmitAuth">
                提交企业认证
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 营业执照放大预览 -->
        <el-dialog v-model="showLicenseDialog" title="营业执照" width="600px" align-center>
          <div style="display: flex; justify-content: center; padding: 16px;">
            <el-image :src="enterpriseLicenseUrl" fit="contain" style="max-width: 100%; max-height: 500px;" />
          </div>
        </el-dialog>
      </el-card>

      <!-- 右栏：个人信息 -->
      <el-card class="profile-card">
        <template #header>
          <div class="card-header">
            <span>个人信息</span>
          </div>
        </template>
        <el-form :model="profileForm" label-width="100px" class="profile-form">
          <el-form-item label="用户名">
            <div class="username-display">
              <el-input v-model="profileForm.username" disabled v-if="!authStore.isEnterprise()" />
              <template v-else>
                <el-input v-model="profileForm.username" :disabled="!editingUsername" />
                <el-button v-if="!editingUsername" text type="primary" @click="editingUsername = true" style="margin-left: 8px;">修改</el-button>
                <template v-else>
                  <el-button type="primary" size="small" @click="handleUpdateUsername" :loading="savingUsername" style="margin-left: 8px;">保存</el-button>
                  <el-button size="small" @click="cancelEditUsername">取消</el-button>
                </template>
              </template>
            </div>
          </el-form-item>
          
          <el-form-item label="邮箱">
            <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
          </el-form-item>
          
          <el-form-item label="联系人姓名">
            <el-input v-model="profileForm.realName" placeholder="请输入联系人姓名" />
          </el-form-item>

          <el-form-item label="联系地址">
            <el-input v-model="profileForm.address" placeholder="请输入常用联系地址" />
          </el-form-item>
          
          <el-form-item label="角色">
            <div class="role-tag-row">
              <el-tag :type="authStore.isAdmin() ? 'warning' : authStore.isStaff() ? 'primary' : 'info'">
                {{ authStore.isAdmin() ? '管理员' : authStore.isStaff() ? '负责人' : '普通用户' }}
              </el-tag>
              <el-tag v-if="authStore.isEnterprise()" type="success" class="enterprise-tag">
                <el-icon style="margin-right: 2px;"><Star /></el-icon>
                企业用户
              </el-tag>
            </div>
          </el-form-item>
          
          <el-form-item label="账户ID">
            <el-input v-model="profileForm.userId" disabled />
          </el-form-item>
          
          <el-form-item>
            <div style="display: flex; gap: 12px; width: 100%;">
              <el-button type="primary" :loading="saving" @click="handleSave">
                保存修改
              </el-button>
              <el-button @click="handleReset">重置</el-button>
              <el-button type="danger" plain @click="handleLogout" style="margin-left: auto;">
                退出登录
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, CircleCheckFilled, Clock, Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { userApi, enterpriseApi } from '@/utils/api'
import type { UploadFile } from 'element-plus'

const router = useRouter()

const authStore = useAuthStore()
const saving = ref(false)
const submittingAuth = ref(false)
const editingUsername = ref(false)
const savingUsername = ref(false)
const licenseFile = ref<File | null>(null)
const licenseFileList = ref<any[]>([])
const showLicenseDialog = ref(false)

const enterpriseLicenseUrl = computed(() => {
  return (authStore.user as any)?.business_license_url || ''
})

const profileForm = reactive({
  username: '',
  email: '',
  realName: '',
  company: '',
  address: '',
  userId: ''
})

const enterpriseForm = reactive({
  name: ''
})

const enterpriseStatus = computed(() => {
  return authStore.user?.enterprise_status || 'none'
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

onMounted(async () => {
  if (authStore.user) {
    profileForm.username = authStore.user.username
    profileForm.email = authStore.user.email || ''
    profileForm.realName = authStore.user.realName || ''
    profileForm.company = authStore.user.company || ''
    profileForm.address = authStore.user.address || ''
    profileForm.userId = authStore.user.id
    // 预填企业名称
    enterpriseForm.name = authStore.user.enterprise_name || authStore.user.company || ''

    // 从服务端实时获取企业认证状态（避免 localStorage 缓存导致状态过时）
    try {
      const res = await enterpriseApi.getStatus()
      const data = res?.data || res
      if (data && data.enterprise_status) {
        authStore.user.enterprise_status = data.enterprise_status
        authStore.user.enterprise_name = data.enterprise_name || authStore.user.enterprise_name
        if (data.enterprise_reject_reason !== undefined) {
          (authStore.user as any).enterprise_reject_reason = data.enterprise_reject_reason
        }
        if (data.business_license_url !== undefined) {
          (authStore.user as any).business_license_url = data.business_license_url
        }
        localStorage.setItem('user', JSON.stringify(authStore.user))
        // 更新企业名称表单
        if (data.enterprise_name) {
          enterpriseForm.name = data.enterprise_name
        }
      }
    } catch (e) {
      // 静默失败，使用本地缓存数据
    }
  }
})

const handleLicenseChange = (file: UploadFile) => {
  if (file.raw) {
    if (file.raw.size > 5 * 1024 * 1024) {
      ElMessage.error('文件大小不能超过 5MB')
      licenseFileList.value = []
      return
    }
    licenseFile.value = file.raw
    licenseFileList.value = [file]
  }
}

const handleSubmitAuth = async () => {
  if (!enterpriseForm.name.trim()) {
    ElMessage.warning('请输入企业名称')
    return
  }
  // 首次提交必须上传执照；重新提交时如果已有执照、可以不重新上传
  if (!licenseFile.value && !enterpriseLicenseUrl.value) {
    ElMessage.warning('请上传营业执照')
    return
  }

  submittingAuth.value = true
  try {
    const formData = new FormData()
    formData.append('enterprise_name', enterpriseForm.name.trim())
    if (licenseFile.value) {
      formData.append('business_license', licenseFile.value)
    }
    
    await enterpriseApi.submit(formData)
    ElMessage.success('企业认证申请已提交')
    
    // 更新本地状态
    if (authStore.user) {
      authStore.user.enterprise_status = 'pending'
      authStore.user.enterprise_name = enterpriseForm.name.trim()
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
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
    await enterpriseApi.updateUsername(profileForm.username.trim())
    if (authStore.user) {
      authStore.user.username = profileForm.username.trim()
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
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
  if (authStore.user) {
    profileForm.username = authStore.user.username
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const res = await userApi.updateProfile(profileForm)
    if (res && authStore.user) {
      authStore.user.email = profileForm.email
      authStore.user.realName = profileForm.realName
      authStore.user.company = profileForm.company
      authStore.user.address = profileForm.address
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
    ElMessage.success('保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  if (authStore.user) {
    profileForm.username = authStore.user.username
    profileForm.email = authStore.user.email || ''
    profileForm.realName = authStore.user.realName || ''
    profileForm.company = authStore.user.company || ''
    profileForm.address = authStore.user.address || ''
    profileForm.userId = authStore.user.id
  }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出当前账号吗？', '退出登录', {
      confirmButtonText: '确定退出',
      cancelButtonText: '暂不退出',
      type: 'warning',
    })
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    // cancelled
  }
}
</script>

<style lang="scss" scoped>
.profile-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-text {
  flex: 1;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #86868B;
  margin: 0;
}

.profile-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

.profile-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 16px;
}

.profile-form {
  max-width: 100%;
}

.username-display {
  display: flex;
  align-items: center;
  width: 100%;
}

.role-tag-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.enterprise-tag {
  :deep(.el-icon) {
    font-size: 12px;
  }
}

/* Enterprise section styles */
.enterprise-card {
  .enterprise-form {
    max-width: 100%;
  }
}

.enterprise-approved,
.enterprise-pending {
  text-align: center;
  padding: 24px 0;
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 16px 0 8px;
  }
}

.enterprise-readonly {
  margin-top: 16px;
  text-align: left;
  
  :deep(.el-input.is-disabled .el-input__inner) {
    color: #303133;
    background-color: #f5f7fa;
    cursor: default;
  }
}

.approved-icon,
.pending-icon {
  margin-bottom: 4px;
}

.enterprise-info-text {
  font-size: 14px;
  color: #303133;
  margin: 4px 0;
}

.enterprise-info-sub {
  font-size: 13px;
  color: #86868B;
  margin: 4px 0;
  line-height: 1.5;
}

.license-preview-inline {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  
  .preview-hint {
    font-size: 12px;
    color: #909399;
  }
  
  &:hover .preview-hint {
    color: #409EFF;
  }
}

.license-uploader {
  :deep(.el-upload--picture-card) {
    width: 148px;
    height: 148px;
  }
  :deep(.el-upload-list__item) {
    width: 148px;
    height: 148px;
  }
}

@media (max-width: 900px) {
  .profile-columns {
    grid-template-columns: 1fr;
  }
}
</style>
