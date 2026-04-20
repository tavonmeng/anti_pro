<template>
  <el-dialog
    v-model="visible"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    width="720px"
    class="confirmation-dialog"
    align-center
  >
    <div class="confirmation-letter">
      <!-- 正式信函头部 -->
      <div class="letter-header">
        <div class="letter-stamp">需求告知函</div>
        <div class="letter-number">编号：{{ orderNumber }}</div>
      </div>

      <div class="letter-divider"></div>

      <!-- 致辞 -->
      <div class="letter-greeting">
        <p>尊敬的客户：</p>
        <p class="greeting-body">
          感谢您选择 <strong>Unique Video AI 设计平台</strong>。以下是您提交的需求确认摘要，
          请您仔细核对并确认，确认后我们将立即进入制作流程。
        </p>
      </div>

      <!-- 需求摘要 -->
      <div class="letter-section">
        <div class="section-label">一、需求摘要</div>
        <div class="summary-table">
          <div class="summary-row">
            <span class="summary-key">订单类型</span>
            <span class="summary-value">{{ orderTypeText }}</span>
          </div>
          <div v-for="item in summaryItems" :key="item.label" class="summary-row">
            <span class="summary-key">{{ item.label }}</span>
            <span class="summary-value">{{ item.value }}</span>
          </div>
        </div>
      </div>

      <!-- 排期 -->
      <div class="letter-section">
        <div class="section-label">二、制作排期</div>
        <div class="schedule-timeline">
          <div class="timeline-row">
            <div class="timeline-dot start"></div>
            <div class="timeline-content">
              <span class="timeline-label">预计开始日期</span>
              <span class="timeline-date">{{ startDate }}</span>
            </div>
          </div>
          <div class="timeline-line"></div>
          <div class="timeline-row">
            <div class="timeline-dot end"></div>
            <div class="timeline-content">
              <span class="timeline-label">预计交付日期</span>
              <span class="timeline-date">{{ endDate }}</span>
            </div>
          </div>
          <div class="timeline-duration">
            制作周期约 <strong>{{ productionDays }} 个工作日</strong>
          </div>
        </div>
      </div>

      <div class="letter-divider"></div>

      <!-- 确认表单 -->
      <div class="letter-section">
        <div class="section-label">三、确认信息</div>
        <p class="confirm-notice">请填写以下信息完成需求确认。确认后即视为您已认可上述需求内容及排期安排。</p>

        <el-form
          ref="confirmFormRef"
          :model="confirmForm"
          :rules="confirmRules"
          label-position="top"
          class="confirm-form"
        >
          <el-form-item label="联系邮箱" prop="email">
            <el-input
              v-model="confirmForm.email"
              placeholder="将用于接收制作进度通知"
              prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item label="签名确认" prop="signature">
            <el-input
              v-model="confirmForm.signature"
              placeholder="请手动输入「我已知晓」以确认"
              class="signature-input"
            />
            <div class="signature-hint">
              <el-icon><WarningFilled /></el-icon>
              请在上方输入框中手动输入"<strong>我已知晓</strong>"完成签名确认
            </div>
          </el-form-item>

          <div class="sms-notice">
            <el-icon><WarningFilled /></el-icon>
            最后一步：请完成手机安全验证以提交需求
          </div>

          <el-form-item label="联系手机" prop="phone">
            <el-input
              v-model="confirmForm.phone"
              placeholder="将用于接收短信通知"
              prefix-icon="Phone"
              maxlength="11"
            />
          </el-form-item>

          <el-form-item label="短信验证码" prop="smsCode">
            <div class="sms-row">
              <el-input
                v-model="confirmForm.smsCode"
                placeholder="请输入验证码"
                maxlength="6"
                class="sms-input"
              />
              <el-button
                :disabled="smsCooldown > 0 || !confirmForm.phone || confirmForm.phone.length !== 11 || confirmForm.signature !== '我已知晓'"
                @click="handleSendSms"
                class="sms-btn"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s 后重发` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel" size="large">返回修改</el-button>
        <el-button
          type="primary"
          size="large"
          :loading="confirming"
          :disabled="!isFormValid"
          @click="handleConfirm"
        >
          确认提交需求
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/utils/api'
import type { OrderType } from '@/types'

const authStore = useAuthStore()

const props = defineProps<{
  modelValue: boolean
  orderNumber: string
  orderType: OrderType
  formData: Record<string, any>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [data: { email: string; phone: string }]
  cancel: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const confirmFormRef = ref<FormInstance>()
const confirming = ref(false)
const smsCooldown = ref(0)
let smsTimer: ReturnType<typeof setInterval> | null = null

const confirmForm = ref({
  email: '',
  phone: '',
  smsCode: '',
  signature: ''
})

// --- 验证规则 ---
const validateSignature = (_rule: any, value: string, callback: Function) => {
  if (value !== '我已知晓') {
    callback(new Error('请输入「我已知晓」完成签名确认'))
  } else {
    callback()
  }
}

const confirmRules: FormRules = {
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  smsCode: [
    { required: true, message: '请输入短信验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ],
  signature: [
    { required: true, message: '请输入签名确认', trigger: 'blur' },
    { validator: validateSignature, trigger: 'blur' }
  ]
}

const isFormValid = computed(() => {
  return (
    confirmForm.value.smsCode?.length === 6 &&
    confirmForm.value.signature === '我已知晓'
  )
})

// --- 订单类型文本 ---
const orderTypeText = computed(() => {
  const map: Record<OrderType, string> = {
    video_purchase: '裸眼3D成片购买适配',
    ai_3d_custom: 'AI裸眼3D内容定制',
    digital_art: '数字艺术内容定制'
  }
  return map[props.orderType] || props.orderType
})

// --- 排期计算 ---
const productionDays = computed(() => {
  const map: Record<OrderType, number> = {
    video_purchase: 5,
    ai_3d_custom: 15,
    digital_art: 7
  }
  return map[props.orderType] || 15
})

const addWorkdays = (start: Date, days: number): Date => {
  const result = new Date(start)
  let added = 0
  while (added < days) {
    result.setDate(result.getDate() + 1)
    const dow = result.getDay()
    if (dow !== 0 && dow !== 6) added++
  }
  return result
}

const formatDate = (date: Date): string => {
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
}

const startDate = computed(() => {
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  // 如果是周末，跳到周一
  while (tomorrow.getDay() === 0 || tomorrow.getDay() === 6) {
    tomorrow.setDate(tomorrow.getDate() + 1)
  }
  return formatDate(tomorrow)
})

const endDate = computed(() => {
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  while (tomorrow.getDay() === 0 || tomorrow.getDay() === 6) {
    tomorrow.setDate(tomorrow.getDate() + 1)
  }
  return formatDate(addWorkdays(tomorrow, productionDays.value))
})

// --- 需求摘要 ---
const summaryItems = computed(() => {
  const items: Array<{ label: string; value: string }> = []
  const d = props.formData

  if (props.orderType === 'video_purchase') {
    const industryMap: Record<string, string> = { movie: '电影', outdoor: '户外', custom: d.customIndustry || '自定义' }
    const styleMap: Record<string, string> = { scifi: '科幻', realistic: '写真', custom: d.customStyle || '自定义' }
    items.push({ label: '行业类型', value: industryMap[d.industryType] || d.industryType })
    items.push({ label: '视觉风格', value: styleMap[d.visualStyle] || d.visualStyle })
    if (d.duration) items.push({ label: '时长', value: `${d.duration} 秒` })
    if (d.priceRange) items.push({ label: '价格区间', value: `¥${d.priceRange.min} - ¥${d.priceRange.max}` })
    if (d.resolution) items.push({ label: '分辨率', value: d.resolution })
    if (d.size) items.push({ label: '屏幕尺寸', value: d.size })
    if (d.curvature) items.push({ label: '曲率', value: d.curvature })
  } else if (props.orderType === 'ai_3d_custom') {
    if (d.brand) items.push({ label: '品牌关键词', value: d.brand })
    if (d.target_group) items.push({ label: '目标受众', value: d.target_group })
    if (d.brand_tone) items.push({ label: '品牌调性', value: d.brand_tone })
    if (d.style) items.push({ label: '风格偏好', value: d.style })
    if (d.content) items.push({ label: '内容需求', value: d.content.length > 60 ? d.content.slice(0, 60) + '...' : d.content })
    if (d.city) items.push({ label: '投放城市', value: d.city })
    if (d.media_size) items.push({ label: '投放媒体尺寸', value: d.media_size })
    if (d.budget) items.push({ label: '制作预算', value: d.budget })
    if (d.online_time) items.push({ label: '预计上刊时间', value: d.online_time })
    if (d.scenePhotos?.length) items.push({ label: '现场实拍图', value: `${d.scenePhotos.length} 张` })
  } else if (props.orderType === 'digital_art') {
    const artMap: Record<string, string> = { abstract: '抽象', realistic: '写实', installation: '装置', dynamic: '动态艺术', custom: d.customDirection || '自定义' }
    items.push({ label: '艺术方向', value: artMap[d.artDirection] || d.artDirection })
    if (d.description) items.push({ label: '说明文字', value: d.description.length > 60 ? d.description.slice(0, 60) + '...' : d.description })
    if (d.materials?.length) items.push({ label: '相关材料', value: `${d.materials.length} 个文件` })
  }

  return items
})

// --- 短信发送 ---
const handleSendSms = async () => {
  if (!confirmForm.value.phone || confirmForm.value.phone.length !== 11) {
    ElMessage.warning('请先输入正确的手机号')
    return
  }

  try {
    // 调用实际的短信发送接口
    await authApi.sendSms(confirmForm.value.phone)
    ElMessage.success('验证码已发送')
    smsCooldown.value = 60
    smsTimer = setInterval(() => {
      smsCooldown.value--
      if (smsCooldown.value <= 0 && smsTimer) {
        clearInterval(smsTimer)
        smsTimer = null
      }
    }, 1000)
  } catch {
    ElMessage.error('发送验证码失败，请稍后重试')
  }
}

// --- 确认提交 ---
const handleConfirm = async () => {
  if (!confirmFormRef.value) return

  await confirmFormRef.value.validate(async (valid) => {
    if (valid) {
      confirming.value = true
      try {
        emit('confirm', {
          email: confirmForm.value.email,
          phone: confirmForm.value.phone
        })
      } finally {
        confirming.value = false
      }
    }
  })
}

const handleCancel = () => {
  emit('cancel')
  visible.value = false
}

// 重置表单，并从用户注册信息预填邮箱和手机号
watch(visible, (val) => {
  if (val) {
    const user = authStore.user
    confirmForm.value = {
      email: user?.email || '',
      phone: user?.phone || '',
      smsCode: '',
      signature: ''
    }
  } else {
    if (smsTimer) {
      clearInterval(smsTimer)
      smsTimer = null
    }
  }
})
</script>

<style lang="scss" scoped>
.confirmation-dialog {
  :deep(.el-dialog) {
    border-radius: 16px;
    overflow: hidden;
  }
  :deep(.el-dialog__body) {
    padding: 0;
    max-height: 70vh;
    overflow-y: auto;
  }
  :deep(.el-dialog__footer) {
    padding: 20px 32px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }
}

.confirmation-letter {
  padding: 40px 40px 24px;
  font-family: 'Inter', 'PingFang SC', system-ui, sans-serif;
}

.letter-header {
  text-align: center;
  margin-bottom: 24px;
}

.letter-stamp {
  font-size: 28px;
  font-weight: 700;
  color: #1a1c1c;
  letter-spacing: 0.15em;
  position: relative;
  display: inline-block;
  padding-bottom: 8px;

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 48px;
    height: 3px;
    background: #0071e3;
    border-radius: 2px;
  }
}

.letter-number {
  margin-top: 12px;
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  color: #86868b;
}

.letter-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,0,0,0.08), transparent);
  margin: 24px 0;
}

.letter-greeting {
  margin-bottom: 28px;

  p {
    font-size: 14px;
    color: #414754;
    line-height: 1.8;
    margin: 0 0 8px 0;
  }

  .greeting-body {
    text-indent: 2em;
  }

  strong {
    color: #1a1c1c;
  }
}

.letter-section {
  margin-bottom: 28px;
}

.section-label {
  font-size: 15px;
  font-weight: 600;
  color: #1a1c1c;
  margin-bottom: 16px;
  padding-left: 12px;
  border-left: 3px solid #0071e3;
}

// --- 需求摘要表格 ---
.summary-table {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  overflow: hidden;
}

.summary-row {
  display: flex;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);

  &:last-child {
    border-bottom: none;
  }
}

.summary-key {
  width: 140px;
  flex-shrink: 0;
  padding: 10px 16px;
  font-size: 13px;
  color: #86868b;
  background: #fafafa;
  border-right: 1px solid rgba(0, 0, 0, 0.04);
}

.summary-value {
  flex: 1;
  padding: 10px 16px;
  font-size: 13px;
  color: #1a1c1c;
  font-weight: 500;
}

// --- 排期时间线 ---
.schedule-timeline {
  padding: 20px 24px;
  background: #f8f9fc;
  border-radius: 12px;
  position: relative;
}

.timeline-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;

  &.start {
    background: #0071e3;
    box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.15);
  }
  &.end {
    background: #34c759;
    box-shadow: 0 0 0 4px rgba(52, 199, 89, 0.15);
  }
}

.timeline-line {
  width: 2px;
  height: 24px;
  background: linear-gradient(to bottom, #0071e3, #34c759);
  margin-left: 5px;
  margin: 4px 0 4px 5px;
}

.timeline-content {
  display: flex;
  justify-content: space-between;
  flex: 1;
}

.timeline-label {
  font-size: 13px;
  color: #86868b;
}

.timeline-date {
  font-size: 13px;
  font-weight: 600;
  color: #1a1c1c;
}

.timeline-duration {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  font-size: 13px;
  color: #414754;
  text-align: center;

  strong {
    color: #0071e3;
  }
}

// --- 确认表单 ---
.confirm-notice {
  font-size: 13px;
  color: #86868b;
  margin: 0 0 16px 0;
  line-height: 1.6;
}

.confirm-form {
  :deep(.el-form-item__label) {
    font-weight: 500;
    font-size: 13px;
    color: #1a1c1c;
  }

  :deep(.el-input__wrapper) {
    border-radius: 8px;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08) !important;
  }

  :deep(.el-input__wrapper:focus-within) {
    box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.3) !important;
  }
}

.sms-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.sms-input {
  flex: 1;
}

.sms-btn {
  white-space: nowrap;
  border-radius: 8px;
}

.signature-input {
  :deep(.el-input__inner) {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: #1a1c1c;
  }
}

.signature-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: #e6a23c;

  strong {
    color: #e6a23c;
  }
}

.sms-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #e6a23c;
  padding: 8px 12px;
  background: rgba(230, 162, 60, 0.08);
  border-radius: 6px;
  border: 1px solid rgba(230, 162, 60, 0.2);
}

// --- 底部按钮 ---
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
