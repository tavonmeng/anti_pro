<template>
  <div class="admin-login-container">
    <div class="admin-login-wrapper">
      <div>
        <div class="admin-login-header">
          <div class="lock-icon">
            <el-icon :size="48"><Suitcase /></el-icon>
          </div>
          <h1 class="admin-title">承包商登录</h1>
          <p class="admin-subtitle">Contractor Portal</p>
          <div class="security-notice">
            <el-icon><Warning /></el-icon>
            <span>仅限授权承包商访问</span>
          </div>
        </div>
        
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="admin-login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="phone">
            <el-input
              v-model="loginForm.phone"
              placeholder="手机号"
              size="large"
              class="admin-input"
            >
              <template #prefix>
                <el-icon class="input-icon"><Iphone /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item prop="sms_code">
            <div class="sms-row">
              <el-input
                v-model="loginForm.sms_code"
                placeholder="短信验证码"
                size="large"
                class="admin-input sms-input"
                @keyup.enter="handleLogin"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Message /></el-icon>
                </template>
              </el-input>
              <el-button
                :disabled="smsCooldown > 0"
                class="sms-btn"
                @click="sendSmsCode"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="admin-login-button"
              :loading="loading"
              @click="handleLogin"
            >
              <span v-if="!loading">登录</span>
              <span v-else>验证中...</span>
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="admin-login-footer">
          <p class="security-tips">
            <el-icon><InfoFilled /></el-icon>
            使用邀请链接注册后可通过手机号登录
          </p>
          <p class="back-link">
            <el-link @click="goToAdminLogin">← 管理员登录</el-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Iphone, Message, Warning, InfoFilled, Suitcase } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types'
import request from '@/utils/request'

const router = useRouter()
const authStore = useAuthStore()
const loginFormRef = ref<FormInstance>()
const loading = ref(false)
const smsCooldown = ref(0)
let smsTimer: any = null

const loginForm = reactive({
  phone: '',
  sms_code: '',
  role: 'contractor' as UserRole,
})

const loginRules: FormRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { len: 11, message: '手机号必须11位', trigger: 'blur' },
  ],
  sms_code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
  ],
}

const sendSmsCode = async () => {
  if (!loginForm.phone || loginForm.phone.length !== 11) {
    ElMessage.warning('请先输入正确的手机号')
    return
  }
  try {
    await request.post('/api/auth/sms/send', { phone: loginForm.phone })
    ElMessage.success('验证码已发送')
    smsCooldown.value = 60
    smsTimer = setInterval(() => {
      smsCooldown.value--
      if (smsCooldown.value <= 0) clearInterval(smsTimer)
    }, 1000)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '发送失败')
  }
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const success = await authStore.login(loginForm)
      if (success) {
        router.push('/contractor')
      }
    } catch (error: any) {
      console.error('登录失败:', error)
    } finally {
      loading.value = false
    }
  })
}

const goToAdminLogin = () => {
  router.push('/admin/login')
}
</script>

<style lang="scss" scoped>
.admin-login-container {
  width: 100%; min-height: 100vh; display: flex;
  flex-direction: column; align-items: center; justify-content: center;
  background: #000; font-family: 'Outfit', 'PingFang SC', sans-serif; color: #fff;
  padding: 20px 0; box-sizing: border-box;
}
.admin-login-wrapper {
  position: relative; z-index: 10; width: 90%; max-width: 400px;
  background: #000; border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
  margin: 0; padding: 32px; box-sizing: border-box;
}
.admin-login-header { text-align: center; margin-bottom: 24px; }
.lock-icon {
  width: 50px; height: 50px; margin: 0 auto 12px;
  display: flex; align-items: center; justify-content: center;
  background: #fff; border-radius: 50%; color: #000;
}
.admin-title { font-size: 24px; font-weight: 800; color: #fff; margin: 0 0 6px 0; text-align: center; }
.admin-subtitle { font-size: 13px; color: rgba(255,255,255,0.5); margin: 0; text-align: center; }
.security-notice {
  font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 8px;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.admin-login-form { width: 100%; display: flex; flex-direction: column; gap: 16px; }
:deep(.el-form-item) { margin-bottom: 0 !important; width: 100%; }
.admin-input {
  :deep(.el-input__wrapper) {
    background-color: transparent !important; border: none !important;
    border-radius: 0 !important; border-bottom: 1px solid rgba(255,255,255,0.2) !important;
    box-shadow: none !important; padding: 0 10px !important; height: 40px;
    &.is-focus, &:hover { border-bottom-color: #fff !important; }
  }
  :deep(.el-input__inner) {
    height: 40px !important; font-size: 15px !important; color: #fff !important;
    &::placeholder { color: rgba(255,255,255,0.4) !important; }
  }
}
.input-icon { color: #888; font-size: 18px; }
.sms-row { display: flex; gap: 12px; width: 100%; }
.sms-input { flex: 1; }
.sms-btn {
  flex-shrink: 0; height: 40px; font-size: 13px;
  background: transparent !important; border: 1px solid rgba(255,255,255,0.3) !important;
  color: #fff !important; border-radius: 8px !important;
  &:hover { border-color: #fff !important; }
  &:disabled, &.is-disabled { opacity: 0.4; }
}
.admin-login-button {
  width: 100%; height: 44px; font-size: 16px; font-weight: 600;
  background: #fff !important; border: none !important;
  border-radius: 60px !important; color: #000 !important; margin-top: 8px;
  &:hover { background: #e0e0e0 !important; transform: translateY(-2px); }
}
.admin-login-footer {
  margin-top: 24px; text-align: center;
  display: flex; flex-direction: column; gap: 12px;
}
.security-tips {
  font-size: 13px; color: rgba(255,255,255,0.4); margin: 0;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.back-link { font-size: 13px; margin: 0; }
:deep(.el-link) { color: #fff !important; font-weight: 600; &:hover { opacity: 0.8; } }
</style>
