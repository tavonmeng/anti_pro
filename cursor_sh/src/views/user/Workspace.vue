<template>
  <div class="workspace-page">
    
    <div class="workspace-layout" :class="{ 'is-split': uiStore.isAiExpanded }">
      <div class="main-column" :class="{ 'is-squished': uiStore.isAiExpanded }">

        <!-- Professional B2B Fast Cross-Fade -->
        <transition name="fade" mode="out-in">
          <!-- Overview Mode -->
          <div v-if="!uiStore.isAiExpanded && !uiStore.isSecondarySidebarVisible" class="overview-state">
            
            <!-- Hero Banner (AI 智能体) -->
            <div class="hero-banner" data-onboarding-target="ai-hero-entry">
              <div class="hero-bg-stack" aria-hidden="true">
                <transition name="hero-bg-fade">
                  <div
                    :key="activePromptBackground"
                    class="hero-bg-image"
                    :style="{ backgroundImage: `url(${activePromptBackground})` }"
                  ></div>
                </transition>
                <div class="hero-bg-overlay"></div>
              </div>
              <div class="hero-content">
                <h1 class="hero-title">Unique Vision AI智能体 | 咨询·需求·下单，一站式协助</h1>
                <div class="hero-input-area" @click="handleAiExpand(true)">
                  <input type="text" :placeholder="placeholderText" class="hero-input" readonly />
                  <div class="generate-btn">
                    发送 <span class="sparkle" aria-hidden="true"></span>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="figma-divider"></div>

            <!-- 业务服务概览 -->
            <div class="business-services-section">
          <div class="section-header">
            <div class="section-titles">
              <h2 class="section-title">业务菜单</h2>
              <p class="section-subtitle">平台服务体系</p>
            </div>
          </div>
          
          <!-- 服务入口卡片 -->
          <div class="service-cards" data-onboarding-target="business-service-list">
            <div
              v-for="service in platformServices"
              :key="service.type"
              class="service-card"
              :data-onboarding-target="`business-service-card-${service.type}`"
              role="button"
              tabindex="0"
              @click="triggerChoreography(service.type)"
              @keydown.enter.self.prevent="triggerChoreography(service.type)"
              @keydown.space.self.prevent="triggerChoreography(service.type)"
            >
              <div class="card-image-wrapper">
                <div class="card-img" :style="{ background: service.gradient }">
                  <img class="card-image" :src="service.image" :alt="service.title" />
                </div>
                <div class="overlay-badge">{{ getServiceBadgeLabel(service.badge) }}</div>
              </div>
              <div class="card-body">
                <h3 class="service-title">{{ service.title }}</h3>
                <div class="service-features">
                  <span v-for="feature in service.features" :key="feature" class="outline-tag">{{ feature }}</span>
                </div>
                <div class="card-footer">
                  <span class="price-text">{{ service.footer }}</span>
                  <el-icon class="arrow-right"><Right /></el-icon>
                </div>
              </div>
            </div>
          </div>
          </div>
          </div>

          <!-- Working Mode: AI Assistant Expanded View -->
          <div class="full-ai-container" v-else-if="uiStore.isAiExpanded">
            <AIChatAssistant @close="handleAiExpand(false)" @mode-change="handleModeChange" />
          </div>

          <!-- Service focus fallback while lazy-loaded business routes resolve -->
          <div v-else class="service-focus-state">
            <div v-if="activeService" class="service-focus-panel">
              <div class="service-focus-media" :style="{ background: activeService.gradient }">
                <img class="service-focus-image" :src="activeService.image" :alt="activeService.title" />
                <div class="service-focus-badge">{{ getServiceBadgeLabel(activeService.badge) }}</div>
              </div>
              <div class="service-focus-copy">
                <div class="section-label">SERVICE DETAIL</div>
                <h2 class="service-focus-title">{{ activeService.title }}</h2>
                <div class="service-focus-features">
                  <span v-for="feature in activeService.features" :key="feature">{{ feature }}</span>
                </div>
                <div class="service-focus-actions">
                  <el-button type="primary" @click="goToActiveService">
                    {{ activeService.type === 'video_purchase' ? '查看资源库' : (activeService.orderable ? '填写需求' : '咨询服务') }}
                    <el-icon class="action-icon"><Right /></el-icon>
                  </el-button>
                  <el-button @click="handleAiExpand(true)">AI 顾问</el-button>
                </div>
              </div>
            </div>
            <div v-else class="overview-state">
              <div class="hero-banner" data-onboarding-target="ai-hero-entry">
                <div class="hero-bg-stack" aria-hidden="true">
                  <transition name="hero-bg-fade">
                    <div
                      :key="activePromptBackground"
                      class="hero-bg-image"
                      :style="{ backgroundImage: `url(${activePromptBackground})` }"
                    ></div>
                  </transition>
                  <div class="hero-bg-overlay"></div>
                </div>
                <div class="hero-content">
                  <h1 class="hero-title">Unique Vision AI智能体 | 咨询·需求·下单，一站式协助</h1>
                  <div class="hero-input-area" @click="handleAiExpand(true)">
                    <input type="text" :placeholder="placeholderText" class="hero-input" readonly />
                    <div class="generate-btn">
                      发送 <span class="sparkle" aria-hidden="true"></span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>

      </div> <!-- end main-column -->
      
      <transition name="fade">
        <StyleInspirationSidebar v-if="uiStore.isAiExpanded && showInspiration && !isMobileWorkspace" @close="showInspiration = false" />
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Right } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { useUiStore } from '@/stores/ui'
import { getServiceBadgeLabel, getServiceByType, platformServices, type ServiceType } from '@/data/platformServices'
import AIChatAssistant from '@/components/AIChatAssistant.vue'
import StyleInspirationSidebar from '@/components/StyleInspirationSidebar.vue'
import { logger } from '@/utils/logger'

const router = useRouter()
const orderStore = useOrderStore()
const uiStore = useUiStore()

const aiSelectedMode = ref<string | null>(null)
const showInspiration = ref(true)
const isMobileWorkspace = ref(false)
const activeService = computed(() => getServiceByType(uiStore.activeModule))

const promptSlides = [
  {
    text: "我想做一个关于蒙牛品牌推广的3D视频，主题是...",
    background: "/background/milk.jpg"
  },
  {
    text: "帮我设计一段赛博朋克风格的裸眼3D球鞋广告，要有超强的出屏效果...",
    background: "/background/shose.jpg"
  },
  {
    text: "想做一条毛绒质感猫狗互动的裸眼3D视频，治愈又有出屏感...",
    background: "/background/dog.jpg"
  },
  {
    text: "帮我生成一段大牌护肤品的新品发布3D视频，要求水珠材质特别逼真...",
    background: "/background/makeup.jpg"
  },
  {
    text: "给我们的新款新能源汽车做个3D动态视频，让车穿梭在未来都市...",
    background: "/background/car.jpg"
  }
]

const promptTexts = promptSlides.map((slide) => slide.text)
const placeholderText = ref("|")
const currentPromptIndex = ref(0)
const activePromptBackground = computed(() => {
  return promptSlides[currentPromptIndex.value]?.background || promptSlides[0].background
})
let timer: ReturnType<typeof setTimeout> | null = null
let blinkTimer: ReturnType<typeof setInterval> | null = null

const updateMobileWorkspaceState = () => {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
  isMobileWorkspace.value = window.matchMedia('(max-width: 768px)').matches
  if (isMobileWorkspace.value && uiStore.isAiExpanded) {
    uiStore.setSecondarySidebar(false)
    uiStore.toggleSidebar(false)
    showInspiration.value = false
  }
}

onMounted(() => {
  logger.logAction('Workspace', 'page_enter')
  orderStore.fetchOrders()
  updateMobileWorkspaceState()
  window.addEventListener('resize', updateMobileWorkspaceState)

  const typingSpeed = 120
  const deletingSpeed = 60
  const pauseDuration = 10000 // 10 seconds

  currentPromptIndex.value = Math.floor(Math.random() * promptTexts.length)

  const startBlinking = (baseText: string) => {
    if (blinkTimer) clearInterval(blinkTimer)
    blinkTimer = setInterval(() => {
      placeholderText.value = placeholderText.value.endsWith('|') 
        ? baseText 
        : baseText + '|'
    }, 500)
  }

  const stopBlinking = () => {
    if (blinkTimer) {
      clearInterval(blinkTimer)
      blinkTimer = null
    }
  }

  const typeWriter = (text: string, index: number, isDeleting: boolean) => {
    stopBlinking()
    
    if (!isDeleting && index <= text.length) {
      placeholderText.value = text.substring(0, index) + '|'
      timer = setTimeout(() => typeWriter(text, index + 1, false), typingSpeed)
    } else if (isDeleting && index >= 0) {
      placeholderText.value = text.substring(0, index) + '|'
      timer = setTimeout(() => typeWriter(text, index - 1, true), deletingSpeed)
    } else if (!isDeleting && index > text.length) {
      placeholderText.value = text + '|'
      startBlinking(text)
      timer = setTimeout(() => typeWriter(text, text.length, true), pauseDuration)
    } else if (isDeleting && index < 0) {
      timer = setTimeout(() => {
        let nextIndex = Math.floor(Math.random() * promptTexts.length)
        if (nextIndex === currentPromptIndex.value && promptTexts.length > 1) {
          nextIndex = (nextIndex + 1) % promptTexts.length
        }
        currentPromptIndex.value = nextIndex
        typeWriter(promptTexts[currentPromptIndex.value], 0, false)
      }, 500)
    }
  }
  
  timer = setTimeout(() => typeWriter(promptTexts[currentPromptIndex.value], 0, false), 500)
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
  if (blinkTimer) clearInterval(blinkTimer)
  window.removeEventListener('resize', updateMobileWorkspaceState)
})

const handleAiExpand = (expanded: boolean) => {
  if (!expanded) {
    uiStore.setIsAiExpanded(false)
    aiSelectedMode.value = null
    uiStore.setSecondarySidebar(false)
    uiStore.toggleSidebar(false)
    return
  }
  // Instant expand without waiting for crazy delays
  uiStore.setIsAiExpanded(true)
  if (isMobileWorkspace.value) {
    uiStore.setSecondarySidebar(false)
    uiStore.toggleSidebar(false)
    showInspiration.value = false
  } else {
    uiStore.setSecondarySidebar(true)
    uiStore.toggleSidebar(true)
    showInspiration.value = true
  }
  logger.logAction('Workspace', 'open_ai_assistant')
}

const handleModeChange = (mode: string) => {
  aiSelectedMode.value = mode
  uiStore.setActiveModule(mode)
  logger.logAction('Workspace', 'switch_ai_mode', { mode })
}

const getServiceTargetPath = (targetType: ServiceType) => {
  return targetType === 'video_purchase'
    ? '/user/video-marketplace'
    : `/user/create-order/${targetType}`
}

const goToActiveService = async () => {
  const type = activeService.value?.type
  if (!type) return
  await triggerChoreography(type)
}

const triggerChoreography = async (targetType: ServiceType | null) => {
  if (targetType) {
    logger.logAction('Workspace', 'click_service_card', { targetType })
    uiStore.setIsAiExpanded(false)
    uiStore.setSecondarySidebar(true)
    uiStore.toggleSidebar(true)
    uiStore.setActiveModule(targetType)
    try {
      await router.push(getServiceTargetPath(targetType))
    } catch (error) {
      console.error('业务模块页面加载失败:', error)
      ElMessage.error('业务模块页面加载失败，请稍后重试')
    }
  } else {
    handleAiExpand(true)
  }
}

</script>

<style lang="scss" scoped>
.workspace-page {
  padding: 0; /* Remove card style */
  display: flex;
  flex-direction: column;
  height: 100%;
  box-sizing: border-box;
}

.overview-state {
  --overview-top-space: clamp(32px, 3.2vh, 48px);
  padding: var(--overview-top-space) 24px 24px 24px;
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.top-search-header {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: #fcf9f8;
  flex-shrink: 0;
}

.search-icon {
  margin-right: 12px;
  font-size: 18px;
  color: #a0a4ae;
}

.search-input {
  border: none;
  background: transparent;
  width: 100%;
  font-size: 16px;
  color: var(--uv-ws-page-text, #1b1b1c);
  outline: none;
  font-family: inherit;
}

.search-input::placeholder {
  color: var(--uv-ws-ai-agent-placeholder, #a0a4ae);
}

.workspace-layout {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 0; 
  /* No default transition on wrapper: guarantees instantly snap layout when Vue mounts real sidebars! */
  width: 100%;
  flex: 1; /* Take up all remaining height past the search bar */
  min-height: 0; /* Crucial: allows internal flex elements to scroll rather than bursting bounds */
  box-sizing: border-box;
}


.main-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%; /* Ensure column fully stretches down */
  position: relative; /* Anchor for absolute dropping items */
  width: 100%;
  box-sizing: border-box;
}

.main-column.is-squished {
  /* Dynamically squeezing content */
  padding-right: 0;
}

/* is-pushed-by-flight removed: real sidebar handles compression now */

.full-ai-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: transparent; /* No more card background */
  border-radius: 0;
  border: none; /* Strip card border */
  overflow: hidden;
}

.full-ai-container.is-dropping-in {
  /* Suspended above the dying layout to stretch downwards magically */
  position: absolute;
  top: 0;
  left: 0;
  right: 0; 
  height: 100%; 
  z-index: 10;
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 -24px; /* Pierce through the parent's padding */
  padding: 16px 24px; /* Push text back into safe alignment */
  border-bottom: 1px solid rgba(0, 0, 0, 0.06); /* Soft subtle header line */
}

.ai-header .ai-hero-title {
  margin: 0;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-feature-settings: "kern" 1;
  font-size: 26px;
  font-weight: 500;
  color: var(--uv-ws-page-text, #000000);
  letter-spacing: -0.26px;
}

.ai-header .collapse-btn {
  font-weight: 600;
}

/* Hero Banner */
.hero-banner {
  position: relative;
  isolation: isolate;
  background: var(--uv-ws-ai-agent-bg, #E9D5BD);
  border-radius: 16px;
  padding: 32px 40px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  transition: all 0.6s cubic-bezier(0.25, 1, 0.3, 1);
  overflow: hidden;
  box-sizing: border-box;
  flex-shrink: 0;
  min-height: 182px;
}

.hero-banner.is-fading-out {
  opacity: 0;
  transform: translateY(-20px);
}

.hero-bg-stack {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
  background: var(--uv-ws-ai-agent-bg, #E9D5BD);
}

.hero-bg-image {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  transform: scale(1.025);
  filter: saturate(1.06) contrast(1.03);
}

.hero-bg-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(8, 8, 10, 0.55) 0%, rgba(8, 8, 10, 0.28) 48%, rgba(8, 8, 10, 0.52) 100%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(0, 0, 0, 0.18) 100%);
}

.hero-bg-fade-enter-active,
.hero-bg-fade-leave-active {
  transition: opacity 0.75s ease, transform 0.95s cubic-bezier(0.22, 1, 0.36, 1);
}

.hero-bg-fade-enter-from,
.hero-bg-fade-leave-to {
  opacity: 0;
  transform: scale(1.05);
}

.hero-content {
  position: relative;
  z-index: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.hero-title {
  font-size: 24px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.96);
  margin: 0 0 24px 0;
  letter-spacing: -0.01em;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.34);
}

.hero-input-area {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 9999px;
  display: flex;
  align-items: center;
  padding: 4px 4px 4px 16px;
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.46);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.hero-input-area:hover {
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.24);
}

.hero-input {
  border: none;
  background: transparent;
  flex: 1;
  font-size: 15px;
  color: var(--uv-ws-ai-agent-input-text, #1b1b1c);
  outline: none;
  font-family: inherit;
  cursor: pointer;
}

.hero-input::placeholder {
  color: var(--uv-ws-ai-agent-placeholder, #a0a4ae);
}

.generate-btn {
  background: var(--uv-ws-send-button-bg, #666666);
  color: var(--uv-ws-send-button-text, #fff);
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 9999px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: transform 0.15s ease, background 0.2s ease;
}

.generate-btn:hover {
  background: var(--uv-ws-send-button-hover, #555555);
  transform: scale(0.98);
}

.sparkle {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--uv-ws-send-dot, #000000);
  display: inline-block;
  flex-shrink: 0;
}

.service-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 288px), 288px));
  gap: 20px;
  justify-content: start;
  margin-bottom: 24px;
}

.service-card {
  cursor: pointer;
  background: transparent;
  border: none;
  display: flex;
  flex-direction: column;
  box-shadow: none;
  gap: 12px;
  width: 288px;
  max-width: 100%;
}

.card-image-wrapper {
  height: 160px;
  width: 100%;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--uv-ws-service-image-border, rgba(0, 0, 0, 0.08));
  transition: border-color 0.2s ease;
}

.service-card:hover .card-image-wrapper {
  border-color: var(--uv-ws-service-image-hover-border, rgba(0, 0, 0, 0.25));
}

.card-img {
  width: 100%;
  height: 100%;
}

.card-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overlay-badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  right: 8px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--uv-ws-service-badge-text, #fff);
  background: var(--uv-ws-service-badge-bg, #000000);
  width: fit-content;
  max-width: calc(100% - 16px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-body {
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.service-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--uv-ws-service-title, #1b1b1c);
  margin: 0 0 6px 0;
}

.service-features {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  flex: 1;
  align-content: flex-start;
}

.outline-tag {
  border: 1px solid var(--uv-ws-service-tag-border, #c1c6d6);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  color: var(--uv-ws-service-tag-text, #414754);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
}

.price-text {
  font-weight: 500;
  font-size: 13px;
  color: var(--uv-ws-service-footer, #A0522D);
}

.arrow-right {
  color: var(--uv-ws-service-arrow, #414754);
  font-size: 18px;
}

.service-focus-state {
  height: 100%;
  padding: 32px 40px;
  box-sizing: border-box;
  overflow-y: auto;
}

.service-focus-panel {
  display: grid;
  grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
  gap: 32px;
  align-items: start;
  max-width: 1080px;
}

.service-focus-media {
  position: relative;
  aspect-ratio: 4 / 3;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.service-focus-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.service-focus-badge {
  position: absolute;
  left: 12px;
  bottom: 12px;
  max-width: calc(100% - 24px);
  padding: 4px 10px;
  border-radius: 4px;
  background: #000;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.service-focus-copy {
  min-width: 0;
  padding-top: 4px;
}

.section-label {
  font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
  font-size: 11px;
  font-weight: 500;
  color: #747474;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}

.service-focus-title {
  margin: 0 0 8px;
  color: var(--uv-ws-service-title, #1b1b1c);
  font-size: 28px;
  font-weight: 500;
  line-height: 1.2;
}

.service-focus-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 28px;
}

.service-focus-features span {
  border: 1px solid var(--uv-ws-service-tag-border, #c1c6d6);
  border-radius: 4px;
  padding: 5px 9px;
  font-size: 12px;
  color: var(--uv-ws-service-tag-text, #414754);
  background: rgba(255, 255, 255, 0.56);
}

.service-focus-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.action-icon {
  margin-left: 4px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.service-button {
  width: 100%;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 12px; /* Extreme compression */
}

.section-titles {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-size: 18px;
  font-weight: 500;
  color: var(--uv-ws-business-title, #1b1b1c);
  margin: 0;
  letter-spacing: -0.01em;
}

.section-subtitle {
  margin: 0;
  font-size: 12px;
  color: var(--uv-ws-business-subtitle, #646a78);
  transition: opacity 0.4s ease;
}

@media (max-width: 900px) {
  .service-focus-state {
    padding: 24px;
  }

  .service-focus-panel {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .service-focus-title {
    font-size: 24px;
  }
}

@media (max-width: 768px) {
  .workspace-page {
    height: 100vh;
    height: 100svh;
    min-height: 100vh;
    min-height: 100svh;
    overflow: hidden;
  }

  .workspace-layout {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .main-column {
    height: 100%;
    min-height: 0;
    width: 100%;
  }

  .overview-state {
    --overview-top-space: 16px;
    height: 100%;
    min-height: 0;
    padding: 16px 14px calc(18px + env(safe-area-inset-bottom));
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .hero-banner {
    padding: 24px 16px;
    margin-bottom: 18px;
    border-radius: 14px;
    min-height: 188px;
  }

  .hero-title {
    margin-bottom: 16px;
    font-size: 20px;
    line-height: 1.25;
    letter-spacing: 0;
  }

  .hero-input-area {
    min-height: 48px;
    padding: 5px 5px 5px 14px;
    border-radius: 18px;
  }

  .hero-input {
    min-width: 0;
    font-size: 16px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .generate-btn {
    flex-shrink: 0;
    padding: 8px 12px;
    font-size: 12px;
  }

  .figma-divider {
    margin: 18px 0 20px;
  }

  .section-header {
    margin-bottom: 14px;
  }

  .section-title {
    font-size: 17px;
  }

  .service-cards {
    grid-template-columns: 1fr;
    gap: 18px;
    margin-bottom: 0;
  }

  .service-card {
    width: 100%;
    gap: 10px;
  }

  .card-image-wrapper {
    height: clamp(148px, 42vw, 190px);
    border-radius: 10px;
  }

  .service-title {
    font-size: 16px;
    line-height: 1.35;
  }

  .service-features {
    gap: 6px;
  }

  .outline-tag {
    font-size: 10px;
    line-height: 1.2;
  }

  .full-ai-container {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .service-focus-state {
    height: 100%;
    padding: 18px 14px calc(20px + env(safe-area-inset-bottom));
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .service-focus-panel {
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .service-focus-title {
    font-size: 22px;
  }

  .service-focus-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .service-focus-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }

  :deep(.style-inspiration-sidebar) {
    display: none !important;
  }
}

.figma-divider {
  width: 100%;
  height: 1px;
  background-color: var(--uv-ws-divider, #e5e5e5);
  margin: 24px 0 32px 0;
}

/* ─── Responsive: 3-tier breakpoint system ─────────────────── */

/* Tier 2: FHD / QHD / high-res monitors (1920px+) */
@media screen and (min-width: 1920px) {
  .overview-state {
    padding: var(--overview-top-space) 32px 24px 32px;
  }
}

/* Tier 3: 4K at 150% scale = 2560px CSS pixels */
@media screen and (min-width: 2560px) {
  .overview-state {
    padding: var(--overview-top-space) 48px 32px 48px;
  }
}
</style>
