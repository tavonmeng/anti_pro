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
            <input type="text" v-model="searchQuery" placeholder="搜索当前聊天与历史记录..." class="search-input" @input="onSearchInput" />
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
              <div v-if="!displayedHistories || displayedHistories.length === 0" class="history-empty">
                <el-icon><Clock /></el-icon>
                <span>{{ searchQuery ? '未找到相关历史记录' : '暂无历史记录' }}</span>
              </div>
              <template v-else>
                <div v-for="(history, hIndex) in displayedHistories" :key="history.id || hIndex" class="history-session-item">
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
                    <button class="history-clear-btn-icon" @click="deleteHistory(history.id)" title="删除记录">
                      <el-icon><Delete /></el-icon>
                    </button>
                    <button class="stitch-primary-btn history-restore-btn-new" @click="restoreHistory(history)">接着上回聊</button>
                  </div>
                  
                  <div class="session-divider" v-if="hIndex < savedHistories.length - 1"></div>
                </div>
              </template>
              <div class="history-master-divider" v-if="displayedHistories && displayedHistories.length > 0"></div>
            </div>
          </transition>
          <!-- Welcome + Quick Actions -->
          <div v-if="!selectedMode" class="welcome-section message assistant">
            <div class="assistant-wrapper">
              <div class="assistant-tag"><span class="engine-name">Catalyst Engine</span> <span class="pro-badge">PRO</span></div>
              <div class="message-bubble glass-ai welcome-bubble">
                <p class="welcome-text">
                  {{ welcomeTitleText }}<span v-if="!showWelcomeOptions && welcomeTitleText.length < welcomeTitleFull.length" class="typing-cursor">|</span>
                </p>
                <p class="welcome-sub" v-if="welcomeTitleText.length === welcomeTitleFull.length || showWelcomeOptions">
                  {{ welcomeDescText }}<span v-if="!showWelcomeOptions && welcomeDescText.length < welcomeDescFull.length" class="typing-cursor">|</span>
                </p>
                
                <transition name="fade">
                  <div v-if="showWelcomeOptions">
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
                </transition>
              </div>
            </div>
          </div>

          <!-- Chat History -->
          <div v-for="(msg, index) in displayedMessages" :key="index" :class="['message', msg.role]" v-show="!msg.isContextCarryOver">
            
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
                        <!-- 订单状态进度流水线 -->
                        <div class="order-progress-timeline" v-if="order.status !== 'cancelled'">
                          <div class="timeline-bg-line"></div>
                          <div class="timeline-progress-line" :style="{ width: getProgressWidth(order.status) }" :class="{'warning-line': order.status === 'revision_needed' || order.status === 'review_rejected'}"></div>
                          <div class="timeline-step" v-for="n in 4" :key="n" :class="getStepClass(order.status, n)">
                            <div class="step-dot">
                              <div class="pulse-ring" v-if="getStepClass(order.status, n) === 'step-active' || getStepClass(order.status, n) === 'step-warning'"></div>
                            </div>
                            <div class="step-label">{{ getStepLabel(n) }}</div>
                          </div>
                        </div>
                        <div class="order-progress-timeline cancelled-timeline" v-else>
                          <div class="timeline-bg-line"></div>
                          <div class="timeline-step step-cancelled">
                            <div class="step-dot"></div>
                            <div class="step-label">已取消</div>
                          </div>
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
                    <div class="guide-order-label">您可以选择感兴趣的业务板块开始需求梳理：</div>
                    <div class="guide-btns">
                      <button class="comp-btn comp-btn-primary" @click="switchToOrderCreate('ai_3d_custom')">AI裸眼3D内容定制</button>
                      <button class="comp-btn comp-btn-outline" @click="switchToOrderCreate('video_purchase')">裸眼3D成片购买适配</button>
                      <button class="comp-btn comp-btn-outline" @click="switchToOrderCreate('digital_art')">数字艺术内容定制</button>
                    </div>
                    <div class="guide-btns" style="margin-top: 6px;">
                      <button class="comp-btn comp-btn-ghost" @click="goToBrowse('ai_3d_custom')">或手动填写表单</button>
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
        <div class="input-area pill-style" :class="{ 'is-voice-recording': isRecording || isTranscribing }">
          <template v-if="!isRecording && !isTranscribing">
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
            :disabled="isLoading || isTyping || isRecording"
            @focus="handleInputFocus"
            rows="1"
          ></textarea>
          
          <!-- Right tools & send -->
          <div class="right-tools">
            <!-- 语音输入按钮 -->
            <button
              class="voice-btn"
              :class="{ recording: isRecording }"
              @click="toggleVoiceInput"
              :title="isRecording ? '停止录音' : '语音输入'"
            >
              <span v-if="isRecording" class="rec-pulse"></span>
              <svg v-if="!isRecording" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2"/>
              </svg>
            </button>

            <button
              class="stitch-send-btn"
              :class="{ disabled: isLoading || isTyping || !inputMsg.trim() }"
              @click="sendMessage"
            >
              <span>Send</span>
              <el-icon><Top /></el-icon>
            </button>
          </div>
          </template>

          <template v-else>
            <!-- ChatGPT style voice recording overlay -->
            <div class="left-tools">
              <el-icon class="tool-icon voice-plus-icon"><Plus /></el-icon>
            </div>
            
            <div class="waveform-container" :style="{ opacity: isTranscribing ? 0.5 : 1 }">
              <canvas ref="waveformCanvas" class="waveform-canvas"></canvas>
            </div>

            <div class="right-tools voice-actions">
              <button class="voice-action-btn cancel" @click="cancelRecording" :disabled="isTranscribing">
                <el-icon><Close /></el-icon>
              </button>

              <div v-if="isTranscribing" class="voice-transcribing-indicator">
                <div class="transcribing-spinner"></div>
              </div>
              <button v-else class="voice-action-btn confirm" @click="confirmRecording">
                <el-icon><Check /></el-icon>
              </button>
            </div>
          </template>
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
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Close, Right, Top, QuestionFilled, CirclePlusFilled, PictureRounded, Search, Clock, Delete, ArrowUp, Loading, Plus, Check } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { useAuthStore } from '@/stores/auth'
import { logger } from '@/utils/logger'
import OrderConfirmationDialog from '@/components/OrderConfirmationDialog.vue'
import type { OrderType } from '@/types'

const emit = defineEmits(['close', 'mode-change'])
const router = useRouter()
const orderStore = useOrderStore()
const authStore = useAuthStore()

const searchQuery = ref('')

// ========== 语音输入 ==========
const isRecording = ref(false)
const realtimeText = ref('')          // 实时识别中间结果
const finalTranscripts = ref<string[]>([])  // 已确认的句子
const recordingDuration = ref(0)
const waveformCanvas = ref<HTMLCanvasElement | null>(null)
let waveformHistory: number[] = []
let mediaStream: MediaStream | null = null
let audioContext: AudioContext | null = null
let scriptProcessor: ScriptProcessorNode | null = null
let audioAnalyser: AnalyserNode | null = null
let visualizerFrameId = 0
let durationTimer: ReturnType<typeof setInterval> | null = null
let audioChunks: Int16Array[] = []        // 本地存储 PCM 音频块
const isTranscribing = ref(false)          // 识别中的加载状态

const toggleVoiceInput = async () => {
  if (isRecording.value) {
    confirmRecording()
  } else {
    await startRecording()
  }
}

const startRecording = async () => {
  try {
    // 获取麦克风权限
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      }
    })

    // 创建 AudioContext
    audioContext = new AudioContext({ sampleRate: 16000 })
    const source = audioContext.createMediaStreamSource(mediaStream)

    // ScriptProcessorNode 采集 PCM 数据（4096 buffer）
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1)

    // 分析器节点（用于 ChatGPT 样式的波浪线动效）
    audioAnalyser = audioContext.createAnalyser()
    audioAnalyser.fftSize = 256
    audioAnalyser.smoothingTimeConstant = 0.7
    source.connect(audioAnalyser)

    // 采集音频数据（本地存储，不实时发送）
    audioChunks = []
    scriptProcessor.onaudioprocess = (e) => {
      if (!isRecording.value) return
      const float32 = e.inputBuffer.getChannelData(0)
      const int16 = new Int16Array(float32.length)
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]))
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
      }
      audioChunks.push(new Int16Array(int16))
    }

    source.connect(scriptProcessor)
    scriptProcessor.connect(audioContext.destination)

    // 重置状态
    isRecording.value = true
    realtimeText.value = ''
    finalTranscripts.value = []
    recordingDuration.value = 0
    waveformHistory = []
    durationTimer = setInterval(() => {
      recordingDuration.value++
    }, 1000)

    // 等 Vue 渲染出 canvas DOM 后再启动可视化
    await nextTick()
    const startVisualizer = () => {
      if (!isRecording.value || !audioAnalyser) return
      const dataArray = new Uint8Array(audioAnalyser.frequencyBinCount)
      let lastPushTime = 0
      const tick = (timestamp: number) => {
        if (!isRecording.value || !audioAnalyser) return
        // 每 ~80ms 推一次数据（约 12fps），匹配 ChatGPT 的速度
        if (timestamp - lastPushTime > 80) {
          audioAnalyser.getByteFrequencyData(dataArray)
          let sum = 0
          for (let i = 0; i < dataArray.length; i++) sum += dataArray[i] * dataArray[i]
          let rms = Math.sqrt(sum / dataArray.length) / 255
          waveformHistory.push(Math.min(1, rms * 2.5))
          if (waveformHistory.length > 300) waveformHistory.shift()
          lastPushTime = timestamp
        }
        drawWaveform()
        visualizerFrameId = requestAnimationFrame(tick)
      }
      visualizerFrameId = requestAnimationFrame(tick)
    }
    startVisualizer()

  } catch (err: any) {
    console.error('[ASR] Start failed:', err)
    if (err.name === 'NotAllowedError') {
      ElMessage.error('请允许浏览器使用麦克风')
    } else {
      ElMessage.error('语音输入启动失败: ' + (err.message || '未知错误'))
    }
    cleanupRecording()
  }
}

/** 清理录音资源（不做识别） */
const cleanupRecording = () => {
  isRecording.value = false
  if (durationTimer) { clearInterval(durationTimer); durationTimer = null }
  if (visualizerFrameId) { cancelAnimationFrame(visualizerFrameId); visualizerFrameId = 0 }
  if (scriptProcessor) { scriptProcessor.disconnect(); scriptProcessor = null }
  if (audioContext) { audioContext.close().catch(() => {}); audioContext = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  audioAnalyser = null
}

/** 取消录音 */
const cancelRecording = () => {
  cleanupRecording()
  audioChunks = []
  realtimeText.value = ''
  finalTranscripts.value = []
}

/** 确认录音 → 发送到后端做一次性识别 */
const confirmRecording = async () => {
  // 先停掉录音硬件
  cleanupRecording()

  if (audioChunks.length === 0) return

  // 拼接所有音频块
  const totalLen = audioChunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const fullAudio = new Int16Array(totalLen)
  let offset = 0
  for (const chunk of audioChunks) {
    fullAudio.set(chunk, offset)
    offset += chunk.length
  }
  audioChunks = []

  // 发送给后端识别
  isTranscribing.value = true
  try {
    const blob = new Blob([fullAudio.buffer], { type: 'audio/pcm' })
    const formData = new FormData()
    formData.append('audio', blob, 'recording.pcm')

    const token = localStorage.getItem('token')
    const resp = await fetch('/api/asr/recognize', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    })
    const result = await resp.json()
    if (result.text) {
      // 打字机效果：逐字显示识别结果
      isTranscribing.value = false
      const text = result.text
      const base = inputMsg.value || ''
      let idx = 0
      const typeInterval = setInterval(() => {
        if (idx < text.length) {
          inputMsg.value = base + text.slice(0, idx + 1)
          idx++
          nextTick(() => adjustTextareaHeight())
        } else {
          clearInterval(typeInterval)
        }
      }, 30)
      return  // 跳过 finally 中的 isTranscribing = false
    } else if (result.error) {
      ElMessage.error('语音识别失败: ' + result.error)
    }
  } catch (err: any) {
    ElMessage.error('语音识别请求失败: ' + (err.message || '网络错误'))
  } finally {
    isTranscribing.value = false
  }
}

const drawWaveform = () => {
  const canvas = waveformCanvas.value
  if (!canvas) return
  const dpr = window.devicePixelRatio || 1
  const parent = canvas.parentElement
  if (!parent) return
  
  const rect = parent.getBoundingClientRect()
  const w = Math.floor(rect.width * dpr)
  const h = Math.floor(rect.height * dpr)
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w
    canvas.height = h
    canvas.style.width = rect.width + 'px'
    canvas.style.height = rect.height + 'px'
  }

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  const barW = 2.5 * dpr
  const gap = 1.5 * dpr
  const step = barW + gap
  const midY = canvas.height / 2
  const totalBars = Math.floor(canvas.width / step)
  const minH = 2 * dpr  // 静音时的小圆点高度
  const maxH = canvas.height * 0.85
  const len = waveformHistory.length

  for (let i = 0; i < totalBars; i++) {
    // 最新数据在最右边（i=totalBars-1），向左回溯
    const barIndex = totalBars - 1 - i
    const dataIdx = len - 1 - i  // 从历史末尾往前取

    let val = 0
    let hasData = false
    if (dataIdx >= 0 && dataIdx < len) {
      val = waveformHistory[dataIdx]
      hasData = true
    }

    const barH = Math.max(minH, val * maxH)
    const x = barIndex * step
    const y = midY - barH / 2

    // 有数据的条用深色，无数据的用浅灰色小圆点
    ctx.fillStyle = hasData ? '#2c2c2e' : '#d1d1d6'
    ctx.beginPath()
    ctx.roundRect(x, y, barW, barH, barW / 2)
    ctx.fill()
  }
}



const onSearchInput = () => {
  if (searchQuery.value && !showHistory.value) {
    showHistory.value = true
    loadSavedHistory()
  }
}

// auth header helper
const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

// ==== 欢迎打字机动画逻辑 ====
const welcomeTitleFull = '您好，我是 Unique Video AI 的项目顾问。'
const welcomeDescFull = '我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多一线品牌提供过高品质视觉解决方案。'
const welcomeTitleText = ref('')
const welcomeDescText = ref('')
const showWelcomeOptions = ref(false)

const playWelcomeAnimation = () => {
  welcomeTitleText.value = ''
  welcomeDescText.value = ''
  showWelcomeOptions.value = false
  
  let charIndexTitle = 0
  let charIndexDesc = 0
  const speed = 25 // 打字速度
  
  const typeNext = () => {
    if (charIndexTitle < welcomeTitleFull.length) {
      welcomeTitleText.value += welcomeTitleFull.charAt(charIndexTitle)
      charIndexTitle++
      setTimeout(typeNext, speed)
    } else if (charIndexDesc < welcomeDescFull.length) {
      welcomeDescText.value += welcomeDescFull.charAt(charIndexDesc)
      charIndexDesc++
      setTimeout(typeNext, speed)
    } else {
      showWelcomeOptions.value = true
      scrollToBottom()
    }
  }
  
  setTimeout(typeNext, 300) // 稍作延迟开始
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
const businessType = ref<string>('ai_3d_custom') // ai_3d_custom / video_purchase / digital_art
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
        router.push(`/user/create-order/${businessType.value}`)
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
  // 如果当前已有对话，保存并将顶部历史面板展开，形成"旧对话被折叠顶上去"的视觉效果
  if (messages.value.length > 0) {
    saveCurrentToHistory()
    loadSavedHistory()
    showHistory.value = true
  } else {
    // 如果当前已经是空白对话，说明用户是单纯想退出历史面板，直接关闭即可
    showHistory.value = false
  }
  
  messages.value = []
  selectedMode.value = null
  session_id.value = Math.random().toString(36).substring(7)
  playWelcomeAnimation()
}

// --- 历史聊天记录 ---
const HISTORY_KEY = 'ai_chat_last_session'
const showHistory = ref(false)

const displayedMessages = computed(() => {
  if (!searchQuery.value.trim()) return messages.value
  const q = searchQuery.value.toLowerCase()
  return messages.value.filter(m => {
    // 包含文本，或者是有卡片内容的特殊气泡
    if (m.content && m.content.toLowerCase().includes(q)) return true
    if (m.isOrderList || m.isCaseList || m.isGuideToOrder || m.isPurchasePrompt || m.isCompletePrompt) return true
    return false
  })
})

interface SavedSession {
  id: string
  messages: any[]
  mode: string | null
  savedAt: string
}

const savedHistories = ref<SavedSession[]>([])
const expandedHistories = ref<Record<string, boolean>>({})

const displayedHistories = computed(() => {
  if (!searchQuery.value.trim()) return savedHistories.value
  const q = searchQuery.value.toLowerCase()
  return savedHistories.value.filter(session => {
    return session.messages.some(m => m.content && m.content.toLowerCase().includes(q))
  })
})

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
  playWelcomeAnimation()
  loadSavedHistory()
  // 监听浏览器关闭/刷新事件，确保保存聊天记录
  window.addEventListener('beforeunload', _handleBeforeUnload)
})

// ── 自动保存聊天记录：确保任何退出方式都会保存 ──

// 1. 组件卸载时保存（父组件切换、v-if 销毁等）
onBeforeUnmount(() => {
  saveCurrentToHistory()
  window.removeEventListener('beforeunload', _handleBeforeUnload)
  // 清理语音录制资源
  if (isRecording.value) cleanupRecording()
})

// 2. 浏览器关闭/刷新时保存
const _handleBeforeUnload = () => {
  saveCurrentToHistory()
}

// 3. 路由切换时保存（用户点击侧边栏导航等）
onBeforeRouteLeave(() => {
  saveCurrentToHistory()
})

let _lastSaveTimestamp = 0

const saveCurrentToHistory = () => {
  if (messages.value.length === 0) return
  
  // 防抖：同一秒内不重复保存（避免 collapse + onBeforeUnmount 双重触发）
  const now = Date.now()
  if (now - _lastSaveTimestamp < 1000) return
  _lastSaveTimestamp = now
  
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
  scrollToBottom(true) // 恢复历史时瞬间到底，不要用平滑动画，否则容易卡在最上面
}

const deleteHistory = (id: string) => {
  const index = savedHistories.value.findIndex(h => h.id === id)
  if (index === -1) return
  savedHistories.value.splice(index, 1)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(savedHistories.value))
  if (savedHistories.value.length === 0) {
    showHistory.value = false
  }
}

const scrollToBottom = async (instant: boolean = false) => {
  await nextTick()
  if (chatContentRef.value) {
    chatContentRef.value.scrollTo({
      top: chatContentRef.value.scrollHeight + 1000,
      behavior: instant ? 'auto' : 'smooth'
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
    draft: '草稿', pending_assign: '待分配', pending_contract: '合同与付款',
    in_production: '制作中',
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

// 从用户文字中检测下单意图，返回对应的 businessType 或 null
const _detectBusinessTypeFromText = (text: string): string | null => {
  const lower = text.toLowerCase()

  // 必须有下单意愿信号词
  const intentWords = [
    '想做', '想定制', '想下单', '要做', '要定制', '开始', '下单',
    '定制', '做一个', '做个', '需要', '想要', '来一个', '搞一个',
    '试试', '选', '就这个', '就选', '可以开始',
  ]
  const hasIntent = intentWords.some(w => lower.includes(w))

  // 即使没有明确意愿词，直接说业务名称也算（如"AI裸眼3D内容定制"）
  const directNames: Record<string, string> = {
    'ai裸眼3d内容定制': 'ai_3d_custom',
    '裸眼3d成片购买适配': 'video_purchase',
    '数字艺术内容定制': 'digital_art',
    '裸眼3d内容定制': 'ai_3d_custom',
    '成片购买适配': 'video_purchase',
  }
  for (const [name, type] of Object.entries(directNames)) {
    if (lower.includes(name)) return type
  }

  if (!hasIntent) return null

  // 业务类型关键词匹配
  if (/裸眼3d|裸眼3D|3d定制|3D定制|3d内容|3D内容|裸眼.*定制/.test(text)) return 'ai_3d_custom'
  if (/成片|购买|模板|现成|成品|买/.test(text)) return 'video_purchase'
  if (/数字艺术|数字.*艺术|沉浸|互动|装置|投影/.test(text)) return 'digital_art'

  return null
}

const getOrderStep = (status: string) => {
  if (status === 'cancelled') return -1
  const map: Record<string, number> = {
    draft: 1, pending_assign: 1, pending_contract: 1,
    in_production: 2, pending_review: 2, review_rejected: 2,
    preview_ready: 3, revision_needed: 3, final_preview: 3,
    completed: 4
  }
  return map[status] || 1
}

const getStepLabel = (step: number) => {
  return ['需求确认', '阶段制作', '交付验收', '项目完成'][step - 1] || ''
}

const getStepClass = (status: string, stepIndex: number) => {
  if (status === 'cancelled') return 'step-cancelled'
  const current = getOrderStep(status)
  if (current > stepIndex) return 'step-done'
  if (current === stepIndex) {
    if (status === 'revision_needed' || status === 'review_rejected') return 'step-warning'
    if (status === 'completed') return 'step-done'
    return 'step-active'
  }
  return 'step-pending'
}

const getProgressWidth = (status: string) => {
  if (status === 'cancelled') return '0%'
  const current = getOrderStep(status)
  return `${25 * (current - 1)}%`
}

const formatOrderDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// 从业务介绍切换到下单 Agent
const switchToOrderCreate = (type: string = 'ai_3d_custom', requirementSummary: string = '') => {
  businessType.value = type
  selectedMode.value = 'order_create'
  emit('mode-change', 'order_create')

  const typeLabels: Record<string, string> = {
    ai_3d_custom: 'AI裸眼3D内容定制',
    video_purchase: '裸眼3D成片购买适配',
    digital_art: '数字艺术内容定制',
  }
  const label = typeLabels[type] || typeLabels.ai_3d_custom

  let openingMsg = ''
  if (requirementSummary) {
    // 有需求摘要：带上客户已描述的信息
    openingMsg = `好的，根据您的描述，我为您匹配的是「${label}」服务。\n\n您已提到的需求：${requirementSummary}\n\n让我来帮您进一步完善剩余信息。`
    // 将摘要信息也作为一条用户消息插入，让需求收集 agent 知道上下文
    messages.value.push({
      role: 'user',
      content: `[用户在业务咨询时描述的需求：${requirementSummary}]`,
      timestamp: getCurrentTime(),
      isContextCarryOver: true  // 标记为上下文携带，不是用户真正输入
    })
  } else {
    const openings: Record<string, string> = {
      ai_3d_custom: `好的，我们进入${label}的需求梳理环节。\n\n首先想了解一下：这次项目是哪个品牌的？主要想呈现什么样的裸眼3D创意画面？`,
      video_purchase: `好的，我们进入${label}的需求梳理环节。\n\n首先想确认一下：您的品牌名称是什么？这样我们可以在成片上做对应的品牌元素适配。`,
      digital_art: `好的，我们进入${label}的需求梳理环节。\n\n首先想了解一下：这次项目的品牌或活动名称是什么？活动场景大概是什么样的？`,
    }
    openingMsg = openings[type] || openings.ai_3d_custom
  }

  messages.value.push({
    role: 'assistant',
    content: openingMsg,
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
  // 跨模式拦截：任何模式下用户问案例，都走 business_intro（它有真实案例库）
  const _caseKeywords = ['案例', '作品', '看看你们做过', '之前做过', '过往项目', '成功案例', '看看案例', '展示一下']
  if (_caseKeywords.some(kw => userText.includes(kw))) {
    // 标记用户的案例请求消息，避免污染需求收集上下文
    const lastUserMsg = messages.value[messages.value.length - 1]
    if (lastUserMsg && lastUserMsg.role === 'user') lastUserMsg.isCaseDetour = true
    await handleBusinessIntro(userText, true)
  } else if (selectedMode.value === 'order_create') {
    await handleCustomAiChat(userText)
  } else if (selectedMode.value === 'order_query') {
    await handleOrderQuery(userText)
  } else if (selectedMode.value === 'business_intro') {
    // 检测用户是否通过文字表达了下单意图，自动切换到对应业务的需求收集
    const detectedType = _detectBusinessTypeFromText(userText)
    if (detectedType) {
      switchToOrderCreate(detectedType)
    } else {
      await handleBusinessIntro(userText)
    }
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
const handleBusinessIntro = async (userText: string, isCaseDetour: boolean = false) => {
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
      // 标记案例回复，避免污染需求收集上下文
      if (isCaseDetour) {
        const lastAssistantMsg = messages.value[messages.value.length - 1]
        if (lastAssistantMsg && lastAssistantMsg.role === 'assistant') lastAssistantMsg.isCaseDetour = true
      }
      // 如果有案例数据，附加到当前消息上（与订单卡片同理）
      if (cases.length > 0) {
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.isCaseList = true
          lastMsg.cases = cases
        }
        scrollToBottom()
      }
      // 如果 AI 建议引导下单
      const guide = data.guide || {}
      if (guide.should_guide) {
        if (guide.business_type && guide.requirement_summary) {
          // 有明确业务类型和需求摘要：直接跳转并携带上下文
          switchToOrderCreate(guide.business_type, guide.requirement_summary)
        } else {
          // 没有明确业务类型：展示三个快速入口供用户选择
          messages.value.push({
            role: 'assistant',
            content: '如您已有初步的项目构想，可以进入需求梳理流程，由我协助您完成订单创建。',
            isGuideToOrder: true,
            timestamp: getCurrentTime()
          })
          scrollToBottom()
        }
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
    // 过滤掉案例浏览的消息，避免污染需求收集上下文
    const historyMessages = messages.value.slice(0, messages.value.length - 1);
    const formattedHistory = historyMessages
      .filter(m => (m.role === 'user' || m.role === 'assistant') && !m.isCaseDetour)
      .map(m => ({ role: m.role, content: m.content }));

    const response = await fetch('/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        session_id: session_id.value, 
        message: userText,
        history: formattedHistory,
        business_type: businessType.value
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
      const orderType = businessType.value
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
  
  // 检查企业认证状态
  if (authStore.user?.enterprise_status !== 'approved') {
    messages.value.push({
      role: 'assistant',
      content: '您尚未完成企业认证，无法正式提交订单。您的需求已自动保存为草稿，请先前往「个人设置」完成企业认证后再提交。',
      timestamp: getCurrentTime()
    })
    scrollToBottom()
    return
  }
  
  confirmOrderType.value = businessType.value as OrderType
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
      await orderStore.updateOrderStatus(draftSavedOrderId.value, 'pending_contract')
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

/* Collapse animation for history panel */
.collapse-history-enter-active {
  transition: opacity 0.4s ease;
}
.collapse-history-leave-active {
  transition: opacity 0.2s ease;
}
.collapse-history-enter-from,
.collapse-history-leave-to {
  opacity: 0;
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
  scroll-behavior: smooth;
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
  max-width: 100%;
  position: relative;
  word-wrap: break-word;
}

/* 打字机光标闪烁 */
.typing-cursor {
  display: inline-block;
  margin-left: 2px;
  width: 2px;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease-out, transform 0.5s ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
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
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
  gap: 12px;
}

.input-area.pill-style.is-voice-recording {
  background: #ffffff;
  border-color: #e5e5ea;
  align-items: center; /* keep waveform visualizer centered */
  padding: 4px 16px;
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
.status-pending_contract { background: #fff8e1; color: #f57f17; }
.status-in_production { background: #e3f2fd; color: #1565c0; }
.status-pending_review { background: #fce4ec; color: #c62828; }
.status-preview_ready { background: #e8f5e9; color: #2e7d32; }
.status-completed { background: #e8f5e9; color: #1b5e20; }
.status-cancelled { background: #f5f5f5; color: #9e9e9e; }

/* ===== 订单进度条 ===== */
.order-progress-timeline {
  display: flex;
  justify-content: space-between;
  position: relative;
  margin: 16px 8px 24px;
}

.timeline-bg-line {
  position: absolute;
  top: 7px;
  left: 12.5%;
  right: 12.5%;
  height: 2px;
  background: rgba(0, 0, 0, 0.05);
  z-index: 0;
}

.timeline-progress-line {
  position: absolute;
  top: 7px;
  left: 12.5%;
  height: 2px;
  background: #3b82f6;
  z-index: 1;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s;
}

.timeline-progress-line.warning-line {
  background: #f59e0b;
}

.timeline-step {
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 25%;
  position: relative;
}

.step-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid rgba(0,0,0,0.1);
  background: #fff;
  box-sizing: border-box;
  transition: all 0.3s;
  position: relative;
}

.step-label {
  font-size: 11px;
  color: rgba(0, 0, 0, 0.35);
  font-weight: 500;
  transition: color 0.3s ease;
  white-space: nowrap;
  position: absolute;
  top: 20px;
}

/* 状态类 */
.step-done .step-dot {
  border-color: #10b981;
  background: #10b981;
}
.step-done .step-label {
  color: #10b981;
}

.step-active .step-dot {
  border-color: #3b82f6;
  background: #fff;
}
.step-active .step-dot::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
}
.step-active .step-label {
  color: #3b82f6;
}

.step-warning .step-dot {
  border-color: #f59e0b;
  background: #fff;
}
.step-warning .step-dot::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f59e0b;
}
.step-warning .step-label {
  color: #f59e0b;
}

.step-cancelled {
  width: 100%;
}
.step-cancelled .step-dot {
  border-color: #9ca3af;
  background: #9ca3af;
}
.step-cancelled .step-label {
  color: #9ca3af;
}
.cancelled-timeline .timeline-bg-line {
  left: 0; right: 0; display: none;
}

.pulse-ring {
  position: absolute;
  top: -4px;
  left: -4px;
  right: -4px;
  bottom: -4px;
  border-radius: 50%;
  border: 2px solid rgba(59, 130, 246, 0.4);
  animation: pulse-ring 2s cubic-bezier(0.25, 0.8, 0.25, 1) infinite;
  pointer-events: none;
}
.step-warning .pulse-ring {
  border-color: rgba(245, 158, 11, 0.4);
}
@keyframes pulse-ring {
  0% { transform: scale(0.6); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; }
}

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

.guide-order-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 10px;
  text-align: center;
}

.guide-btns {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.comp-btn-outline {
  background: transparent;
  border: 1px solid rgba(0, 0, 0, 0.15);
  color: #333;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.comp-btn-outline:hover {
  border-color: #4f46e5;
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.04);
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

/* ========== 语音输入样式 ========== */
.voice-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #86868b;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;

  &:hover {
    background: rgba(0, 0, 0, 0.06);
    color: #1d1d1f;
  }

  &.recording {
    background: #ff3b30;
    color: #fff;
    animation: voice-glow 1.5s ease-in-out infinite;

    &:hover {
      background: #e0332b;
      color: #fff;
    }
  }
}

.rec-pulse {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px solid #ff3b30;
  animation: pulse-ring 1.2s ease-out infinite;
}

@keyframes voice-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(255, 59, 48, 0); }
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(1.5); opacity: 0; }
}



/* ========== ChatGPT风格波形图 ========== */
.voice-plus-icon {
  font-size: 20px !important;
  color: #888 !important;
}

.waveform-container {
  flex: 1;
  height: 36px;
  margin: 0 16px;
  position: relative;
  display: flex;
  align-items: center;
}

.waveform-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.voice-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.voice-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #333;
  transition: all 0.2s ease;
}

.voice-action-btn.cancel:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #ff3b30;
}

.voice-action-btn.confirm {
  background: transparent;
}

.voice-action-btn.confirm:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #34c759;
}

/* ========== 语音识别中状态 ========== */
.waveform-container {
  transition: opacity 0.3s ease;
}

.voice-transcribing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.transcribing-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e5ea;
  border-top-color: #333333;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>




