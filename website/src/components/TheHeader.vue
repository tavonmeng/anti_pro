<template>
  <header
    class="header-bar"
    :class="{ 'is-light': isLightMode }"
    @mouseenter="onHeaderEnter"
    @mouseleave="onHeaderLeave"
  >
    <!-- 左：Logo 区域 -->
    <div class="header-logo" @click="scrollToTop">
      <span class="logo-icon">🛡️</span>
      <span class="logo-text">Unique Vision</span>
    </div>

    <!-- 中间竖线 -->
    <div class="divider"></div>

    <!-- 中/右：菜单内容区 -->
    <div class="header-menu">
      <!-- 用一个容器实现平滑宽度伸展，并在右侧容纳菜单文本或标签 -->
      <div class="menu-text-wrapper" :class="{ 'is-expanded': isExpanded, 'has-label': !isExpanded && activeSectionLabel }">
        <!-- 展开状态：一排菜单文字 -->
        <transition name="fade-slide">
          <nav v-show="isExpanded" class="menu-nav">
            <!-- 业务介绍左侧的分割线 -->
            <div class="divider nav-inner-divider"></div>
            <a
              v-for="item in menuItems"
              :key="item.id"
              href="#"
              class="menu-link"
              :class="{
                'is-dim': hoveredItem && hoveredItem !== item.id
              }"
              @mouseenter="hoveredItem = item.id"
              @mouseleave="hoveredItem = null"
              @click.prevent="handleClick(item)"
            >{{ item.label }}</a>
          </nav>
        </transition>

        <!-- 收起状态：当前 section 名称 -->
        <transition name="fade-slide">
          <span
            v-show="!isExpanded && activeSectionLabel"
            class="current-section-label"
          >{{ activeSectionLabel }}</span>
        </transition>
      </div>

      <!-- 菜单图标 -->
      <div class="divider menu-divider"></div>
      <button
        class="menu-icon-btn"
        :class="{ rotated: isExpanded }"
        aria-label="菜单"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <rect x="3" y="5" width="14" height="1.6" rx="0.8" fill="currentColor"/>
          <rect x="3" y="9.2" width="14" height="1.6" rx="0.8" fill="currentColor"/>
          <rect x="3" y="13.4" width="14" height="1.6" rx="0.8" fill="currentColor"/>
        </svg>
      </button>

      <!-- Auth Buttons -->
      <div class="divider auth-divider"></div>
      <div class="auth-buttons">
        <button class="auth-btn btn-login" @click.prevent="openAuthModal('login')">登录</button>
        <button class="auth-btn btn-register" @click.prevent="openAuthModal('register')">注册</button>
      </div>
    </div>

    <!-- 底部白线（进度条） -->
    <div class="bottom-line">
      <div class="progress-fill" :style="{ width: scrollProgress + '%' }"></div>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { openAuthModal } from '../stores/ui.js'

const props = defineProps({
  forceLight: {
    type: Boolean,
    default: false
  },
  forceTransparent: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['logoClick', 'menuClick'])

// ─── 菜单项 ──────────────────────────────────────────────────
const menuItems = [
  { id: 'intro',    label: '业务介绍' },
  { id: 'cases',    label: '著作案例' },
  { id: 'contact',  label: '联系我们' },
]

// ─── 状态 ────────────────────────────────────────────────────
const isExpanded = ref(false)
const hoveredItem = ref(null)
const activeSectionLabel = ref('')
const scrollProgress = ref(0)
const isLightModeInternal = ref(false)

const isLightMode = computed(() => {
  if (props.forceTransparent) return false
  return props.forceLight || isLightModeInternal.value
})

// ─── hover 展开/收起 ─────────────────────────────────────────
let collapseTimer = null

const onHeaderEnter = () => {
  clearTimeout(collapseTimer)
  isExpanded.value = true
}

const onHeaderLeave = () => {
  collapseTimer = setTimeout(() => {
    isExpanded.value = false
    hoveredItem.value = null
  }, 200)
}

// ─── 点击 logo 回首页 ────────────────────────────────────────
const scrollToTop = () => {
  emit('logoClick')
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ─── 点击菜单项 ──────────────────────────────────────────────
const handleClick = (item) => {
  emit('menuClick', item)
  const el = document.getElementById(item.id)
  if (el) {
    const headerOffset = 68;
    const elementPosition = el.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.scrollY - headerOffset;
    
    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    })
  }
  isExpanded.value = false
  hoveredItem.value = null
  activeSectionLabel.value = item.label
}

// ─── 滚动检测 ────────────────────────────────────────────────
let sectionEls = []

const onScroll = (e) => {
  let scrollY = window.scrollY
  let docHeight = document.documentElement.scrollHeight - window.innerHeight
  const target = e?.target

  if (target && target.classList && target.classList.contains('case-detail-page')) {
    scrollY = target.scrollTop
    docHeight = target.scrollHeight - target.clientHeight
  }

  // 进度条
  if (docHeight > 0) {
    scrollProgress.value = (scrollY / docHeight) * 100
  }

  // Section 检测
  if (scrollY < 100) {
    activeSectionLabel.value = ''
    isLightModeInternal.value = false
    return
  }

  // Check light mode threshold (cases section) - Disabled per user request
  // const casesEl = document.getElementById('cases')
  // if (casesEl) {
  //   const rect = casesEl.getBoundingClientRect()
  //   // 菜单栏高68px，当cases容器到达或越过菜单栏下沿时切换反色
  //   if (rect.top <= 68) {
  //     isLightModeInternal.value = true
  //   } else {
  //     isLightModeInternal.value = false
  //   }
  // }

  const winH = window.innerHeight
  let best = null
  let bestScore = -Infinity

  sectionEls.forEach(({ label, el }) => {
    if (!el) return
    const rect = el.getBoundingClientRect()
    const top = Math.max(rect.top, 0)
    const bottom = Math.min(rect.bottom, winH)
    const visible = bottom - top
    if (visible > bestScore) {
      bestScore = visible
      best = label
    }
  })

  if (best && bestScore > 0) {
    activeSectionLabel.value = best
  }
}

onMounted(() => {
  sectionEls = menuItems.map(item => ({
    ...item,
    el: document.getElementById(item.id)
  }))
  window.addEventListener('scroll', onScroll, true)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll, true)
  clearTimeout(collapseTimer)
})
</script>

<style scoped>
/* ─── 全宽通栏（无边框，只有底线） ──────────────────────────── */
.header-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 68px; /* Increased by ~30% from 52px */
  display: flex;
  align-items: center;
  z-index: 5001;
  background: transparent;
  /* 无上左右边框 */
  border: none;
}

/* ─── Logo ─────────────────────────────────────────────────── */
.header-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex-shrink: 0;
  padding: 0 24px; /* 稍微收紧 logo 的横向间距 */
  height: 100%;
  z-index: 10;
}

.logo-icon {
  font-size: 20px;
  line-height: 1;
}

.logo-text {
  font-family: var(--font-primary);
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
}

/* ─── 竖线分割 ──────────────────────────── */
.divider {
  width: 2px;
  height: 40px; /* Lengthened but not touching 68px header edges */
  background: rgba(255, 255, 255, 0.35);
  flex-shrink: 0;
}

/* 靠近菜单按钮的分割线 */
.menu-divider {
  margin-left: 12px;
}

/* 导航内的分割线 */
.nav-inner-divider {
  margin-right: 12px;
}

/* ─── 菜单区域 ─────────────────────────────────────────────── */
.header-menu {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 32px 0 0; /* 右侧对齐 logo 的左边距 */
  height: 100%;
  position: relative;
}



/* ─── 文字占位容器（通过 width 实现平滑扩展） ───────────── */
.menu-text-wrapper {
  display: flex;
  align-items: center;
  position: relative;
  width: 0px; 
  height: 100%;
  transition: width 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 展开时：容纳 3 个导航文本，给予每个项约 100px-110px 空间 */
.menu-text-wrapper.is-expanded {
  width: 320px; 
}

/* 收起但有滚动标签时：足够容纳 "商业综合体视觉" 等较长标签 */
.menu-text-wrapper.has-label {
  width: 140px; 
}

/* 导航链接 / 收起标签：相对包裹容器右对齐绝对定位，实现优雅的 cross-fade 且不闪烁宽度 */
.menu-nav, .current-section-label {
  position: absolute;
  right: 0;
  white-space: nowrap;
}

/* ─── 展开导航（纯文字） ────────────────────────────────────── */
.menu-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.menu-link {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 1);
  text-decoration: none;
  padding: 6px 14px;
  letter-spacing: 0.04em;
  white-space: nowrap;
  transition: opacity 0.25s ease;
  background: none;
}

.menu-link.is-dim {
  opacity: 0.5;
}

.menu-link:hover {
  opacity: 1;
}

/* ─── 收起时 section 名称 ──────────────────────────────────── */
.current-section-label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.05em;
  /* 为了微调居中感，可以稍微给点右边距 */
  padding-right: 6px; 
}

/* ─── nav 和 label 同时切换的动画 ─────────────────────────── */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* ─── 菜单图标 ─────────────────────────────────────────────── */
.menu-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  min-width: 36px;
  border: 1.6px solid currentColor;
  border-radius: 50%;
  background: transparent;
  color: #fff;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s ease;
  margin-left: 16px;
}

.menu-icon-btn:hover {
  opacity: 0.8;
}

.menu-icon-btn.rotated {
  transform: rotate(90deg);
}

/* ─── 登录/注册 按钮 ────────────────────────────────────────────── */
.auth-divider {
  margin-left: 16px;
  margin-right: 16px;
}

.auth-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-btn {
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  height: 36px;
  border-radius: 50px; /* Pill */
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-login {
  background: transparent;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 0 16px;
}

.btn-login:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.5);
}

.btn-register {
  background: #fff;
  color: #000;
  border: none;
  padding: 0 20px;
  font-weight: 600;
}

.btn-register:hover {
  opacity: 0.85;
}

/* ─── 底部白线 + 进度条 ────────────────────────────────────── */
.bottom-line {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: rgba(255, 255, 255, 0.3);
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 0%;
  background: rgba(255, 255, 255, 0.85);
  transition: width 0.08s linear, background 0.3s ease;
  box-shadow: 0 0 6px rgba(255, 255, 255, 0.3);
}

/* ─── Light Mode Theme (Triggered below Cases) ─────────────── */
.header-bar.is-light {
  background: #fff;
  border-bottom: 2px solid rgba(0, 0, 0, 0.12); /* Thicker border */
  transition: background 0.3s ease, border-color 0.3s ease;
}

.header-bar.is-light .logo-text,
.header-bar.is-light .current-section-label,
.header-bar.is-light .menu-link {
  color: #000;
}

.header-bar.is-light .menu-icon-btn {
  color: #000;
}

.header-bar.is-light .divider {
  background: rgba(0, 0, 0, 0.15);
}

.header-bar.is-light .bottom-line {
  background: transparent;
}

.header-bar.is-light .progress-fill {
  background: #000;
  box-shadow: none;
}

.header-bar.is-light .btn-login {
  color: #000;
  border-color: rgba(0, 0, 0, 0.2);
}

.header-bar.is-light .btn-login:hover {
  background: rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.4);
}

.header-bar.is-light .btn-register {
  background: #000; /* Black Pill Button in Light Mode */
  color: #fff;
}

.header-bar.is-light .btn-register:hover {
  opacity: 0.85;
}


/* ─── 响应式 ───────────────────────────────────────────────── */
@media (max-width: 768px) {
  .header-bar {
    height: 57px;
  }
  .header-logo {
    padding: 0 16px;
  }
  .logo-text {
    font-size: 15px;
  }
  .menu-link {
    font-size: 13px;
    padding: 4px 10px;
  }
  .header-menu {
    padding: 0 12px;
  }
}
</style>
