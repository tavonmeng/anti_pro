<template>
  <div class="register-container" :class="{ 'is-modal': isModal }">
    <!-- 背景 -->
    <div class="minimal-background" v-if="!isModal"></div>

    <div class="register-wrapper">
      <div>
        <div class="register-header">
          <h1 class="register-title">Unique Vision 注册</h1>
        </div>
        
        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="register-form"
          @submit.prevent="handleRegister"
        >
          <!-- 手机号 -->
          <el-form-item prop="phone">
            <div class="input-wrapper">
              <el-input
                v-model="registerForm.phone"
                placeholder="请输入手机号"
                size="large"
                class="tech-input"
                maxlength="11"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Iphone /></el-icon>
                </template>
              </el-input>
            </div>
          </el-form-item>
          
          <!-- 短信验证码（常驻显示） -->
          <el-form-item prop="smsCode">
            <div class="step-hint step-hint-success" v-if="smsCooldown > 0">
              <span class="step-hint-icon">✅</span>
              验证码已发送至 {{ registerForm.phone.slice(0,3) }}****{{ registerForm.phone.slice(7) }}
            </div>
            <div class="sms-code-row">
              <el-input
                v-model="registerForm.smsCode"
                placeholder="请输入短信验证码"
                size="large"
                class="tech-input sms-input"
                maxlength="6"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Key /></el-icon>
                </template>
              </el-input>
              <el-button
                class="sms-button"
                :disabled="smsCooldown > 0 || !isPhoneValid"
                :loading="smsSending"
                @click="openCaptchaDialog"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s 后重发` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>
          
          <!-- 用户名 -->
          <el-form-item prop="username">
            <div class="input-wrapper">
              <el-input
                v-model="registerForm.username"
                placeholder="请设置用户名（3-20个字符）"
                size="large"
                class="tech-input"
              >
                <template #prefix>
                  <el-icon class="input-icon"><User /></el-icon>
                </template>
              </el-input>
            </div>
          </el-form-item>
          
          <!-- 邮箱 -->
          <el-form-item prop="email">
            <div class="input-wrapper">
              <el-input
                v-model="registerForm.email"
                placeholder="请输入邮箱地址"
                size="large"
                class="tech-input"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Message /></el-icon>
                </template>
              </el-input>
            </div>
          </el-form-item>
          
          <!-- 密码 -->
          <el-form-item prop="password">
            <div class="input-wrapper">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="请设置密码（至少6个字符）"
                size="large"
                class="tech-input"
                show-password
              >
                <template #prefix>
                  <el-icon class="input-icon"><Lock /></el-icon>
                </template>
              </el-input>
            </div>
          </el-form-item>
          
          <!-- 确认密码 -->
          <el-form-item prop="confirmPassword">
            <div class="input-wrapper">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="请再次输入密码"
                size="large"
                class="tech-input"
                show-password
              >
                <template #prefix>
                  <el-icon class="input-icon"><Lock /></el-icon>
                </template>
              </el-input>
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="register-button"
              :loading="loading"
              @click="handleRegister"
            >
              <span v-if="!loading">注册</span>
              <span v-else>注册中...</span>
              <el-icon v-if="!loading" class="button-icon"><Right /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="register-footer">
          <p class="footer-text">
            已有账户？
            <el-link type="primary" @click="goToLogin">立即登录</el-link>
          </p>
        </div>
      </div>
    </div>

    <!-- 安全验证弹窗 (只针对发短信) -->
    <el-dialog
      v-model="captchaDialogVisible"
      title="安全验证"
      width="340px"
      center
      :close-on-click-modal="false"
      class="captcha-dialog"
    >
      <div class="dialog-captcha-wrapper">
        <p class="dialog-captcha-tip">请完成下方图形验证以发送短信</p>
        <Captcha ref="dialogCaptchaRef" v-model="dialogCaptcha" @verify="handleDialogCaptchaVerify" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Message, Right, Iphone, Key } from '@element-plus/icons-vue'
import { authApi } from '@/utils/api'
import type { UserRole } from '@/types'
import Captcha from '@/components/Captcha.vue'

const router = useRouter()
const route = useRoute()
const registerFormRef = ref<FormInstance>()
const loading = ref(false)
const smsSending = ref(false)
const smsCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const captchaDialogVisible = ref(false)
const dialogCaptcha = ref('')
const dialogCaptchaRef = ref<InstanceType<typeof Captcha>>()

const isModal = computed(() => route.query.modal === 'true')

const registerForm = reactive({
  phone: '',
  smsCode: '',
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'user' as UserRole,
})

const openCaptchaDialog = () => {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入有效的11位手机号')
    return
  }
  dialogCaptcha.value = ''
  captchaDialogVisible.value = true
  setTimeout(() => {
    if (dialogCaptchaRef.value) dialogCaptchaRef.value.refresh()
  }, 100)
}

const handleDialogCaptchaVerify = (isValid: boolean) => {
  if (isValid) {
    captchaDialogVisible.value = false
    handleSendSms()
  }
}

// 手机号格式是否合法
const isPhoneValid = computed(() => {
  return /^1[3-9]\d{9}$/.test(registerForm.phone)
})

// ========== 验证规则 ==========
const validatePhone = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入手机号'))
  } else if (!/^1[3-9]\d{9}$/.test(value)) {
    callback(new Error('请输入有效的11位手机号'))
  } else {
    callback()
  }
}

const validateSmsCode = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入验证码'))
  } else if (value.length < 4) {
    callback(new Error('验证码格式不正确'))
  } else {
    callback()
  }
}

const validateUsername = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入用户名'))
  } else if (value.length < 3 || value.length > 20) {
    callback(new Error('用户名长度在3到20个字符'))
  } else if (!/^[a-zA-Z0-9_\u4e00-\u9fa5]+$/.test(value)) {
    callback(new Error('用户名只能包含字母、数字、下划线和中文'))
  } else {
    callback()
  }
}

const validateEmail = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入邮箱地址'))
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
    callback(new Error('请输入有效的邮箱地址'))
  } else {
    callback()
  }
}

const validatePassword = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入密码'))
  } else if (value.length < 6) {
    callback(new Error('密码长度至少6个字符'))
  } else {
    callback()
  }
}

const validateConfirmPassword = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  smsCode: [{ validator: validateSmsCode, trigger: 'blur' }],
  username: [{ validator: validateUsername, trigger: 'blur' }],
  email: [{ validator: validateEmail, trigger: 'blur' }],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
}

// ========== 发送验证码 ==========
const handleSendSms = async () => {
  if (!isPhoneValid.value) {
    ElMessage.warning('请先输入有效的手机号')
    return
  }
  
  smsSending.value = true
  try {
    await authApi.sendSms(registerForm.phone)
    ElMessage.success('验证码已发送，请注意查收短信')
    
    // 开始倒计时
    smsCooldown.value = 60
    cooldownTimer = setInterval(() => {
      smsCooldown.value--
      if (smsCooldown.value <= 0) {
        if (cooldownTimer) clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }, 1000)
  } catch (error: any) {
    console.error('发送验证码失败:', error)
  } finally {
    smsSending.value = false
  }
}

// ========== 注册 ==========
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const success = await authApi.register({
          phone: registerForm.phone,
          sms_code: registerForm.smsCode,
          username: registerForm.username,
          email: registerForm.email,
          password: registerForm.password,
          role: registerForm.role
        })
        
        if (success) {
          ElMessage.success('注册成功！请登录')
          if (isModal.value) {
            router.push({ path: '/login', query: { modal: 'true' }})
          } else {
            router.push('/login')
          }
        }
      } catch (error: any) {
        console.error('注册失败:', error)
      } finally {
        loading.value = false
      }
    }
  })
}

const goToLogin = () => {
  if (isModal.value) {
    router.push({ path: '/login', query: { modal: 'true' }})
  } else {
    router.push('/login')
  }
}
</script>

<style lang="scss" scoped>
.login-container, .admin-login-container, .register-container {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  font-family: 'SF Pro Text', 'SF Pro Display', system-ui, -apple-system, sans-serif;
  color: #1d1d1f;
  padding: 20px 0;
  box-sizing: border-box;
}

.login-container.is-modal, .register-container.is-modal {
  background: #ffffff;
  padding: 24px 32px;
}

.login-wrapper, .admin-login-wrapper, .register-wrapper {
  position: relative;
  z-index: 10;
  width: 90%;
  max-width: 400px;
  background: #ffffff;
  border-radius: 8px;
  border: none;
  box-shadow: none;
  margin: 0;
  padding: 32px;
  box-sizing: border-box;
}

.register-container.is-modal .register-wrapper {
  box-shadow: none;
  border: none;
  width: 100%;
  max-width: 100%;
  padding: 0;
}

/* 头部重置 */
.login-header, .admin-login-header, .register-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title, .admin-title, .register-title {
  font-family: 'SF Pro Display', system-ui, sans-serif;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.196px;
  color: #1d1d1f;
  margin: 0;
  text-align: center;
  line-height: 1.14;
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

/* 短信验证码行 */
.sms-code-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.sms-input {
  flex: 1;
}

.sms-button {
  flex-shrink: 0;
  height: 44px;
  min-width: 120px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 11px !important;
  border: 3px solid rgba(0, 0, 0, 0.04) !important;
  background: #fafafc !important;
  color: #0071e3 !important;
  transition: all 0.2s;
  
  &:hover:not(:disabled) {
    background: #ffffff !important;
    border-color: #0071e3 !important;
  }
  
  &:disabled, &.is-disabled {
    color: rgba(0, 0, 0, 0.3) !important;
    cursor: not-allowed;
  }
}

/* 输入框 Figma 主题覆写 */
.tech-input, .admin-input, .captcha-input {
  :deep(.el-input__wrapper) {
    background-color: #fafafc !important;
    border: 3px solid rgba(0, 0, 0, 0.04) !important;
    border-radius: 11px !important;
    box-shadow: none !important;
    padding: 0 14px !important;
    height: 44px;
    transition: all 0.2s;
    
    &.is-focus, &:hover {
      background-color: #ffffff !important;
    }
    
    &.is-focus {
      outline: 2px solid #0071e3 !important;
      outline-offset: 2px;
      border-color: transparent !important;
    }
  }

  :deep(.el-input__inner) {
    height: 44px !important;
    font-size: 17px !important;
    font-weight: 400;
    letter-spacing: -0.374px;
    color: #1d1d1f !important;
    &::placeholder {
      color: rgba(0, 0, 0, 0.4) !important;
    }
  }
}

.input-border { display: none !important; }

.input-icon { 
  color: #1d1d1f; 
  font-size: 18px; 
  opacity: 0.48; 
  margin-right: 4px;
}
:deep(.el-input__wrapper.is-focus) .input-icon { opacity: 1; }

/* 按钮 */
.login-button, .admin-login-button, .register-button {
  width: 100%;
  height: 44px;
  font-family: 'SF Pro Text', system-ui, sans-serif;
  font-size: 17px;
  font-weight: 400;
  letter-spacing: -0.374px;
  background: #0071e3 !important;
  border: 1px solid transparent !important;
  border-radius: 8px !important;
  color: #ffffff !important;
  margin-top: 16px; 
  transition: background-color 0.2s, transform 0.1s;
  
  &:hover {
    background: #0077ed !important;
    opacity: 1;
    transform: none;
  }
  
  &:active {
    background: #005bb5 !important;
  }
  
  &:focus-visible {
    outline: 2px solid #0071e3;
    outline-offset: 2px;
  }
}

.button-icon { margin-left: 8px; }

/* 尾部区域 */
.login-footer, .admin-login-footer, .register-footer {
  margin-top: 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.footer-text, .security-notice, .security-tips {
  font-size: 14px;
  font-weight: 400;
  letter-spacing: -0.224px;
  color: rgba(0, 0, 0, 0.48);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.footer-link, .back-link {
  font-size: 14px;
  letter-spacing: -0.224px;
  margin: 0;
  color: #1d1d1f;
}

:deep(.el-link) {
  color: #0066cc !important;
  font-weight: 400;
  text-decoration: none;
  &:hover { text-decoration: underline; opacity: 1; }
}

.minimal-background {
  display: none !important;
}

/* 步骤提示 */
.step-hint {
  width: 100%;
  padding: 8px 12px;
  margin-bottom: 10px;
  border-radius: 8px;
  background: #f5f5f7;
  font-size: 13px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.56);
  display: flex;
  align-items: center;
  gap: 6px;
  line-height: 1.4;
}

.step-hint-success {
  background: #f0faf0;
  color: #1a7f37;
}

.step-hint-icon {
  font-size: 14px;
  flex-shrink: 0;
}

/* 弹窗验证码 */
.dialog-captcha-wrapper {
  padding: 10px 0;
}
.dialog-captcha-tip {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin-top: 0;
  margin-bottom: 20px;
}
:deep(.captcha-dialog) {
  border-radius: 12px;
}
</style>
