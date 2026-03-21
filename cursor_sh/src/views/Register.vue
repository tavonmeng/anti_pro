<template>
  <div class="register-container">
    <!-- 科技感背景 -->
    <div class="minimal-background"></div>

    <div class="register-wrapper">
      <div>
        <div class="register-header">
          <div class="logo-icon">
            <svg viewBox="0 0 100 100" class="logo-svg">
              <circle cx="50" cy="50" r="45" fill="none" stroke="#000" stroke-width="2" />
              <path d="M 30 50 L 45 65 L 70 35" fill="none" stroke="#000" stroke-width="3" />
              
            </svg>
          </div>
          <h1 class="register-title">用户注册</h1>
          <p class="register-subtitle">创建您的账户，开始使用AI设计任务管理系统</p>
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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Message, Right } from '@element-plus/icons-vue'
import { authApi } from '@/utils/api'
import type { UserRole } from '@/types'
import Captcha from '@/components/Captcha.vue'

const router = useRouter()
const registerFormRef = ref<FormInstance>()
const loading = ref(false)
const captchaValid = ref(false)
const captchaRef = ref<InstanceType<typeof Captcha>>()

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'user' as UserRole,
  captcha: ''
})

const validateUsername = (rule: any, value: string, callback: Function) => {
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

const validateEmail = (rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入邮箱地址'))
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
    callback(new Error('请输入有效的邮箱地址'))
  } else {
    callback()
  }
}

const validatePassword = (rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请输入密码'))
  } else if (value.length < 6) {
    callback(new Error('密码长度至少6个字符'))
  } else {
    callback()
  }
}

const validateConfirmPassword = (rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const validateCaptcha = (rule: any, value: string, callback: Function) => {
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
          router.push('/login')
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
  router.push('/login')
}


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
</style>

