<template>
  <div v-if="isVisible" class="chat-overlay">
    <div class="chat-container" :class="{ 'expanded': showForm }">
      <div class="chat-header">
        <h3>找AI - 项目需求智能向导</h3>
        <button @click="closeChat" class="close-btn">&times;</button>
      </div>
      
      <div class="chat-content">
        <!-- Chat Area -->
        <div class="chat-area" v-if="!showForm">
          <div class="messages" ref="messagesContainer">
            <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
              <div class="message-bubble">{{ msg.content }}</div>
            </div>
            <div v-if="isLoading" class="message assistant">
              <div class="message-bubble typing">正在思考...</div>
            </div>
          </div>
          <div class="input-area">
            <input 
              v-model="inputMsg" 
              @keyup.enter="sendMessage" 
              placeholder="输入您的回复..." 
              :disabled="isLoading"
            />
            <button class="send-btn" @click="sendMessage" :disabled="isLoading || !inputMsg.trim()">发送</button>
          </div>
        </div>

        <!-- Requirements Form -->
        <div class="form-area" v-else>
          <h4 class="form-title">已为您整理的需求详情，请核对并编辑后提交：</h4>
          <form @submit.prevent="submitForm">
            <div class="form-grid">
              <div class="form-group">
                <label>品牌与产品关键词</label>
                <input v-model="formData.brand" type="text" placeholder="例：蒙牛；酸酸乳；酸甜好滋味">
              </div>
              <div class="form-group full-width">
                <label>项目背景</label>
                <textarea v-model="formData.background" rows="2" placeholder="例：新品上市，需要多媒体矩阵联动"></textarea>
              </div>
              <div class="form-group">
                <label>目标受众</label>
                <input v-model="formData.target_group" type="text">
              </div>
              <div class="form-group">
                <label>品牌调性</label>
                <input v-model="formData.brand_tone" type="text">
              </div>
              <div class="form-group full-width">
                <label>内容需求</label>
                <textarea v-model="formData.content" rows="2" placeholder="如需呈现LOGO、主视觉等..."></textarea>
              </div>
              <div class="form-group">
                <label>风格偏好</label>
                <input v-model="formData.style" type="text" placeholder="例：写实/卡通/高科技">
              </div>
              <div class="form-group">
                <label>品牌禁忌内容</label>
                <input v-model="formData.prohibited_content" type="text">
              </div>
              <div class="form-group">
                <label>投放城市或站点</label>
                <input v-model="formData.city" type="text">
              </div>
              <div class="form-group">
                <label>投放媒体尺寸</label>
                <input v-model="formData.media_size" type="text">
              </div>
              <div class="form-group">
                <label>投放时长与数量</label>
                <input v-model="formData.time_number" type="text">
              </div>
              <div class="form-group">
                <label>技术需求</label>
                <input v-model="formData.technology" type="text" placeholder="例：4K、MP4">
              </div>
              <div class="form-group">
                <label>项目预算</label>
                <input v-model="formData.budget" type="text">
              </div>
              <div class="form-group">
                <label>预计上刊时间</label>
                <input v-model="formData.online_time" type="text">
              </div>
              <div class="form-group">
                <label>销售对接人</label>
                <input v-model="formData.sales_contact" type="text">
              </div>
            </div>
            <div class="form-actions">
              <button type="button" @click="showForm = false" class="btn-secondary">返回聊天</button>
              <button type="submit" class="btn-primary" :disabled="isSubmitting">
                {{ isSubmitting ? '提交中...' : '提交需求' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  isVisible: Boolean
})
const emit = defineEmits(['close'])

const session_id = ref(Math.random().toString(36).substring(7))
const messages = ref([
  { role: 'assistant', content: '您好！我是您的项目需求收集助手。我们将通过对话为您梳理出准确的投放需求表单，请问您的品牌和产品是什么呢？' }
])
const inputMsg = ref('')
const isLoading = ref(false)

const showForm = ref(false)
const requirements_gathered = ref(false)
const formData = ref({})
const isSubmitting = ref(false)

const messagesContainer = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight + 100
  }
}

watch(() => messages.value.length, scrollToBottom)

const sendMessage = async () => {
  if (!inputMsg.value.trim() || isLoading.value) return
  
  const userText = inputMsg.value.trim()
  messages.value.push({ role: 'user', content: userText })
  inputMsg.value = ''
  isLoading.value = true

  try {
    const response = await fetch('/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: session_id.value,
        message: userText
      })
    })

    const result = await response.json()
    // It's possible for there to be a blank reply if the model ONLY generated JSON, so add a generic msg or just ignore.
    if (result.reply && result.reply.trim() !== '') {
      messages.value.push({ role: 'assistant', content: result.reply })
    } else {
      messages.value.push({ role: 'assistant', content: '需求收集完成，正在为您生成表格...' })
    }
    
    if (result.requirements_gathered) {
      requirements_gathered.value = true
      Object.assign(formData.value, result.data || {})
      setTimeout(() => {
        showForm.value = true
      }, 1500)
    }
  } catch (error) {
    console.error(error)
    messages.value.push({ role: 'assistant', content: '抱歉，服务未响应。请检查后端是否已启动，并重试。' })
  } finally {
    isLoading.value = false
  }
}

const submitForm = async () => {
  isSubmitting.value = true
  try {
    await fetch('/ai/submit_requirements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData.value)
    })
    alert('需求提交成功！')
    emit('close')
  } catch(e) {
    alert('提交失败，请重试')
  } finally {
    isSubmitting.value = false
  }
}

const closeChat = () => {
  emit('close')
}
</script>

<style scoped>
.chat-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0,0,0,0.4);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.chat-container {
  background: #ffffff;
  width: 90%;
  max-width: 480px;
  height: 80vh;
  border-radius: 20px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: max-width 0.4s cubic-bezier(0.16, 1, 0.3, 1), height 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.chat-container.expanded {
  max-width: 900px;
  height: 85vh;
}

.chat-header {
  background: #000;
  color: #fff;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.chat-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 500;
  letter-spacing: 1px;
}

.close-btn {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
  padding: 0 8px;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f8f9fa;
}

.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  color: #fff;
}

.message.assistant {
  align-self: flex-start;
  color: #000;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 0.95rem;
  line-height: 1.5;
  white-space: pre-wrap;
}

.message.user .message-bubble {
  background: #000;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-bubble {
  background: #fff;
  border: 1px solid #eaeaea;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.02);
}

.typing {
  color: #888;
  font-style: italic;
}

.input-area {
  padding: 16px;
  background: #fff;
  border-top: 1px solid #eaeaea;
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.input-area input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 24px;
  outline: none;
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.input-area input:focus {
  border-color: #000;
}

.send-btn {
  background: #000;
  color: #fff;
  border: none;
  padding: 0 24px;
  border-radius: 24px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
}

.send-btn:disabled {
  background: #aaa;
  cursor: not-allowed;
}

.send-btn:not(:disabled):active {
  transform: scale(0.96);
}

.form-area {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  background: #fff;
}

.form-title {
  margin-top: 0;
  margin-bottom: 24px;
  font-size: 1.1rem;
  font-weight: 600;
  color: #000;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group.full-width {
  grid-column: span 2;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #444;
}

.form-group input,
.form-group textarea {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 0.95rem;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: #000;
}

.form-group textarea {
  resize: vertical;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid #eaeaea;
}

.btn-primary, .btn-secondary {
  padding: 12px 28px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
}

.btn-primary {
  background: #000;
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background: #e4e4e4;
}

/* 响应式 */
@media (max-width: 600px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .form-group.full-width {
    grid-column: span 1;
  }
  .chat-container.expanded {
    height: 95vh;
  }
}
</style>
