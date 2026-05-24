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
            <input type="text" v-model="searchQuery" placeholder="搜索当前聊天..." class="search-input" @input="onSearchInput" />
          </div>
        </div>

        <div class="header-right">
          <button class="icon-toggle" title="帮助"><el-icon><QuestionFilled /></el-icon></button>
          <button class="new-session-btn" @click="startNewSession">新建会话</button>
          <button class="icon-toggle collapse-btn" @click="collapse"><el-icon><Close /></el-icon></button>
        </div>
      </header>
      
      <div class="gradient-banner"></div>

      <div class="chat-content" ref="chatContentRef">
        <div class="messages-container" ref="messagesContainer">
          <!-- Welcome + Quick Actions -->
          <div v-if="!selectedMode" class="welcome-section message assistant">
            <div class="assistant-wrapper">
              <div class="assistant-tag"><span class="engine-name">智能引擎</span> <span class="pro-badge">专业版</span></div>
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
                    <p class="welcome-hint">也可以直接在下方输入您的问题</p>
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
                    <span class="user-tag">你</span>
                    <div v-if="isInlineEditingMessage(msg)" class="inline-message-edit">
                      <textarea
                        :ref="setInlineEditTextareaRef"
                        v-model="inlineEditText"
                        class="inline-message-edit-textarea"
                        placeholder="编辑这条消息..."
                        rows="1"
                        @input="adjustInlineEditHeight"
                        @keydown.enter="handleInlineEditEnter($event, msg)"
                        @compositionstart="isComposing = true"
                        @compositionend="isComposing = false"
                      ></textarea>
                      <div class="inline-message-edit-actions">
                        <button class="inline-edit-btn secondary" @click.stop="cancelInlineEdit">取消</button>
                        <button class="inline-edit-btn primary" @click.stop="submitInlineEdit(msg)">发送</button>
                      </div>
                    </div>
                    <div
                      v-else-if="displayUserMessageText(msg.content)"
                      class="message-bubble user-bubble"
                      v-html="highlightSearch(displayUserMessageText(msg.content))"
                    ></div>
                    <div v-if="!isInlineEditingMessage(msg) && msg.attachments?.length" class="message-attachment-grid">
                      <div
                        v-for="file in msg.attachments"
                        :key="file.objectKey || file.url || file.name"
                        class="message-attachment-preview"
                        :title="file.name"
                      >
                        <img v-if="file.isImage && file.url" :src="file.url" class="message-attachment-thumb" />
                        <div v-else class="message-file-preview">
                          <el-icon><PictureRounded /></el-icon>
                          <span>{{ getFileExtension(file.name) }}</span>
                        </div>
                      </div>
                    </div>
                    <div v-if="canModifyLastUserMessage(msg) && !isInlineEditingMessage(msg)" class="user-message-actions">
                      <button class="msg-action-btn" @click.stop="startInlineEdit(msg)">编辑</button>
                      <button class="msg-action-btn danger" @click.stop="revokeLastUserMessage(msg)">撤回</button>
                    </div>
                    <span class="msg-time" v-if="!isInlineEditingMessage(msg) && msg.timestamp">{{ msg.timestamp }}</span>
                  </div>
                  <div class="user-avatar" :class="{ 'has-image': !!currentUserAvatar }">
                    <img v-if="currentUserAvatar" :src="currentUserAvatar" :alt="currentUserName" />
                    <span v-else>{{ currentUserInitial }}</span>
                  </div>
                </div>
              </div>
            </template>

            <template v-else>
              <div class="assistant-wrapper">
                <div class="assistant-tag"><span class="engine-name">智能引擎</span></div>
                <div class="message-bubble glass-ai">
                  <p class="bubble-text" v-html="highlightSearch(displayContent(msg.content))"></p>
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
                      <div v-if="submittedFiles.length > 0" class="form-attachment-preview">
                        <div class="form-attachment-label">已上传素材</div>
                        <div class="form-attachment-list">
                          <div
                            v-for="file in submittedFiles"
                            :key="file.objectKey || file.url || file.name"
                            class="form-attachment-item"
                            :title="file.name"
                          >
                            <img v-if="file.isImage && file.url" :src="file.url" class="form-attachment-thumb" />
                            <div v-else class="form-file-thumb">
                              <el-icon><PictureRounded /></el-icon>
                            </div>
                            <span class="form-attachment-name">{{ file.name }}</span>
                          </div>
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
                          <div class="order-info-row" v-if="order.project_name"><span class="info-label">项目</span><span class="info-val">{{ order.project_name }}</span></div>
                          <div class="order-info-row" v-if="order.city_location"><span class="info-label">城市</span><span class="info-val">{{ order.city_location }}</span></div>
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
                      <button class="comp-btn comp-btn-primary" @click="switchToOrderCreate('ai_3d_custom')">AI驱动3D OOH内容定制</button>
                      <button class="comp-btn comp-btn-outline" @click="switchToOrderCreate('video_purchase')">3D OOH数字内容资源库</button>
                      <button class="comp-btn comp-btn-outline" @click="switchToOrderCreate('digital_art')">数字艺术与沉浸式视觉设计</button>
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
               <div class="assistant-tag"><span class="engine-name">智能引擎</span></div>
               <div class="message-bubble glass-ai typing">
                 <span>智能体思考中</span>
                 <span class="thinking-ellipsis" aria-hidden="true">
                   <span>.</span>
                   <span>.</span>
                   <span>.</span>
                   <span>.</span>
                   <span>.</span>
                   <span>.</span>
                 </span>
               </div>
            </div>
          </div>
          <div v-if="isTyping && !isLoading" class="typing-cursor-indicator">
            <span>智能体思考中</span>
            <span class="thinking-ellipsis" aria-hidden="true">
              <span>.</span>
              <span>.</span>
              <span>.</span>
              <span>.</span>
              <span>.</span>
              <span>.</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Input Area — Stitch Style Pill -->
      <div class="input-area-container">
        <div class="input-area pill-style" :class="{ 'is-voice-recording': isRecording || isTranscribing }">
          <template v-if="!isRecording && !isTranscribing">
            <!-- Left icons mock -->
            <div class="left-tools">
              <el-icon class="tool-icon" @click="triggerGenericFileUpload" title="上传参考文件（PDF、Word、压缩包等）"><CirclePlusFilled /></el-icon>
              <el-icon class="tool-icon" @click="triggerFileUpload" title="上传现场实拍图或参考文件"><PictureRounded /></el-icon>
              <input
                type="file"
                ref="fileInputRef"
                multiple
                :accept="supportingFileAccept"
                style="display: none;"
                @change="handleFileSelected"
              />
              <input
                type="file"
                ref="genericFileInputRef"
                multiple
                :accept="supportingFileAccept"
                style="display: none;"
                @change="handleFileSelected"
              />
            </div>
            <!-- 已上传文件预览条 -->
            <div v-if="uploadedFiles.length > 0" class="uploaded-files-strip">
              <div v-for="(file, idx) in uploadedFiles" :key="idx" class="uploaded-file-chip">
                <img v-if="file.isImage" :src="file.url" class="file-thumb" />
                <el-icon v-else class="file-icon-placeholder"><PictureRounded /></el-icon>
                <span class="file-name">{{ file.name }}</span>
                <span class="file-status">待发送</span>
                <span class="file-remove" @click="removeUploadedFile(idx)">&times;</span>
              </div>
              <span class="upload-more-hint">可继续上传更多文件或图片，完成后点击发送</span>
            </div>

          <textarea
            ref="textareaRef"
            v-model="inputMsg"
            placeholder="描述您的需求，或直接输入问题..."
            class="chat-native-textarea"
            @input="adjustTextareaHeight"
            @keydown.enter="handleEnterKey"
            @compositionstart="isComposing = true"
            @compositionend="isComposing = false"
            :disabled="isLoading || isTyping || isRecording"
            @focus="handleInputFocus"
            rows="1"
          ></textarea>
          
          <!-- Right tools & send -->
          <div class="right-tools">
            <!-- 语音输入按钮 -->
            <button
              v-if="ENABLE_VOICE_INPUT"
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
              :class="{ disabled: isLoading || isTyping || isUploadingFiles || (!inputMsg.trim() && uploadedFiles.length === 0) }"
              @click="sendMessage"
            >
              <span>发送</span>
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
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Close, Right, Top, QuestionFilled, CirclePlusFilled, PictureRounded, Search, Loading, Plus, Check } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { logger } from '@/utils/logger'
import { chatHistoryApi, orderApi } from '@/utils/api'
import {
  createAiChatSessionFromRemote,
  deleteAiChatSession,
  loadAiChatSessions,
  makeAiChatSessionTitle,
  upsertAiChatSession,
  type AiChatRemoteSession,
  type AiChatSavedSession,
} from '@/utils/aiChatSessions'
import { getLatestEnterpriseStatus } from '@/utils/enterpriseGuard'
import OrderConfirmationDialog from '@/components/OrderConfirmationDialog.vue'

// 语音输入开关，通过 .env 文件配置
const ENABLE_VOICE_INPUT = import.meta.env.VITE_ENABLE_VOICE_INPUT === 'true'
import type { OrderStatus, OrderType } from '@/types'

const emit = defineEmits(['close', 'mode-change'])
const router = useRouter()
const route = useRoute()
const orderStore = useOrderStore()
const authStore = useAuthStore()
const uiStore = useUiStore()

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



const onSearchInput = () => {}

// auth header helper
const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

// ==== 欢迎打字机动画逻辑 ====
// Agent 模式：brand（品牌方）/ media（媒体方），通过 .env 配置
const agentMode = import.meta.env.VITE_AGENT_MODE || 'media'
const isMediaMode = agentMode === 'media'

const welcomeTitleFull = '您好，我是 Unique Vision AI 的项目顾问。'
const welcomeDescFull = isMediaMode
  ? '我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多媒体方客户提供过高品质的裸眼3D视觉内容解决方案。'
  : '我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多一线品牌提供过高品质视觉解决方案。'
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
const orderSubmitCompleted = ref(false)

type ConversationStateSnapshot = {
  agentKey?: string
  agentLabel?: string
  sessionType?: string
  agentMode?: string
  selectedMode: string | null
  businessType: string
  inlineFormData: Record<string, string> | null
  draftSavedOrderId: string | null
  showConfirmation: boolean
  confirmOrderNumber: string
  confirmOrderType: OrderType
  submittedFilesLength?: number
  submittedFiles?: UploadedFile[]
  uploadedFiles?: UploadedFile[]
  inputMsg?: string
  orderSubmitCompleted: boolean
  routeFullPath: string
}

const clonePlain = <T,>(value: T): T => JSON.parse(JSON.stringify(value))

// ===== 文件上传相关 =====
type UploadedFile = {
  name: string
  url: string
  isImage: boolean
  size: number
  type: string
  uploadTime: string
  objectKey?: string
}

const fileInputRef = ref<HTMLInputElement | null>(null)
const genericFileInputRef = ref<HTMLInputElement | null>(null)
const uploadedFiles = ref<UploadedFile[]>([])
const submittedFiles = ref<UploadedFile[]>([])
const isUploadingFiles = ref(false)
const failedUploadNames = ref<string[]>([])
const supportingFileAccept = [
  'image/*',
  '.pdf',
  '.ppt',
  '.pptx',
  '.key',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.zip',
  '.rar',
  '.7z',
  '.mp4',
  '.mov',
  '.avi',
].join(',')

const triggerFileUpload = () => {
  fileInputRef.value?.click()
}

const triggerGenericFileUpload = () => {
  genericFileInputRef.value?.click()
}

const handleFileSelected = async (e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return

  const uploadedNames: string[] = []
  const failedNames: string[] = []
  isUploadingFiles.value = true

  for (const file of Array.from(input.files)) {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const token = authStore.token
      const res = await fetch('/api/upload/site-photo', {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData
      })
      if (res.ok) {
        const data = await res.json()
        const isImage = /\.(jpg|jpeg|png|gif|webp|bmp)$/i.test(file.name)
        uploadedFiles.value.push({
          name: file.name,
          url: data.url || data.file_url || '',
          isImage,
          size: data.size || file.size,
          type: file.type || '',
          uploadTime: data.uploadedAt || new Date().toISOString(),
          objectKey: data.object_key || ''
        })
        uploadedNames.push(file.name)
      } else {
        failedNames.push(file.name)
        ElMessage.error(`上传失败: ${file.name}`)
      }
    } catch (err) {
      failedNames.push(file.name)
      ElMessage.error(`上传失败: ${file.name}`)
    }
  }
  // 清空 input 值，允许重复上传同一文件
  input.value = ''
  isUploadingFiles.value = false

  if (uploadedNames.length > 0) {
    ElMessage.success(uploadedNames.length === 1
      ? `${uploadedNames[0]} 已添加到本轮消息`
      : `${uploadedNames.length} 个文件已添加到本轮消息`
    )
  }
  if (failedNames.length > 0) {
    failedUploadNames.value = Array.from(new Set([...failedUploadNames.value, ...failedNames]))
  }
}

const removeUploadedFile = (index: number) => {
  uploadedFiles.value.splice(index, 1)
}

const buildFileSummaryText = (files: UploadedFile[]) => {
  if (files.length === 0) return ''
  const names = files.map(file => file.name).join('、')
  return files.length === 1
    ? `[已上传文件: ${names}]`
    : `[已上传 ${files.length} 个文件: ${names}]`
}

const buildUserMessageContent = (text: string, files: UploadedFile[]) => {
  return [text, buildFileSummaryText(files)].filter(Boolean).join('\n')
}

const HUMAN_HANDOFF_MARKER = '【转人工】'
const HUMAN_HANDOFF_FALLBACK_REPLY = '已识别到您希望转人工，但当前系统未能完成草稿保存和管理员通知。请稍后重试。'

const isHumanHandoffRequest = (text: string = '') => {
  const normalized = text.toLowerCase().replace(/\s+/g, '')
  if (!normalized) return false
  const negativePatterns = [
    '不需要人工', '不用人工', '无需人工', '不要人工', '别转人工',
    '不转人工', '暂不转人工', '先不转人工', '不是要人工', '不是找人工',
    '不是转人工', '不用真人', '不需要真人',
  ]
  if (negativePatterns.some(pattern => normalized.includes(pattern))) return false
  const handoffText = normalized.replace(/人工智能/g, '')
  const explicitPatterns = [
    '转人工', '接人工', '切人工', '换人工', '找人工', '人工客服',
    '人工服务', '人工顾问', '人工接待', '真人客服', '真人顾问',
    '真人服务', '找真人', '联系人工', '联系顾问', '联系销售',
    '客服介入', '销售联系', '顾问联系', '人工',
  ]
  if (explicitPatterns.some(pattern => handoffText.includes(pattern))) return true
  const noAiPatterns = [
    '不想用ai', '不使用ai', '不用ai', '不要ai', '别用ai',
    '不想用智能体', '不使用智能体', '不用智能体', '不要智能体', '别用智能体',
    '不想和机器人聊', '不跟机器人聊', '不要机器人', '不用机器人',
    '不想和agent聊', '不用agent', '不要agent',
  ]
  return noAiPatterns.some(pattern => normalized.includes(pattern))
}

const displayUserMessageText = (text: string = '') => {
  return text
    .replace(/\n?\[已上传文件: [^\]]+\]/g, '')
    .replace(/\n?\[已上传 \d+ 个文件: [^\]]+\]/g, '')
    .trim()
}

const getFileExtension = (name: string = '') => {
  const ext = name.split('.').pop()
  return ext && ext !== name ? ext.slice(0, 5).toUpperCase() : 'FILE'
}

// 表单字段定义
// ===== 品牌方表单字段 =====
const _brandFormFields = [
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
  { key: 'site_photos', label: '现场实拍图', placeholder: '选填，通过左侧上传按钮上传的文件将自动归入此项', multiline: false },
]

// ===== 媒体方表单字段 =====
const _mediaFormFields = [
  { key: 'resource_background', label: '项目背景 & 媒体简介', placeholder: '媒体资源背景介绍，位置特点、日均客流等', multiline: true },
  { key: 'audience_scene', label: '目标受众 & 场景特点', placeholder: '受众画像和场景特征', multiline: true },
  { key: 'city_location', label: '投放城市 & 媒体位置', placeholder: '城市、区域、具体位置', multiline: false },
  { key: 'viewing_path', label: '观看动线说明', placeholder: '观众主要视角、人流方向、最佳观看点', multiline: true },
  { key: 'art_direction', label: '艺术方向 & 风格偏好', placeholder: '未来科技/自然生态/城市文化/抽象艺术等', multiline: false },
  { key: 'theme_concept', label: '内容主题 & 核心表达', placeholder: '核心概念、IP形象、品牌露出等', multiline: true },
  { key: 'media_specs', label: '媒体尺寸 & 物理规格', placeholder: '屏幕分辨率、物理尺寸', multiline: false },
  { key: 'tech_delivery', label: '技术需求', placeholder: '分辨率、格式、帧率、色彩空间等', multiline: false },
  { key: 'content_review', label: '素材审核规范 & 周期', placeholder: '审核要求、周期、规避内容等', multiline: true },
  { key: 'timing_number', label: '投放时长 & 数量', placeholder: '选填，几支内容、每支多少秒', multiline: false },
  { key: 'budget', label: '项目制作预算', placeholder: '选填，预算范围或待定', multiline: false },
  { key: 'online_time', label: '预计上刊时间', placeholder: '以最迟提交报审时间为准', multiline: false },
  { key: 'project_name', label: '项目名称', placeholder: '系统将根据点位、屏幕和核心概念自动生成，可修改', multiline: false },
  { key: 'media_positioning', label: '媒体定位 & 品牌调性', placeholder: '选填，适配的品牌类型', multiline: false },
  { key: 'special_requirements', label: '其他特殊合作要求', placeholder: '选填，特殊定制效果等', multiline: true },
  { key: 'site_photos', label: '现场实拍图', placeholder: '选填，通过左侧上传按钮上传', multiline: false },
]

const formFields = isMediaMode ? _mediaFormFields : _brandFormFields

const selectedMode = ref<string | null>(null)
const businessType = ref<string>('ai_3d_custom') // ai_3d_custom / video_purchase / digital_art
const messages = ref<any[]>([])
const inputMsg = ref('')
const isLoading = ref(false)
const isTyping = ref(false) // AI 正在逐字输出中
const extractLoading = ref(false) // 信息提取整理中
const createSessionId = () => `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
const session_id = ref(createSessionId())
const createMessageId = (role: string) => `${session_id.value}_${role}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
const chatContentRef = ref<any>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const inlineEditTextareaRef = ref<HTMLTextAreaElement | null>(null)
const inlineEditingKey = ref('')
const inlineEditText = ref('')
const isComposing = ref(false) // 中文输入法组合输入状态

const adjustTextareaHeight = () => {
  const ta = textareaRef.value
  if (!ta) return
  ta.style.height = 'auto'
  ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
}

const adjustInlineEditHeight = () => {
  const ta = inlineEditTextareaRef.value
  if (!ta) return
  ta.style.height = 'auto'
  ta.style.height = Math.min(ta.scrollHeight, 220) + 'px'
}

const setInlineEditTextareaRef = (el: Element | null) => {
  inlineEditTextareaRef.value = el as HTMLTextAreaElement | null
}

/** 处理 Enter 键：IME 组合输入期间不发送消息 */
const handleEnterKey = (e: KeyboardEvent) => {
  // 正在使用输入法组合输入时，Enter 用于确认候选词，不发送消息
  if (e.isComposing || isComposing.value) return
  e.preventDefault()
  sendMessage()
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
  saveCurrentToHistory({ force: true })
  clearInlineEdit()
  messages.value = []
  selectedMode.value = null
  businessType.value = 'ai_3d_custom'
  inlineFormData.value = null
  draftSavedOrderId.value = null
  showConfirmation.value = false
  confirmOrderNumber.value = ''
  confirmOrderType.value = 'ai_3d_custom'
  orderSubmitCompleted.value = false
  uploadedFiles.value = []
  submittedFiles.value = []
  inputMsg.value = ''
  session_id.value = createSessionId()
  uiStore.setActiveAIChatSession(session_id.value)
  playWelcomeAnimation()
}

// --- 历史聊天记录 ---
// 使用用户 ID 隔离存储，防止不同用户看到彼此的聊天记录
const getCurrentUserId = () => authStore.user?.id || 'anonymous'

const currentUserName = computed(() => authStore.user?.username || '用户')
const currentUserAvatar = computed(() => authStore.user?.avatar || '')
const currentUserInitial = computed(() => currentUserName.value.charAt(0).toUpperCase())

const displayedMessages = computed(() => {
  if (!searchQuery.value.trim()) return messages.value
  const q = searchQuery.value.toLowerCase()
  return messages.value.filter(m => {
    // 包含文本，或者是有卡片内容的特殊气泡
    if (m.content && m.content.toLowerCase().includes(q)) return true
    if (m.isOrderList || m.isCaseList || m.isGuideToOrder || m.isPurchasePrompt || m.isCompletePrompt || m.isHumanHandoff) return true
    return false
  })
})

type SavedSession = AiChatSavedSession

const agentRegistry: Record<string, { label: string; sessionType: string; selectedMode: string | null; businessType?: string }> = {
  general: { label: '通用问答', sessionType: 'general', selectedMode: null },
  business_intro: { label: '业务介绍', sessionType: 'business_intro', selectedMode: 'business_intro' },
  case_intro: { label: '案例介绍', sessionType: 'case_intro', selectedMode: 'business_intro' },
  order_query: { label: '订单查询', sessionType: 'order_query', selectedMode: 'order_query' },
  requirement_ai_3d_custom: { label: 'AI驱动3D OOH内容定制', sessionType: 'requirement', selectedMode: 'order_create', businessType: 'ai_3d_custom' },
  requirement_video_purchase: { label: '3D OOH数字内容资源库', sessionType: 'requirement', selectedMode: 'order_create', businessType: 'video_purchase' },
  requirement_digital_art: { label: '数字艺术与沉浸式视觉设计', sessionType: 'requirement', selectedMode: 'order_create', businessType: 'digital_art' },
}

const savedHistories = ref<SavedSession[]>([])

const ensureMessageClientIds = (items: any[] = messages.value) => {
  items.forEach((m: any) => {
    if ((m?.role === 'user' || m?.role === 'assistant') && !m.client_message_id) {
      m.client_message_id = createMessageId(m.role)
    }
  })
}

const getCurrentAgentKey = () => {
  if (selectedMode.value === 'order_create') {
    return `requirement_${businessType.value || 'ai_3d_custom'}`
  }
  if (selectedMode.value === 'order_query') return 'order_query'
  if (selectedMode.value === 'business_intro') {
    const hasCaseContext = messages.value.some(m => m?.isCaseList || m?.isCaseDetour || /案例|作品|过往项目/.test(m?.content || ''))
    return hasCaseContext ? 'case_intro' : 'business_intro'
  }
  return 'general'
}

const getAgentMeta = (agentKey = getCurrentAgentKey()) => {
  return agentRegistry[agentKey] || {
    label: agentKey,
    sessionType: 'general',
    selectedMode: null,
  }
}

const loadSavedHistory = () => {
  savedHistories.value = loadAiChatSessions(getCurrentUserId())
}

const loadBackendHistoryById = async (id: string): Promise<SavedSession | null> => {
  if (!localStorage.getItem('token')) return null
  try {
    const [summaries, remoteMessages] = await Promise.all([
      chatHistoryApi.getSessions(50).catch(() => []),
      chatHistoryApi.getSessionMessages(id),
    ])
    const summary = Array.isArray(summaries)
      ? summaries.find((item: AiChatRemoteSession) => item.id === id)
      : null
    const session = createAiChatSessionFromRemote(
      summary || { id, sessionType: 'general', businessType: 'ai_3d_custom' },
      Array.isArray(remoteMessages) ? remoteMessages : [],
    )
    if (session.messages.length === 0) return null
    savedHistories.value = upsertAiChatSession(getCurrentUserId(), session)
    return session
  } catch (error) {
    console.warn('[ChatHistory] 从后端恢复历史失败:', error)
    return null
  }
}

onMounted(() => {
  playWelcomeAnimation()
  loadSavedHistory()
  uiStore.setActiveAIChatSession(session_id.value)
  if (uiStore.pendingAIChatSessionId) {
    void restoreHistoryById(uiStore.pendingAIChatSessionId)
  }
  // 监听浏览器关闭/刷新事件，确保保存聊天记录
  window.addEventListener('beforeunload', _handleBeforeUnload)
})

watch(() => uiStore.pendingAIChatSessionId, (sessionId) => {
  if (sessionId) void restoreHistoryById(sessionId)
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

const hasCurrentSessionContent = () => {
  return messages.value.length > 0
    || Boolean(inputMsg.value.trim())
    || uploadedFiles.value.length > 0
    || submittedFiles.value.length > 0
    || Boolean(inlineFormData.value)
}

const saveCurrentToHistory = (options: { force?: boolean; syncBackend?: boolean } = {}) => {
  if (!hasCurrentSessionContent()) return
  ensureMessageClientIds()

  // 防抖：同一秒内不重复保存（避免 collapse + onBeforeUnmount 双重触发）
  const now = Date.now()
  if (!options.force && now - _lastSaveTimestamp < 1000) return
  _lastSaveTimestamp = now

  const agentKey = getCurrentAgentKey()
  const agentMeta = getAgentMeta(agentKey)
  
  const session: SavedSession = {
    id: session_id.value,
    title: makeAiChatSessionTitle(messages.value),
    messages: clonePlain(messages.value),
    mode: selectedMode.value,
    agentKey,
    agentLabel: agentMeta.label,
    sessionType: agentMeta.sessionType,
    businessType: businessType.value,
    agentMode,
    routeFullPath: route.fullPath,
    stateSnapshot: captureConversationState(),
    updatedAt: now,
    savedAt: new Date().toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  savedHistories.value = upsertAiChatSession(getCurrentUserId(), session)
  uiStore.setActiveAIChatSession(session.id)
  uiStore.markAIChatHistoryChanged()

  // 同步到后端数据库（静默，不阻断前端流程）
  if (options.syncBackend !== false) {
    _syncToBackend(session)
  }
}

/** 将会话同步到后端数据库（异步静默） */
const _syncToBackend = async (session: SavedSession, replace = false) => {
  try {
    const token = localStorage.getItem('token')
    if (!token) return // 未登录不同步

    const msgs = (session.messages || []).filter(
      (m: any) => m.role === 'user' || m.role === 'assistant'
    ).map((m: any) => ({
      client_message_id: m.client_message_id || (m.client_message_id = createMessageId(m.role)),
      role: m.role,
      content: m.content,
      timestamp: m.timestamp || '',
      metadata: m.attachments?.length ? { attachments: m.attachments } : undefined,
    }))
    if (msgs.length === 0 && !replace) return

    await chatHistoryApi.syncSession({
      session_id: session.id || session_id.value,
      business_type: session.businessType || businessType.value,
      session_type: session.sessionType || 'requirement',
      messages: msgs,
      replace,
    })
  } catch (e) {
    // 静默失败，不阻断用户体验
    console.warn('[ChatHistory] 同步失败:', e)
  }
}

let _lastBackendSyncSignature = ''

/** 将当前会话按稳定 session_id 同步到后端，供管理员实时查看。 */
const syncCurrentConversationToBackend = async () => {
  ensureMessageClientIds()
  const session: SavedSession = {
    id: session_id.value,
    messages: clonePlain(messages.value),
    mode: selectedMode.value,
    agentKey: getCurrentAgentKey(),
    agentLabel: getAgentMeta().label,
    sessionType: getAgentMeta().sessionType,
    businessType: businessType.value,
    agentMode,
    routeFullPath: route.fullPath,
    stateSnapshot: captureConversationState(),
    savedAt: new Date().toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  const msgs = session.messages.filter((m: any) =>
    (m.role === 'user' || m.role === 'assistant') && (m.content || '').trim()
  )
  if (msgs.length === 0) return

  const signature = JSON.stringify({
    id: session.id,
    messages: msgs.map((m: any) => ({
      id: m.client_message_id || '',
      role: m.role,
      content: m.content,
    })),
  })
  if (signature === _lastBackendSyncSignature) return
  _lastBackendSyncSignature = signature

  saveCurrentToHistory({ force: true, syncBackend: false })
  await _syncToBackend(session)
}

const buildCurrentSavedSession = (): SavedSession => {
  ensureMessageClientIds()
  return {
    id: session_id.value,
    title: makeAiChatSessionTitle(messages.value),
    messages: clonePlain(messages.value),
    mode: selectedMode.value,
    agentKey: getCurrentAgentKey(),
    agentLabel: getAgentMeta().label,
    sessionType: getAgentMeta().sessionType,
    businessType: businessType.value,
    agentMode,
    routeFullPath: route.fullPath,
    stateSnapshot: captureConversationState(),
    updatedAt: Date.now(),
    savedAt: new Date().toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }
}

const removeCurrentSessionFromLocalHistory = () => {
  savedHistories.value = deleteAiChatSession(getCurrentUserId(), session_id.value)
  uiStore.markAIChatHistoryChanged()
}

const syncConversationReplace = async () => {
  _lastBackendSyncSignature = ''
  const session = buildCurrentSavedSession()
  if (messages.value.length === 0) {
    removeCurrentSessionFromLocalHistory()
  } else {
    _lastSaveTimestamp = 0
    saveCurrentToHistory({ force: true })
  }
  await _syncToBackend(session, true)
}

const getLastUserMessage = () => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const msg = messages.value[i]
    if (msg.role === 'user' && !msg.isContextCarryOver) {
      return msg
    }
  }
  return null
}

const hasUploadedFileSummary = (msg: any) => {
  return /\[已上传/.test(msg?.content || '')
}

const getMessageEditKey = (msg: any) => {
  return msg?.client_message_id || `${msg?.timestamp || ''}:${msg?.content || ''}`
}

const isInlineEditingMessage = (msg: any) => {
  return Boolean(inlineEditingKey.value && inlineEditingKey.value === getMessageEditKey(msg))
}

const clearInlineEdit = () => {
  inlineEditingKey.value = ''
  inlineEditText.value = ''
  inlineEditTextareaRef.value = null
  isComposing.value = false
}

const captureConversationState = (): ConversationStateSnapshot => ({
  agentKey: getCurrentAgentKey(),
  agentLabel: getAgentMeta().label,
  sessionType: getAgentMeta().sessionType,
  agentMode,
  selectedMode: selectedMode.value,
  businessType: businessType.value,
  inlineFormData: inlineFormData.value ? clonePlain(inlineFormData.value) : null,
  draftSavedOrderId: draftSavedOrderId.value,
  showConfirmation: showConfirmation.value,
  confirmOrderNumber: confirmOrderNumber.value,
  confirmOrderType: confirmOrderType.value,
  submittedFilesLength: submittedFiles.value.length,
  submittedFiles: clonePlain(submittedFiles.value),
  uploadedFiles: clonePlain(uploadedFiles.value),
  inputMsg: inputMsg.value,
  orderSubmitCompleted: orderSubmitCompleted.value,
  routeFullPath: route.fullPath,
})

const cancelGeneratedDraftIfNeeded = async (snapshot?: ConversationStateSnapshot) => {
  const currentDraftId = draftSavedOrderId.value
  if (!currentDraftId || currentDraftId === snapshot?.draftSavedOrderId) return
  try {
    await orderApi.updateOrderStatus(currentDraftId, 'cancelled' as OrderStatus)
  } catch (e) {
    console.warn('[AIChat] 自动草稿取消失败:', e)
  }
}

const restoreConversationState = async (snapshot?: ConversationStateSnapshot) => {
  clearInlineEdit()
  await cancelGeneratedDraftIfNeeded(snapshot)
  selectedMode.value = snapshot?.selectedMode ?? null
  businessType.value = snapshot?.businessType || 'ai_3d_custom'
  inlineFormData.value = snapshot?.inlineFormData ? clonePlain(snapshot.inlineFormData) : null
  draftSavedOrderId.value = snapshot?.draftSavedOrderId ?? null
  showConfirmation.value = snapshot?.showConfirmation ?? false
  confirmOrderNumber.value = snapshot?.confirmOrderNumber || ''
  confirmOrderType.value = snapshot?.confirmOrderType || 'ai_3d_custom'
  orderSubmitCompleted.value = snapshot?.orderSubmitCompleted ?? false
  submittedFiles.value = snapshot?.submittedFiles
    ? clonePlain(snapshot.submittedFiles)
    : submittedFiles.value.slice(0, snapshot?.submittedFilesLength ?? submittedFiles.value.length)
  uploadedFiles.value = snapshot?.uploadedFiles ? clonePlain(snapshot.uploadedFiles) : []
  inputMsg.value = snapshot?.inputMsg || ''
  emit('mode-change', selectedMode.value)
}

const restoreSavedSessionState = async (session: SavedSession) => {
  clearInlineEdit()
  const snapshot = session.stateSnapshot as ConversationStateSnapshot | undefined
  const agentKey = session.agentKey || snapshot?.agentKey || 'general'
  const agentMeta = getAgentMeta(agentKey)

  selectedMode.value = snapshot?.selectedMode ?? session.mode ?? agentMeta.selectedMode
  businessType.value = snapshot?.businessType || session.businessType || agentMeta.businessType || 'ai_3d_custom'
  inlineFormData.value = snapshot?.inlineFormData ? clonePlain(snapshot.inlineFormData) : null
  draftSavedOrderId.value = snapshot?.draftSavedOrderId ?? null
  showConfirmation.value = snapshot?.showConfirmation ?? false
  confirmOrderNumber.value = snapshot?.confirmOrderNumber || ''
  confirmOrderType.value = snapshot?.confirmOrderType || (businessType.value as OrderType) || 'ai_3d_custom'
  orderSubmitCompleted.value = snapshot?.orderSubmitCompleted ?? false
  submittedFiles.value = snapshot?.submittedFiles ? clonePlain(snapshot.submittedFiles) : []
  uploadedFiles.value = snapshot?.uploadedFiles ? clonePlain(snapshot.uploadedFiles) : []
  inputMsg.value = snapshot?.inputMsg || ''

  isLoading.value = false
  isTyping.value = false
  extractLoading.value = false
  isUploadingFiles.value = false
  failedUploadNames.value = []
  emit('mode-change', selectedMode.value)
  await nextTick()
  adjustTextareaHeight()
}

const canModifyLastUserMessage = (msg: any) => {
  if (!msg || msg.role !== 'user') return false
  if (!msg.stateBeforeSend) return false
  const snapshot = msg.stateBeforeSend as ConversationStateSnapshot
  if (snapshot.routeFullPath && snapshot.routeFullPath !== route.fullPath) return false
  if (orderSubmitCompleted.value) return false
  if (isLoading.value || isTyping.value || extractLoading.value || isUploadingFiles.value || showConfirmation.value) return false
  if (hasUploadedFileSummary(msg)) return false
  return getLastUserMessage() === msg
}

const truncateFromMessage = async (msg: any) => {
  const idx = messages.value.findIndex(m => m === msg)
  if (idx < 0) return false
  const snapshot = msg.stateBeforeSend as ConversationStateSnapshot | undefined
  messages.value = messages.value.slice(0, idx)
  await restoreConversationState(snapshot)
  return true
}

const editLastUserMessage = async (msg: any) => {
  await startInlineEdit(msg)
}

const startInlineEdit = async (msg: any) => {
  if (hasUploadedFileSummary(msg)) {
    ElMessage.warning('包含上传文件的消息暂不支持编辑')
    return
  }
  if (!canModifyLastUserMessage(msg)) return
  inlineEditingKey.value = getMessageEditKey(msg)
  inlineEditText.value = displayUserMessageText(msg.content || '')
  await nextTick()
  adjustInlineEditHeight()
  const ta = inlineEditTextareaRef.value
  if (ta) {
    ta.focus()
    const end = ta.value.length
    ta.setSelectionRange(end, end)
  }
}

const cancelInlineEdit = () => {
  clearInlineEdit()
}

const submitInlineEdit = async (msg: any) => {
  if (!isInlineEditingMessage(msg)) return
  if (!canModifyLastUserMessage(msg)) {
    clearInlineEdit()
    return
  }

  const editedText = inlineEditText.value.trim()
  if (!editedText) {
    ElMessage.warning('编辑内容不能为空')
    await nextTick()
    inlineEditTextareaRef.value?.focus()
    return
  }

  if (editedText === displayUserMessageText(msg.content || '').trim()) {
    clearInlineEdit()
    return
  }

  if (!(await truncateFromMessage(msg))) return
  clearInlineEdit()
  await syncConversationReplace()
  inputMsg.value = editedText
  await nextTick()
  await sendMessage()
}

const handleInlineEditEnter = (e: KeyboardEvent, msg: any) => {
  if (e.shiftKey) return
  if (e.isComposing || isComposing.value) return
  e.preventDefault()
  submitInlineEdit(msg)
}

const revokeLastUserMessage = async (msg: any) => {
  if (hasUploadedFileSummary(msg)) {
    ElMessage.warning('包含上传文件的消息暂不支持撤回')
    return
  }
  if (!canModifyLastUserMessage(msg)) return
  if (!(await truncateFromMessage(msg))) return
  clearInlineEdit()
  inputMsg.value = ''
  await syncConversationReplace()
  ElMessage.success('已撤回最后一条消息')
}

const restoreHistoryById = async (id: string) => {
  if (!id) return
  if (id === session_id.value) {
    uiStore.clearPendingAIChatSession()
    uiStore.setActiveAIChatSession(id)
    return
  }

  saveCurrentToHistory({ force: true })
  loadSavedHistory()
  let history = savedHistories.value.find(session => session.id === id)
  if (!history) {
    history = await loadBackendHistoryById(id) || undefined
  }
  if (!history) {
    uiStore.clearPendingAIChatSession()
    return
  }

  session_id.value = history.id
  messages.value = clonePlain(history.messages || [])
  await restoreSavedSessionState(history)
  uiStore.setActiveAIChatSession(history.id)
  uiStore.clearPendingAIChatSession()
  scrollToBottom(true) // 恢复历史时瞬间到底，不要用平滑动画，否则容易卡在最上面
}

const displayContent = (text: string) => {
  if (!text) return ''
  return text.replace(/【推荐案例:case_\w+】/g, '').replace(/【引导下单(?::[^】]+)?】/g, '').trim()
}

// 高亮搜索关键词
const highlightSearch = (text: string) => {
  if (!text) return ''
  // 先转义 HTML 实体防止 XSS
  const sanitized = text.replace(/</g, "&lt;").replace(/>/g, "&gt;")
  const q = searchQuery.value.trim()
  if (!q) return sanitized
  
  // 正则转义关键词
  const escapedQ = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escapedQ})`, 'gi')
  return sanitized.replace(regex, '<mark class="highlight-text">$1</mark>')
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
const typewriterEffect = (fullText: string, onComplete?: () => void | Promise<void>, clientMessageId?: string) => {
  isLoading.value = false
  isTyping.value = true
  
  // 先 push 一条空的 assistant 消息
  const msgIndex = messages.value.length
  messages.value.push({
    client_message_id: clientMessageId || createMessageId('assistant'),
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
      
      ;(async () => {
        if (onComplete) await onComplete()
        saveCurrentToHistory({ force: true, syncBackend: false })
        await syncCurrentConversationToBackend()
      })()
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
    video_purchase: '3D OOH数字内容资源库',
    ai_3d_custom: 'AI驱动3D OOH内容定制',
    digital_art: '数字艺术与沉浸式视觉设计',
    motion_content: '广告视觉与动态影像制作',
    media_post_production: '户外媒体后期制作服务',
    campaign_analytics: '广告投放分析与效果报告'
  }
  return map[type] || type
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

const activateOrderCreateFromGuide = (type: string = 'ai_3d_custom', requirementSummary: string = '') => {
  businessType.value = type
  selectedMode.value = 'order_create'
  emit('mode-change', 'order_create')

  if (requirementSummary) {
    messages.value.push({
      role: 'user',
      content: `[用户在业务咨询时描述的需求：${requirementSummary}]`,
      timestamp: getCurrentTime(),
      isContextCarryOver: true
    })
  }
}

// 从业务介绍切换到下单 Agent。可见话术统一由后端 /ai/start 输出。
const switchToOrderCreate = async (type: string = 'ai_3d_custom') => {
  activateOrderCreateFromGuide(type)
  isLoading.value = true
  try {
    const params = new URLSearchParams({
      session_id: session_id.value,
      business_type: type,
    })
    const response = await fetch(`/ai/start?${params.toString()}`, {
      headers: getAuthHeaders()
    })
    if (!response.ok || response.headers.get('content-type')?.includes('text/html')) {
      throw new Error('API not available')
    }
    const result = await response.json()
    if (result.reply) typewriterEffect(result.reply)
  } catch (e) {
    typewriterEffect('已进入需求梳理流程。请先告诉我项目名称。')
  } finally {
    isLoading.value = false
  }
}

const selectMode = async (mode: string) => {
  selectedMode.value = mode
  emit('mode-change', mode)
  
  if (mode === 'order_create') {
    // 需求收集 Agent 开场白
    isLoading.value = true
    try {
      const response = await fetch(`/ai/start?session_id=${session_id.value}`, {
        headers: getAuthHeaders()
      })
      if (!response.ok || response.headers.get('content-type')?.includes('text/html')) {
        throw new Error('API not available')
      }
      const result = await response.json()
      if (result.reply) typewriterEffect(result.reply)
    } catch (e) {
      const fallback = '您好，我是 Unique Vision AI 的项目顾问。\n\n我可以协助您梳理项目需求、确认关键制作信息，并在信息完整后生成需求单。\n\n请先简单介绍这次项目的背景、投放场景或内容方向。'
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
        headers: getAuthHeaders(),
        body: JSON.stringify({ message: '请介绍一下你们的业务', history: [] })
      })
      if (!response.ok) throw new Error('intro failed')
      const data = await response.json()
      const cleanMsg = (data.message || '').replace(/【引导下单(?::[^】]+)?】/g, '').trim()
      typewriterEffect(cleanMsg)
    } catch (e) {
      const fallback = 'Unique Vision AI 提供六大平台服务：\n\n**3D OOH数字内容资源库**\nReady-to-Deploy 3D DOOH Assets：即用型裸眼3D数字内容资产\nScreen-Adaptive Content Packages：多屏适配内容方案\nGlobal Landmark Screen Formats：全球地标大屏内容规格适配\n\n**AI驱动3D OOH内容定制**\nAI-Based Creative Development：AI创意内容开发\nSite-Specific 3D Screen Adaptation：场景化裸眼3D空间适配\nReal-World Playback Simulation：真实环境播放模拟\nEnd-to-End DOOH Content Production：一站式DOOH内容制作\n\n**数字艺术与沉浸式视觉设计**\nArt Direction & Visual Design：艺术指导与视觉设计\nVirtual Installation Art：虚拟装置艺术\nImmersive Spatial Visuals：沉浸式空间视觉\nExperimental Digital Art Content：实验性数字艺术内容\n\n**广告视觉与动态影像制作**\nStatic Advertising Visuals：平面广告视觉设计\nTVC Production：TVC广告影片制作\nFOOH Campaign Content：FOOH数字传播内容\nVJ Visual Performance Content：VJ视觉演出内容\nMotion Graphic Design：动态视觉设计\n\n**户外媒体后期制作服务**\nHigh-End Retouching：高端精修图像处理\nCinematic Video Finishing：电影级视频精修\nCGI Enhancement：CGI视觉增强\nCommercial Photography & Filming：商业摄影与视频拍摄\nDrone Cinematography：航拍影像制作\n\n**广告投放分析与效果报告**\nDOOH Campaign Analytics：DOOH广告投放数据分析\nAudience Performance Reports：受众效果分析报告\nVisual Impact Assessment：视觉传播效果评估\nDownloadable Data Reports：可下载数据报告系统\n\n如需了解某个板块的详细信息或过往案例，请直接告知。'
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
  if (isLoading.value || isTyping.value) return
  if (inlineEditingKey.value) {
    ElMessage.warning('请先完成或取消当前消息编辑')
    await nextTick()
    inlineEditTextareaRef.value?.focus()
    return
  }
  if (isUploadingFiles.value) {
    ElMessage.warning('文件仍在上传中，请稍候再发送')
    return
  }

  const userText = inputMsg.value.trim()
  const pendingFiles = [...uploadedFiles.value]
  if (!userText && pendingFiles.length === 0) return

  if (failedUploadNames.value.length > 0) {
    const failedNames = failedUploadNames.value.join('、')
    failedUploadNames.value = []
    ElMessage.warning(`${failedNames} 上传失败，未随本条消息发送。请重新选择文件后再发送。`)
    return
  }

  const messageContent = buildUserMessageContent(userText, pendingFiles)
  const stateBeforeSend = captureConversationState()
  const userMessageId = createMessageId('user')
  messages.value.push({
    client_message_id: userMessageId,
    role: 'user',
    content: messageContent,
    timestamp: getCurrentTime(),
    attachments: pendingFiles.length ? pendingFiles : undefined,
    stateBeforeSend,
  })
  inputMsg.value = ''
  if (pendingFiles.length > 0) {
    submittedFiles.value.push(...pendingFiles)
    uploadedFiles.value = []
  }
  saveCurrentToHistory({ force: true, syncBackend: false })
  logger.logAction('AI', 'send_message', { mode: selectedMode.value, textLength: userText.length, fileCount: pendingFiles.length })
  
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
  
  // 如果还没有选择模式，先做意图分类
  if (!selectedMode.value) {
    isLoading.value = true
    try {
      const classifyRes = await fetch('/ai/classify', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message: messageContent })
      })
      if (classifyRes.ok) {
        const { intent, business_type } = await classifyRes.json()
        if (business_type) businessType.value = business_type
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
  if (_caseKeywords.some(kw => messageContent.includes(kw))) {
    // 标记用户的案例请求消息，避免污染需求收集上下文
    const lastUserMsg = messages.value[messages.value.length - 1]
    if (lastUserMsg && lastUserMsg.role === 'user') lastUserMsg.isCaseDetour = true
    await handleBusinessIntro(messageContent, true)
    return
  }

  if (isHumanHandoffRequest(messageContent)) {
    selectedMode.value = 'order_create'
    emit('mode-change', 'order_create')
    await handleCustomAiChat(messageContent, userMessageId)
    return
  }

  if (selectedMode.value === 'order_create') {
    await handleCustomAiChat(messageContent, userMessageId)
  } else if (selectedMode.value === 'order_query') {
    await handleOrderQuery(messageContent)
  } else if (selectedMode.value === 'business_intro') {
    await handleBusinessIntro(messageContent)
  } else {
    await handleGeneral(messageContent, userMessageId)
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
    void syncCurrentConversationToBackend()
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
      headers: getAuthHeaders(),
      body: JSON.stringify({ message: userText, history: historyMsgs })
    })
    if (!response.ok) throw new Error('intro failed')
    const data = await response.json()
    if (data.business_type) businessType.value = data.business_type
    const replyContent = data.message || ''
    // 显示时清洗掉内部标记
    const cleanMsg = replyContent.replace(/【推荐案例:case_\w+】/g, '').replace(/【引导下单(?::[^】]+)?】/g, '').trim()
    const cases = data.cases || []
    
    typewriterEffect(cleanMsg, () => {
      // 打字结束后，用原始内容（含案例标记）覆盖 content
      // 这样下一轮历史发给 LLM 时，它能看到之前推荐过哪些案例
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content = replyContent
      }
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
          // 后端已经输出了可见引导语，前端只切换状态并携带隐藏上下文。
          activateOrderCreateFromGuide(guide.business_type, guide.requirement_summary)
        } else {
          // 后端已经输出了可见引导语，前端只把业务选择按钮挂到同一条消息上。
          const lastGuideMsg = messages.value[messages.value.length - 1]
          if (lastGuideMsg && lastGuideMsg.role === 'assistant') {
            lastGuideMsg.isGuideToOrder = true
          }
          scrollToBottom()
        }
      }
    })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '获取信息时遇到问题，请稍后重试。', timestamp: getCurrentTime() })
    void syncCurrentConversationToBackend()
  } finally {
    isLoading.value = false
  }
}

// ===== 通用问答 handler =====
const routeByBackendIntent = async (data: any, userText: string, userMessageId?: string) => {
  const intent = data?.intent
  const routedBusinessType = data?.business_type
  if (intent === 'order_create') {
    businessType.value = routedBusinessType || businessType.value || 'ai_3d_custom'
    selectedMode.value = 'order_create'
    emit('mode-change', 'order_create')
    logger.logAction('AI', 'backend_route_detected', { intent, businessType: businessType.value, sessionId: session_id.value })
    await handleCustomAiChat(userText, userMessageId)
    return true
  }
  if (intent === 'order_query') {
    selectedMode.value = 'order_query'
    emit('mode-change', 'order_query')
    logger.logAction('AI', 'backend_route_detected', { intent, sessionId: session_id.value })
    await handleOrderQuery(userText)
    return true
  }
  if (intent === 'business_intro') {
    selectedMode.value = 'business_intro'
    emit('mode-change', 'business_intro')
    logger.logAction('AI', 'backend_route_detected', { intent, sessionId: session_id.value })
    await handleBusinessIntro(userText)
    return true
  }
  return false
}

const handleGeneral = async (userText: string, userMessageId?: string) => {
  isLoading.value = true
  try {
    const historyMsgs = messages.value
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }))
    const response = await fetch('/ai/general', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: session_id.value, message: userText, history: historyMsgs })
    })
    if (!response.ok) throw new Error('general failed')
    const data = await response.json()
    if (await routeByBackendIntent(data, userText, userMessageId)) return
    typewriterEffect(data.message || '感谢您的提问！')
  } catch (e) {
    const fallback = '我是 Unique Vision AI 的项目顾问。\n\n我可以协助您梳理项目需求、查询订单进展，或介绍平台服务体系。请问您需要哪方面的支持？'
    typewriterEffect(fallback)
  } finally {
    isLoading.value = false
  }
}

const cleanRequirementReply = (text: string = '') => {
  const controlMarkers = ['【需求收集完成】', HUMAN_HANDOFF_MARKER]
  let cleaned = text
  for (const marker of controlMarkers) {
    cleaned = cleaned.replace(new RegExp(marker, 'g'), '')
  }
  for (const marker of controlMarkers) {
    for (let i = 1; i < marker.length; i += 1) {
      const prefix = marker.slice(0, i)
      if (cleaned.endsWith(prefix)) {
        cleaned = cleaned.slice(0, -prefix.length)
        break
      }
    }
  }
  return cleaned.trim()
}

const findAssistantMessage = (assistantMessageId?: string) => {
  if (assistantMessageId) {
    const byId = messages.value.find(m => m.client_message_id === assistantMessageId)
    if (byId && byId.role === 'assistant') return byId
  }
  const lastMsg = messages.value[messages.value.length - 1]
  return lastMsg && lastMsg.role === 'assistant' ? lastMsg : null
}

const applyCustomAiChatFinalState = async (data: any, replyContent: string, assistantMessageId?: string) => {
  const isHumanHandoff = Boolean(data?.handoff) || replyContent.includes(HUMAN_HANDOFF_MARKER)
  const userMsgCount = messages.value.filter(m => m.role === 'user').length
  const shouldComplete = !isHumanHandoff && replyContent.includes('【需求收集完成】') && userMsgCount >= 3
  const assistantMsg = findAssistantMessage(assistantMessageId)

  if (assistantMsg) {
    assistantMsg.content = cleanRequirementReply(replyContent)
  }

  if (isHumanHandoff) {
    if (assistantMsg) {
      assistantMsg.isHumanHandoff = true
      assistantMsg.formHidden = true
    }
    if (data?.draft_order_id) {
      draftSavedOrderId.value = data.draft_order_id
      await orderStore.fetchOrders()
    }
    return
  }

  if (shouldComplete) {
    if (assistantMsg) {
      assistantMsg.isCompletePrompt = true
    }
    await autoExtractAndSaveDraft()
  }
}

const buildRequirementChatPayload = (userText: string, userMessageId?: string, assistantMessageId?: string) => {
  const historyMessages = messages.value.slice(0, messages.value.length - 1)
  const formattedHistory = historyMessages
    .filter(m => (m.role === 'user' || m.role === 'assistant') && !m.isCaseDetour)
    .map(m => ({ role: m.role, content: m.content }))

  return {
    session_id: session_id.value,
    message: userText,
    history: formattedHistory,
    business_type: businessType.value,
    user_message_id: userMessageId,
    assistant_message_id: assistantMessageId
  }
}

const handleCustomAiChatJson = async (userText: string, userMessageId?: string, assistantMessageId?: string) => {
  const response = await fetch('/ai/chat', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(buildRequirementChatPayload(userText, userMessageId, assistantMessageId))
  })

  if (!response.ok || response.headers.get('content-type')?.includes('text/html')) {
    throw new Error('API not available, fallback to user-visible error')
  }

  const data = await response.json()
  const replyContent = data.message || data.answer || '处理成功'
  typewriterEffect(cleanRequirementReply(replyContent), async () => {
    await applyCustomAiChatFinalState(data, replyContent, assistantMessageId)
  }, assistantMessageId)
}

const handleCustomAiChatStream = async (userText: string, userMessageId?: string, assistantMessageId?: string) => {
  const response = await fetch('/ai/chat/stream', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(buildRequirementChatPayload(userText, userMessageId, assistantMessageId))
  })

  if (!response.ok || response.headers.get('content-type')?.includes('text/html') || !response.body) {
    throw new Error('stream API not available')
  }

  const msgIndex = messages.value.length
  messages.value.push({
    client_message_id: assistantMessageId || createMessageId('assistant'),
    role: 'assistant',
    content: '',
    timestamp: getCurrentTime()
  })
  isLoading.value = false
  isTyping.value = true

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let rawReply = ''
  let sawDelta = false
  let finalReceived = false

  const dispatchEvent = async (block: string) => {
    if (!block.trim()) return
    let eventName = 'message'
    const dataLines: string[] = []
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) eventName = line.slice(6).trim()
      if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (dataLines.length === 0) return
    const data = JSON.parse(dataLines.join('\n'))

    if (eventName === 'delta') {
      const chunk = data.content || ''
      if (!chunk) return
      rawReply += chunk
      sawDelta = true
      const msg = messages.value[msgIndex]
      if (msg && msg.role === 'assistant') {
        msg.content = cleanRequirementReply(rawReply)
      }
      scrollToBottom()
      return
    }

    if (eventName === 'final') {
      const replyContent = data.message || rawReply
      const msg = messages.value[msgIndex]
      if (msg && msg.role === 'assistant') {
        msg.content = cleanRequirementReply(replyContent)
      }
      await applyCustomAiChatFinalState(data, replyContent, assistantMessageId)
      finalReceived = true
      return
    }

    if (eventName === 'error') {
      throw new Error(data.detail || 'stream failed')
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split(/\n\n/)
      buffer = blocks.pop() || ''
      for (const block of blocks) {
        await dispatchEvent(block)
      }
    }
    buffer += decoder.decode()
    if (buffer.trim()) {
      await dispatchEvent(buffer)
    }
    if (!finalReceived) {
      throw new Error('stream ended before final event')
    }
    isTyping.value = false
    scrollToBottom()
    nextTick(() => textareaRef.value?.focus())
    saveCurrentToHistory({ force: true, syncBackend: false })
    await syncCurrentConversationToBackend()
    return true
  } catch (error) {
    isTyping.value = false
    isLoading.value = false
    logger.logAction('AI', 'chat_stream_failed', { mode: selectedMode.value, businessType: businessType.value, sessionId: session_id.value })
    if (!sawDelta) {
      const msg = messages.value[msgIndex]
      if (msg && msg.role === 'assistant' && !msg.content) {
        messages.value.splice(msgIndex, 1)
      }
      return false
    }
    const msg = messages.value[msgIndex]
    if (msg && msg.role === 'assistant') {
      msg.content = `${cleanRequirementReply(rawReply)}\n\n模型响应中断，请重新发送上一条内容，我会继续从当前上下文往下梳理。`.trim()
    }
    saveCurrentToHistory({ force: true, syncBackend: false })
    await syncCurrentConversationToBackend()
    return true
  } finally {
    reader.releaseLock()
  }
}

const handleCustomAiChat = async (userText: string, userMessageId?: string) => {
  isLoading.value = true
  const assistantMessageId = createMessageId('assistant')
  try {
    try {
      const streamHandled = await handleCustomAiChatStream(userText, userMessageId, assistantMessageId)
      if (streamHandled) {
        return
      }
    } catch (streamError) {
      logger.logAction('AI', 'chat_stream_unavailable', { mode: selectedMode.value, businessType: businessType.value, sessionId: session_id.value })
    }
    isLoading.value = true
    await handleCustomAiChatJson(userText, userMessageId, assistantMessageId)

  } catch (error) {
    if (isHumanHandoffRequest(userText)) {
      typewriterEffect(HUMAN_HANDOFF_FALLBACK_REPLY, () => {
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.isHumanHandoff = true
          lastMsg.formHidden = true
        }
      })
      return
    }

    logger.logAction('AI', 'chat_request_failed', { mode: selectedMode.value, businessType: businessType.value, sessionId: session_id.value })
    messages.value.push({
      role: 'assistant',
      content: '模型响应超时或暂时不可用，这条需求还没有成功记录。请稍后重新发送上一条内容，我会继续从当前上下文往下梳理。',
      timestamp: getCurrentTime()
    })
    void syncCurrentConversationToBackend()
    isLoading.value = false
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
        headers: getAuthHeaders(),
        body: JSON.stringify({ history: formattedHistory })
      })
      if (response.ok) {
        const data = await response.json()
        if (Object.keys(data).length > 0) extracted = data
      }
    } catch (e) {
      console.error('extract failed:', e)
    }
    const hasExtractedValue = Object.values(extracted).some(v => String(v || '').trim())
    if (!hasExtractedValue) {
      messages.value.push({
        role: 'assistant',
        content: '需求整理暂时失败，未生成草稿。请稍后点击继续对话补充或重新发送上一条信息，我会重新整理。',
        timestamp: getCurrentTime()
      })
      void syncCurrentConversationToBackend()
      return
    }
    for (const field of formFields) {
      if (!extracted[field.key]) extracted[field.key] = ''
    }
    
    // ===== 专业项目评估 =====
    let assessmentText = ''
    try {
      const assessRes = await fetch('/ai/assess', {
        method: 'POST',
        headers: getAuthHeaders(),
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
    // 将上传的文件信息自动填入"现场实拍图"字段（文本展示）
    if (submittedFiles.value.length > 0) {
      const fileInfo = submittedFiles.value.map(f => f.name).join('、')
      inlineFormData.value.site_photos = (inlineFormData.value.site_photos || '') 
        ? inlineFormData.value.site_photos + '；' + fileInfo 
        : fileInfo
    }
    try {
      const orderType = businessType.value
      // 构造 scenePhotos 数组（后端需要 FileUpload 格式的对象数组）
      const scenePhotos = submittedFiles.value.map((f, idx) => ({
        id: `upload_${Date.now()}_${idx}`,
        name: f.name,
        size: f.size || 0,
        type: f.type || 'application/octet-stream',
        uploadTime: f.uploadTime || new Date().toISOString(),
        url: f.url,
        object_key: f.objectKey || ''
      }))
      const newOrder = await orderStore.createOrder({ orderType, ...extracted, scenePhotos }, true)
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

const handleSubmitOrder = async () => {
  if (!inlineFormData.value) return
  
  // 检查企业认证状态
  const enterpriseStatus = await getLatestEnterpriseStatus(authStore)
  if (enterpriseStatus !== 'approved') {
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
    // 构造 scenePhotos 数组（后端需要 FileUpload 格式的对象数组）
    const scenePhotos = submittedFiles.value.map((f, idx) => ({
      id: `upload_${Date.now()}_${idx}`,
      name: f.name,
      size: f.size || 0,
      type: f.type || 'application/octet-stream',
      uploadTime: f.uploadTime || new Date().toISOString(),
      url: f.url,
      object_key: f.objectKey || ''
    }))
    if (draftSavedOrderId.value) {
      await orderStore.updateOrder(draftSavedOrderId.value, {
        orderType: confirmOrderType.value,
        ...inlineFormData.value,
        scenePhotos
      })
      await orderStore.updateOrderStatus(draftSavedOrderId.value, 'pending_contract')
    } else {
      await orderStore.createOrder({
        orderType: confirmOrderType.value,
        ...inlineFormData.value,
        scenePhotos
      }, false)
    }
    messages.value.push({
      role: 'assistant',
      content: '🎉 订单已正式提交成功！我们的团队会尽快开始处理。您可以在"我的订单"中查看进度。',
      timestamp: getCurrentTime()
    })
    orderSubmitCompleted.value = true
    scrollToBottom()
    saveCurrentToHistory()
  } catch (e) {
    console.error('submit order failed', e)
    ElMessage.error('订单提交失败，请稍后重试')
  }
}

</script>

<style lang="scss" scoped>
/* 搜索高亮样式 */
:deep(.highlight-text) {
  background-color: rgba(255, 215, 0, 0.4);
  color: inherit;
  border-radius: 2px;
  padding: 0 2px;
}
.typing-cursor-indicator {
  display: inline-flex;
  align-items: center;
  margin: -4px 0 0 0;
  padding-left: 12px;
  color: rgba(0, 0, 0, 0.4);
  font-size: 13px;
  line-height: 1.5;
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
  position: relative;
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

.user-message-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  min-height: 18px;
  opacity: 0;
  transform: translateY(-2px);
  pointer-events: none;
  transition: opacity 0.18s ease 0.22s, transform 0.18s ease 0.22s;
}

.user-col:hover .user-message-actions,
.user-col:focus-within .user-message-actions {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
  transition-delay: 0s;
}

.msg-action-btn {
  appearance: none;
  border: none;
  background: transparent;
  color: #7c828c;
  font-size: 11px;
  line-height: 1;
  padding: 3px 0;
  cursor: pointer;
}

.msg-action-btn:hover {
  color: #1a1c1c;
}

.msg-action-btn.danger:hover {
  color: #b42318;
}

.inline-message-edit {
  width: min(520px, 72vw);
  min-width: 280px;
  max-width: 100%;
  background: #ffffff;
  border: 1px solid #d8dde6;
  border-radius: 12px 12px 0 12px;
  box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08);
  padding: 10px;
}

.inline-message-edit-textarea {
  width: 100%;
  min-height: 72px;
  max-height: 220px;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  color: #1a1c1c;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
  letter-spacing: 0;
  padding: 0;
  overflow-y: auto;
}

.inline-message-edit-textarea::placeholder {
  color: #9aa0a6;
}

.inline-message-edit-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.inline-edit-btn {
  appearance: none;
  border: 1px solid transparent;
  border-radius: 9999px;
  height: 28px;
  padding: 0 14px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.inline-edit-btn.secondary {
  background: #f6f7f8;
  border-color: #e5e7eb;
  color: #3f4652;
}

.inline-edit-btn.secondary:hover {
  background: #eef0f3;
}

.inline-edit-btn.primary {
  background: #0d99ff;
  color: #ffffff;
}

.inline-edit-btn.primary:hover {
  background: #087bd3;
}

.message-attachment-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  max-width: 280px;
  margin-top: 6px;
}

.message-attachment-preview {
  width: 64px;
  height: 64px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.message-attachment-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.message-file-preview {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #5f6368;
  font-size: 10px;
  font-weight: 600;
  background: #f6f7f8;
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
  background: #0058bc;
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
  overflow: hidden;
}

.user-avatar.has-image {
  background: #ffffff;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
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
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.thinking-ellipsis {
  display: inline-flex;
  width: 3em;
  margin-left: 1px;
}

.thinking-ellipsis span {
  opacity: 0;
  animation: thinking-dot-reveal 1.4s steps(1, end) infinite;
}

.thinking-ellipsis span:nth-child(2) {
  animation-delay: 0.16s;
}

.thinking-ellipsis span:nth-child(3) {
  animation-delay: 0.32s;
}

.thinking-ellipsis span:nth-child(4) {
  animation-delay: 0.48s;
}

.thinking-ellipsis span:nth-child(5) {
  animation-delay: 0.64s;
}

.thinking-ellipsis span:nth-child(6) {
  animation-delay: 0.8s;
}

@keyframes thinking-dot-reveal {
  0%, 72%, 100% { opacity: 0; }
  12%, 60% { opacity: 1; }
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

/* 已上传文件预览条 */
.uploaded-files-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 4px 0;
  max-width: 100%;
}

.uploaded-file-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(13, 153, 255, 0.08);
  border: 1px solid rgba(13, 153, 255, 0.2);
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 12px;
  color: #555;
  max-width: 180px;
}

.file-thumb {
  width: 24px;
  height: 24px;
  object-fit: cover;
  border-radius: 3px;
}

.file-icon-placeholder {
  font-size: 18px;
  color: #0d99ff;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100px;
}

.file-status {
  flex: 0 0 auto;
  color: #0d99ff;
  font-size: 11px;
}

.upload-more-hint {
  flex: 0 1 auto;
  margin-left: auto;
  min-width: 0;
  color: #9aa0a6;
  font-size: 12px;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-remove {
  cursor: pointer;
  color: #999;
  font-size: 14px;
  line-height: 1;
  margin-left: 2px;
}

.file-remove:hover {
  color: #f56c6c;
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

.form-attachment-preview {
  margin-top: 12px;
}

.form-attachment-label {
  font-size: 11px;
  font-weight: 600;
  color: #86868b;
  margin-bottom: 6px;
}

.form-attachment-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.form-attachment-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  max-width: 180px;
  padding: 4px 8px 4px 4px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
}

.form-attachment-thumb,
.form-file-thumb {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  flex: 0 0 auto;
}

.form-attachment-thumb {
  object-fit: cover;
  display: block;
}

.form-file-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0d99ff;
  background: rgba(13, 153, 255, 0.08);
}

.form-attachment-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #555;
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
