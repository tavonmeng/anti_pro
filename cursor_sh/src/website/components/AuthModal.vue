<template>
  <Transition name="modal-fade">
    <div v-if="visible" class="auth-modal-overlay" @click.self="$emit('close')">
      <div class="auth-modal-container" :class="{ 'register-mode': activeTab === 'register' }">
        <!-- 关闭按钮 -->
        <button class="modal-close-btn" @click="$emit('close')">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>

        <!-- 标题 -->
        <div class="modal-header">
          <h2 class="modal-title">Unique Vision</h2>
        </div>

        <!-- Tab 切换 -->
        <div class="modal-tabs">
          <button class="modal-tab" :class="{ active: activeTab === 'login' }" @click="activeTab = 'login'">登录</button>
          <button class="modal-tab" :class="{ active: activeTab === 'register' }" @click="activeTab = 'register'">注册</button>
        </div>

        <!-- ===== 登录表单 ===== -->
        <div v-if="activeTab === 'login'" class="modal-body">
          <!-- 登录方式切换 -->
          <div class="login-mode-tabs">
            <button class="mode-tab" :class="{ active: loginMode === 'sms' }" @click="loginMode = 'sms'">验证码登录</button>
            <button class="mode-tab" :class="{ active: loginMode === 'password' }" @click="loginMode = 'password'">密码登录</button>
          </div>

          <!-- 密码登录 -->
          <el-form v-if="loginMode === 'password'" ref="loginFormRef" :model="loginForm" :rules="loginRules" @submit.prevent="handleLogin">
            <el-form-item prop="phone">
              <el-input v-model="loginForm.phone" placeholder="请输入手机号" size="large" class="modal-input" maxlength="11">
                <template #prefix><el-icon class="modal-icon"><Iphone /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" class="modal-input" show-password @keyup.enter="handleLogin">
                <template #prefix><el-icon class="modal-icon"><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item prop="captcha">
              <Captcha ref="captchaRef" v-model="loginForm.captcha" @verify="handleCaptchaVerify" />
            </el-form-item>
            <el-button type="primary" size="large" class="modal-submit-btn" :loading="loading" @click="handleLogin">
              {{ loading ? '登录中...' : '登录' }}
            </el-button>
          </el-form>

          <!-- 验证码登录 -->
          <el-form v-if="loginMode === 'sms'" ref="smsFormRef" :model="smsForm" :rules="smsRules" @submit.prevent="handleSmsLogin">
            <el-form-item prop="phone">
              <el-input v-model="smsForm.phone" placeholder="请输入手机号" size="large" class="modal-input" maxlength="11">
                <template #prefix><el-icon class="modal-icon"><Iphone /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item prop="smsCode">
              <div class="sms-row">
                <el-input v-model="smsForm.smsCode" placeholder="短信验证码" size="large" class="modal-input sms-input" maxlength="6" @keyup.enter="handleSmsLogin">
                  <template #prefix><el-icon class="modal-icon"><Key /></el-icon></template>
                </el-input>
                <el-button class="sms-send-btn" :disabled="smsCooldown > 0 || !isSmsPhoneValid" :loading="smsSending" @click="openCaptchaDialog('login')">
                  {{ smsCooldown > 0 ? `${smsCooldown}s` : '发送验证码' }}
                </el-button>
              </div>
            </el-form-item>
            <el-button type="primary" size="large" class="modal-submit-btn" :loading="loading" @click="handleSmsLogin">
              {{ loading ? '登录中...' : '登录' }}
            </el-button>
          </el-form>
        </div>

        <!-- ===== 注册表单 ===== -->
        <div v-if="activeTab === 'register'" class="modal-body">
          <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" @submit.prevent="handleRegister">
            <el-form-item prop="phone">
              <el-input v-model="registerForm.phone" placeholder="请输入手机号" size="large" class="modal-input" maxlength="11">
                <template #prefix><el-icon class="modal-icon"><Iphone /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item prop="smsCode">
              <div class="sms-row">
                <el-input v-model="registerForm.smsCode" placeholder="短信验证码" size="large" class="modal-input sms-input" maxlength="6">
                  <template #prefix><el-icon class="modal-icon"><Key /></el-icon></template>
                </el-input>
                <el-button class="sms-send-btn" :disabled="regSmsCooldown > 0 || !isRegPhoneValid" :loading="regSmsSending" @click="openCaptchaDialog('register')">
                  {{ regSmsCooldown > 0 ? `${regSmsCooldown}s` : '发送验证码' }}
                </el-button>
              </div>
            </el-form-item>
            <el-form-item prop="username">
              <el-input v-model="registerForm.username" placeholder="请设置用户名（3-20个字符）" size="large" class="modal-input">
                <template #prefix><el-icon class="modal-icon"><User /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item prop="email">
              <el-input v-model="registerForm.email" placeholder="请输入邮箱" size="large" class="modal-input">
                <template #prefix><el-icon class="modal-icon"><Message /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="请设置密码（至少6位）" size="large" class="modal-input" show-password>
                <template #prefix><el-icon class="modal-icon"><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item prop="confirmPassword">
              <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码" size="large" class="modal-input" show-password @keyup.enter="handleRegister">
                <template #prefix><el-icon class="modal-icon"><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-button type="primary" size="large" class="modal-submit-btn" :loading="loading" @click="handleRegister">
              {{ loading ? '注册中...' : '注册' }}
            </el-button>
          </el-form>
        </div>

        <!-- 安全验证弹窗 -->
        <el-dialog v-model="captchaDialogVisible" title="安全验证" width="340px" center :close-on-click-modal="false" class="captcha-dialog" append-to-body>
          <div style="padding: 10px 0; text-align: center;">
            <p style="font-size: 14px; color: #666; margin-bottom: 20px;">请完成下方图形验证以发送短信</p>
            <Captcha ref="dialogCaptchaRef" v-model="dialogCaptcha" @verify="handleDialogCaptchaVerify" />
          </div>
        </el-dialog>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Lock, Iphone, Key, User, Message } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/utils/api'
import type { UserRole } from '@/types'
import Captcha from '@/components/Captcha.vue'

const props = defineProps<{ visible: boolean, initialTab?: 'login' | 'register' }>()
const emit = defineEmits(['close'])

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const activeTab = ref<'login' | 'register'>('login')

// 当弹窗打开时，同步 initialTab
watch(() => props.visible, (v) => {
  if (v && props.initialTab) activeTab.value = props.initialTab
})

// ========== 密码登录 ==========
const loginMode = ref<'password' | 'sms'>('sms')
const loginFormRef = ref<FormInstance>()
const captchaValid = ref(false)
const captchaRef = ref<InstanceType<typeof Captcha>>()

const loginForm = reactive({ phone: '', password: '', role: 'user' as UserRole, captcha: '' })
const loginRules: FormRules = {
  phone: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || !/^1[3-9]\d{9}$/.test(v)) cb(new Error('请输入有效的11位手机号')); else cb() }, trigger: 'blur' }],
  password: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 6) cb(new Error('密码长度至少6个字符')); else cb() }, trigger: 'blur' }],
  captcha: [{ validator: (_r: any, _v: string, cb: Function) => { if (!captchaValid.value) cb(new Error('请完成验证码')); else cb() }, trigger: 'blur' }]
}
const handleCaptchaVerify = (isValid: boolean) => { captchaValid.value = isValid; loginFormRef.value?.validateField('captcha') }

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      if (!captchaValid.value) { ElMessage.error('请先通过验证码验证'); captchaRef.value?.refresh(); return }
      loading.value = true
      try {
        const success = await authStore.login({ phone: loginForm.phone, password: loginForm.password, role: loginForm.role })
        if (success) handleLoginSuccess()
      } catch (error: any) {
        if (error?.message?.includes('尚未注册')) {
          ElMessageBox.confirm('该手机号尚未注册，是否去注册？', '提示', { confirmButtonText: '去注册', cancelButtonText: '取消', type: 'warning', center: true })
            .then(() => { activeTab.value = 'register' }).catch(() => {})
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
const smsForm = reactive({ phone: '', smsCode: '', role: 'user' as UserRole })
const isSmsPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(smsForm.phone))
const smsRules: FormRules = {
  phone: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || !/^1[3-9]\d{9}$/.test(v)) cb(new Error('请输入有效的11位手机号')); else cb() }, trigger: 'blur' }],
  smsCode: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 4) cb(new Error('请输入验证码')); else cb() }, trigger: 'blur' }],
}

const handleSmsLogin = async () => {
  if (!smsFormRef.value) return
  await smsFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const success = await authStore.login({ phone: smsForm.phone, sms_code: smsForm.smsCode, role: smsForm.role })
        if (success) handleLoginSuccess()
      } catch (error: any) {
        if (error?.message?.includes('尚未注册')) {
          ElMessageBox.confirm('该手机号尚未注册，是否去注册？', '提示', { confirmButtonText: '去注册', cancelButtonText: '取消', type: 'warning', center: true })
            .then(() => { activeTab.value = 'register' }).catch(() => {})
        }
      } finally { loading.value = false }
    }
  })
}

// ========== 注册 ==========
const registerFormRef = ref<FormInstance>()
const regSmsSending = ref(false)
const regSmsCooldown = ref(0)
const isRegPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(registerForm.phone))

const registerForm = reactive({ phone: '', smsCode: '', username: '', email: '', password: '', confirmPassword: '', role: 'user' as UserRole })
const registerRules: FormRules = {
  phone: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || !/^1[3-9]\d{9}$/.test(v)) cb(new Error('请输入有效的11位手机号')); else cb() }, trigger: 'blur' }],
  smsCode: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 4) cb(new Error('请输入验证码')); else cb() }, trigger: 'blur' }],
  username: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 3 || v.length > 20) cb(new Error('用户名长度3-20个字符')); else cb() }, trigger: 'blur' }],
  email: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) cb(new Error('请输入有效的邮箱')); else cb() }, trigger: 'blur' }],
  password: [{ validator: (_r: any, v: string, cb: Function) => { if (!v || v.length < 6) cb(new Error('密码至少6个字符')); else cb() }, trigger: 'blur' }],
  confirmPassword: [{ validator: (_r: any, v: string, cb: Function) => { if (!v) cb(new Error('请再次输入密码')); else if (v !== registerForm.password) cb(new Error('两次密码不一致')); else cb() }, trigger: 'blur' }],
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const success = await authApi.register({
          phone: registerForm.phone, sms_code: registerForm.smsCode,
          username: registerForm.username, email: registerForm.email,
          password: registerForm.password, role: registerForm.role
        })
        if (success) {
          ElMessage.success('注册成功！请登录')
          activeTab.value = 'login'
          loginMode.value = 'sms'
          smsForm.phone = registerForm.phone
        }
      } catch (error: any) {
        if (error?.message?.includes('已注册')) {
          ElMessageBox.confirm('该手机号已注册，是否去登录？', '提示', { confirmButtonText: '去登录', cancelButtonText: '取消', type: 'info', center: true })
            .then(() => { activeTab.value = 'login' }).catch(() => {})
        }
      } finally { loading.value = false }
    }
  })
}

// ========== 公共：弹窗图形验证 + 发送短信 ==========
const captchaDialogVisible = ref(false)
const currentCaptchaScene = ref<'login' | 'register'>('login')
const dialogCaptcha = ref('')
const dialogCaptchaRef = ref<InstanceType<typeof Captcha>>()

const openCaptchaDialog = (scene: 'login' | 'register') => {
  const phone = scene === 'login' ? smsForm.phone : registerForm.phone
  if (!phone || !/^1[3-9]\d{9}$/.test(phone)) { ElMessage.warning('请输入有效的11位手机号'); return }
  currentCaptchaScene.value = scene
  dialogCaptcha.value = ''
  captchaDialogVisible.value = true
  setTimeout(() => { dialogCaptchaRef.value?.refresh() }, 100)
}

const handleDialogCaptchaVerify = (isValid: boolean) => {
  if (isValid) { captchaDialogVisible.value = false; handleSendSms(currentCaptchaScene.value) }
}

const handleSendSms = async (scene: 'login' | 'register') => {
  const phone = scene === 'login' ? smsForm.phone : registerForm.phone
  const sendingRef = scene === 'login' ? smsSending : regSmsSending
  sendingRef.value = true
  try {
    await authApi.sendSms(phone)
    ElMessage.success('验证码已发送')
    const cooldownRef = scene === 'login' ? smsCooldown : regSmsCooldown
    cooldownRef.value = 60
    const timer = setInterval(() => { cooldownRef.value--; if (cooldownRef.value <= 0) clearInterval(timer) }, 1000)
  } catch (e) { console.error('发送验证码失败:', e) }
  finally { sendingRef.value = false }
}

// ========== 登录成功 ==========
function handleLoginSuccess() {
  emit('close')
  if (authStore.isAdmin()) router.push('/admin')
  else if (authStore.isStaff()) router.push('/staff')
  else router.push('/user/workspace')
}
</script>

<style scoped>
/* 遮罩层 */
.auth-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'SF Pro Text', 'SF Pro Display', system-ui, -apple-system, sans-serif;
}

/* 弹窗容器 */
.auth-modal-container {
  position: relative;
  background: #ffffff;
  border-radius: 16px;
  width: 90%;
  max-width: 420px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 36px 32px 28px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.25);
  animation: modal-pop 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.auth-modal-container.register-mode {
  max-width: 440px;
}

@keyframes modal-pop {
  from { opacity: 0; transform: scale(0.92) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* 关闭按钮 */
.modal-close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: #f5f5f7;
  color: #86868b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.modal-close-btn:hover { background: #e8e8ed; color: #1d1d1f; }

/* 标题 */
.modal-header { text-align: center; margin-bottom: 20px; }
.modal-title {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: 0.196px;
  margin: 0;
}

/* Tab */
.modal-tabs {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-bottom: 24px;
  background: #f5f5f7;
  border-radius: 8px;
  padding: 3px;
}
.modal-tab {
  flex: 1;
  padding: 8px 0;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: #86868b;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.25s;
}
.modal-tab.active {
  background: #ffffff;
  color: #1d1d1f;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

/* 登录方式 Tab */
.login-mode-tabs {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  justify-content: center;
}
.mode-tab {
  border: none;
  background: none;
  font-size: 13px;
  color: #86868b;
  cursor: pointer;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.mode-tab.active {
  color: #1d1d1f;
  border-bottom-color: #0071e3;
}

/* 输入框 */
.modal-input :deep(.el-input__wrapper) {
  background: #fafafc !important;
  border: 2px solid rgba(0,0,0,0.04) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  padding: 0 14px !important;
  height: 44px;
  transition: all 0.2s;
}
.modal-input :deep(.el-input__wrapper.is-focus) {
  background: #fff !important;
  border-color: #0071e3 !important;
}
.modal-input :deep(.el-input__inner) {
  height: 44px !important;
  font-size: 15px !important;
  color: #1d1d1f !important;
}
.modal-input :deep(.el-input__inner::placeholder) { color: rgba(0,0,0,0.35) !important; }
.modal-icon { color: #86868b; font-size: 16px; }

/* 短信验证码行 */
.sms-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.sms-input { flex: 1; }
.sms-send-btn {
  flex-shrink: 0;
  height: 44px;
  min-width: 110px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 10px !important;
  border: 2px solid rgba(0,0,0,0.04) !important;
  background: #fafafc !important;
  color: #0071e3 !important;
}
.sms-send-btn:hover:not(:disabled) { background: #fff !important; border-color: #0071e3 !important; }
.sms-send-btn:disabled { color: rgba(0,0,0,0.25) !important; }

/* 提交按钮 */
.modal-submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  background: #0071e3 !important;
  border: none !important;
  border-radius: 10px !important;
  color: #fff !important;
  margin-top: 8px;
  transition: background 0.2s;
}
.modal-submit-btn:hover { background: #0077ed !important; }
.modal-submit-btn:active { background: #005bb5 !important; }

/* Form spacing */
.modal-body :deep(.el-form-item) { margin-bottom: 14px !important; }
.modal-body :deep(.el-form-item__content) { line-height: normal !important; }

/* 过渡动画 */
.modal-fade-enter-active { transition: opacity 0.3s ease; }
.modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

/* 滚动条 */
.auth-modal-container::-webkit-scrollbar { width: 4px; }
.auth-modal-container::-webkit-scrollbar-thumb { background: #d2d2d7; border-radius: 2px; }
</style>

<!-- 全局样式：确保 ElMessage / ElMessageBox 显示在弹窗之上 -->
<style>
.el-message {
  z-index: 6001 !important;
}
.el-overlay {
  z-index: 5500 !important;
}
.el-message-box {
  z-index: 5501 !important;
}
</style>
