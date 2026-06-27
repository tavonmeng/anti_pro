<template>
  <div class="admin-login-container">
    <div ref="bookRef" class="admin-login-card" :style="{ '--step-accent': currentSlide.accent }">
      <section class="left-page-overlay">
        <div class="visual-stage">
          <transition name="workflow-fade">
            <div :key="currentSlide.key" class="workflow-visual">
              <img :src="currentSlide.image" :alt="currentSlide.title" />
              <div class="workflow-label">
                <span>{{ currentSlide.number }}</span>
                <strong>{{ currentSlide.title }}</strong>
              </div>
            </div>
          </transition>
          <div class="slide-dots" aria-hidden="true">
            <span
              v-for="(slide, index) in businessSlides"
              :key="slide.key"
              :class="{ active: activeSlideIndex === index }"
            />
          </div>
        </div>
      </section>

      <section ref="portalRef" class="portal-panel">
        <div class="admin-login-header">
          <div class="portal-brand">
            <img src="/landing/logo/official-mark-black.svg" alt="Unique Vision" />
            <span>Unique Vision</span>
          </div>
          <h1 class="admin-title">管理员登录</h1>
          <div class="security-notice">
            <el-icon><Warning /></el-icon>
            <span>仅限授权内部人员访问</span>
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

          <el-form-item prop="captcha">
            <Captcha
              ref="captchaRef"
              v-model="smsForm.captcha"
              placeholder="输入字母验证码"
              @verify="handleCaptchaVerify"
            />
          </el-form-item>

          <el-form-item prop="smsCode">
            <div class="sms-row">
              <el-input
                v-model="smsForm.smsCode"
                placeholder="短信验证码"
                size="large"
                class="admin-input sms-input"
                maxlength="6"
                @keyup.enter="handleSmsLogin"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Message /></el-icon>
                </template>
              </el-input>
              <el-button
                class="sms-btn"
                :disabled="smsCooldown > 0 || !isSmsPhoneValid"
                :loading="smsSending"
                native-type="button"
                @click="handleSendSms"
              >
                {{ smsButtonText }}
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
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Warning, InfoFilled, Message } from '@element-plus/icons-vue'
import { gsap } from 'gsap'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/utils/api'
import { platformServices } from '@/data/platformServices'
import type { LoginRequest, UserRole } from '@/types'
import Captcha from '@/components/Captcha.vue'

const router = useRouter()
const authStore = useAuthStore()
const smsFormRef = ref<FormInstance>()
const captchaRef = ref<InstanceType<typeof Captcha>>()
const loading = ref(false)
const smsSending = ref(false)
const smsCooldown = ref(0)
const captchaValid = ref(false)
const activeSlideIndex = ref(0)
const bookRef = ref<HTMLElement>()
const portalRef = ref<HTMLElement>()
let smsCooldownTimer: ReturnType<typeof setInterval> | undefined
let slideTimer: ReturnType<typeof setInterval> | undefined

const slideAccents = ['#5d6f82', '#3fb8af', '#f0764f', '#7d3c98', '#566573', '#00796b']

const businessSlides = platformServices.map((service, index) => ({
  key: service.type,
  number: String(index + 1).padStart(2, '0'),
  title: service.title,
  image: service.image,
  accent: slideAccents[index] || '#34373d'
}))

const currentSlide = computed(() => businessSlides[activeSlideIndex.value])
const isSmsPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(smsForm.phone))
const smsButtonText = computed(() => {
  return smsCooldown.value > 0 ? `${smsCooldown.value}s` : '发送验证码'
})

const showNextSlide = () => {
  activeSlideIndex.value = (activeSlideIndex.value + 1) % businessSlides.length
}

const smsForm = reactive({
  phone: '',
  captcha: '',
  smsCode: ''
})

const validatePhone = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入管理员手机号'))
  } else if (!/^1[3-9]\d{9}$/.test(value)) {
    callback(new Error('请输入有效的11位手机号'))
  } else {
    callback()
  }
}

const validateCaptcha = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入字母验证码'))
  } else if (!captchaValid.value) {
    callback(new Error('字母验证码错误'))
  } else {
    callback()
  }
}

const validateSmsCode = (_rule: any, value: string, callback: Function) => {
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
  captcha: [{ validator: validateCaptcha, trigger: 'blur' }],
  smsCode: [{ validator: validateSmsCode, trigger: 'blur' }]
}

const handleCaptchaVerify = (isValid: boolean) => {
  captchaValid.value = isValid
  smsFormRef.value?.validateField('captcha')
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

const startSmsCooldown = () => {
  smsCooldown.value = 60
  if (smsCooldownTimer) clearInterval(smsCooldownTimer)
  smsCooldownTimer = setInterval(() => {
    smsCooldown.value--
    if (smsCooldown.value <= 0 && smsCooldownTimer) {
      clearInterval(smsCooldownTimer)
      smsCooldownTimer = undefined
    }
  }, 1000)
}

const handleSendSms = async () => {
  if (!isSmsPhoneValid.value) {
    ElMessage.warning('请输入有效的11位手机号')
    return
  }
  if (!captchaValid.value) {
    ElMessage.warning('请先输入正确的字母验证码')
    captchaRef.value?.refresh()
    return
  }

  smsSending.value = true
  try {
    await authApi.sendSms(smsForm.phone)
    ElMessage.success('验证码已发送，请注意查收短信')
    startSmsCooldown()
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

onMounted(() => {
  if (bookRef.value) {
    gsap.fromTo(
      bookRef.value,
      { autoAlpha: 0, y: 24, scale: 0.985 },
      { autoAlpha: 1, y: 0, scale: 1, duration: 0.9, ease: 'power3.out' }
    )
  }

  if (portalRef.value) {
    gsap.fromTo(
      portalRef.value,
      { autoAlpha: 0, x: 10 },
      { autoAlpha: 1, x: 0, duration: 0.62, delay: 0.16, ease: 'power2.out' }
    )
  }

  slideTimer = setInterval(showNextSlide, 3600)
})

onBeforeUnmount(() => {
  if (smsCooldownTimer) clearInterval(smsCooldownTimer)
  if (slideTimer) clearInterval(slideTimer)
})
</script>

<style lang="scss" scoped>
:global(html:has(.admin-login-container)),
:global(body:has(.admin-login-container)) {
  height: 100%;
  overflow: hidden;
}

.admin-login-container {
  position: relative;
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.68), transparent 34%),
    #d8d8d8;
  color: #1c1d20;
  font-family: 'Outfit', 'PingFang SC', sans-serif;
  padding: 34px;
  box-sizing: border-box;
  overflow: hidden;
}

.admin-login-card {
  --step-accent: #7b7fef;
  position: relative;
  z-index: 1;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(320px, 0.88fr);
  gap: clamp(42px, 5vw, 76px);
  width: min(1080px, calc(100vw - 70px));
  min-height: min(560px, calc(100vh - 72px));
  padding: clamp(30px, 3.3vw, 42px);
  border-radius: 48px;
  background: #fff;
  box-shadow:
    0 44px 90px rgba(46, 48, 55, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.96);
  opacity: 0;
}

.left-page-overlay,
.portal-panel {
  position: relative;
  min-width: 0;
}

.left-page-overlay {
  display: flex;
  flex-direction: column;
}

.visual-stage {
  position: relative;
  flex: 1;
  min-height: 440px;
}

.workflow-visual {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: 34px;
  background: #eef0f2;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.74),
    0 20px 44px rgba(52, 55, 63, 0.12);
  will-change: opacity, filter;
}

.workflow-visual img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.92) contrast(1.02);
  transform: scale(1.015);
}

.workflow-visual::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(180deg, rgba(10, 12, 16, 0.02), transparent 40%, rgba(10, 12, 16, 0.28)),
    radial-gradient(circle at 22% 12%, rgba(255, 255, 255, 0.28), transparent 32%);
}

.workflow-label {
  position: absolute;
  left: 24px;
  bottom: 24px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  max-width: calc(100% - 48px);
  padding: 11px 15px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #1d1f25;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 16px 32px rgba(20, 22, 26, 0.14);
  backdrop-filter: blur(14px);
}

.workflow-label span {
  color: var(--step-accent);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.1em;
}

.workflow-label strong {
  overflow: hidden;
  font-size: 17px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slide-dots {
  position: absolute;
  right: 24px;
  bottom: 28px;
  z-index: 4;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.slide-dots span {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.52);
  box-shadow: 0 2px 8px rgba(18, 20, 24, 0.18);
  transition: width 0.32s ease, background 0.32s ease;
}

.slide-dots span.active {
  width: 24px;
  background: #fff;
}

.portal-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: min(320px, 100%);
  margin: 0 auto;
  opacity: 0;
}

.admin-login-header {
  margin-bottom: 22px;
  text-align: center;
}

.portal-brand {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-bottom: 14px;
  color: #34373d;
  font-size: 22px;
  font-weight: 900;
}

.portal-brand img {
  width: 46px;
  height: 46px;
  object-fit: contain;
}

.admin-title {
  margin: 0;
  color: #202126;
  font-size: clamp(24px, 2.2vw, 29px);
  line-height: 1.04;
  font-weight: 900;
  letter-spacing: 0;
}

.security-notice {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 9px;
  color: #8a8f99;
  font-size: 12px;
}

.admin-login-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

:deep(.el-form-item) {
  width: 100%;
  margin-bottom: 0 !important;
}

.admin-input {
  :deep(.el-input__wrapper) {
    height: 44px;
    padding: 0 !important;
    border: none !important;
    border-bottom: 1px solid rgba(31, 33, 38, 0.24) !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;

    &.is-focus,
    &:hover {
      border-bottom-color: #1d1f25 !important;
    }
  }

  :deep(.el-input__inner) {
    height: 44px !important;
    color: #1d1f25 !important;
    font-size: 15px !important;
    font-weight: 700;

    &::placeholder {
      color: #8d929b !important;
      font-weight: 600;
    }
  }
}

:deep(.captcha-container) {
  width: 100%;
  display: flex;
  gap: 14px;
  align-items: center;
}

:deep(.captcha-display) {
  flex: 0 0 110px;
  height: 40px;
  border: 1px solid rgba(31, 33, 38, 0.12);
  border-radius: 14px;
  background: #f4f5f6;

  canvas {
    width: 100%;
    height: 100%;
  }
}

:deep(.captcha-input) {
  flex: 1;
  min-width: 0;

  .el-input__wrapper {
    height: 40px;
    padding: 0 !important;
    border: none !important;
    border-bottom: 1px solid rgba(31, 33, 38, 0.24) !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;

    &.is-focus,
    &:hover {
      border-bottom-color: #1d1f25 !important;
    }
  }

  .el-input__inner {
    height: 40px !important;
    color: #1d1f25 !important;
    font-size: 15px !important;
    font-weight: 700;

    &::placeholder {
      color: #8d929b !important;
      font-weight: 600;
    }
  }
}

.input-icon {
  color: #6f737b;
  font-size: 18px;
}

.sms-row {
  display: flex;
  width: 100%;
  gap: 14px;
}

.sms-input {
  flex: 1;
  min-width: 0;
}

.sms-btn {
  flex-shrink: 0;
  width: 112px;
  height: 40px;
  border: none !important;
  border-radius: 999px !important;
  background: #f1f2f3 !important;
  color: #1d1f25 !important;
  font-size: 13px;
  font-weight: 900;

  &:hover {
    background: #e6e8ea !important;
  }

  &:disabled,
  &.is-disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.admin-login-button {
  width: 100%;
  height: 44px;
  margin-top: 2px;
  border: none !important;
  border-radius: 999px !important;
  background: #1c1d22 !important;
  color: #fff !important;
  font-size: 15px;
  font-weight: 900;
  transition: transform 0.24s ease, background 0.24s ease;

  &:hover {
    background: #000 !important;
    transform: translateY(-2px);
  }

  &:disabled,
  &.is-disabled {
    background: #9ea2aa !important;
    cursor: not-allowed;
    transform: none;
  }
}

.admin-login-footer {
  margin-top: 18px;
  text-align: center;
}

.security-tips {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  color: #8f949c;
  font-size: 12px;
  line-height: 1.5;
}

.workflow-fade-enter-active,
.workflow-fade-leave-active {
  transition: opacity 0.72s ease, filter 0.72s ease;
}

.workflow-fade-enter-active {
  z-index: 2;
}

.workflow-fade-leave-active {
  z-index: 1;
}

.workflow-fade-enter-from,
.workflow-fade-leave-to {
  opacity: 0;
  filter: saturate(0.86) contrast(0.98) brightness(1.04);
}

.workflow-fade-enter-to,
.workflow-fade-leave-from {
  opacity: 1;
  filter: saturate(1) contrast(1) brightness(1);
}

@media (max-width: 900px) {
  :global(html:has(.admin-login-container)),
  :global(body:has(.admin-login-container)) {
    height: auto;
    min-height: 100%;
    overflow: auto;
  }

  .admin-login-container {
    align-items: flex-start;
    min-height: 100svh;
    padding: 14px;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .admin-login-card {
    grid-template-columns: 1fr;
    gap: 18px;
    width: min(460px, 100%);
    min-height: auto;
    margin-top: 0;
    padding: 16px;
    border-radius: 28px;
  }

  .visual-stage {
    min-height: 0;
    aspect-ratio: 16 / 9;
  }

  .workflow-visual {
    border-radius: 22px;
  }

  .portal-panel {
    width: min(320px, 100%);
    padding: 4px 4px 2px;
  }

  .admin-login-header {
    margin-bottom: 18px;
  }

  .admin-login-form {
    gap: 14px;
  }

  .workflow-label {
    left: 16px;
    bottom: 16px;
    max-width: calc(100% - 86px);
    padding: 9px 12px;
  }

  .workflow-label strong {
    font-size: 14px;
  }

  .slide-dots {
    right: 16px;
    bottom: 20px;
  }
}

@media (max-width: 480px) {
  .admin-login-container {
    padding: 10px;
  }

  .admin-login-card {
    width: 100%;
    padding: 14px;
    border-radius: 24px;
  }

  .visual-stage {
    aspect-ratio: 1.72 / 1;
  }

  .portal-brand {
    gap: 10px;
    font-size: 20px;
  }

  .portal-brand img {
    width: 40px;
    height: 40px;
  }

  :deep(.captcha-container),
  .sms-row {
    gap: 10px;
  }

  :deep(.captcha-display) {
    flex-basis: 96px;
  }

  .sms-btn {
    width: 104px;
  }
}

@media (max-width: 380px) {
  .admin-login-container {
    padding: 8px;
  }

  .admin-login-card {
    padding: 12px;
    border-radius: 22px;
  }

  .visual-stage {
    aspect-ratio: 1.8 / 1;
  }

  .workflow-label {
    left: 12px;
    bottom: 12px;
    max-width: calc(100% - 74px);
    padding: 8px 10px;
    gap: 8px;
  }

  .workflow-label span {
    font-size: 10px;
  }

  .workflow-label strong {
    font-size: 13px;
  }

  .slide-dots {
    right: 12px;
    bottom: 15px;
    gap: 5px;
  }

  .slide-dots span {
    width: 6px;
    height: 6px;
  }

  .slide-dots span.active {
    width: 18px;
  }

  .portal-panel {
    padding: 2px 0 0;
  }

  .portal-brand {
    margin-bottom: 10px;
    font-size: 18px;
  }

  .portal-brand img {
    width: 36px;
    height: 36px;
  }

  .admin-title {
    font-size: 23px;
  }

  .admin-login-footer {
    margin-top: 14px;
  }

  .security-tips {
    align-items: flex-start;
    text-align: left;
  }

  :deep(.captcha-display) {
    flex-basis: 88px;
  }

  .sms-btn {
    width: 96px;
    font-size: 12px;
  }
}
</style>
