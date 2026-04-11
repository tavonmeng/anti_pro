<template>
  <div class="register-container" :class="{ 'is-modal': isModal }">
    <!-- 科技感背景 -->
    <div class="minimal-background" v-if="!isModal"></div>

    <div class="register-wrapper">
      <div>
        <div class="register-header">
          <h1 class="register-title">Unique Vision 系统</h1>
        </div>
        
        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="register-form"
          @submit.prevent="handleRegister"
        >
          <el-form-item prop="username">
            <div class="input-wrapper">
              <el-input
                v-model="registerForm.username"
                placeholder="请输入用户名（3-20个字符）"
                size="large"
                class="tech-input"
              >
                <template #prefix>
                  <el-icon class="input-icon"><User /></el-icon>
                </template>
              </el-input>
              <div class="input-border"></div>
            </div>
          </el-form-item>
          
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
              <div class="input-border"></div>
            </div>
          </el-form-item>
          
          <el-form-item prop="password">
            <div class="input-wrapper">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="请输入密码（至少6个字符）"
                size="large"
                class="tech-input"
                show-password
              >
                <template #prefix>
                  <el-icon class="input-icon"><Lock /></el-icon>
                </template>
              </el-input>
              <div class="input-border"></div>
            </div>
          </el-form-item>
          
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
              <div class="input-border"></div>
            </div>
          </el-form-item>
          
          <el-form-item prop="captcha">
            <Captcha ref="captchaRef" v-model="registerForm.captcha" @verify="handleCaptchaVerify" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Message, Right } from '@element-plus/icons-vue'
import { authApi } from '@/utils/api'
import type { UserRole } from '@/types'
import Captcha from '@/components/Captcha.vue'

const router = useRouter()
const route = useRoute()
const registerFormRef = ref<FormInstance>()
const loading = ref(false)
const captchaValid = ref(false)
const captchaRef = ref<InstanceType<typeof Captcha>>()

const isModal = computed(() => route.query.modal === 'true')

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'user' as UserRole,
  captcha: ''
})

const validateUsername = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入用户名'))
  } else if (value.length < 3 || value.length > 20) {
    callback(new Error('用户名长度在3到20个字符'))
  } else if (!/^[a-zA-Z0-9_]+$/.test(value)) {
    callback(new Error('用户名只能包含字母、数字和下划线'))
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

const validateCaptcha = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入验证码'))
  } else if (!captchaValid.value) {
    callback(new Error('验证码错误'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  username: [{ validator: validateUsername, trigger: 'blur' }],
  email: [{ validator: validateEmail, trigger: 'blur' }],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
  captcha: [{ validator: validateCaptcha, trigger: 'blur' }]
}

const handleCaptchaVerify = (isValid: boolean) => {
  captchaValid.value = isValid
  if (registerFormRef.value) {
    registerFormRef.value.validateField('captcha')
  }
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      if (!captchaValid.value) {
        ElMessage.error('请先通过验证码验证')
        captchaRef.value?.refresh()
        return
      }
      
      loading.value = true
      try {
        const success = await authApi.register({
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
        if (captchaRef.value) {
          captchaRef.value.refresh()
          registerForm.captcha = ''
          captchaValid.value = false
        }
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

/* 验证码特殊布局补丁 */
.captcha-container { display: flex; gap: 12px; align-items: center; width: 100%; }
.captcha-display {
  border-radius: 8px; overflow: hidden; height: 44px; 
  border: 1px solid rgba(0, 0, 0, 0.08);
}
.captcha-display canvas { height: 100% !important; display: block; }
.captcha-input { flex: 1; }

.minimal-background {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-color: #000; z-index: 1; pointer-events: none;
}
</style>

