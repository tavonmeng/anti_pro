<template>
  <div class="landing-scope">
    <PageLoader v-if="!loaderDestroyed" @complete="handleLoadComplete" />
    <MarketingTopBar
      @visibility-change="isMarketingBarVisible = $event"
      @active-change="isMarketingBarActive = $event"
    />
    <TheHeader
      :top-offset="headerTopOffset"
      @openLogin="openAuth('login')"
      @openRegister="openAuth('register')"
    />
    <CustomCursor />
    
    <div class="main-page">
      <main>
        <HeroSection :is-loaded="isLoaded" />
        <IntroSection />
        <BrandsSection />
        <ContactSection @open-login="openAuth('login')" />
      </main>
      
      <TheFooter />
    </div>

    <!-- 登录/注册弹窗 -->
    <AuthModal
      :visible="authModalVisible"
      :initial-tab="authModalTab"
      :invite-token="inviteToken"
      :invite-company-name="inviteCompanyName"
      @close="authModalVisible = false"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import TheHeader from './components/TheHeader.vue'
import MarketingTopBar from './components/MarketingTopBar.vue'
import AuthModal from './components/AuthModal.vue'
import CustomCursor from './components/CustomCursor.vue'
import PageLoader from './components/PageLoader.vue'

import HeroSection from './sections/HeroSection.vue'
import IntroSection from './sections/IntroSection.vue'
import BrandsSection from './sections/BrandsSection.vue'
import ContactSection from './sections/ContactSection.vue'
import TheFooter from './sections/TheFooter.vue'
import { authApi } from '@/utils/api'

// 状态
const isMarketingBarVisible = ref(true)
const isMarketingBarActive = ref(false)
const marketingBarHeight = 58
const headerTopOffset = computed(() => (
  isMarketingBarActive.value && isMarketingBarVisible.value
    ? marketingBarHeight
    : 0
))

// 登录/注册弹窗
const authModalVisible = ref(false)
const authModalTab = ref('login')
const inviteToken = ref('')
const inviteCompanyName = ref('')

const openAuth = (tab) => {
  if (tab === 'register' && !inviteToken.value) {
    ElMessage.info('当前仍在内测阶段，仅支持受邀用户注册。请联系管理员获取邀请链接。')
    return
  }
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

onMounted(() => {
  // 设置官网专属背景色
  document.body.classList.add('landing-active')
  handleInviteLink()
})

onUnmounted(() => {
  // 离开官网时恢复背景色
  document.body.classList.remove('landing-active')
})

const handleInviteLink = async () => {
  const params = new URLSearchParams(window.location.search)
  const token = (params.get('invite') || params.get('user_invite') || '').trim()
  if (!token) return

  try {
    const data = await authApi.validateInvite(token)
    if (data?.valid) {
      inviteToken.value = token
      inviteCompanyName.value = data.companyName || ''
      openAuth('register')
    } else {
      ElMessage.warning(data?.message || '邀请链接无效或已过期')
    }
  } catch (e) {
    const message = e?.response?.data?.message || e?.message || '邀请链接无效或已过期'
    ElMessage.warning(message)
  }
}
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
