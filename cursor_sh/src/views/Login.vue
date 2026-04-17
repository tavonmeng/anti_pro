<template>
  <div class="login-container" :class="{ 'is-modal': isModal }">
    <div class="minimal-background" v-if="!isModal"></div>

    <div class="login-wrapper">
      <div>
        <div class="login-header">
          <h1 class="login-title">Unique Vision 系统</h1>
        </div>

        <!-- 登录方式切换 -->
        <div class="login-tabs" v-if="currentView === 'login'">
          <button class="tab-btn" :class="{ active: loginMode === 'password' }" @click="loginMode = 'password'">密码登录</button>
          <button class="tab-btn" :class="{ active: loginMode === 'sms' }" @click="loginMode = 'sms'">验证码登录</button>
        </div>
        
        <!-- ========== 密码登录 ========== -->
        <el-form
          v-if="currentView === 'login' && loginMode === 'password'"
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="phone">
            <div class="input-wrapper">
              <el-input v-model="loginForm.phone" placeholder="请输入手机号" size="large" class="tech-input" maxlength="11">
                <template #prefix><el-icon class="input-icon"><Iphone /></el-icon></template>
              </el-input>
            </div>
          </el-form-item>
          
          <el-form-item prop="password">
            <div class="input-wrapper">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" class="tech-input" show-password @keyup.enter="handleLogin">
                <template #prefix><el-icon class="input-icon"><Lock /></el-icon></template>
              </el-input>
            </div>
          </el-form-item>
          
          <el-form-item prop="captcha">
            <Captcha ref="captchaRef" v-model="loginForm.captcha" @verify="handleCaptchaVerify" />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" size="large" class="login-button" :loading="loading" @click="handleLogin">
              <span v-if="!loading">登录</span>
              <span v-else>登录中...</span>
              <el-icon v-if="!loading" class="button-icon"><Right /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>

        <!-- ========== 验证码登录 ========== -->
        <el-form
          v-if="currentView === 'login' && loginMode === 'sms'"
          ref="smsFormRef"
          :model="smsForm"
          :rules="smsRules"
          class="login-form"
          @submit.prevent="handleSmsLogin"
        >
          <el-form-item prop="phone">
            <div class="input-wrapper">
              <el-input v-model="smsForm.phone" placeholder="请输入手机号" size="large" class="tech-input" maxlength="11">
                <template #prefix><el-icon class="input-icon"><Iphone /></el-icon></template>
              </el-input>
            </div>
          </el-form-item>


          <!-- 短信验证码（常驻显示） -->
          <el-form-item prop="smsCode">
            <div class="step-hint step-hint-success" v-if="smsCooldown > 0">
              <span class="step-hint-icon">✅</span>
              验证码已发送至 {{ smsForm.phone.slice(0,3) }}****{{ smsForm.phone.slice(7) }}
            </div>
            <div class="sms-code-row">
              <el-input v-model="smsForm.smsCode" placeholder="请输入短信验证码" size="large" class="tech-input sms-input" maxlength="6" @keyup.enter="handleSmsLogin">
                <template #prefix><el-icon class="input-icon"><Key /></el-icon></template>
              </el-input>
              <el-button class="sms-button" :disabled="smsCooldown > 0 || !isSmsPhoneValid" :loading="smsSending" @click="openCaptchaDialog('login')">
                {{ smsCooldown > 0 ? `${smsCooldown}s` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" size="large" class="login-button" :loading="loading" @click="handleSmsLogin">
              <span v-if="!loading">登录</span>
              <span v-else>登录中...</span>
              <el-icon v-if="!loading" class="button-icon"><Right /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>

        <!-- ========== 忘记密码 ========== -->
        <el-form
          v-if="currentView === 'reset'"
          ref="resetFormRef"
          :model="resetForm"
          :rules="resetRules"
          class="login-form"
          @submit.prevent="handleResetPassword"
        >
          <div class="reset-header">
            <h2 class="reset-title">重置密码</h2>
            <p class="reset-desc">通过手机号验证码重置密码</p>
          </div>

          <el-form-item prop="phone">
            <div class="input-wrapper">
              <el-input v-model="resetForm.phone" placeholder="请输入手机号" size="large" class="tech-input" maxlength="11">
                <template #prefix><el-icon class="input-icon"><Iphone /></el-icon></template>
              </el-input>
            </div>
          </el-form-item>

          <!-- 短信验证码（常驻显示） -->
          <el-form-item prop="smsCode">
            <div class="step-hint step-hint-success" v-if="resetCooldown > 0">
              <span class="step-hint-icon">✅</span>
              验证码已发送至 {{ resetForm.phone.slice(0,3) }}****{{ resetForm.phone.slice(7) }}
            </div>
            <div class="sms-code-row">
              <el-input v-model="resetForm.smsCode" placeholder="请输入短信验证码" size="large" class="tech-input sms-input" maxlength="6">
                <template #prefix><el-icon class="input-icon"><Key /></el-icon></template>
              </el-input>
              <el-button class="sms-button" :disabled="resetCooldown > 0 || !isResetPhoneValid" :loading="resetSmsSending" @click="openCaptchaDialog('reset')">
                {{ resetCooldown > 0 ? `${resetCooldown}s` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <!-- 新密码 -->
          <el-form-item prop="newPassword">
            <div class="input-wrapper">
              <el-input v-model="resetForm.newPassword" type="password" placeholder="请设置新密码（至少6位）" size="large" class="tech-input" show-password>
                <template #prefix><el-icon class="input-icon"><Lock /></el-icon></template>
              </el-input>
            </div>
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <div class="input-wrapper">
              <el-input v-model="resetForm.confirmPassword" type="password" placeholder="请再次输入新密码" size="large" class="tech-input" show-password @keyup.enter="handleResetPassword">
                <template #prefix><el-icon class="input-icon"><Lock /></el-icon></template>
              </el-input>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" size="large" class="login-button" :loading="loading" @click="handleResetPassword">
              <span v-if="!loading">重置密码</span>
              <span v-else>重置中...</span>
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="login-footer">
          <p class="footer-text" v-if="currentView === 'login'">
            <el-link type="primary" @click="currentView = 'reset'">忘记密码？</el-link>
          </p>
          <p class="footer-text" v-if="currentView === 'reset'">
            <el-link type="primary" @click="currentView = 'login'">← 返回登录</el-link>
          </p>
          <p class="footer-link" v-if="currentView === 'login'">
            还没有账户？
            <el-link type="primary" @click="goToRegister">立即注册</el-link>
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
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Lock, Right, InfoFilled, Iphone, Key } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/utils/api'
import type { UserRole } from '@/types'
import Captcha from '@/components/Captcha.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isModal = computed(() => route.query.modal === 'true')
const loading = ref(false)

// ========== 视图切换 ==========
const currentView = ref<'login' | 'reset'>('login')
const loginMode = ref<'password' | 'sms'>('sms')

// ========== 密码登录 ==========
const loginFormRef = ref<FormInstance>()
const captchaValid = ref(false)
const captchaRef = ref<InstanceType<typeof Captcha>>()

const loginForm = reactive({
  phone: '',
  password: '',
  role: 'user' as UserRole,
  captcha: ''
})

const loginRules: FormRules = {
  phone: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || !/^1[3-9]\d{9}$/.test(v)) cb(new Error('请输入有效的11位手机号')); else cb() }, trigger: 'blur' }],
  password: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 6) cb(new Error('密码长度至少6个字符')); else cb() }, trigger: 'blur' }],
  captcha: [{ validator: (_r: any, v: string, cb: Function) => { if (!v) cb(new Error('请输入验证码')); else if (!captchaValid.value) cb(new Error('验证码错误')); else cb() }, trigger: 'blur' }]
}

const handleCaptchaVerify = (isValid: boolean) => {
  captchaValid.value = isValid
  if (loginFormRef.value) loginFormRef.value.validateField('captcha')
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      if (!captchaValid.value) {
        ElMessage.error('请先通过验证码验证')
        captchaRef.value?.refresh()
        return
      }
      loading.value = true
      try {
        const success = await authStore.login({
          phone: loginForm.phone,
          password: loginForm.password,
          role: loginForm.role,
        })
        if (success) handleLoginSuccess()
      } catch (error: any) { 
        if (error?.message && (error.message.includes('尚未注册') || error.message.includes('不存在'))) {
          ElMessageBox.confirm(
            '该手机号尚未注册，是否直接去注册？',
            '提示',
            {
              confirmButtonText: '去注册',
              cancelButtonText: '再看看',
              type: 'warning',
              center: true
            }
          ).then(() => {
            goToRegister()
          }).catch(() => {})
        }
        captchaRef.value?.refresh(); loginForm.captcha = ''; captchaValid.value = false
      } finally { loading.value = false }
    }
  })
}

// ========== 验证码登录 ==========
const smsFormRef = ref<FormInstance>()
const smsSending = ref(false)
const smsCooldown = ref(0)
let smsCooldownTimer: ReturnType<typeof setInterval> | null = null

const smsForm = reactive({
  phone: '',
  smsCode: '',
  role: 'user' as UserRole,
})

const isSmsPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(smsForm.phone))

const smsRules: FormRules = {
  phone: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || !/^1[3-9]\d{9}$/.test(v)) cb(new Error('请输入有效的11位手机号')); else cb() }, trigger: 'blur' }],
  smsCode: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 4) cb(new Error('请输入验证码')); else cb() }, trigger: 'blur' }],
}

const handleSmsCaptchaVerify = (isValid: boolean) => {
  smsCaptchaValid.value = isValid
  if (isValid && isSmsPhoneValid.value) handleSendSms('login')
}

const handleSmsLogin = async () => {
  if (!smsFormRef.value) return
  await smsFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const success = await authStore.login({
          phone: smsForm.phone,
          sms_code: smsForm.smsCode,
          role: smsForm.role,
        })
        if (success) handleLoginSuccess()
      } catch (error: any) { 
        if (error?.message && error.message.includes('尚未注册')) {
          ElMessageBox.confirm(
            '该手机号尚未注册，是否直接去注册？',
            '提示',
            {
              confirmButtonText: '去注册',
              cancelButtonText: '再看看',
              type: 'warning',
              center: true
            }
          ).then(() => {
            goToRegister()
          }).catch(() => {})
        } else {
          console.error('登录失败:', error)
        }
      } finally { loading.value = false }
    }
  })
}

// ========== 忘记密码 ==========
const resetFormRef = ref<FormInstance>()
const resetSmsSending = ref(false)
const resetCooldown = ref(0)
let resetCooldownTimer: ReturnType<typeof setInterval> | null = null

const resetForm = reactive({
  phone: '',
  smsCode: '',
  newPassword: '',
  confirmPassword: '',
})

const isResetPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(resetForm.phone))

const resetRules: FormRules = {
  phone: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || !/^1[3-9]\d{9}$/.test(v)) cb(new Error('请输入有效的11位手机号')); else cb() }, trigger: 'blur' }],
  smsCode: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 4) cb(new Error('请输入验证码')); else cb() }, trigger: 'blur' }],
  newPassword: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 6) cb(new Error('密码长度至少6个字符')); else cb() }, trigger: 'blur' }],
  confirmPassword: [{ validator: (_r: any, v: string, cb: Function) => { if (!v) cb(new Error('请再次输入密码')); else if (v !== resetForm.newPassword) cb(new Error('两次输入的密码不一致')); else cb() }, trigger: 'blur' }],
}

const handleResetPassword = async () => {
  if (!resetFormRef.value) return
  await resetFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authApi.resetPassword(resetForm.phone, resetForm.smsCode, resetForm.newPassword)
        ElMessage.success('密码重置成功！请登录')
        currentView.value = 'login'
        loginMode.value = 'sms'
        loginForm.phone = resetForm.phone
        // 清理 reset 表单
        resetForm.phone = ''
        resetForm.smsCode = ''
        resetForm.newPassword = ''
        resetForm.confirmPassword = ''
        resetCaptchaValid.value = false
      } catch (e: any) { console.error('密码重置失败:', e)
      } finally { loading.value = false }
    }
  })
}

// ========== 公共：弹窗图形验证与发送短信 ==========
const captchaDialogVisible = ref(false)
const currentCaptchaScene = ref<'login' | 'reset'>('login')
const dialogCaptcha = ref('')
const dialogCaptchaRef = ref<InstanceType<typeof Captcha>>()

const openCaptchaDialog = (scene: 'login' | 'reset') => {
  const phone = scene === 'login' ? smsForm.phone : resetForm.phone
  if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
    ElMessage.warning('请输入有效的11位手机号')
    return
  }
  currentCaptchaScene.value = scene
  dialogCaptcha.value = ''
  captchaDialogVisible.value = true
  // dialog 出现后再刷新验证码
  setTimeout(() => {
    if (dialogCaptchaRef.value) dialogCaptchaRef.value.refresh()
  }, 100)
}

const handleDialogCaptchaVerify = (isValid: boolean) => {
  if (isValid) {
    captchaDialogVisible.value = false
    handleSendSms(currentCaptchaScene.value)
  }
}

const handleSendSms = async (scene: 'login' | 'reset') => {
  const phone = scene === 'login' ? smsForm.phone : resetForm.phone
  if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
    ElMessage.warning('请先输入有效的手机号')
    return
  }
  
  const sendingRef = scene === 'login' ? smsSending : resetSmsSending
  sendingRef.value = true
  
  try {
    await authApi.sendSms(phone)
    ElMessage.success('验证码已发送，请注意查收短信')
    
    // 启动倒计时
    const cooldownRef = scene === 'login' ? smsCooldown : resetCooldown
    cooldownRef.value = 60
    const timer = setInterval(() => {
      cooldownRef.value--
      if (cooldownRef.value <= 0) clearInterval(timer)
    }, 1000)
    if (scene === 'login') smsCooldownTimer = timer
    else resetCooldownTimer = timer
  } catch (e: any) { console.error('发送验证码失败:', e)
  } finally { sendingRef.value = false }
}

// ========== 公共方法 ==========
function handleLoginSuccess() {
  if (authStore.isUser()) {
    if (isModal.value) {
      window.parent.postMessage({ type: 'LOGIN_SUCCESS' }, '*')
    } else {
      const redirect = router.currentRoute.value.query.redirect as string || undefined
      router.push(redirect || '/user/workspace')
    }
  } else {
    ElMessage.error('请使用管理员登录入口')
    authStore.logout()
  }
}

const goToRegister = () => {
  if (isModal.value) {
    router.push({ path: '/register', query: { modal: 'true' }})
  } else {
    router.push('/register')
  }
}
</script>

<style lang="scss" scoped>
.login-container {
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

.login-container.is-modal {
  background: #ffffff;
  padding: 24px 32px;
}

.login-wrapper {
  position: relative;
  z-index: 10;
  width: 90%;
  max-width: 400px;
  background: #ffffff;
  border-radius: 8px;
  padding: 32px;
  box-sizing: border-box;
}

.login-container.is-modal .login-wrapper {
  width: 100%;
  max-width: 100%;
  padding: 0;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.login-title {
  font-family: 'SF Pro Display', system-ui, sans-serif;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.196px;
  color: #1d1d1f;
  margin: 0;
  line-height: 1.14;
}

/* 重置密码头部 */
.reset-header {
  text-align: center;
  margin-bottom: 20px;
}
.reset-title {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 6px 0;
}
.reset-desc {
  font-size: 14px;
  color: rgba(0,0,0,0.45);
  margin: 0;
}

/* 登录切换标签 */
.login-tabs {
  display: flex;
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.tab-btn {
  flex: 1;
  padding: 10px 0;
  font-size: 15px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.4);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  &:hover { color: rgba(0, 0, 0, 0.7); }
  &.active { color: #0071e3; border-bottom-color: #0071e3; }
}

/* 表单 */
.login-form {  width: 100%; display: flex; flex-direction: column; gap: 16px; }
:deep(.el-form-item) { margin-bottom: 0 !important; width: 100%; }
:deep(.el-form-item__content) { line-height: normal !important; }
.input-wrapper { width: 100%; }

/* 短信验证码行 */
.sms-code-row { display: flex; gap: 10px; width: 100%; }
.sms-input { flex: 1; }

.sms-button {
  flex-shrink: 0; height: 44px; min-width: 120px;
  font-size: 14px; font-weight: 500;
  border-radius: 11px !important;
  border: 3px solid rgba(0, 0, 0, 0.04) !important;
  background: #fafafc !important; color: #0071e3 !important;
  transition: all 0.2s;
  &:hover:not(:disabled) { background: #ffffff !important; border-color: #0071e3 !important; }
  &:disabled, &.is-disabled { color: rgba(0, 0, 0, 0.3) !important; cursor: not-allowed; }
}

/* 输入框 */
.tech-input {
  :deep(.el-input__wrapper) {
    background-color: #fafafc !important;
    border: 3px solid rgba(0, 0, 0, 0.04) !important;
    border-radius: 11px !important; box-shadow: none !important;
    padding: 0 14px !important; height: 44px; transition: all 0.2s;
    &.is-focus, &:hover { background-color: #ffffff !important; }
    &.is-focus { outline: 2px solid #0071e3 !important; outline-offset: 2px; border-color: transparent !important; }
  }
  :deep(.el-input__inner) {
    height: 44px !important; font-size: 17px !important;
    font-weight: 400; letter-spacing: -0.374px; color: #1d1d1f !important;
    &::placeholder { color: rgba(0, 0, 0, 0.4) !important; }
  }
}

.input-icon { color: #1d1d1f; font-size: 18px; opacity: 0.48; margin-right: 4px; }
:deep(.el-input__wrapper.is-focus) .input-icon { opacity: 1; }

/* 按钮 */
.login-button {
  width: 100%; height: 44px;
  font-family: 'SF Pro Text', system-ui, sans-serif;
  font-size: 17px; font-weight: 400; letter-spacing: -0.374px;
  background: #0071e3 !important; border: 1px solid transparent !important;
  border-radius: 8px !important; color: #ffffff !important;
  margin-top: 16px; transition: background-color 0.2s, transform 0.1s;
  &:hover { background: #0077ed !important; }
  &:active { background: #005bb5 !important; }
  &:focus-visible { outline: 2px solid #0071e3; outline-offset: 2px; }
}
.button-icon { margin-left: 8px; }

/* 尾部 */
.login-footer { margin-top: 32px; text-align: center; display: flex; flex-direction: column; gap: 12px; }
.footer-text { font-size: 14px; color: rgba(0,0,0,0.48); margin: 0; display: flex; align-items: center; justify-content: center; gap: 6px; }
.footer-link { font-size: 14px; margin: 0; color: #1d1d1f; }
:deep(.el-link) { color: #0066cc !important; font-weight: 400; text-decoration: none; &:hover { text-decoration: underline; opacity: 1; } }

/* 验证码 */
.captcha-container { display: flex; gap: 12px; align-items: center; width: 100%; }
.captcha-display { border-radius: 8px; overflow: hidden; height: 44px; border: 1px solid rgba(0,0,0,0.08); }
.captcha-display canvas { height: 100% !important; display: block; }
.captcha-input { flex: 1; }

.minimal-background { display: none !important; }

/* 步骤提示 */
.step-hint {
  width: 100%; padding: 8px 12px; margin-bottom: 10px;
  border-radius: 8px; background: #f5f5f7;
  font-size: 13px; font-weight: 500; color: rgba(0,0,0,0.56);
  display: flex; align-items: center; gap: 6px; line-height: 1.4;
}
.step-hint-success { background: #f0faf0; color: #1a7f37; }
.step-hint-icon { font-size: 14px; flex-shrink: 0; }

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
