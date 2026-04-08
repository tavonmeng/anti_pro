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
  height: 100%; /* Fill the workspace layout organically */
  background: transparent; /* Rely on the parent container's light blue background */
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: none;
  box-sizing: border-box;
}

.expanded-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  height: 60px;
  background: transparent; /* No extra grey header anymore */
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.ai-title {
  font-weight: 600;
  font-size: 16px;
  color: #1b1b1c; /* on_surface */
}

.chat-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: transparent; /* Expose the light blue! */
}

.messages-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.options-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-card {
  background: #ffffff; /* Crisp white cards on blue background */
  border: none;
  border-radius: 12px;
  padding: 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 4px 16px rgba(0, 88, 188, 0.04); /* Adjusted shadow for the blue theme */
}

.option-card:hover {
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(0, 88, 188, 0.08); /* Elevate off the blue plane */
  transform: translateY(-2px);
}

.emoji {
  font-size: 18px;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 90%;
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-bubble {
  padding: 14px 18px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.message.user .message-bubble {
  background: linear-gradient(135deg, #0058bc, #0070eb); /* Primary gradient */
  color: #ffffff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 88, 188, 0.2);
}

.message.assistant .message-bubble {
  background: #ffffff; /* Clean white bubble strongly popping out from the blue ambient background */
  color: #1b1b1c; /* on_surface */
  border: none;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 88, 188, 0.03); /* Subtle depth */
}

.message-actions {
  margin-top: 12px;
  padding-left: 12px;
}

.typing {
  color: #999;
  font-style: italic;
}

.input-area {
  padding: 16px;
  background: transparent;
  border-top: none;
  flex-shrink: 0;
  margin-bottom: 8px;
  /* Pill bar — exact clone of hero-input-area */
  display: flex;
  align-items: center;
  background: #ffffff;
  border-radius: 9999px;
  padding: 4px 4px 4px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  max-width: 800px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto 12px auto;
}

.chat-native-input {
  border: none;
  background: transparent;
  flex: 1;
  font-size: 15px;
  color: #1b1b1c;
  outline: none;
  font-family: inherit;
  min-width: 0;
}

.chat-native-input::placeholder {
  color: #a0a4ae;
}

.chat-native-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn {
  background: #0058bc;
  color: #fff;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 9999px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.send-btn:hover {
  opacity: 0.9;
}

.send-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

.sparkle {
  font-size: 14px;
}

.form-area {
  padding: 20px;
  background: #fff;
  border-top: 1px solid #eee;
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
  font-size: 15px;
}

.full-btn {
  width: 100%;
}
</style>
