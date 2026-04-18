<template>
  <div id="app-container">
    <PageLoader v-if="!loaderDestroyed" @complete="handleLoadComplete" />
    <TheHeader :force-light="isDetailOpen" :force-transparent="isShowcaseOpen && !isDetailOpen" @logoClick="handleGlobalLogoClick" @menuClick="handleGlobalMenuClick" />
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

    <AuthModal
      :is-open="uiState.authModalOpen"
      :mode="uiState.authMode"
      @close="closeAuthModal"
    />

    <Experiment3D 
      v-if="isExperimentOpen" 
      @close="isExperimentOpen = false" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import TheHeader from './components/TheHeader.vue'
import CaseDetailPage from './components/CaseDetailPage.vue'
import CaseShowcasePage from './components/CaseShowcasePage.vue'
import CustomCursor from './components/CustomCursor.vue'
import PageLoader from './components/PageLoader.vue'
import AuthModal from './components/AuthModal.vue'
import Experiment3D from './components/Experiment3D.vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

import { uiState, closeAuthModal } from './stores/ui'

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
  // mount logic if needed
})

onUnmounted(() => {
  // cleanup if needed
})
</script>

<style>
/* 全局平滑滚动 */
html {
  scroll-behavior: smooth;
}

#app-container {
  position: relative;
  overflow-x: hidden;
}

.main-page {
  position: relative;
  /* Removed will-change and transform-style to avoid stacking context issues with fixed elements */
}
</style>
