<template>
  <div class="landing-scope">
    <PageLoader v-if="!loaderDestroyed" @complete="handleLoadComplete" />
    <TheHeader :force-light="isDetailOpen" :force-transparent="isShowcaseOpen && !isDetailOpen" @logoClick="handleGlobalLogoClick" @menuClick="handleGlobalMenuClick" @openLogin="openAuth('login')" @openRegister="openAuth('register')" />
    <CustomCursor />
    
    <div class="main-page" ref="mainPageRef">
      <main>
        <HeroSection :is-loaded="isLoaded" />
        <IntroSection />
        <BrandsSection />
        <CasesSection @open-showcase="handleCaseClick" />
        <ContactSection />
      </main>
      
      <TheFooter @open-experiment="isExperimentOpen = true" />
    </div>

    <CaseShowcasePage 
      v-if="isShowcaseOpen"
      :cases="cases"
      :initial-case-id="activeCaseShowcase?.id"
      @open-detail="handleOpenDetail"
      @close="handleCloseShowcase"
    />

    <CaseDetailPage 
      v-if="isDetailOpen" 
      :case-data="activeCaseDetail"
      @close="handleCloseDetail"
      @navigate-case="handleNavigateCase"
    />

    <Experiment3D 
      v-if="isExperimentOpen" 
      @close="isExperimentOpen = false" 
    />

    <!-- 登录/注册弹窗 -->
    <AuthModal :visible="authModalVisible" :initial-tab="authModalTab" @close="authModalVisible = false" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import TheHeader from './components/TheHeader.vue'
import AuthModal from './components/AuthModal.vue'
import CaseDetailPage from './components/CaseDetailPage.vue'
import CaseShowcasePage from './components/CaseShowcasePage.vue'
import CustomCursor from './components/CustomCursor.vue'
import PageLoader from './components/PageLoader.vue'
import Experiment3D from './components/Experiment3D.vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

import HeroSection from './sections/HeroSection.vue'
import IntroSection from './sections/IntroSection.vue'
import BrandsSection from './sections/BrandsSection.vue'
import CasesSection from './sections/CasesSection.vue'
import ContactSection from './sections/ContactSection.vue'
import TheFooter from './sections/TheFooter.vue'

import { cases } from './data/cases'

// 状态
const mainPageRef = ref(null)
const activeCaseShowcase = ref(null)
const isShowcaseOpen = ref(false)
const activeCaseDetail = ref(null)
const isDetailOpen = ref(false)
const isExperimentOpen = ref(false)

// 登录/注册弹窗
const authModalVisible = ref(false)
const authModalTab = ref('login')

const openAuth = (tab) => {
  authModalTab.value = tab
  authModalVisible.value = true
}

// 页面加载状态
const isLoaded = ref(false)
const loaderDestroyed = ref(false)

const handleLoadComplete = () => {
  isLoaded.value = true
  // 等动画安全完成并渐隐后再彻底销毁loader，给GSAP一些预留时间（0.5s fade out）
  setTimeout(() => loaderDestroyed.value = true, 800)
}

const handleGlobalLogoClick = () => {
  if (isDetailOpen.value) handleCloseDetail()
  if (isShowcaseOpen.value) handleCloseShowcase()
}

const handleGlobalMenuClick = (item) => {
  if (isDetailOpen.value) handleCloseDetail()
  if (isShowcaseOpen.value) handleCloseShowcase()
}

// 处理案例点击（打开陈列页）
const handleCaseClick = (caseData) => {
  // 记录当前滚动位置
  const currentScrollY = window.scrollY
  activeCaseShowcase.value = caseData
  isShowcaseOpen.value = true
  
  // 禁用ScrollTrigger以防止冲突
  ScrollTrigger.getAll().forEach(st => st.disable(false))
  
  // 页面切换动画：主页面左移
  gsap.to(mainPageRef.value, {
    x: '-30%',
    opacity: 0.5,
    duration: 0.8,
    ease: 'power3.out',
    onComplete: () => {
        // 关键：锁定主页面位置，防止背景滚动
        mainPageRef.value.style.position = 'fixed'
        mainPageRef.value.style.width = '100%'
        mainPageRef.value.style.top = `-${currentScrollY}px`
    }
  })
}

// 关闭陈列页
const handleCloseShowcase = () => {
  const scrollY = Math.abs(parseFloat(mainPageRef.value.style.top || '0'))
  
  mainPageRef.value.style.position = ''
  mainPageRef.value.style.width = ''
  mainPageRef.value.style.top = ''
  window.scrollTo(0, scrollY)

  gsap.to(mainPageRef.value, {
    x: '0%',
    opacity: 1,
    duration: 0.8,
    ease: 'power3.out',
    onComplete: () => {
      gsap.set(mainPageRef.value, { clearProps: 'transform,opacity' })
      ScrollTrigger.getAll().forEach(st => st.enable())
      ScrollTrigger.refresh()
    }
  })
  
  isShowcaseOpen.value = false
  activeCaseShowcase.value = null
}

// 打开详情页
const handleOpenDetail = (caseData) => {
  activeCaseDetail.value = caseData
  isDetailOpen.value = true
}

const handleNavigateCase = (nextCase) => {
  activeCaseDetail.value = nextCase
  // also update showcase background if navigating using NEXT link in details
  activeCaseShowcase.value = nextCase 
}

// 关闭详情页（返回陈列页）
const handleCloseDetail = () => {
  const detailPageEl = document.querySelector('.case-detail-page')
  if (detailPageEl) {
    gsap.to(detailPageEl, {
      x: '100%',
      duration: 0.6,
      ease: 'power3.in',
      onComplete: () => {
        isDetailOpen.value = false
        activeCaseDetail.value = null
      }
    })
  } else {
    isDetailOpen.value = false
    activeCaseDetail.value = null
  }
}

onMounted(() => {
  // 设置官网专属背景色
  document.body.classList.add('landing-active')
})

onUnmounted(() => {
  // 离开官网时恢复背景色
  document.body.classList.remove('landing-active')
})
</script>

<style>
/* 
 * 官网专属样式域 — 仅在 LandingPage 路由激活时生效
 * 使用 body.landing-active 控制全局背景色切换
 */
body.landing-active {
  background-color: #000000 !important;
  color: #FFFFFF;
}

.landing-scope {
  --color-bg-primary: #000000;
  --color-bg-secondary: #1A1A1A;
  --color-bg-tertiary: #2A2A2A;
  --color-text-primary: #FFFFFF;
  --color-text-secondary: rgba(255, 255, 255, 0.7);
  --color-text-tertiary: rgba(255, 255, 255, 0.5);
  --color-accent: #00D1FF;
  --color-glow: rgba(0, 209, 255, 0.4);
  --font-primary: 'Outfit', 'PingFang SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --spacing-xs: 8px;
  --spacing-sm: 16px;
  --spacing-md: 24px;
  --spacing-lg: 32px;
  --spacing-xl: 48px;
  --spacing-2xl: 64px;
  --spacing-3xl: 96px;
  --z-header: 1000;
  --z-menu: 2000;
  --z-progress: 3000;
  --z-glow: 50;

  position: relative;
  overflow-x: hidden;
  font-family: var(--font-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 全局平滑滚动 */
.landing-scope {
  scroll-behavior: smooth;
}

.landing-scope .main-page {
  position: relative;
}

/* 隐藏滚动条但保留滚动功能 (landing only) */
body.landing-active::-webkit-scrollbar {
  width: 6px;
}
body.landing-active::-webkit-scrollbar-track {
  background: #000000;
}
body.landing-active::-webkit-scrollbar-thumb {
  background: #1A1A1A;
  border-radius: 3px;
}
</style>
