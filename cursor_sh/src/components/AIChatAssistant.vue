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
          <!-- Welcome + Quick Actions -->
          <div v-if="!selectedMode" class="welcome-section message assistant">
            <div class="assistant-wrapper">
              <div class="assistant-tag"><span class="engine-name">Catalyst Engine</span> <span class="pro-badge">PRO</span></div>
              <div class="message-bubble glass-ai welcome-bubble">
                <p class="welcome-text">您好，我是 Unique Video AI 的项目顾问。</p>
                <p class="welcome-sub">我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多一线品牌提供过高品质视觉解决方案。</p>
                <div class="options-container stitched-options">
                  <div class="option-card stitch-card" @click="selectMode('order_create')">
                    <span class="opt-text">咨询下单</span>
                    <span class="opt-desc">梳理项目需求，创建订单</span>
                  </div>
                  <div class="option-card stitch-card" @click="selectMode('order_query')">
                    <span class="opt-text">查看订单</span>
                    <span class="opt-desc">查询订单进展与状态</span>
                  </div>
                  <div class="option-card stitch-card" @click="selectMode('business_intro')">
                    <span class="opt-text">了解业务</span>
                    <span class="opt-desc">服务体系与过往案例</span>
                  </div>
                </div>
                <p class="welcome-hint">也可以直接在下方输入您的问题，系统将自动识别并路由至对应流程。</p>
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
                  <!-- 需求收集完成后：内嵌可编辑表单 -->
                  <div v-if="msg.isCompletePrompt && !msg.formHidden" class="inline-form-section">
                    <div v-if="extractLoading" class="form-loading">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      <span>正在为您整理需求信息...</span>
                    </div>
                    <template v-else-if="inlineFormData">
                      <p class="form-intro">以下各项均可直接修改，也可通过对话补充调整：</p>
                      <div class="inline-form">
                        <div class="form-field" v-for="field in formFields" :key="field.key">
                          <label class="field-label">{{ field.label }}</label>
                          <input
                            v-if="!field.multiline"
                            type="text"
                            class="field-input"
                            v-model="inlineFormData[field.key]"
                            :placeholder="field.placeholder"
                          />
                          <textarea
                            v-else
                            class="field-textarea"
                            v-model="inlineFormData[field.key]"
                            :placeholder="field.placeholder"
                            rows="2"
                          ></textarea>
                        </div>
                      </div>
                      <div class="inline-form-actions">
                        <button class="comp-btn comp-btn-ghost" @click="handleContinueEditing(msg)">继续对话补充</button>
                        <button class="comp-btn comp-btn-primary" @click="handleSubmitOrder">确认无误，提交订单</button>
                      </div>
                      <p class="auto-draft-notice" v-if="draftSavedOrderId">已自动保存至草稿箱</p>
                    </template>
                  </div>
                  <!-- 订单列表卡片展示 -->
                  <div v-if="msg.isOrderList && msg.orders" class="inline-form-section">
                    <div class="order-list-cards">
                      <div v-for="order in msg.orders" :key="order.id" class="order-card-inline" @click="goToOrderDetail(order.id)">
                        <div class="order-card-header">
                          <span class="order-num">{{ order.orderNumber || order.order_number }}</span>
                          <span class="order-status" :class="'status-' + order.status">{{ getStatusText(order.status) }}</span>
                        </div>
                        <div class="order-card-body">
                          <div class="order-info-row"><span class="info-label">类型</span><span class="info-val">{{ getTypeText(order.orderType || order.order_type) }}</span></div>
                          <div class="order-info-row" v-if="order.brand"><span class="info-label">品牌</span><span class="info-val">{{ order.brand }}</span></div>
                          <div class="order-info-row" v-if="order.city"><span class="info-label">城市</span><span class="info-val">{{ order.city }}</span></div>
                          <div class="order-info-row"><span class="info-label">时间</span><span class="info-val">{{ formatOrderDate(order.createdAt || order.created_at) }}</span></div>
                        </div>
                        <div class="order-card-footer">
                          <span class="view-detail-link">查看详情 →</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <!-- 案例视频卡片 -->
                  <div v-if="msg.isCaseList && msg.cases" class="inline-form-section">
                    <div class="case-video-cards">
                      <div v-for="c in msg.cases" :key="c.id" class="case-card">
                        <div class="case-card-video" v-if="c.video_url">
                          <video
                            :src="c.video_url"
                            controls
                            preload="metadata"
                            :poster="c.thumbnail_url || ''"
                            class="case-video-player"
                          ></video>
                        </div>
                        <div class="case-card-info">
                          <div class="case-title">{{ c.title }}</div>
                          <div class="case-desc">{{ c.description }}</div>
                          <div class="case-meta">
                            <span class="case-tag">{{ getTypeText(c.category) }}</span>
                            <span class="case-duration" v-if="c.duration">{{ c.duration }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <!-- 引导下单按钮 -->
                  <div v-if="msg.isGuideToOrder" class="guide-order-section">
                    <div class="guide-btns">
                      <button class="comp-btn comp-btn-primary" @click="switchToOrderCreate">开始下单</button>
                      <button class="comp-btn comp-btn-ghost" @click="goToBrowse('ai_3d_custom')">手动填写表单</button>
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
            placeholder="描述您的需求，或直接输入问题..."
            class="chat-native-textarea"
            @input="adjustTextareaHeight"
            @keydown.enter.prevent="sendMessage"
            :disabled="isLoading || isTyping"
            @focus="handleInputFocus"
            rows="1"
          ></textarea>
          
          <!-- Right tools & send -->
          <div class="right-tools">
            <button
              class="stitch-send-btn"
              :class="{ disabled: isLoading || isTyping || !inputMsg.trim() }"
              @click="sendMessage"
            >
              <span>Send</span>
              <el-icon><Top /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 确认函弹窗 -->
    <OrderConfirmationDialog
      v-model="showConfirmation"
      :order-number="confirmOrderNumber"
      :order-type="confirmOrderType"
      :form-data="inlineFormData || {}"
      @confirm="handleConfirmationDone"
      @cancel="showConfirmation = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Close, Right, Top, QuestionFilled, CirclePlusFilled, PictureRounded, Search, Clock, Delete, ArrowUp, Loading } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { logger } from '@/utils/logger'
import OrderConfirmationDialog from '@/components/OrderConfirmationDialog.vue'
import type { OrderType } from '@/types'

const emit = defineEmits(['close', 'mode-change'])
const router = useRouter()
const orderStore = useOrderStore()

// auth header helper
const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

// ===== 内嵌表单相关状态 =====
const inlineFormData = ref<Record<string, string> | null>(null)
const draftSavedOrderId = ref<string | null>(null)
const showConfirmation = ref(false)
const confirmOrderNumber = ref('')
const confirmOrderType = ref<OrderType>('ai_3d_custom')

// 表单字段定义
const formFields = [
  { key: 'brand', label: '品牌/产品', placeholder: '品牌名称和产品关键词', multiline: false },
  { key: 'target_group', label: '目标受众', placeholder: '内容面向的人群', multiline: false },
  { key: 'content', label: '内容需求', placeholder: '期望的创意画面和场景描述', multiline: true },
  { key: 'city', label: '投放城市/站点', placeholder: '投放地点', multiline: false },
  { key: 'budget', label: '制作预算', placeholder: '预算范围', multiline: false },
  { key: 'online_time', label: '预计上刊时间', placeholder: '预期上线日期', multiline: false },
  { key: 'background', label: '项目背景', placeholder: '选填', multiline: false },
  { key: 'style', label: '风格偏好', placeholder: '选填，如赛博朋克、极简、写实等', multiline: false },
  { key: 'media_size', label: '投放媒体及尺寸', placeholder: '选填', multiline: false },
  { key: 'technology', label: '技术需求', placeholder: '选填，如分辨率、格式等', multiline: false },
]

const selectedMode = ref<string | null>(null)
const messages = ref<any[]>([])
const inputMsg = ref('')
const isLoading = ref(false)
const isTyping = ref(false) // AI 正在逐字输出中
const extractLoading = ref(false) // 信息提取整理中
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
      let parsedArr = Array.isArray(parsed) ? parsed : [parsed]
      // 按照 ID（时间戳）升序排列，最新的记录在最下方（靠近输入框）
      parsedArr.sort((a, b) => Number(a.id) - Number(b.id))
      savedHistories.value = parsedArr
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
  
  histories.push(session)
  // 按时间升序排序（最新的在最下方，靠近输入框）
  histories.sort((a, b) => Number(a.id) - Number(b.id))
  
  // 如果超过 5 条，保留最新的 5 条
  if (histories.length > 5) histories = histories.slice(-5)
  
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
      
      // 打字结束后自动让输入框获取焦点，方便用户继续输入
      nextTick(() => {
        textareaRef.value?.focus()
      })
      
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

// ===== 订单展示辅助函数 =====
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    draft: '草稿', pending_assign: '待分配', in_production: '制作中',
    pending_review: '待审核', review_rejected: '审核驳回',
    preview_ready: '初稿就绪', final_preview: '终稿就绪',
    revision_needed: '需修改', completed: '已完成', cancelled: '已取消'
  }
  return map[status] || status
}

const getTypeText = (type: string) => {
  const map: Record<string, string> = {
    video_purchase: '裸眼3D成片购买适配',
    ai_3d_custom: 'AI裸眼3D内容定制',
    digital_art: '数字艺术内容定制'
  }
  return map[type] || type
}

const formatOrderDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// 从业务介绍切换到下单 Agent
const switchToOrderCreate = () => {
  selectedMode.value = 'order_create'
  emit('mode-change', 'order_create')
  messages.value.push({
    role: 'assistant',
    content: '请提供项目的基本信息，我将逐步为您梳理完整的需求。首先，请告知品牌名称和内容方向。',
    timestamp: getCurrentTime()
  })
  scrollToBottom()
}

const selectMode = async (mode: string) => {
  selectedMode.value = mode
  emit('mode-change', mode)
  
  if (mode === 'order_create') {
    // 需求收集 Agent 开场白
    isLoading.value = true
    try {
      const response = await fetch(`/ai/start?session_id=${session_id.value}`)
      if (!response.ok || response.headers.get('content-type')?.includes('text/html')) {
        throw new Error('API not available')
      }
      const result = await response.json()
      if (result.reply) typewriterEffect(result.reply)
    } catch (e) {
      const fallback = '您好，我是 Unique Video AI 的项目顾问。\n\n请描述您的项目需求，包括品牌名称、内容方向、预算和时间节点等关键信息。我将协助您完成完整的需求梳理。\n\n**首先，请告知您的项目背景。**'
      typewriterEffect(fallback)
    } finally {
      isLoading.value = false
    }
  } else if (mode === 'order_query') {
    // 订单查询 Agent
    isLoading.value = true
    try {
      const response = await fetch('/ai/query-orders', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message: '查看我的订单', history: [] })
      })
      if (!response.ok) throw new Error('query failed')
      const data = await response.json()
      // 将订单卡片附加到打字机消息完成后的同一条消息上
      typewriterEffect(data.message || '正在为您查询订单...', () => {
        if (data.orders && data.orders.length > 0) {
          // 找到打字机刚刚写入的那条消息，给它挂载订单卡片
          const lastMsg = messages.value[messages.value.length - 1]
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.isOrderList = true
            lastMsg.orders = data.orders
          }
          scrollToBottom()
        }
      })
    } catch (e) {
      typewriterEffect('正在为您查询订单信息，请稍候...\n\n（当前为离线模式，请确保已登录后重试）')
    } finally {
      isLoading.value = false
    }
  } else if (mode === 'business_intro') {
    // 业务介绍 Agent
    isLoading.value = true
    try {
      const response = await fetch('/ai/business-intro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '请介绍一下你们的业务', history: [] })
      })
      if (!response.ok) throw new Error('intro failed')
      const data = await response.json()
      const cleanMsg = (data.message || '').replace('【引导下单】', '').trim()
      typewriterEffect(cleanMsg)
    } catch (e) {
      const fallback = 'Unique Video AI 提供三大核心业务板块：\n\n**裸眼3D成片购买适配** — 上百款精选模板，5个工作日交付\n**AI裸眼3D内容定制** — 品牌专属定制，15个工作日交付\n**数字艺术内容定制** — 沉浸式互动体验，7个工作日交付\n\n如需了解某个板块的详细信息或过往案例，请直接告知。'
      typewriterEffect(fallback)
    } finally {
      isLoading.value = false
    }
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
  logger.logAction('AI', 'send_message', { mode: selectedMode.value, textLength: userText.length })
  
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
  
  // 如果还没有选择模式，先做意图分类
  if (!selectedMode.value) {
    isLoading.value = true
    try {
      const classifyRes = await fetch('/ai/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
      })
      if (classifyRes.ok) {
        const { intent } = await classifyRes.json()
        selectedMode.value = intent
        emit('mode-change', intent)
      } else {
        selectedMode.value = 'order_create'
        emit('mode-change', 'order_create')
      }
    } catch (e) {
      // 降级：关键词快速匹配
      if (/订单|进度|状态|查看|查询/.test(userText)) {
        selectedMode.value = 'order_query'
      } else if (/了解|介绍|业务|案例|服务/.test(userText)) {
        selectedMode.value = 'business_intro'
      } else {
        selectedMode.value = 'order_create'
      }
      emit('mode-change', selectedMode.value)
    } finally {
      isLoading.value = false
    }
  }
  
  // 根据当前意图路由到对应 handler
  if (selectedMode.value === 'order_create') {
    await handleCustomAiChat(userText)
  } else if (selectedMode.value === 'order_query') {
    await handleOrderQuery(userText)
  } else if (selectedMode.value === 'business_intro') {
    await handleBusinessIntro(userText)
  } else {
    await handleGeneral(userText)
  }
}

// ===== 订单查询 handler =====
const handleOrderQuery = async (userText: string) => {
  isLoading.value = true
  try {
    const historyMsgs = messages.value
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }))
    const response = await fetch('/ai/query-orders', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ message: userText, history: historyMsgs })
    })
    if (!response.ok) throw new Error('query failed')
    const data = await response.json()
    typewriterEffect(data.message || '暂无更多信息', () => {
      if (data.orders && data.orders.length > 0) {
        // 将卡片挂载到打字机刚刚写入的同一条消息上
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.isOrderList = true
          lastMsg.orders = data.orders
        }
        scrollToBottom()
      }
    })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '查询遇到问题，请稍后重试。', timestamp: getCurrentTime() })
  } finally {
    isLoading.value = false
  }
}

// 订单卡片点击跳转
const goToOrderDetail = (orderId: string) => {
  if (!orderId) return
  router.push(`/user/orders/${orderId}`)
}

// ===== 业务介绍 handler =====
const handleBusinessIntro = async (userText: string) => {
  isLoading.value = true
  try {
    const historyMsgs = messages.value
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }))
    const response = await fetch('/ai/business-intro', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, history: historyMsgs })
    })
    if (!response.ok) throw new Error('intro failed')
    const data = await response.json()
    const replyContent = data.message || ''
    const cleanMsg = replyContent.replace('【引导下单】', '').trim()
    const cases = data.cases || []
    
    typewriterEffect(cleanMsg, () => {
      // 如果有案例数据，展示案例视频卡片
      if (cases.length > 0) {
        messages.value.push({
          role: 'assistant',
          content: '',
          isCaseList: true,
          cases: cases,
          timestamp: getCurrentTime()
        })
        scrollToBottom()
      }
      // 如果 AI 建议引导下单
      if (replyContent.includes('【引导下单】')) {
        messages.value.push({
          role: 'assistant',
          content: '如您已有初步的项目构想，可以进入需求梳理流程，由我协助您完成订单创建。',
          isGuideToOrder: true,
          timestamp: getCurrentTime()
        })
        scrollToBottom()
      }
    })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '获取信息时遇到问题，请稍后重试。', timestamp: getCurrentTime() })
  } finally {
    isLoading.value = false
  }
}

// ===== 通用问答 handler =====
const handleGeneral = async (userText: string) => {
  isLoading.value = true
  try {
    const historyMsgs = messages.value
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }))
    const response = await fetch('/ai/general', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: session_id.value, message: userText, history: historyMsgs })
    })
    if (!response.ok) throw new Error('general failed')
    const data = await response.json()
    typewriterEffect(data.message || '感谢您的提问！')
  } catch (e) {
    const fallback = '我是 Unique Video AI 的项目顾问。\n\n我可以协助您咨询下单、查看订单或了解我们的业务。请问您需要哪方面的支持？'
    typewriterEffect(fallback)
  } finally {
    isLoading.value = false
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
    const cleanContent = replyContent.replace('【需求收集完成】', '').trim();
    
    // 前端兜底：至少3轮用户对话才允许触发完成
    const userMsgCount = messages.value.filter(m => m.role === 'user').length;
    const shouldComplete = replyContent.includes('【需求收集完成】') && userMsgCount >= 3;
    
    typewriterEffect(cleanContent, async () => {
      if (shouldComplete) {
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.isCompletePrompt = true
        }
        await autoExtractAndSaveDraft()
      }
    })

  } catch (error) {
    // 降级兜底：前端 Mock 模拟对话收集需求（至少5轮）
    const userMsgCount = messages.value.filter(m => m.role === 'user').length;
    
    const mockReplies: Record<number, string> = {
      1: '好的，产品很有意思。为了让最终视觉效果更匹配，您期望这支视频想要打动哪类年轻受众呢？（比如在校学生、或者职场新人等）',
      2: '明白。在视觉呈现上，您大概有什么特定的风格倾向吗？（比如赛博朋克、极简风，或者写实拟真都可以）',
      3: '非常清晰。接下来想了解一下，您准备把这支内容具体投放在哪个城市或站点呢？',
      4: '好的。那制作预算大概在什么范围呢？这样我可以帮您推荐最合适的方案。',
      5: '最后一个问题：您期望这支内容什么时候上线呢？了解时间节点后我就可以帮您汇总所有信息了。',
    }
    
    setTimeout(() => {
      if (userMsgCount <= 5 && mockReplies[userMsgCount]) {
        messages.value.push({ 
          role: 'assistant', 
          content: mockReplies[userMsgCount], 
          timestamp: getCurrentTime() 
        })
      } else {
        const summaryMsg = '需求信息收集完毕，正在为您生成项目评估...'
        messages.value.push({ 
          role: 'assistant', 
          content: summaryMsg, 
          timestamp: getCurrentTime(),
          isCompletePrompt: true
        })
        // mock 数据填充表单
        inlineFormData.value = {
          brand: '示例品牌 (Mock)',
          target_group: '年轻群体',
          content: '裸眼3D视觉创意内容',
          city: '北京',
          budget: '10万以上',
          online_time: '2026年6月',
          background: '',
          style: '科技感设计',
          media_size: '',
          technology: ''
        }
      }
      isLoading.value = false
    }, 1000)
  }
}

// ===== 需求收集完成 -> 自动提取 + 专业评估 + 保存草稿 + 内嵌表单 =====
const autoExtractAndSaveDraft = async () => {
  extractLoading.value = true
  try {
    const formattedHistory = messages.value
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }));
    let extracted: Record<string, string> = {}
    try {
      const response = await fetch('/ai/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ history: formattedHistory })
      })
      if (response.ok) {
        const data = await response.json()
        if (Object.keys(data).length > 0) extracted = data
      }
    } catch (e) {
      console.error('extract failed:', e)
    }
    if (Object.keys(extracted).length === 0) {
      const brandMatch = messages.value.find(m => m.role === 'user')?.content.slice(0, 15) || '';
      extracted = { brand: brandMatch, target_group: '', content: '', city: '', budget: '', online_time: '', background: '', style: '', media_size: '', technology: '' }
    }
    for (const field of formFields) {
      if (!extracted[field.key]) extracted[field.key] = ''
    }
    
    // ===== 专业项目评估 =====
    let assessmentText = ''
    try {
      const assessRes = await fetch('/ai/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ extracted })
      })
      if (assessRes.ok) {
        const assessData = await assessRes.json()
        assessmentText = assessData.assessment || ''
      }
    } catch (e) {
      console.error('assess failed:', e)
    }
    
    // 展示专业评估（在表单之前）
    if (assessmentText) {
      // 找到最后一条 isCompletePrompt 的消息，替换其 content
      const lastCompleteMsg = messages.value.filter(m => m.isCompletePrompt).pop()
      if (lastCompleteMsg) {
        lastCompleteMsg.content = assessmentText
      } else {
        messages.value.push({
          role: 'assistant',
          content: assessmentText,
          isCompletePrompt: true,
          timestamp: getCurrentTime()
        })
      }
    }
    
    inlineFormData.value = extracted
    try {
      const orderType = selectedMode.value === 'digital_art' ? 'digital_art' : 'ai_3d_custom'
      const newOrder = await orderStore.createOrder({ orderType, ...extracted }, true)
      draftSavedOrderId.value = newOrder.id
    } catch (e) {
      console.error('auto save draft failed:', e)
    }
  } finally {
    extractLoading.value = false
    scrollToBottom()
  }
}

const handleContinueEditing = (msg: any) => {
  msg.formHidden = true
}

const handleSubmitOrder = () => {
  if (!inlineFormData.value) return
  confirmOrderType.value = (selectedMode.value === 'digital_art' ? 'digital_art' : 'ai_3d_custom') as OrderType
  confirmOrderNumber.value = draftSavedOrderId.value
    ? 'DRAFT-' + draftSavedOrderId.value.slice(-8).toUpperCase()
    : 'NEW-' + Date.now().toString(36).toUpperCase()
  showConfirmation.value = true
}

const handleConfirmationDone = async (data: { email: string; phone: string }) => {
  showConfirmation.value = false
  try {
    if (draftSavedOrderId.value) {
      await orderStore.updateOrder(draftSavedOrderId.value, {
        orderType: confirmOrderType.value,
        ...inlineFormData.value
      })
      await orderStore.updateOrderStatus(draftSavedOrderId.value, 'pending_assign')
    } else {
      await orderStore.createOrder({
        orderType: confirmOrderType.value,
        ...inlineFormData.value
      }, false)
    }
    messages.value.push({
      role: 'assistant',
      content: '🎉 订单已正式提交成功！我们的团队会尽快开始处理。您可以在"我的订单"中查看进度。',
      timestamp: getCurrentTime()
    })
    scrollToBottom()
    saveCurrentToHistory()
  } catch (e) {
    console.error('submit order failed', e)
    ElMessage.error('订单提交失败，请稍后重试')
  }
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
.comp-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

/* ===== 内嵌可编辑表单样式 ===== */
.inline-form-section {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.form-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0d99ff;
  font-size: 13px;
  padding: 12px 0;
}

.form-intro {
  font-size: 12px;
  color: #86868b;
  line-height: 1.5;
  margin: 0 0 14px 0;
}

.inline-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-field:nth-child(3) {
  grid-column: 1 / -1;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.field-input, .field-textarea {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  color: #1a1c1c;
  background: rgba(255, 255, 255, 0.7);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  width: 100%;
  box-sizing: border-box;
}

.field-input:focus, .field-textarea:focus {
  border-color: #0d99ff;
  box-shadow: 0 0 0 2px rgba(13, 153, 255, 0.1);
}

.field-input::placeholder, .field-textarea::placeholder {
  color: #c0c4cc;
  font-size: 12px;
}

.field-textarea {
  resize: vertical;
  min-height: 48px;
}

.inline-form-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  justify-content: flex-end;
}

.auto-draft-notice {
  font-size: 11px;
  color: #67c23a;
  margin: 8px 0 0 0;
  text-align: right;
}

/* ===== 新欢迎区样式 ===== */
.welcome-sub {
  font-size: 13px;
  color: #86868b;
  margin: 4px 0 16px 0;
  line-height: 1.5;
}

.welcome-hint {
  font-size: 12px;
  color: #a0a0a5;
  margin: 14px 0 0 0;
  text-align: center;
}

.opt-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.opt-desc {
  font-size: 11px;
  color: #86868b;
  margin-top: 2px;
}

.option-card.stitch-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 2px;
  padding: 14px 12px;
}

/* ===== 订单卡片样式 ===== */
.order-list-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-card-inline {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.6);
  transition: box-shadow 0.2s, transform 0.15s;
  cursor: pointer;
}

.order-card-inline:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.order-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.order-num {
  font-size: 13px;
  font-weight: 600;
  color: #1a1c1c;
  font-family: 'SF Mono', monospace;
}

.order-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.status-draft { background: #f0f0f5; color: #86868b; }
.status-pending_assign { background: #fff3e0; color: #e65100; }
.status-in_production { background: #e3f2fd; color: #1565c0; }
.status-pending_review { background: #fce4ec; color: #c62828; }
.status-preview_ready { background: #e8f5e9; color: #2e7d32; }
.status-completed { background: #e8f5e9; color: #1b5e20; }
.status-cancelled { background: #f5f5f5; color: #9e9e9e; }

.order-card-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.order-info-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.info-label {
  color: #86868b;
  min-width: 52px;
  flex-shrink: 0;
}

.info-val {
  color: #1a1c1c;
}

.order-card-footer {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  text-align: right;
}

.view-detail-link {
  font-size: 12px;
  color: #1565c0;
  font-weight: 500;
}

.order-card-inline:hover .view-detail-link {
  color: #0d47a1;
}

.status-revision_needed { background: #fff3e0; color: #e65100; }
.status-review_rejected { background: #fce4ec; color: #c62828; }
.status-final_preview { background: #e0f7fa; color: #00695c; }

/* ===== 引导下单区 ===== */
.guide-order-section {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.guide-btns {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* ===== 案例视频卡片 ===== */
.case-video-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.case-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.7);
  transition: box-shadow 0.2s, transform 0.15s;
}

.case-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.case-card-video {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #0a0a0a;
  position: relative;
}

.case-video-player {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.case-card-info {
  padding: 10px 14px 12px;
}

.case-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1c1c;
  margin-bottom: 4px;
}

.case-desc {
  font-size: 12px;
  color: #555;
  line-height: 1.5;
  margin-bottom: 8px;
}

.case-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.case-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #e3f2fd;
  color: #1565c0;
  font-weight: 500;
}

.case-duration {
  font-size: 11px;
  color: #86868b;
}
</style>



