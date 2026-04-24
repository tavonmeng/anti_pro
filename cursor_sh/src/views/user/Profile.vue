<template>
  <div class="profile-page">
    <div class="page-header">
      <div class="header-text">
        <h1 class="page-title">个人设置</h1>
        <p class="page-subtitle">管理您的个人信息</p>
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
        
        <el-form-item label="联系人姓名">
          <el-input v-model="profileForm.realName" placeholder="请输入联系人姓名" />
        </el-form-item>

        <el-form-item label="公司/单位">
          <el-input v-model="profileForm.company" placeholder="请输入公司或单位名称" />
        </el-form-item>

        <el-form-item label="联系地址">
          <el-input v-model="profileForm.address" placeholder="请输入常用联系地址" />
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
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { userApi } from '@/utils/api'

const router = useRouter()

const authStore = useAuthStore()
const saving = ref(false)

const profileForm = reactive({
  username: '',
  email: '',
  realName: '',
  company: '',
  address: '',
  userId: ''
})

onMounted(() => {
  if (authStore.user) {
    profileForm.username = authStore.user.username
    profileForm.email = authStore.user.email || ''
    profileForm.realName = authStore.user.realName || ''
    profileForm.company = authStore.user.company || ''
    profileForm.address = authStore.user.address || ''
    profileForm.userId = authStore.user.id
  }
})

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

.profile-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.profile-form {
  max-width: 600px;
}
</style>
