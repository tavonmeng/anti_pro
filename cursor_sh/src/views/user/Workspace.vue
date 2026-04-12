<template>
  <div class="workspace-page">
    
    <div class="workspace-layout" :class="{ 'is-split': uiStore.isAiExpanded }">
      <div class="main-column" :class="{ 'is-squished': uiStore.isAiExpanded }">

        <!-- Professional B2B Fast Cross-Fade -->
        <transition name="fade" mode="out-in">
          <!-- Overview Mode -->
          <div v-if="!uiStore.isAiExpanded && !uiStore.isSecondarySidebarVisible" class="overview-state">
            
            <!-- Top Search Header (Now inside overview only) -->
            <div class="top-search-header">
              <el-icon class="search-icon"><Search /></el-icon>
              <input type="text" placeholder="Search projects or assets..." class="search-input" />
            </div>
            <!-- Hero Banner (AI 智能体) -->
            <div class="hero-banner">
              <h1 class="hero-title">AI智能体帮你理清思路</h1>
              <div class="hero-input-area" @click="handleAiExpand(true)">
                <input type="text" :placeholder="placeholderText" class="hero-input" readonly />
                <div class="generate-btn">
                  发送 <span class="sparkle">✨</span>
                </div>
              </div>
            </div>
            
            <div class="figma-divider"></div>

            <!-- 业务服务概览 -->
            <div class="business-services-section">
          <div class="section-header">
            <div class="section-titles">
              <h2 class="section-title">业务菜单</h2>
              <p class="section-subtitle">高质量3D视频内容交付，让每一个户外屏都有优质的内容</p>
            </div>
          </div>
          
          <!-- 服务入口卡片 -->
          <div class="service-cards">
            <!-- Card 1 -->
            <div class="service-card" @click="triggerChoreography('video_purchase')">
              <div class="card-image-wrapper">
                <div class="card-img" style="background: linear-gradient(to bottom, #111, #333);">
                  <!-- Placeholder Character -->
                </div>
                <div class="overlay-badge premium" style="background: #0070eb; color: #fff;">PREMIUM 3D</div>
              </div>
              <div class="card-body">
                <h3 class="service-title">裸眼3D成片购买</h3>
                <p class="service-description">
                  专业的裸眼3D视频内容库，根据您的屏幕参数精准适配，快速交付高质量成片。支持多种行业应用和视觉风格选择。
                </p>
                <div class="service-features">
                  <span class="outline-tag">快速交付</span>
                  <span class="outline-tag">专业适配</span>
                  <span class="outline-tag">多种风格</span>
                </div>
                <div class="card-footer">
                  <span class="price-text">From $2,499</span>
                  <el-icon class="arrow-right"><Right /></el-icon>
                </div>
              </div>
            </div>

            <!-- Card 2 -->
            <div class="service-card" @click="triggerChoreography('ai_3d_custom')">
              <div class="card-image-wrapper">
                <div class="card-img" style="background: linear-gradient(to bottom, #001f3f, #004080);">
                   <!-- Placeholder Typography -->
                </div>
                <div class="overlay-badge creative" style="background: #0070eb; color: #fff;">AI CREATIVE</div>
              </div>
              <div class="card-body">
                <h3 class="service-title">AI裸眼3D内容定制</h3>
                <p class="service-description">
                  基于AI技术的定制化3D内容创作，从创意构思到成品落地的全流程服务。上传现场照片，描述您的想法，我们将AI技术转化为震撼的裸眼3D效果。
                </p>
                <div class="card-footer">
                  <span class="price-text">Custom Quote</span>
                  <el-icon class="arrow-right"><Right /></el-icon>
                </div>
              </div>
            </div>

            <!-- Card 3 -->
            <div class="service-card" @click="triggerChoreography('digital_art')">
              <div class="card-image-wrapper">
                <div class="card-img" style="background: linear-gradient(to bottom, #4a0000, #ff1a1a);">
                   <!-- Placeholder Abstract -->
                </div>
                <div class="overlay-badge art" style="background: #0070eb; color: #fff;">DIGITAL ART</div>
              </div>
              <div class="card-body">
                <h3 class="service-title">数字艺术内容定制</h3>
                <p class="service-description">
                  专业数字艺术创作服务，涵盖抽象、写实、装置、动态艺术等多种风格。由资深艺术家团队倾力打造，3天内提供初稿预览。
                </p>
                <div class="card-footer">
                  <span class="price-text">From $1,200</span>
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
        </transition>

      </div> <!-- end main-column -->
      
      <transition name="fade">
        <StyleInspirationSidebar v-if="uiStore.isAiExpanded && showInspiration" @close="showInspiration = false" />
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Right } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { useUiStore } from '@/stores/ui'
import type { OrderType } from '@/types'
import AIChatAssistant from '@/components/AIChatAssistant.vue'
import StyleInspirationSidebar from '@/components/StyleInspirationSidebar.vue'

const router = useRouter()
const orderStore = useOrderStore()
const uiStore = useUiStore()

const aiSelectedMode = ref<string | null>(null)
const showInspiration = ref(true)

const promptTexts = [
  "我想做一个关于蒙牛品牌推广的3D视频，主题是...",
  "帮我设计一段赛博朋克风格的裸眼3D球鞋广告，要有超强的出屏效果...",
  "我需要一个高端科技论坛的开场3D倒计时动画，充满未来科技感...",
  "帮我生成一段大牌护肤品的新品发布3D视频，要求水珠材质特别逼真...",
  "给我们的新款新能源汽车做个3D动态视频，让车穿梭在未来都市..."
]

const placeholderText = ref("|")
let timer: ReturnType<typeof setTimeout> | null = null
let blinkTimer: ReturnType<typeof setInterval> | null = null
let currentPromptIndex = 0

onMounted(() => {
  orderStore.fetchOrders()

  const typingSpeed = 120
  const deletingSpeed = 60
  const pauseDuration = 10000 // 10 seconds

  currentPromptIndex = Math.floor(Math.random() * promptTexts.length)

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
        if (nextIndex === currentPromptIndex && promptTexts.length > 1) {
          nextIndex = (nextIndex + 1) % promptTexts.length
        }
        currentPromptIndex = nextIndex
        typeWriter(promptTexts[currentPromptIndex], 0, false)
      }, 500)
    }
  }
  
  timer = setTimeout(() => typeWriter(promptTexts[currentPromptIndex], 0, false), 500)
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
  if (blinkTimer) clearInterval(blinkTimer)
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
  uiStore.setSecondarySidebar(true)
  uiStore.toggleSidebar(true)
  showInspiration.value = true
}

const handleModeChange = (mode: string) => {
  aiSelectedMode.value = mode
  uiStore.setActiveModule(mode)
}

const triggerChoreography = (targetType: OrderType | string | null) => {
  // B2B direct routing layout shift: instantly navigate and apply system states
  if (targetType) {
    if (targetType === 'video_purchase') {
      router.push('/user/video-marketplace')
    } else {
      router.push(`/user/create-order/${targetType}`)
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
  padding: 0 24px 24px 24px;
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
  color: #1b1b1c;
  outline: none;
  font-family: inherit;
}

.search-input::placeholder {
  color: #a0a4ae;
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
  color: #000000;
  letter-spacing: -0.26px;
}

.ai-header .collapse-btn {
  font-weight: 600;
}

/* Hero Banner */
.hero-banner {
  background: #f0f5fc;
  border-radius: 16px;
  padding: 32px 40px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  transition: all 0.6s cubic-bezier(0.25, 1, 0.3, 1);
  overflow: visible;
  box-sizing: border-box;
  flex-shrink: 0;
}

.hero-banner.is-fading-out {
  opacity: 0;
  transform: translateY(-20px);
}

.hero-title {
  font-size: 24px;
  font-weight: 500;
  color: #1b1b1c;
  margin: 0 0 24px 0;
  letter-spacing: -0.01em;
}

.hero-input-area {
  background: #ffffff;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  padding: 4px 4px 4px 16px;
  width: 100%;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.hero-input-area:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.hero-input {
  border: none;
  background: transparent;
  flex: 1;
  font-size: 15px;
  color: #1b1b1c;
  outline: none;
  font-family: inherit;
  cursor: pointer;
}

.hero-input::placeholder {
  color: #a0a4ae;
}

.generate-btn {
  background: #0d99ff; /* Matched to Figma primary blue (View orders color) */
  color: #fff;
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
  background: #0a8bed;
  transform: scale(0.98);
}

.service-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
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
}

.card-image-wrapper {
  height: 160px;
  width: 100%;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: border-color 0.2s ease;
}

.service-card:hover .card-image-wrapper {
  border-color: rgba(0, 0, 0, 0.25);
}

.card-img {
  width: 100%;
  height: 100%;
}

.overlay-badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #fff;
  background: #0070eb;
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
  color: #1b1b1c;
  margin: 0 0 6px 0;
}

.service-description {
  font-size: 12px;
  color: #646a78;
  line-height: 1.4;
  margin: 0 0 12px 0;
  flex: 1;
}

.service-features {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.outline-tag {
  border: 1px solid #c1c6d6;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  color: #414754;
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
  color: #0058bc;
}

.arrow-right {
  color: #414754;
  font-size: 18px;
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
  color: #1b1b1c;
  margin: 0;
  letter-spacing: -0.01em;
}

.section-subtitle {
  margin: 0;
  font-size: 12px;
  color: #646a78;
  transition: opacity 0.4s ease;
}

.figma-divider {
  width: 100%;
  height: 1px;
  background-color: #e5e5e5;
  margin: 24px 0 32px 0;
}

/* ─── Responsive: 3-tier breakpoint system ─────────────────── */

/* Tier 2: FHD / QHD / high-res monitors (1920px+) */
@media screen and (min-width: 1920px) {
  .overview-state {
    padding: 0 32px 24px 32px;
  }
  .card-image-wrapper {
    height: 180px;
  }
}

/* Tier 3: 4K at 150% scale = 2560px CSS pixels */
@media screen and (min-width: 2560px) {
  .overview-state {
    padding: 0 48px 32px 48px;
  }
  .card-image-wrapper {
    height: 200px;
  }
  .service-cards {
    gap: 24px;
  }
}
</style>
