<template>
  <div id="app-container">
    <PageLoader v-if="!loaderDestroyed" @complete="handleLoadComplete" />
    <TheHeader :force-light="!!activeCase" @logoClick="handleGlobalLogoClick" @menuClick="handleGlobalMenuClick" />
    <CustomCursor />
    
    <div class="main-page" ref="mainPageRef">
      <main>
        <HeroSection :is-loaded="isLoaded" />
        <IntroSection />
        <BrandsSection />
        <CasesSection @open-detail="handleCaseClick" />
        <ContactSection />
      </main>
      
      <TheFooter />
    </div>

    <CaseDetailPage 
      v-if="activeCase" 
      :case-data="activeCase"
      @close="handleCloseDetail"
      @navigate-case="handleNavigateCase"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import TheHeader from './components/TheHeader.vue'
import CaseDetailPage from './components/CaseDetailPage.vue'
import CustomCursor from './components/CustomCursor.vue'
import PageLoader from './components/PageLoader.vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

import HeroSection from './sections/HeroSection.vue'
import IntroSection from './sections/IntroSection.vue'
import BrandsSection from './sections/BrandsSection.vue'
import CasesSection from './sections/CasesSection.vue'
import ContactSection from './sections/ContactSection.vue'
import TheFooter from './sections/TheFooter.vue'

// 状态
const activeCase = ref(null)
const mainPageRef = ref(null)

// 页面加载状态
const isLoaded = ref(false)
const loaderDestroyed = ref(false)

const handleLoadComplete = () => {
  isLoaded.value = true
  // 等动画安全完成并渐隐后再彻底销毁loader，给GSAP一些预留时间（0.5s fade out）
  setTimeout(() => loaderDestroyed.value = true, 800)
}

const handleGlobalLogoClick = () => {
  if (activeCase.value) handleCloseDetail()
}

const handleGlobalMenuClick = (item) => {
  if (activeCase.value) handleCloseDetail()
}

// 处理案例点击
const handleCaseClick = (caseData) => {
  // 记录当前滚动位置
  const currentScrollY = window.scrollY
  activeCase.value = caseData
  
  // 禁用ScrollTrigger以防止冲突
  ScrollTrigger.getAll().forEach(st => st.disable(false)) // false: 不重置位置
  
  // 页面切换动画：主页面左移，详情页保持右侧进入动画(由组件内部控制)
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

const handleNavigateCase = (nextCase) => {
  activeCase.value = nextCase
}

// 处理关闭详情页
const handleCloseDetail = () => {
    // 恢复之前的滚动位置
    const scrollY = Math.abs(parseFloat(mainPageRef.value.style.top || '0'))
    
    // 解除锁定
    mainPageRef.value.style.position = ''
    mainPageRef.value.style.width = ''
    mainPageRef.value.style.top = ''
    window.scrollTo(0, scrollY)

  // 主页面恢复
  gsap.to(mainPageRef.value, {
    x: '0%',
    opacity: 1,
    duration: 0.8,
    ease: 'power3.out',
    onComplete: () => {
      // 动画完成后清除 transform 和 opacity，以恢复正常的层叠上下文 (stacking context)
      // 这对于 position: fixed 的元素（如 ScrollTrigger pinning）至关重要
      gsap.set(mainPageRef.value, { clearProps: 'transform,opacity' })
      
      // 恢复ScrollTrigger
      ScrollTrigger.getAll().forEach(st => st.enable())
      ScrollTrigger.refresh()
    }
  })
  
  // 详情页退出动画
  const detailPageEl = document.querySelector('.case-detail-page')
  if (detailPageEl) {
    gsap.to(detailPageEl, {
      x: '100%',
      duration: 0.6,
      ease: 'power3.in',
      onComplete: () => {
        activeCase.value = null
      }
    })
  } else {
    activeCase.value = null
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
