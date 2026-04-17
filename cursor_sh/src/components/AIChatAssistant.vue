<template>
  <div class="ai-assistant-wrapper">
    <!-- Expanded View (Sidebar Chat) -->
    <div class="expanded-view">
      <!-- Stitch Header -->
      <header class="stitch-header">
        <div class="header-left">
          <h2 class="font-headline">AI智能体帮你理清思路</h2>
        </div>
        
        <!-- Fused Search Bar -->
        <div class="header-center">
          <div class="header-search">
            <el-icon class="search-icon"><Search /></el-icon>
            <input type="text" placeholder="Search insights and assets..." class="search-input" />
          </div>
        </div>

        <div class="header-right">
          <button
            class="icon-toggle history-btn"
            :class="{ active: showHistory }"
            title="历史聊天"
            @click="toggleHistory"
          >
            <el-icon><Clock /></el-icon>
          </button>
          <button class="icon-toggle" title="Help"><el-icon><QuestionFilled /></el-icon></button>
          <button class="new-session-btn" @click="startNewSession">New Session</button>
          <button class="icon-toggle collapse-btn" @click="collapse"><el-icon><Close /></el-icon></button>
        </div>
      </header>
      
      <div class="gradient-banner"></div>

      <div class="chat-content" ref="chatContentRef">
        <div class="messages-container" ref="messagesContainer">
          <!-- 历史聊天记录（内联下压式，保存多条，无卡片底色） -->
          <transition name="collapse-history">
            <div v-if="showHistory" class="history-inline">
              <div v-if="!savedHistories || savedHistories.length === 0" class="history-empty">
                <el-icon><Clock /></el-icon>
                <span>暂无历史记录</span>
              </div>
              <template v-else>
                <div v-for="(history, hIndex) in savedHistories" :key="history.id || hIndex" class="history-session-item">
                  <div class="history-header">
                    <div class="history-title-group">
                      <el-icon class="history-icon"><Clock /></el-icon>
                      <span class="history-time">{{ history.savedAt }} 的对话记录</span>
                    </div>
                  </div>
                  
                  <div class="history-preview-chat">
                    <div
                      v-for="(msg, i) in (expandedHistories[history.id] ? history.messages : history.messages.slice(0, 3))"
                      :key="i"
                      :class="['preview-msg', msg.role]"
                    >
                      <div class="preview-avatar">{{ msg.role === 'user' ? 'U' : 'AI' }}</div>
                      <div class="preview-bubble">{{ (!expandedHistories[history.id] && msg.content.length > 80) ? msg.content.slice(0, 80) + '...' : msg.content }}</div>
                    </div>
                    <div v-if="history.messages.length > 3" class="history-more-indicator" @click="toggleExpandHistory(history.id)">
                      <template v-if="!expandedHistories[history.id]">
                        <div class="more-dots">
                          <span></span><span></span><span></span>
                        </div>
                        <span class="more-text">点击展开剩余 {{ history.messages.length - 3 }} 条</span>
                      </template>
                      <template v-else>
                        <el-icon class="collapse-icon"><ArrowUp /></el-icon>
                        <span class="more-text">收起内容</span>
                      </template>
                    </div>
                  </div>
                  
                  <div class="history-actions-bottom-right">
                    <button class="history-clear-btn-icon" @click="deleteHistory(hIndex)" title="删除记录">
                      <el-icon><Delete /></el-icon>
                    </button>
                    <button class="stitch-primary-btn history-restore-btn-new" @click="restoreHistory(history)">接着上回聊</button>
                  </div>
                  
                  <div class="session-divider" v-if="hIndex < savedHistories.length - 1"></div>
                </div>
              </template>
              <div class="history-master-divider" v-if="savedHistories && savedHistories.length > 0"></div>
            </div>
          </transition>
          <!-- Always show initial 3 options if no option selected -->
          <div v-if="!selectedMode" class="welcome-section message assistant">
            <div class="assistant-wrapper">
              <div class="assistant-tag"><span class="engine-name">Catalyst Engine</span> <span class="pro-badge">PRO</span></div>
              <div class="message-bubble glass-ai welcome-bubble">
                <p class="welcome-text">您好！我是您的专属业务助手。请问您今天需要处理什么类型的业务？</p>
                <div class="options-container stitched-options">
                  <div class="option-card stitch-card" @click="selectMode('purchase')">
                    <span class="opt-text">裸眼3D成片购买适配</span>
                  </div>
                  <div class="option-card stitch-card" @click="selectMode('custom_ai')">
                    <span class="opt-text">AI裸眼3D内容定制</span>
                  </div>
                  <div class="option-card stitch-card" @click="selectMode('digital_art')">
                    <span class="opt-text">数字艺术内容定制</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Chat History -->
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            
            <template v-if="msg.role === 'user'">
              <div class="user-message-container">
                <div class="user-content-row">
                  <div class="user-col">
                    <span class="user-tag">You</span>
                    <div class="message-bubble user-bubble">{{ msg.content }}</div>
                    <span class="msg-time" v-if="msg.timestamp">{{ msg.timestamp }}</span>
                  </div>
                  <div class="user-avatar">t</div>
                </div>
              </div>
            </template>

            <template v-else>
              <div class="assistant-wrapper">
                <div class="assistant-tag"><span class="engine-name">Catalyst Engine</span></div>
                <div class="message-bubble glass-ai">
                  <div v-if="index > 0 && msg.role === 'assistant' && !msg.isPurchasePrompt" class="reasoning-mock">
                    <span class="reasoning-text">Reasoning <el-icon><Right /></el-icon></span>
                  </div>
                  <p class="bubble-text">{{ msg.content }}</p>
                  <!-- Special button for 'purchase' mode in the AI msg -->
                  <div v-if="msg.isPurchasePrompt" class="message-actions">
                    <el-button class="stitch-primary-btn" @click="goToBrowse('video_purchase')">
                      先去浏览
                    </el-button>
                  </div>
                  <!-- 需求收集完成后的三个操作按钮 -->
                  <div v-if="msg.isCompletePrompt" class="completion-actions">
                    <p class="completion-hint">您可以在表单中修改信息、补充细节字段、上传现场实拍图等附件资料</p>
                    <div class="completion-btns">
                      <button class="comp-btn comp-btn-ghost" @click="handleStayInChat">继续对话</button>
                      <button class="comp-btn comp-btn-outline" @click="handleSaveDraftFromChat">保存草稿</button>
                      <button class="comp-btn comp-btn-primary" @click="handleGoToForm">前往确认表单 →</button>
                    </div>
                  </div>
                </div>
                <span class="msg-time ai-time" v-if="msg.timestamp">{{ msg.timestamp }}</span>
              </div>
            </template>
          </div>
          
          <div v-if="isLoading" class="message assistant">
            <div class="assistant-wrapper">
               <div class="assistant-tag"><span class="engine-name">Catalyst Engine</span></div>
               <div class="message-bubble glass-ai typing">正在思考中...</div>
            </div>
          </div>
          <div v-if="isTyping && !isLoading" class="typing-cursor-indicator">
            <span class="cursor-blink">▍</span>
          </div>
        </div>
      </div>

      <!-- Input Area — Stitch Style Pill -->
      <div class="input-area-container">
        <div class="input-area pill-style">
          <!-- Left icons mock -->
          <div class="left-tools">
            <el-icon class="tool-icon"><CirclePlusFilled /></el-icon>
            <el-icon class="tool-icon"><PictureRounded /></el-icon>
          </div>

          <textarea
            ref="textareaRef"
            v-model="inputMsg"
            :placeholder="selectedMode ? '描述您的需求...' : '请先选择上方业务类型'"
            class="chat-native-textarea"
            :class="{ 'is-locked': !selectedMode }"
            @input="adjustTextareaHeight"
            @keydown.enter.prevent="sendMessage"
            :disabled="isLoading || isTyping || !selectedMode"
            @focus="handleInputFocus"
            rows="1"
          ></textarea>
          
          <!-- Right tools & send -->
          <div class="right-tools">
            <button
              class="stitch-send-btn"
              :class="{ disabled: isLoading || isTyping || !inputMsg.trim() || !selectedMode }"
              @click="sendMessage"
            >
              <span>Send</span>
              <el-icon><Top /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Close, Right, Top, QuestionFilled, CirclePlusFilled, PictureRounded, Search, Clock, Delete, ArrowUp } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'

const emit = defineEmits(['close', 'mode-change'])
const router = useRouter()
const orderStore = useOrderStore()

const selectedMode = ref<string | null>(null)
const messages = ref<any[]>([])
const inputMsg = ref('')
const isLoading = ref(false)
const isTyping = ref(false) // AI 正在逐字输出中
const session_id = ref(Math.random().toString(36).substring(7))
const chatContentRef = ref<any>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const adjustTextareaHeight = () => {
  const ta = textareaRef.value
  if (!ta) return
  ta.style.height = 'auto'
  ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
}

const handleInputFocus = () => {
  if (!selectedMode.value) {
    // Gentle visual hint: the welcome options flash
    const el = document.querySelector('.stitched-options')
    if (el) {
      el.classList.add('hint-flash')
      setTimeout(() => el.classList.remove('hint-flash'), 600)
    }
  }
}

const collapse = () => {
  // 当用户选择了定制模式，且对话已经开始，但还没收集全信息（测试阈值设为3）
  if (selectedMode.value === 'custom_ai' || selectedMode.value === 'digital_art') {
    const userMsgCount = messages.value.filter(m => m.role === 'user').length;
    if (userMsgCount > 0 && userMsgCount < 4) {
      ElMessageBox.confirm(
        '我们发现您的项目部分需求信息（如预算、人群、投放场景等）还未提供完整。您希望继续由 AI 帮您引导梳理，还是直接退出并跳转到表单页面手动填写？',
        '需求尚未收集完整 📝',
        {
          confirmButtonText: '去手动填表',
          cancelButtonText: '继续聊天',
          type: 'warning',
          center: true,
          closeOnClickModal: false,
          showClose: false
        }
      ).then(() => {
        // 用户选择去填表：保存历史，将已有数据打成草稿带过去
        saveCurrentToHistory()
        const mockDraftData = {
          brand: messages.value.find(m => m.role === 'user')?.content.slice(0, 15) + "..." || "未提及品牌",
          target_group: "",
          style: "",
          budget: ""
        }
        sessionStorage.setItem('ai_draft_order', JSON.stringify(mockDraftData))
        emit('close')
        router.push(selectedMode.value === 'digital_art' ? '/user/create-order/digital_art' : '/user/create-order/ai_3d_custom')
      }).catch(() => {
        // 用户选择继续聊天，面板保持开启，啥都不做
      })
      return; 
    }
  }

  saveCurrentToHistory()
  emit('close')
}

const startNewSession = () => {
  // 保存当前会话到历史（只保存最近1个）
  saveCurrentToHistory()
  messages.value = []
  selectedMode.value = null
  session_id.value = Math.random().toString(36).substring(7)
}

// --- 历史聊天记录 ---
const HISTORY_KEY = 'ai_chat_last_session'
const showHistory = ref(false)

interface SavedSession {
  id: string
  messages: any[]
  mode: string | null
  savedAt: string
}

const savedHistories = ref<SavedSession[]>([])
const expandedHistories = ref<Record<string, boolean>>({})

const toggleExpandHistory = (id: string) => {
  expandedHistories.value[id] = !expandedHistories.value[id]
}

const loadSavedHistory = () => {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      savedHistories.value = Array.isArray(parsed) ? parsed : [parsed]
    }
  } catch {
    savedHistories.value = []
  }
}

onMounted(() => {
  loadSavedHistory()
})

const saveCurrentToHistory = () => {
  if (messages.value.length === 0) return
  
  const session: SavedSession = {
    id: Date.now().toString(),
    messages: [...messages.value],
    mode: selectedMode.value,
    savedAt: new Date().toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  let histories: SavedSession[] = []
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (raw) {
       const parsed = JSON.parse(raw)
       histories = Array.isArray(parsed) ? parsed : [parsed]
    }
  } catch(e) {}
  
  histories.unshift(session)
  if (histories.length > 5) histories = histories.slice(0, 5)
  
  localStorage.setItem(HISTORY_KEY, JSON.stringify(histories))
  savedHistories.value = histories
}

const toggleHistory = () => {
  showHistory.value = !showHistory.value
  if (showHistory.value) {
    loadSavedHistory()
  }
}

const restoreHistory = (history: SavedSession) => {
  messages.value = [...history.messages]
  selectedMode.value = history.mode
  if (selectedMode.value) {
    emit('mode-change', selectedMode.value)
  }
  showHistory.value = false
  scrollToBottom()
}

const deleteHistory = (index: number) => {
  savedHistories.value.splice(index, 1)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(savedHistories.value))
  if (savedHistories.value.length === 0) {
    showHistory.value = false
  }
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

// ===== 打字机效果：逐字显示 AI 回复 =====
const typewriterEffect = (fullText: string, onComplete?: () => void) => {
  isLoading.value = false
  isTyping.value = true
  
  // 先 push 一条空的 assistant 消息
  const msgIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    timestamp: getCurrentTime()
  })

  let charIndex = 0
  const speed = 25 // 每个字符间隔 ms
  
  const typeNext = () => {
    if (charIndex < fullText.length) {
      // 一次追加 1~2 个字符，让速度更自然
      const chunk = fullText.slice(charIndex, charIndex + 2)
      messages.value[msgIndex].content += chunk
      charIndex += chunk.length
      
      // 每 20 个字符滚动一次，避免过于频繁
      if (charIndex % 20 === 0) scrollToBottom()
      
      setTimeout(typeNext, speed)
    } else {
      // 打字完成
      isTyping.value = false
      scrollToBottom()
      if (onComplete) onComplete()
    }
  }
  
  typeNext()
}

watch(() => messages.value.length, scrollToBottom)
watch(() => isLoading.value, scrollToBottom)

const getCurrentTime = () => {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const selectMode = async (mode: string) => {
  selectedMode.value = mode
  emit('mode-change', mode)
  if (mode === 'purchase') {
    messages.value.push({ role: 'assistant', content: '您选择了【裸眼3D成片购买适配】。您可以直接告诉我您的需求，或者点击下方按钮先去浏览我们的案例库：', isPurchasePrompt: true, timestamp: getCurrentTime() })
  } else if (mode === 'custom_ai') {
    isLoading.value = true
    try {
      // 从后端读取真实设计的开场白
      const response = await fetch(`/ai/start?session_id=${session_id.value}`)
      if (!response.ok || (response.headers.get('content-type') && response.headers.get('content-type')?.includes('text/html'))) {
        throw new Error('API not available, fallback to mock')
      }
      const result = await response.json()
      if (result.reply) {
        typewriterEffect(result.reply)
      }
    } catch (e) {
      // 降级兜底
      const fallbackMsg = `你好！我是您的项目需求AI助手 👋\n\n你可以直接告诉我你的项目想法，不用担心格式——哪怕只是一段随意的描述，比如：\n\n> "我们是一个运动饮料品牌，想在今年夏天做一波地铁广告投放，主要面向年轻白领..."\n\n我会从你的描述里提取需要的信息，然后针对还不清楚的地方，我们会一个个讨论 😊\n\n**所以，先告诉我你的项目是什么吧？**`;
      typewriterEffect(fallbackMsg)
    } finally {
      isLoading.value = false
    }
  } else if (mode === 'digital_art') {
    messages.value.push({ role: 'assistant', content: '您选择了【数字艺术内容定制】。请简单描述您的视觉风格倾向和应用场景：', timestamp: getCurrentTime() })
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
  messages.value.push({ role: 'user', content: userText, timestamp: getCurrentTime() })
  inputMsg.value = ''
  
  // reset textarea height
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
  
  if (selectedMode.value === 'custom_ai') {
    await handleCustomAiChat(userText)
  } else if (selectedMode.value === 'purchase') {
    isLoading.value = true
    setTimeout(() => {
      messages.value.push({ role: 'assistant', content: '好的，我已经了解了您的需求，您可以前往库中挑选相近的模板。', isPurchasePrompt: true, timestamp: getCurrentTime() })
      isLoading.value = false
    }, 1000)
  } else {
    // Dummy response for the other modes
    isLoading.value = true
    setTimeout(() => {
      messages.value.push({ role: 'assistant', content: '好的，我已经记录下您的初步需求，很快会安排对应的服务专家与您对接。', timestamp: getCurrentTime() })
      isLoading.value = false
    }, 1000)
  }
}

const handleCustomAiChat = async (userText: string) => {
  isLoading.value = true
  try {
    // 提取所有除当前这句（即最后一条）以外的历史记录
    const historyMessages = messages.value.slice(0, messages.value.length - 1);
    const formattedHistory = historyMessages
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }));

    const response = await fetch('/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        session_id: session_id.value, 
        message: userText,
        history: formattedHistory
      })
    })
    
    // 如果线上环境 Nginx 把请求拦截并回退给了 index.html 导致没报错而是 200 OK，我们需要手动抛出异常去触发降级
    if (!response.ok || (response.headers.get('content-type') && response.headers.get('content-type')?.includes('text/html'))) {
      throw new Error('API not available, fallback to mock')
    }

    const data = await response.json()
    const replyContent = data.message || data.answer || '处理成功';
    // 隐藏掉触发表单的系统标记串，避免在UI中展示给用户
    const cleanContent = replyContent.replace('【需求收集完成】', '').trim();
    
    // 使用打字机效果逐字显示
    typewriterEffect(cleanContent, () => {
      // 打字完成后，检测是否触发建单
      if (replyContent.includes('【需求收集完成】')) {
        // 给最后一条 AI 消息加上操作按钮标记
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.isCompletePrompt = true
        }
      }
    })

  } catch (error) {
    // 降级兜底：前端 Mock 模拟对话收集需求
    const userMsgCount = messages.value.filter(m => m.role === 'user').length;
    
    setTimeout(() => {
      if (userMsgCount === 1) {
        messages.value.push({ 
          role: 'assistant', 
          content: '好的，产品很有意思。为了让最终视觉效果更匹配，您期望这支视频想要打动哪类年轻受众呢？（比如在校学生、或者职场新人等）', 
          timestamp: getCurrentTime() 
        })
      } else if (userMsgCount === 2) {
        messages.value.push({ 
          role: 'assistant', 
          content: '明白。在视觉呈现上，您大概有什么特定的风格倾向吗？（比如赛博朋克、极简风，或者写实拟真都可以）', 
          timestamp: getCurrentTime() 
        })
      } else if (userMsgCount === 3) {
        messages.value.push({ 
          role: 'assistant', 
          content: '非常清晰。最后了解一下，您准备把这支内容具体投放在哪里？以及大概的预算区间是多少呢？', 
          timestamp: getCurrentTime() 
        })
      } else {
        messages.value.push({ 
          role: 'assistant', 
          content: '太好了，所有核心信息都已经收集完毕！我这就为您整理生成标准的专属开发需求单...', 
          timestamp: getCurrentTime() 
        })
        
        setTimeout(() => {
          messages.value.push({ role: 'assistant', content: '需求收集完成！正在为您跳转到完整的核对表单...' })
          // 生成一些假数据作为 Draft 传递给建单页
          const mockDraftData = {
            brand: "示例品牌 (AI已提取)",
            target_group: "年轻群体",
            style: "科技感设计",
            budget: "10万以上"
          }
          sessionStorage.setItem('ai_draft_order', JSON.stringify(mockDraftData))
          
          setTimeout(() => {
            collapse()
            router.push('/user/create-order/ai_3d_custom')
          }, 1500)
        }, 1000)
      }
      isLoading.value = false
    }, 1000)
  }
}

// ===== 需求收集完成后的三个操作按钮处理 =====
const buildDraftData = () => {
  const brandMatch = messages.value.find(m => m.role === 'user')?.content.slice(0, 15) || "未知品牌";
  return {
    brand: brandMatch + "... (AI提取)",
    target_group: "基于对话已梳理",
    style: "基于对话已判定",
    budget: "基于对话已记录"
  }
}

const handleStayInChat = () => {
  // 移除最后一条消息的完成按钮标记，让用户继续聊天
  const lastMsg = messages.value[messages.value.length - 1]
  if (lastMsg) lastMsg.isCompletePrompt = false
}

const handleSaveDraftFromChat = async () => {
  try {
    const draftData = buildDraftData()
    await orderStore.createOrder({
      orderType: selectedMode.value === 'digital_art' ? 'digital_art' : 'ai_3d_custom',
      ...draftData
    }, true)
    saveCurrentToHistory()
  } catch (e) {
    console.error('保存草稿失败', e)
  }
}

const handleGoToForm = () => {
  sessionStorage.setItem('ai_draft_order', JSON.stringify(buildDraftData()))
  saveCurrentToHistory()
  emit('close')
  router.push(selectedMode.value === 'digital_art' ? '/user/create-order/digital_art' : '/user/create-order/ai_3d_custom')
}

</script>

<style lang="scss" scoped>
/* 打字机光标动画 */
.typing-cursor-indicator {
  display: inline-block;
  margin-left: 4px;
  margin-top: -8px;
}
.cursor-blink {
  animation: blink-cursor 0.8s step-end infinite;
  color: #0071e3;
  font-size: 16px;
  font-weight: 600;
}
@keyframes blink-cursor {
  50% { opacity: 0; }
}

/* \u9700\u6c42\u6536\u96c6\u5b8c\u6210\u540e\u7684\u5185\u8054\u64cd\u4f5c\u6309\u94ae */
.completion-actions {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}
.completion-hint {
  font-size: 12px;
  color: #86868b;
  line-height: 1.5;
  margin: 0 0 12px 0;
}
.completion-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.comp-btn {
  padding: 7px 16px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  white-space: nowrap;
}
.comp-btn-ghost {
  background: transparent;
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: #747474;
}
.comp-btn-ghost:hover {
  border-color: rgba(0, 0, 0, 0.25);
  color: #1a1c1c;
}
.comp-btn-outline {
  background: transparent;
  border: 1px solid #0071e3;
  color: #0071e3;
}
.comp-btn-outline:hover {
  background: rgba(0, 113, 227, 0.06);
}
.comp-btn-primary {
  background: #0d99ff;
  border: 1px solid #0d99ff;
  color: #fff;
}
.comp-btn-primary:hover {
  background: #0a8bed;
  border-color: #0a8bed;
}

/* === Main Layout === */
.ai-assistant-wrapper {
  height: 100%; 
  background: transparent; 
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: none;
  box-sizing: border-box;
  font-family: 'Inter', 'SF Pro Text', system-ui, sans-serif;
  color: #1a1c1c;
}

.expanded-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

/* Stitch Header */
.stitch-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06); /* Perfectly align with inspiration sidebar tracker */
  box-sizing: border-box;
  z-index: 20;
}

.header-left .font-headline {
  margin: 0;
  font-weight: 500;
  font-size: 13px;
  letter-spacing: -0.01em;
  color: #1a1c1c;
  white-space: nowrap;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 40px;
}

.header-search {
  display: flex;
  align-items: center;
  background: #f3f3f4;
  border-radius: 999px;
  padding: 6px 16px;
  width: 100%;
  max-width: 480px;
  border: 1px solid transparent;
  transition: border-color 0.2s;
}

.header-search:focus-within {
  border-color: rgba(0,0,0,0.1);
  background: #ffffff;
}

.header-search .search-icon {
  color: #a0a4ae;
  font-size: 14px;
  margin-right: 8px;
}

.header-search .search-input {
  border: none;
  background: transparent;
  flex: 1;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  color: #1a1c1c;
}

.header-search .search-input::placeholder {
  color: #a0a4ae;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.is-locked {
  background-color: transparent !important;
  color: #a0a4ae;
}

/* History Inline Panel */
.history-inline {
  width: 100%;
  padding: 16px 0 0 0;
  box-sizing: border-box;
}

.history-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a0a4ae;
  gap: 8px;
  font-size: 13px;
  padding: 20px 0;
}

.history-empty .el-icon {
  font-size: 18px;
}

.history-session-item {
  padding: 16px 24px;
}

.history-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.history-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-icon {
  font-size: 14px;
  color: #a0a4ae;
}

.history-time {
  font-size: 12px;
  color: #747474;
  font-weight: 500;
}

.history-actions-bottom-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.history-restore-btn-new {
  font-size: 12px;
  padding: 6px 16px;
  height: auto;
  border-radius: 99px;
  box-shadow: 0 2px 8px rgba(13, 153, 255, 0.2);
}

.history-clear-btn-icon {
  background: transparent;
  border: none;
  color: #a0a4ae;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s;
}

.history-clear-btn-icon:hover {
  background: rgba(229, 57, 53, 0.1);
  color: #e53935;
}

/* Chat Preview Timeline */
.history-preview-chat {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
}

.history-preview-chat::before {
  content: '';
  position: absolute;
  left: 14px;
  top: 24px;
  bottom: 24px;
  width: 2px;
  background: rgba(0, 0, 0, 0.04);
  z-index: 0;
}

.preview-msg {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  z-index: 1;
}

.preview-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: #1a1c1c;
  flex-shrink: 0;
}

.preview-msg.assistant .preview-avatar {
  background: linear-gradient(135deg, #0d99ff, #0a8bed);
  color: #fff;
  border: none;
}

.preview-bubble {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.04);
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  color: #4a4d55;
  max-width: 85%;
  box-shadow: 0 1px 4px rgba(0,0,0,0.02);
}

.preview-msg.user .preview-bubble {
  background: #fdfdfd;
  color: #1a1c1c;
}

.history-more-indicator {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-left: 3px;
  padding: 6px 10px;
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s;
  z-index: 1;
}

.history-more-indicator:hover {
  background-color: rgba(0,0,0,0.02);
}

.collapse-icon {
  font-size: 16px;
  color: #a0a4ae;
  margin: 0 4px;
}

.more-dots {
  display: flex;
  flex-direction: column;
  gap: 3px;
  align-items: center;
  width: 24px;
}

.more-dots span {
  display: block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #d1d5db;
}

.more-text {
  font-size: 12px;
  color: #a0a4ae;
}

.session-divider {
  width: calc(100% + 112px); /* 48px (item padding) + 64px (container padding) */
  margin-left: -56px; /* -24px (item) + -32px (container) */
  height: 1px;
  background: rgba(0, 0, 0, 0.05); /* very thin subtle line */
  margin-top: 16px;
}

.history-master-divider {
  width: calc(100% + 64px); /* 64px (container padding) */
  margin-left: -32px;
  height: 1px;
  background: rgba(0, 0, 0, 0.08); /* slightly more visible */
}

.history-btn.active {
  color: #0d99ff;
  background: rgba(13, 153, 255, 0.08);
  border-radius: 8px;
}

/* Collapse animation for history panel push-down */
.collapse-history-enter-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.collapse-history-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.collapse-history-enter-from,
.collapse-history-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  margin-top: 0;
}
.collapse-history-enter-to,
.collapse-history-leave-from {
  max-height: 2000px;
  opacity: 1;
}

.icon-toggle {
  background: transparent;
  border: none;
  color: #747474;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
  padding: 8px;
}

.icon-toggle:hover {
  color: #000;
}

.new-session-btn {
  background: #0d99ff; /* Figma primary blue */
  color: #ffffff;
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 0.15s ease, background 0.2s ease;
}

.new-session-btn:hover {
  background: #0a8bed; /* Slightly darker vivid blue */
  transform: scale(0.98);
}

.gradient-banner {
  display: none;
}

.chat-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.messages-container {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  box-sizing: border-box;
}

/* User & Assistant tags */
.assistant-tag, .user-tag {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em; 
  color: #747474;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
}

.pro-badge {
  font-size: 9px;
  background: #e2e2e2;
  padding: 2px 8px;
  border-radius: 9999px; /* Pill radius */
  color: #747474;
  font-weight: 600;
}

.user-tag {
  text-align: right;
  justify-content: flex-end;
}

.message {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-bottom: 12px; /* Tight conversation flow */
}

.message.user {
  align-items: flex-end;
}

.message.assistant {
  align-items: flex-start;
}

.user-message-container {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 85%; /* Let text breathe a bit more */
}

.user-content-row {
  display: flex;
  align-items: flex-start; /* Changed to start so avatar aligns with tag */
  gap: 12px;
}

.user-col {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.assistant-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 90%;
}

.msg-time {
  font-size: 10px;
  color: #a0a4ae;
  margin-top: 6px; /* Just beneath the bubble */
  font-family: 'SF Mono', 'Menlo', monospace;
  letter-spacing: 0.05em;
}

.ai-time {
  padding-left: 4px; /* Align slightly inwards matching the bubble */
}

.user-col {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.user-avatar {
  background: #65a30d; 
  color: #fff;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
  margin-top: 24px;
}

.assistant-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message-bubble {
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.5;
  letter-spacing: -0.01em;
  white-space: pre-wrap;
  font-weight: 400;
}

/* User Message: White bubble, bordered */
.message-bubble.user-bubble {
  background: #ffffff; 
  color: #1a1c1c;
  border-radius: 12px 12px 0px 12px; /* Tighter 12px radius */
  border: 1px solid #f0f1f1;
  padding: 8px 12px; 
  box-shadow: 0 2px 12px rgba(0,0,0,0.02);
}

/* Assistant Message: Glassmorphism */
.glass-ai {
  background: rgba(0, 0, 0, 0.03); 
  color: #1a1c1c; 
  border-radius: 12px 12px 12px 0px; 
  border: none;
  padding: 8px 12px; 
}

.welcome-bubble {
  background: #f7f7f8;
  border-radius: 16px;
  padding: 20px 24px;
  border: none;
  box-shadow: none;
}

.welcome-text {
  font-size: 13px;
  font-weight: 400;
  color: #1a1c1c;
  margin: 0 0 16px 0;
  line-height: 1.6;
  letter-spacing: -0.01em;
}

.bubble-text {
  margin: 0;
}

/* Stitch Welcome Options Layout */
.stitched-options {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.stitch-card {
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.03);
  border-radius: 12px;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 500;
  color: #1a1c1c;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0, 1);
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

.stitch-card .emoji {
  font-size: 14px;
}

.stitch-card:hover {
  background: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  border-color: rgba(0,0,0,0.06);
}

.message-actions {
  margin-top: 16px;
}

.stitch-primary-btn {
  background: #000;
  border: none;
  color: #fff;
  border-radius: 99px;
  padding: 8px 24px;
  font-weight: 500;
}

.stitch-primary-btn:hover {
  background: rgba(0,0,0,0.8);
  color: #fff;
}

.typing {
  color: rgba(0, 0, 0, 0.4);
}

/* Stitch Input Bar styling */
.input-area-container {
  padding: 16px 32px;
  background: #ffffff;
  border-top: 1px solid rgba(0,0,0,0.05);
}

.input-area.pill-style {
  background: #f3f3f4; /* surface-container-low */
  border-radius: 9999px; /* Absolute pill */
  padding: 4px 6px 4px 16px;
  border: 2px solid transparent; 
  display: flex;
  flex-direction: row;
  align-items: flex-end; /* vertically align tools with bottom of expanding textarea */
  transition: all 0.2s ease;
  min-height: 40px; 
  width: 100%;
  box-sizing: border-box;
  gap: 12px;
}

.input-area.pill-style:focus-within {
  border-color: rgba(0,0,0,0.08); /* ringing effect */
}

.chat-native-textarea {
  border: none;
  background: transparent;
  flex: 1;
  font-family: inherit;
  font-size: 13px;
  font-weight: 400;
  letter-spacing: -0.01em;
  color: #1a1c1c;
  outline: none;
  resize: none; 
  min-height: 20px;
  height: auto;
  line-height: 1.5;
  padding: 5px 0; 
  overflow-y: hidden;
}

.chat-native-textarea::placeholder {
  color: #a0a4ae;
}

.left-tools {
  display: flex;
  gap: 12px;
  color: #a0a4ae;
  padding-bottom: 6px; /* Offset to center with 1 line of text */
}

.tool-icon {
  font-size: 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.tool-icon:hover {
  color: #000;
}

.right-tools {
  display: flex;
  align-items: center;
}

.stitch-send-btn {
  background: #0d99ff; /* Same as new session btn */
  color: #fff;
  border: none;
  height: 32px; /* Super slim button to allow pill to shrink */
  padding: 0 16px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.15em;
}

.stitch-send-btn .el-icon {
  font-size: 12px;
}

.stitch-send-btn:hover {
  background: #0a8bed;
  transform: scale(0.98);
}

.stitch-send-btn:active {
  transform: scale(0.95);
}

.stitch-send-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

/* Locked input when no mode selected */
.chat-native-textarea.is-locked {
  cursor: not-allowed;
  opacity: 0.5;
}

.chat-native-textarea.is-locked::placeholder {
  color: #b0b4be;
  font-style: italic;
}

/* Hint flash on options when user tries to type without selecting */
@keyframes hint-flash {
  0%, 100% { box-shadow: 0 0 0 0 transparent; }
  50% { box-shadow: 0 0 0 3px rgba(0, 88, 188, 0.15); }
}
.stitched-options.hint-flash .stitch-card {
  animation: hint-flash 0.3s ease 2;
}

/* ─── Responsive: expand breathing room on large monitors ─── */
@media screen and (min-width: 1920px) {
  .stitch-header {
    padding: 0 32px;
  }
  .messages-container {
    padding: 28px 40px;
  }
  .input-area-container {
    padding: 20px 40px;
  }
}

@media screen and (min-width: 2560px) {
  .stitch-header {
    padding: 0 48px;
  }
  .messages-container {
    padding: 32px 56px;
  }
  .input-area-container {
    padding: 24px 56px;
  }
}
</style>
