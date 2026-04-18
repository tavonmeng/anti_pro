<template>
  <div class="captcha-container">
    <div class="captcha-display" @click="refreshCaptcha">
      <canvas ref="canvasRef" :width="width" :height="height"></canvas>
      <div class="captcha-overlay">
        <el-icon class="refresh-icon"><Refresh /></el-icon>
      </div>
    </div>
    <el-input
      v-model="inputValue"
      :placeholder="placeholder"
      size="large"
      maxlength="4"
      class="captcha-input"
      @input="handleInput"
    >
      <template #suffix>
        <el-icon class="input-icon"><Key /></el-icon>
      </template>
    </el-input>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Refresh, Key } from '@element-plus/icons-vue'

interface Props {
  modelValue: string
  width?: number
  height?: number
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: 120,
  height: 40,
  placeholder: '请输入验证码'
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'verify': [isValid: boolean]
}>()

const canvasRef = ref<HTMLCanvasElement>()
const inputValue = ref(props.modelValue)
const captchaCode = ref('')

// 生成随机字符
const generateRandomChar = () => {
  const chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
  return chars[Math.floor(Math.random() * chars.length)]
}

// 生成验证码
const generateCaptcha = () => {
  if (!canvasRef.value) return
  
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // 清空画布
  ctx.clearRect(0, 0, props.width, props.height)
  
  // 设置背景
  ctx.fillStyle = '#f0f0f0'
  ctx.fillRect(0, 0, props.width, props.height)
  
  // 生成验证码文字
  let code = ''
  for (let i = 0; i < 4; i++) {
    code += generateRandomChar()
  }
  captchaCode.value = code
  
  // 绘制文字
  ctx.font = 'bold 24px Arial'
  ctx.textBaseline = 'middle'
  
  for (let i = 0; i < code.length; i++) {
    const char = code[i]
    const x = (props.width / 5) * (i + 1)
    const y = props.height / 2
    
    // 随机颜色
    ctx.fillStyle = `rgb(${Math.floor(Math.random() * 100)}, ${Math.floor(Math.random() * 100)}, ${Math.floor(Math.random() * 100)})`
    
    // 随机旋转
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate((Math.random() - 0.5) * 0.4)
    ctx.fillText(char, 0, 0)
    ctx.restore()
  }
  
  // 绘制干扰线
  for (let i = 0; i < 3; i++) {
    ctx.strokeStyle = `rgba(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, 0.3)`
    ctx.beginPath()
    ctx.moveTo(Math.random() * props.width, Math.random() * props.height)
    ctx.lineTo(Math.random() * props.width, Math.random() * props.height)
    ctx.stroke()
  }
  
  // 绘制干扰点
  for (let i = 0; i < 20; i++) {
    ctx.fillStyle = `rgba(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, 0.5)`
    ctx.beginPath()
    ctx.arc(Math.random() * props.width, Math.random() * props.height, 1, 0, Math.PI * 2)
    ctx.fill()
  }
  
  // 清空输入
  inputValue.value = ''
  emit('update:modelValue', '')
}

// 刷新验证码
const refreshCaptcha = () => {
  generateCaptcha()
}

// 验证输入
const verifyCaptcha = (input: string): boolean => {
  return input.toUpperCase() === captchaCode.value.toUpperCase()
}

// 处理输入
const handleInput = (value: string) => {
  emit('update:modelValue', value)
  const isValid = verifyCaptcha(value)
  emit('verify', isValid && value.length === 4)
}

// 暴露验证方法
const validate = (): boolean => {
  return verifyCaptcha(inputValue.value) && inputValue.value.length === 4
}

// 重置验证码
const reset = () => {
  inputValue.value = ''
  emit('update:modelValue', '')
  generateCaptcha()
}

watch(() => props.modelValue, (val) => {
  inputValue.value = val
})

onMounted(() => {
  generateCaptcha()
})

defineExpose({
  validate,
  refresh: refreshCaptcha,
  reset
})
</script>

<style lang="scss" scoped>
.captcha-container {
  display: flex;
  gap: 12px;
  align-items: center;
}

.captcha-display {
  position: relative;
  cursor: pointer;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  background: transparent;
  transition: all 0.3s ease;
  
  &:hover {
    border-color: #667eea;
    box-shadow: 0 0 8px rgba(102, 126, 234, 0.2);
    
    .captcha-overlay {
      opacity: 1;
    }
  }
  
  canvas {
    display: block;
  }
}

.captcha-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  
  .refresh-icon {
    color: #FFFFFF;
    font-size: 20px;
  }
}

.captcha-input {
  flex: 1;
  
  :deep(.el-input__wrapper) {
    border-radius: 8px;
  }
}

.input-icon {
  color: #667eea;
  font-size: 18px;
}
</style>




