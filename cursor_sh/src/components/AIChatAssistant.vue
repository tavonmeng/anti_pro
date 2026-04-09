<template>
  <div class="ai-assistant-wrapper">
    <!-- Expanded View (Sidebar Chat) -->
    <div class="expanded-view">
      <div class="chat-header">
        <div class="header-left">
          <span class="ai-title">🤖 项目需求智能向导</span>
        </div>
        <el-button text circle @click="collapse"><el-icon><Close /></el-icon></el-button>
      </div>

      <div class="chat-content" ref="chatContentRef">
        <div class="messages-container" ref="messagesContainer">
          <!-- Always show initial 3 options if no option selected -->
          <div v-if="!selectedMode" class="welcome-section">
            <div class="message assistant">
              <div class="message-bubble">
                您好！我是您的专属业务助手。请问您今天需要处理什么类型的业务？
              </div>
            </div>
            <div class="options-container">
              <div class="option-card" @click="selectMode('purchase')">
                <span class="emoji">📹</span> 裸眼3D成片购买适配
              </div>
              <div class="option-card" @click="selectMode('custom_ai')">
                <span class="emoji">🎨</span> AI裸眼3D内容定制
              </div>
              <div class="option-card" @click="selectMode('digital_art')">
                <span class="emoji">🖼️</span> 数字艺术内容定制
              </div>
            </div>
          </div>

          <!-- Chat History -->
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <div class="message-bubble">{{ msg.content }}</div>
            <!-- Special button for 'purchase' mode in the AI msg -->
            <div v-if="msg.isPurchasePrompt" class="message-actions">
              <el-button type="primary" size="small" @click="goToBrowse('video_purchase')">
                先去浏览
              </el-button>
            </div>
          </div>
          <div v-if="isLoading" class="message assistant">
            <div class="message-bubble typing">正在思考...</div>
          </div>
        </div>



      </div>

      <!-- Input Area — mirrors hero-input-area design exactly -->
      <div class="input-area morph-ai-input" data-flip-id="ai-input-bar">
        <input
          type="text"
          v-model="inputMsg"
          placeholder="描述您的需求..."
          class="chat-native-input"
          @keyup.enter="sendMessage"
          :disabled="isLoading"
        />
        <div
          class="send-btn"
          :class="{ disabled: isLoading || !inputMsg.trim() }"
          @click="sendMessage"
        >
          发送 <span class="sparkle">✨</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'

const emit = defineEmits(['close', 'mode-change'])
const router = useRouter()

const selectedMode = ref<string | null>(null)
const messages = ref<any[]>([])
const inputMsg = ref('')
const isLoading = ref(false)
const session_id = ref(Math.random().toString(36).substring(7))
const chatContentRef = ref<any>(null)

const collapse = () => {
  emit('close')
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContentRef.value) {
    chatContentRef.value.scrollTo({
      top: chatContentRef.value.scrollHeight + 100,
      behavior: 'smooth'
    })
  }
}

watch(() => messages.value.length, scrollToBottom)
watch(() => isLoading.value, scrollToBottom)

const selectMode = async (mode: string) => {
  selectedMode.value = mode
  emit('mode-change', mode)
  if (mode === 'purchase') {
    messages.value.push({ role: 'assistant', content: '您选择了【裸眼3D成片购买适配】。您可以直接告诉我您的需求，或者点击下方按钮先去浏览我们的案例库：', isPurchasePrompt: true })
  } else if (mode === 'custom_ai') {
    isLoading.value = true
    try {
      // 从后端读取真实设计的开场白
      const response = await fetch(`/ai/start?session_id=${session_id.value}`)
      const result = await response.json()
      if (result.reply) {
        messages.value.push({ role: 'assistant', content: result.reply })
      }
    } catch (e) {
      // 降级兜底
      messages.value.push({ role: 'assistant', content: '您选择了【AI裸眼3D内容定制】。我将引导您梳理详细的投放需求清单，请问您的品牌和产品是什么呢？' })
    } finally {
      isLoading.value = false
    }
  } else if (mode === 'digital_art') {
    messages.value.push({ role: 'assistant', content: '您选择了【数字艺术内容定制】。请简单描述您的视觉风格倾向和应用场景：' })
  }
}

const goToBrowse = (type: string) => {
  if (type === 'video_purchase') {
    router.push('/user/video-marketplace')
  } else {
    router.push(`/user/create-order/${type}`)
  }
}

const sendMessage = async () => {
  if (!inputMsg.value.trim() || isLoading.value) return
  const userText = inputMsg.value.trim()
  messages.value.push({ role: 'user', content: userText })
  inputMsg.value = ''
  
  if (selectedMode.value === 'custom_ai') {
    await handleCustomAiChat(userText)
  } else if (selectedMode.value === 'purchase') {
    isLoading.value = true
    setTimeout(() => {
      messages.value.push({ role: 'assistant', content: '好的，我已经了解了您的需求，您可以前往库中挑选相近的模板。', isPurchasePrompt: true })
      isLoading.value = false
    }, 1000)
  } else {
    // Dummy response for the other modes
    isLoading.value = true
    setTimeout(() => {
      messages.value.push({ role: 'assistant', content: '好的，我已经记录下您的初步需求，很快会安排对应的服务专家与您对接。' })
      isLoading.value = false
    }, 1000)
  }
}

const handleCustomAiChat = async (userText: string) => {
  isLoading.value = true
  try {
    const response = await fetch('/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: session_id.value, message: userText })
    })
    const result = await response.json()
    if (result.reply && result.reply.trim() !== '') {
      messages.value.push({ role: 'assistant', content: result.reply })
    }
    
    if (result.requirements_gathered) {
      messages.value.push({ role: 'assistant', content: '需求收集完成！正在为您跳转到完整的核对表单...' })
      sessionStorage.setItem('ai_draft_order', JSON.stringify(result.data || {}))
      
      setTimeout(() => {
        collapse()
        router.push('/user/create-order/ai_3d_custom')
      }, 1500)
    }
  } catch (error) {
    messages.value.push({ role: 'assistant', content: '后端服务连接失败。' })
  } finally {
    isLoading.value = false
  }
}


</script>

<style scoped>
.ai-assistant-wrapper {
  height: 100%; 
  background: transparent; 
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: none;
  box-sizing: border-box;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-feature-settings: "kern" 1;
  color: #000000;
}

.expanded-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  height: 52px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08); /* Black scale */
}

.ai-title {
  font-weight: 500;
  font-size: 14px;
  color: #000000;
  letter-spacing: -0.1px;
}

.chat-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.messages-container {
  padding: 24px; /* More breathing room */
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.welcome-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.options-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-card {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px; /* Figma dialog base */
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 400;
  color: #000000;
  letter-spacing: -0.14px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.25, 1, 0.3, 1);
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: none; /* Flat by default */
}

.option-card:hover {
  background: #fafafa;
  border-color: rgba(0, 0, 0, 0.16);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  transform: translateY(-1px);
}

.emoji {
  font-size: 18px;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-bubble {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.45;
  letter-spacing: -0.14px;
  white-space: pre-wrap;
}

/* User Message: Black Solid */
.message.user .message-bubble {
  background: #000000; 
  color: #ffffff;
  border-radius: 12px;
  border-bottom-right-radius: 4px; /* Slight anchoring */
  box-shadow: none;
}

/* Assistant Message: Glass Dark */
.message.assistant .message-bubble {
  background: rgba(0, 0, 0, 0.04);
  color: #000000;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
  box-shadow: none;
}

.message-actions {
  margin-top: 12px;
  padding-left: 12px;
}

.message-actions :deep(.el-button--primary) {
  background: #000;
  border-color: #000;
  color: #fff;
  border-radius: 50px;
}

.message-actions :deep(.el-button--primary:hover) {
  background: rgba(0,0,0,0.8);
  border-color: rgba(0,0,0,0.8);
}

.typing {
  color: rgba(0, 0, 0, 0.5);
  font-style: italic;
}

.input-area {
  padding: 0;
  background: transparent;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  background: #ffffff;
  border-radius: 50px; /* Pill */
  padding: 4px 4px 4px 16px;
  box-shadow: none;
  border: 1px solid rgba(0, 0, 0, 0.16);
  max-width: 800px;
  width: calc(100% - 48px);
  box-sizing: border-box;
  margin: 0 auto 24px auto; /* Spacing below */
  transition: all 0.2s;
}

.input-area:focus-within {
  outline: dashed 2px #000;
  outline-offset: 2px;
  border-color: transparent;
}

.chat-native-input {
  border: none;
  background: transparent;
  flex: 1;
  font-size: 15px;
  letter-spacing: -0.14px;
  color: #000000;
  outline: none;
  font-family: inherit;
  min-width: 0;
}

.chat-native-input::placeholder {
  color: rgba(0, 0, 0, 0.4);
}

.chat-native-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn {
  background: #000000; /* Black Pill Button */
  color: #ffffff;
  font-weight: 500;
  padding: 8px 20px;
  border-radius: 50px; /* Pill */
  font-size: 14px;
  letter-spacing: -0.1px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.send-btn:hover {
  opacity: 0.85;
}

.send-btn:focus-visible {
  outline: dashed 2px #000;
  outline-offset: 2px;
}

.send-btn.disabled {
  opacity: 0.3;
  cursor: not-allowed;
  pointer-events: none;
}

.sparkle {
  font-size: 14px;
}

.form-area {
  padding: 24px;
  background: #fff;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  max-height: 50%;
}

.form-scroll {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
}

.form-title {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
}

.full-btn {
  width: 100%;
}
</style>
