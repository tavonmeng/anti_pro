<template>
  <div class="profile-page">
    <div class="page-header">
      <el-button text type="primary" :icon="ArrowLeft" @click="goToWorkspace" class="back-button">
        返回工作台
      </el-button>
      <div class="header-text">
        <h1 class="page-title">个人设置</h1>
        <p class="page-subtitle">管理您的个人信息和账户设置</p>
      </div>
    </div>
    
    <el-card class="profile-card">
      <el-form :model="profileForm" label-width="120px" class="profile-form">
        <el-form-item label="用户名">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        
        <el-form-item label="邮箱">
          <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        
        <el-form-item label="角色">
          <el-tag :type="authStore.isAdmin() ? 'warning' : authStore.isStaff() ? 'primary' : 'info'">
            {{ authStore.isAdmin() ? '管理员' : authStore.isStaff() ? '负责人' : '普通用户' }}
          </el-tag>
        </el-form-item>
        
        <el-form-item label="账户ID">
          <el-input v-model="profileForm.userId" disabled />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">
            保存修改
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card class="password-card" style="margin-top: 24px;">
      <template #header>
        <span class="card-title">修改密码</span>
      </template>
      
      <el-form :model="passwordForm" label-width="120px" :rules="passwordRules" ref="passwordFormRef">
        <el-form-item label="旧密码" prop="oldPassword">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            placeholder="请输入旧密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" :loading="changingPassword" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { authApi, userApi } from '@/utils/api'

const router = useRouter()
const authStore = useAuthStore()
const saving = ref(false)
const changingPassword = ref(false)
const passwordFormRef = ref<FormInstance>()

const profileForm = reactive({
  username: '',
  email: '',
  userId: ''
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule: any, value: string, callback: Function) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  oldPassword: [
    { required: true, message: '请输入旧密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

onMounted(() => {
  if (authStore.user) {
    profileForm.username = authStore.user.username
    profileForm.email = authStore.user.email || ''
    profileForm.userId = authStore.user.id
  }
})

const handleSave = async () => {
  saving.value = true
  try {
    // 调用API保存用户信息
    const res = await userApi.updateProfile(profileForm)
    if (res && authStore.user) {
      authStore.user.email = profileForm.email
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
    profileForm.userId = authStore.user.id
  }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      changingPassword.value = true
      try {
        await authApi.changePassword({
          oldPassword: passwordForm.oldPassword,
          newPassword: passwordForm.newPassword
        })
        ElMessage.success('密码修改成功')
        passwordForm.oldPassword = ''
        passwordForm.newPassword = ''
        passwordForm.confirmPassword = ''
        passwordFormRef.value.resetFields()
      } catch (error: any) {
        ElMessage.error(error.message || '密码修改失败')
      } finally {
        changingPassword.value = false
      }
    }
  })
}

const goToWorkspace = () => {
  router.push('/user/workspace')
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

.back-button {
  margin-right: 8px;
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

.profile-card,
.password-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1D1D1F;
}

.profile-form {
  max-width: 600px;
}
</style>

