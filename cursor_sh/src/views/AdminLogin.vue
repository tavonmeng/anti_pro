<template>
  <div class="admin-login-container">
    <div class="admin-login-wrapper">
      <div>
        <div class="admin-login-header">
          <div class="lock-icon">
            <el-icon :size="48"><Lock /></el-icon>
          </div>
          <h1 class="admin-title">系统管理</h1>
          <p class="admin-subtitle">Management Portal</p>
          <div class="security-notice">
            <el-icon><Warning /></el-icon>
            <span>仅限授权人员访问</span>
          </div>
        </div>

        <el-form
          ref="smsFormRef"
          :model="smsForm"
          :rules="smsRules"
          class="admin-login-form"
          @submit.prevent="handleSmsLogin"
        >
          <el-form-item prop="phone">
            <el-input
              v-model="smsForm.phone"
              placeholder="管理员手机号"
              size="large"
              class="admin-input"
              maxlength="11"
            >
              <template #prefix>
                <el-icon class="input-icon"><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="smsCode">
            <div class="sms-code-row">
              <el-input
                v-model="smsForm.smsCode"
                placeholder="短信验证码"
                size="large"
                class="admin-input sms-code-input"
                maxlength="6"
                @keyup.enter="handleSmsLogin"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Message /></el-icon>
                </template>
              </el-input>
              <el-button
                class="sms-send-button"
                :disabled="smsCooldown > 0 || !isSmsPhoneValid"
                :loading="smsSending"
                @click="openSmsCaptcha"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="admin-login-button"
              :loading="loading"
              @click="handleSmsLogin"
            >
              <span v-if="!loading">登录系统</span>
              <span v-else>验证中...</span>
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="admin-login-footer">
          <p class="security-tips">
            <el-icon><InfoFilled /></el-icon>
            系统将记录所有登录行为
          </p>
        </div>
      </div>
    </div>

    <el-dialog v-model="smsCaptchaVisible" width="360px" :show-close="false" class="captcha-dialog" append-to-body>
      <template #header>
        <span class="dialog-title">安全验证</span>
      </template>
      <Captcha ref="dialogCaptchaRef" v-model="dialogCaptcha" @verify="handleDialogCaptchaVerify" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Warning, InfoFilled, Message } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/utils/api'
import type { LoginRequest, UserRole } from '@/types'
import Captcha from '@/components/Captcha.vue'

const router = useRouter()
const authStore = useAuthStore()
const smsFormRef = ref<FormInstance>()
const loading = ref(false)
const smsSending = ref(false)
const smsCooldown = ref(0)
const smsCaptchaVisible = ref(false)
const dialogCaptcha = ref('')
const dialogCaptchaRef = ref<InstanceType<typeof Captcha>>()
let smsCooldownTimer: ReturnType<typeof setInterval> | undefined

const smsForm = reactive({
  phone: '',
  smsCode: ''
})

const isSmsPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(smsForm.phone))

const validatePhone = (rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入管理员手机号'))
  } else if (value.length !== 11) {
    callback(new Error('手机号必须是11位'))
  } else {
    callback()
  }
}

const validateSmsCode = (rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入短信验证码'))
  } else if (value.length < 4) {
    callback(new Error('验证码格式不正确'))
  } else {
    callback()
  }
}

const smsRules: FormRules = {
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  smsCode: [{ validator: validateSmsCode, trigger: 'blur' }]
}

const routeAfterInternalLogin = () => {
  const redirect = router.currentRoute.value.query.redirect as string || undefined

  if (authStore.isAdmin()) {
    router.push(redirect || '/admin')
  } else if (authStore.isStaff()) {
    router.push(redirect || '/staff')
  } else if (authStore.isContractor()) {
    router.push(redirect || '/contractor')
  } else {
    ElMessage.error('您没有内部系统访问权限')
    authStore.logout()
  }
}

const tryInternalLogin = async (payload: Omit<LoginRequest, 'role'>) => {
  const roles: UserRole[] = ['admin', 'staff', 'contractor']

  for (const role of roles) {
    try {
      const success = await authStore.login({ ...payload, role }, true)
      if (success) {
        ElMessage.success('登录成功')
        routeAfterInternalLogin()
        return true
      }
    } catch {
      // Continue with the next internal role; show one clear error after all attempts fail.
    }
  }

  ElMessage.error('手机号或验证码错误')
  return false
}

const openSmsCaptcha = () => {
  if (!isSmsPhoneValid.value) {
    ElMessage.warning('请输入有效的11位手机号')
    return
  }
  dialogCaptcha.value = ''
  smsCaptchaVisible.value = true
  setTimeout(() => dialogCaptchaRef.value?.refresh(), 100)
}

const handleDialogCaptchaVerify = (isValid: boolean) => {
  if (!isValid) return
  smsCaptchaVisible.value = false
  handleSendSms()
}

const handleSendSms = async () => {
  if (!isSmsPhoneValid.value) {
    ElMessage.warning('请输入有效的11位手机号')
    return
  }

  smsSending.value = true
  try {
    await authApi.sendSms(smsForm.phone)
    ElMessage.success('验证码已发送，请注意查收短信')
    smsCooldown.value = 60
    if (smsCooldownTimer) clearInterval(smsCooldownTimer)
    smsCooldownTimer = setInterval(() => {
      smsCooldown.value--
      if (smsCooldown.value <= 0 && smsCooldownTimer) {
        clearInterval(smsCooldownTimer)
        smsCooldownTimer = undefined
      }
    }, 1000)
  } catch (error) {
    console.error('发送验证码失败:', error)
  } finally {
    smsSending.value = false
  }
}

const handleSmsLogin = async () => {
  if (!smsFormRef.value) return

  await smsFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await tryInternalLogin({
        phone: smsForm.phone,
        sms_code: smsForm.smsCode
      })
    } finally {
      loading.value = false
    }
  })
}

onBeforeUnmount(() => {
  if (smsCooldownTimer) clearInterval(smsCooldownTimer)
})
</script>

<style lang="scss" scoped>
/* 统一最外层布局强制居中 */
.login-container, .admin-login-container, .register-container {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #000;
  font-family: 'Outfit', 'PingFang SC', sans-serif;
  color: #fff;
  padding: 20px 0;
  box-sizing: border-box;
}

.login-wrapper, .admin-login-wrapper, .register-wrapper {
  position: relative;
  z-index: 10;
  width: 90%;
  max-width: 400px;
  background: #000;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  margin: 0;
  padding: 32px;
  box-sizing: border-box;
}

/* 头部重置 */
.login-header, .admin-login-header, .register-header {
  text-align: center;
  margin-bottom: 24px;
}

.logo-icon, .lock-icon {
  width: 50px;
  height: 50px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 50%;
  color: #000;
}

.logo-svg { width: 32px; height: 32px; }
.logo-svg circle, .logo-svg path { stroke: #000 !important; }

.login-title, .admin-title, .register-title {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  margin: 0 0 6px 0;
  text-align: center;
  line-height: 1.2;
}

.login-subtitle, .admin-subtitle, .register-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
  text-align: center;
}

/* 表单紧凑设定 */
.login-form, .admin-login-form, .register-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

:deep(.el-form-item) {
  margin-bottom: 0 !important; 
  width: 100%;
}
:deep(.el-form-item__content) {
  line-height: normal !important;
}

.input-wrapper {
  width: 100%;
}

/* 黑底输入框原生主题覆写 */
.tech-input, .admin-input, .captcha-input {
  :deep(.el-input__wrapper) {
    background-color: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important;
    box-shadow: none !important;
    padding: 0 10px !important;
    height: 40px;
    transition: all 0.3s;
    
    &.is-focus, &:hover {
      border-bottom-color: #fff !important;
    }
  }

  :deep(.el-input__inner) {
    height: 40px !important;
    font-size: 15px !important;
    color: #fff !important;
    &::placeholder {
      color: rgba(255, 255, 255, 0.4) !important;
    }
  }
}

.input-border { display: none !important; }
.input-icon { color: #888; font-size: 18px; }

.sms-code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 104px;
  gap: 10px;
  width: 100%;
  align-items: center;
}

.sms-send-button {
  height: 40px;
  border-radius: 999px !important;
  border: 1px solid rgba(255, 255, 255, 0.32) !important;
  background: transparent !important;
  color: #fff !important;
  padding: 0 12px !important;
  font-size: 13px;
  white-space: nowrap;

  &:hover:not(.is-disabled) {
    border-color: #fff !important;
    background: rgba(255, 255, 255, 0.1) !important;
  }
}

/* 按钮 */
.login-button, .admin-login-button, .register-button {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: #fff !important;
  border: none !important;
  border-radius: 60px !important;
  color: #000 !important;
  margin-top: 8px; 
  transition: all 0.2s;
  
  &:hover {
    background: #e0e0e0 !important;
    transform: translateY(-2px);
  }
}

.button-icon { margin-left: 8px; }

/* 尾部区域 */
.login-footer, .admin-login-footer, .register-footer {
  margin-top: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.footer-text, .security-notice, .security-tips {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.footer-link, .back-link {
  font-size: 13px;
  margin: 0;
}

:deep(.el-link) {
  color: #fff !important;
  font-weight: 600;
  &:hover { opacity: 0.8; }
}

/* 验证码特殊布局补丁 */
.captcha-container { display: flex; gap: 12px; align-items: center; width: 100%; }
.captcha-display {
  border-radius: 8px; overflow: hidden; height: 40px; 
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.captcha-display canvas { height: 100% !important; display: block; }
.captcha-input { flex: 1; }

.minimal-background {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-color: #000; z-index: 1; pointer-events: none;
}

.dialog-title {
  color: #111;
  font-weight: 700;
}

@media (max-width: 420px) {
  .sms-code-row {
    grid-template-columns: 1fr;
  }

  .sms-send-button {
    width: 100%;
  }
}
</style>
