<template>
  <div class="admin-login-container">
    <div class="register-wrapper">
      <!-- 链接验证中 -->
      <div v-if="validating" class="validating-state">
        <el-icon class="loading-icon" :size="40"><Loading /></el-icon>
        <p>正在验证邀请链接...</p>
      </div>

      <!-- 链接无效 -->
      <div v-else-if="!isValid" class="invalid-state">
        <div class="lock-icon" style="background:#ff4d4f">
          <el-icon :size="32" color="#fff"><CircleCloseFilled /></el-icon>
        </div>
        <h2 class="admin-title">邀请链接无效</h2>
        <p class="admin-subtitle">{{ invalidReason }}</p>
      </div>

      <!-- 注册表单 -->
      <div v-else>
        <div class="admin-login-header">
          <div class="lock-icon">
            <el-icon :size="32"><Suitcase /></el-icon>
          </div>
          <h1 class="admin-title">承包商注册</h1>
          <p class="admin-subtitle">请填写您的信息以完成注册</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="admin-login-form"
          label-position="top"
        >
          <el-form-item prop="phone" label="手机号">
            <div class="sms-row">
              <el-input v-model="form.phone" placeholder="手机号" class="admin-input sms-input" />
              <el-button :disabled="smsCooldown > 0" class="sms-btn" @click="sendSms">
                {{ smsCooldown > 0 ? `${smsCooldown}s` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item prop="sms_code" label="验证码">
            <el-input v-model="form.sms_code" placeholder="短信验证码" class="admin-input" />
          </el-form-item>

          <el-form-item prop="username" label="用户名">
            <el-input v-model="form.username" placeholder="用于登录的用户名" class="admin-input" />
          </el-form-item>

          <el-form-item prop="password" label="密码">
            <el-input v-model="form.password" type="password" placeholder="登录密码" class="admin-input" show-password />
          </el-form-item>

          <el-form-item prop="email" label="邮箱">
            <el-input v-model="form.email" placeholder="联系邮箱" class="admin-input" />
          </el-form-item>

          <el-form-item label="公司名称（选填）">
            <el-input v-model="form.company" placeholder="公司名称" class="admin-input" />
          </el-form-item>

          <el-form-item label="地址（选填）">
            <el-input v-model="form.address" placeholder="联系地址" class="admin-input" />
          </el-form-item>

          <el-form-item label="专业方向（选填）">
            <el-input v-model="form.specialty" placeholder="如：3D建模、视频后期" class="admin-input" />
          </el-form-item>

          <el-form-item label="擅长领域（选填）">
            <el-input v-model="form.expertise" placeholder="如：裸眼3D广告、产品展示" class="admin-input" />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="admin-login-button"
              :loading="submitting"
              @click="handleRegister"
            >
              {{ submitting ? '注册中...' : '完成注册' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Suitcase, Loading, CircleCloseFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()

const validating = ref(true)
const isValid = ref(false)
const invalidReason = ref('')
const submitting = ref(false)
const smsCooldown = ref(0)
let smsTimer: any = null

const inviteToken = ref('')

const form = reactive({
  phone: '',
  sms_code: '',
  username: '',
  password: '',
  email: '',
  company: '',
  address: '',
  specialty: '',
  expertise: '',
})

const rules: FormRules = {
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }, { len: 11, message: '手机号必须11位', trigger: 'blur' }],
  sms_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 2, max: 20, message: '2-20个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '至少6位', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
}

onMounted(async () => {
  const token = route.query.invite as string
  if (!token) {
    validating.value = false
    isValid.value = false
    invalidReason.value = '缺少邀请参数'
    return
  }
  inviteToken.value = token
  try {
    const res = await request.get(`/api/contractor/validate-invite/${token}`)
    if (res.data?.valid) {
      isValid.value = true
    } else {
      isValid.value = false
      const reason = res.data?.reason
      invalidReason.value = reason === 'used' ? '该链接已被使用' : reason === 'expired' ? '该链接已过期' : '链接无效'
    }
  } catch {
    isValid.value = false
    invalidReason.value = '链接验证失败'
  } finally {
    validating.value = false
  }
})

const sendSms = async () => {
  if (!form.phone || form.phone.length !== 11) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  try {
    await request.post('/api/auth/sms/send', { phone: form.phone })
    ElMessage.success('验证码已发送')
    smsCooldown.value = 60
    smsTimer = setInterval(() => {
      smsCooldown.value--
      if (smsCooldown.value <= 0) clearInterval(smsTimer)
    }, 1000)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  }
}

const handleRegister = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await request.post('/api/contractor/register', {
        invite_token: inviteToken.value,
        ...form,
      })
      ElMessage.success('注册成功，请使用手机号登录')
      router.push('/admin/login')
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '注册失败')
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style lang="scss" scoped>
.admin-login-container {
  width: 100%; min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: #000; font-family: 'Outfit','PingFang SC',sans-serif; color: #fff;
  padding: 40px 20px; box-sizing: border-box;
}
.register-wrapper {
  width: 90%; max-width: 440px; background: #000; border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 40px rgba(0,0,0,0.5);
  padding: 32px; box-sizing: border-box;
}
.admin-login-header { text-align: center; margin-bottom: 24px; }
.lock-icon {
  width: 50px; height: 50px; margin: 0 auto 12px;
  display: flex; align-items: center; justify-content: center;
  background: #fff; border-radius: 50%; color: #000;
}
.admin-title { font-size: 22px; font-weight: 800; color: #fff; margin: 0 0 6px; text-align: center; }
.admin-subtitle { font-size: 13px; color: rgba(255,255,255,0.5); margin: 0; text-align: center; }
.admin-login-form { width: 100%; display: flex; flex-direction: column; gap: 12px; }
:deep(.el-form-item) { margin-bottom: 0 !important; }
:deep(.el-form-item__label) { color: rgba(255,255,255,0.6) !important; font-size: 13px !important; padding-bottom: 4px !important; }
.admin-input {
  :deep(.el-input__wrapper) {
    background-color: transparent !important; border: none !important; border-radius: 0 !important;
    border-bottom: 1px solid rgba(255,255,255,0.2) !important; box-shadow: none !important;
    padding: 0 10px !important; height: 40px;
    &.is-focus, &:hover { border-bottom-color: #fff !important; }
  }
  :deep(.el-input__inner) {
    height: 40px !important; font-size: 15px !important; color: #fff !important;
    &::placeholder { color: rgba(255,255,255,0.4) !important; }
  }
}
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
  background: #fff !important; border: none !important; border-radius: 60px !important;
  color: #000 !important; margin-top: 8px;
  &:hover { background: #e0e0e0 !important; transform: translateY(-2px); }
}
.validating-state, .invalid-state {
  text-align: center; padding: 40px 0;
  p { color: rgba(255,255,255,0.5); margin-top: 12px; }
}
.loading-icon { animation: spin 1s linear infinite; color: #fff; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
