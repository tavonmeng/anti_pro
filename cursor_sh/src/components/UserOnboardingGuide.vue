<template>
  <teleport to="body">
    <div v-if="isActive && currentStep && targetRect" class="onboarding-guide">
      <div class="guide-highlight" :style="highlightStyle" aria-hidden="true"></div>

      <section class="guide-card" :style="cardStyle" role="dialog" aria-live="polite">
        <div class="guide-meta">
          <span>新手引导</span>
          <span>{{ activeIndex + 1 }} / {{ steps.length }}</span>
        </div>
        <h2>{{ currentStep.title }}</h2>
        <p>{{ currentStep.description }}</p>

        <div class="guide-progress" :style="progressStyle" aria-hidden="true">
          <span
            v-for="(_, index) in steps"
            :key="index"
            :class="{ active: index <= activeIndex }"
          ></span>
        </div>

        <div class="guide-actions">
          <button type="button" class="guide-text-btn" @click="skipGuide">跳过</button>
          <div class="guide-action-group">
            <button
              v-if="activeIndex > 0"
              type="button"
              class="guide-secondary-btn"
              @click="goToPreviousStep"
            >
              上一步
            </button>
            <button type="button" class="guide-primary-btn" @click="goToNextStep">
              {{ currentStep.primaryLabel || (isLastStep ? '完成' : '下一步') }}
            </button>
          </div>
        </div>
      </section>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

interface OnboardingStep {
  id: string
  target: string
  title: string
  description: string
  primaryLabel?: string
  route?: string
  prepare?: () => void | Promise<void>
  completeOnTargetClick?: boolean
  cardPlacement?: 'auto' | 'target-bottom-right' | 'target-right'
}

interface RectState {
  top: number
  left: number
  width: number
  height: number
  right: number
  bottom: number
  borderRadius: string
}

const GUIDE_STORAGE_PREFIX = 'uv-user-onboarding-guide-v3'
const NEW_REGISTRATION_STORAGE_PREFIX = 'uv-user-onboarding-new-registration'
const START_GUIDE_EVENT = 'uv:start-user-onboarding'
const HIGHLIGHT_PADDING = 8
const CARD_WIDTH = 320
const CARD_GAP = 16
const VIEWPORT_MARGIN = 16

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()

const activeIndex = ref(0)
const isActive = ref(false)
const targetRect = ref<RectState | null>(null)
let refreshTimer: ReturnType<typeof setTimeout> | null = null
let startTimer: ReturnType<typeof setTimeout> | null = null

const steps: OnboardingStep[] = [
  {
    id: 'workspace-nav',
    target: '[data-onboarding-target="workspace-nav"]',
    title: '左侧菜单从工作台开始',
    description: '工作台是用户端的首页。这里可以打开智能体、浏览业务模块，也能回到平台的主要入口。',
    primaryLabel: '继续',
    route: '/user/workspace',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'orders-nav',
    target: '[data-onboarding-target="orders-nav"]',
    title: '我的订单用于跟进项目',
    description: '已经提交的需求会进入这里。用户可以查看项目进度、订单状态和后续交付信息。',
    route: '/user/workspace',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'drafts-nav',
    target: '[data-onboarding-target="drafts-nav"]',
    title: '草稿箱保存未完成需求',
    description: '企业认证前或信息没填完时，需求可以先保存成草稿，之后再继续补充。',
    route: '/user/workspace',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'announcement-nav',
    target: '[data-onboarding-target="announcement-nav"]',
    title: '公告用于查看平台消息',
    description: '平台的重要通知、功能更新或服务说明会放在这里。进入用户端后，可以先看是否有未读公告。',
    route: '/user/workspace',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'notification-nav',
    target: '[data-onboarding-target="notification-nav"]',
    title: '通知会提醒项目动态',
    description: '订单状态变化、交付更新和需要您处理的事项，会通过通知提醒，方便及时跟进。',
    route: '/user/workspace',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'help-nav',
    target: '[data-onboarding-target="help-nav"]',
    title: '帮助与支持在这里',
    description: '遇到系统使用问题或需要联系设计专家时，可以从这里打开帮助信息，也可以通过文字入口重看系统引导。',
    route: '/user/workspace',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'profile-nav',
    target: '[data-onboarding-target="profile-nav"]',
    title: '个人中心管理账号信息',
    description: '这里可以进入个人中心，维护账号资料和企业认证信息。后面我们会单独介绍企业认证模块。',
    route: '/user/workspace',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'enterprise-form',
    target: '[data-onboarding-target="enterprise-auth-section"]',
    title: '企业认证决定能否正式下单',
    description: '个人中心里最重要的是企业认证。如果需要提交正式订单，请完成企业名称和营业执照认证；未认证时，需求会优先保存为草稿。',
    route: '/user/profile',
    prepare: () => {
      uiStore.setIsAiExpanded(false)
      uiStore.setSecondarySidebar(false)
      uiStore.toggleSidebar(false)
      uiStore.setActiveModule('')
    }
  },
  {
    id: 'ai-entry',
    target: '[data-onboarding-target="ai-hero-entry"]',
    title: '第一个核心功能是智能体',
    description: '您可以先和 Unique Vision 智能体沟通项目 brief、初步创意方向、业务选择、订单提交，以及已有订单制作状态查询。',
    primaryLabel: '介绍业务模块',
    route: '/user/workspace',
    cardPlacement: 'target-bottom-right',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'business-overview',
    target: '[data-onboarding-target="business-service-list"]',
    title: '这里是业务模块',
    description: '业务菜单汇总了平台服务。您可以先浏览每个业务的适用场景、能力范围和交付方向，再决定从哪里开始。',
    primaryLabel: '继续看侧栏',
    route: '/user/workspace',
    cardPlacement: 'target-bottom-right',
    prepare: () => resetToWorkspaceOverview()
  },
  {
    id: 'business-sidebar',
    target: '[data-onboarding-target="secondary-business-list"]',
    title: '业务侧栏用于快速切换',
    description: '进入某个业务后，侧栏会保留业务列表和简介。用户可以边看介绍边切换，不需要回到首页重找。',
    route: '/user/create-order/ai_3d_custom',
    cardPlacement: 'target-right',
    prepare: () => {
      uiStore.setIsAiExpanded(false)
      uiStore.setSecondarySidebar(true)
      uiStore.toggleSidebar(true)
      uiStore.setActiveModule('ai_3d_custom')
    }
  },
  {
    id: 'order-form',
    target: '[data-onboarding-target="order-form-surface"]',
    title: '手动填写是备用路径',
    description: '如果需求已经很明确，也可以直接填写表单。这里主要用于补充项目信息、上传素材，或把未完成内容保存为草稿。',
    primaryLabel: '回到智能体',
    route: '/user/create-order/ai_3d_custom',
    prepare: () => {
      uiStore.setIsAiExpanded(false)
      uiStore.setSecondarySidebar(true)
      uiStore.toggleSidebar(true)
      uiStore.setActiveModule('ai_3d_custom')
    }
  },
  {
    id: 'final-ai-chat',
    target: '[data-onboarding-target="ai-chat-input"]',
    title: '建议从智能体开始交流',
    description: '把项目背景、目标、预算或已有素材直接输入这里。智能体会帮您理清 brief、讨论创意方向，并继续引导提交订单或查询项目状态。',
    primaryLabel: '开始交流',
    route: '/user/workspace',
    completeOnTargetClick: true,
    cardPlacement: 'target-right',
    prepare: () => {
      uiStore.setIsAiExpanded(true)
      uiStore.setSecondarySidebar(true)
      uiStore.toggleSidebar(true)
      uiStore.setActiveModule('ai_agent')
    }
  }
]

const currentStep = computed(() => steps[activeIndex.value])
const isLastStep = computed(() => activeIndex.value === steps.length - 1)
const storageKey = computed(() => {
  const userId = authStore.user?.id || 'anonymous'
  return `${GUIDE_STORAGE_PREFIX}:${userId}`
})
const newRegistrationKey = computed(() => {
  const userId = authStore.user?.id || 'anonymous'
  return `${NEW_REGISTRATION_STORAGE_PREFIX}:${userId}`
})

const resetToWorkspaceOverview = () => {
  uiStore.setIsAiExpanded(false)
  uiStore.setSecondarySidebar(false)
  uiStore.toggleSidebar(false)
  uiStore.setActiveModule('')
}

const clamp = (value: number, min: number, max: number) => {
  return Math.min(Math.max(value, min), Math.max(min, max))
}

const wait = (ms: number) => {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

const paddedRect = computed(() => {
  if (!targetRect.value) return null
  const top = Math.max(0, targetRect.value.top - HIGHLIGHT_PADDING)
  const left = Math.max(0, targetRect.value.left - HIGHLIGHT_PADDING)
  const right = Math.min(window.innerWidth, targetRect.value.right + HIGHLIGHT_PADDING)
  const bottom = Math.min(window.innerHeight, targetRect.value.bottom + HIGHLIGHT_PADDING)
  return {
    top,
    left,
    right,
    bottom,
    width: right - left,
    height: bottom - top
  }
})

const highlightStyle = computed(() => {
  if (!paddedRect.value) return {}
  return {
    top: `${paddedRect.value.top}px`,
    left: `${paddedRect.value.left}px`,
    width: `${paddedRect.value.width}px`,
    height: `${paddedRect.value.height}px`,
    borderRadius: targetRect.value?.borderRadius || '10px'
  }
})

const progressStyle = computed(() => {
  return {
    gridTemplateColumns: `repeat(${steps.length}, 1fr)`
  }
})

const cardStyle = computed(() => {
  const rect = paddedRect.value
  if (!rect) return {}
  const cardWidth = Math.min(CARD_WIDTH, Math.max(260, window.innerWidth - VIEWPORT_MARGIN * 2))
  const availableRight = window.innerWidth - rect.right
  const availableLeft = rect.left
  const availableBottom = window.innerHeight - rect.bottom
  const cardHeight = Math.min(280, Math.max(210, window.innerHeight - VIEWPORT_MARGIN * 2))

  if (currentStep.value?.cardPlacement === 'target-bottom-right') {
    const rightAlignedLeft = rect.right - cardWidth
    const belowTop = rect.bottom + CARD_GAP
    const bottomLimit = window.innerHeight - cardHeight - VIEWPORT_MARGIN
    const preferredTop = belowTop <= bottomLimit ? belowTop : rect.bottom - cardHeight
    return {
      width: `${cardWidth}px`,
      top: `${clamp(preferredTop, VIEWPORT_MARGIN, bottomLimit)}px`,
      left: `${clamp(rightAlignedLeft, VIEWPORT_MARGIN, window.innerWidth - cardWidth - VIEWPORT_MARGIN)}px`
    }
  }

  if (currentStep.value?.cardPlacement === 'target-right') {
    const rightSideLeft = rect.right + CARD_GAP
    return {
      width: `${cardWidth}px`,
      top: `${clamp(rect.top, VIEWPORT_MARGIN, window.innerHeight - cardHeight - VIEWPORT_MARGIN)}px`,
      left: `${clamp(rightSideLeft, VIEWPORT_MARGIN, window.innerWidth - cardWidth - VIEWPORT_MARGIN)}px`
    }
  }

  let left = rect.left
  let top = rect.bottom + CARD_GAP

  if (availableRight >= cardWidth + CARD_GAP + VIEWPORT_MARGIN) {
    left = rect.right + CARD_GAP
    top = rect.top
  } else if (availableLeft >= cardWidth + CARD_GAP + VIEWPORT_MARGIN) {
    left = rect.left - cardWidth - CARD_GAP
    top = rect.top
  } else if (availableBottom < cardHeight && rect.top > cardHeight + CARD_GAP) {
    top = rect.top - cardHeight - CARD_GAP
  }

  return {
    width: `${cardWidth}px`,
    top: `${clamp(top, VIEWPORT_MARGIN, window.innerHeight - cardHeight - VIEWPORT_MARGIN)}px`,
    left: `${clamp(left, VIEWPORT_MARGIN, window.innerWidth - cardWidth - VIEWPORT_MARGIN)}px`
  }
})

const getTargetElement = () => {
  const target = currentStep.value?.target
  return target ? document.querySelector<HTMLElement>(target) : null
}

const updateTargetRect = () => {
  if (!isActive.value) return
  const element = getTargetElement()
  if (!element) {
    targetRect.value = null
    queueTargetRefresh()
    return
  }
  const rect = element.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) {
    targetRect.value = null
    queueTargetRefresh()
    return
  }
  const computedStyle = window.getComputedStyle(element)
  const borderRadius = computedStyle.borderRadius && computedStyle.borderRadius !== '0px'
    ? computedStyle.borderRadius
    : '10px'
  targetRect.value = {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
    right: rect.right,
    bottom: rect.bottom,
    borderRadius
  }
}

const queueTargetRefresh = () => {
  if (refreshTimer) clearTimeout(refreshTimer)
  refreshTimer = setTimeout(updateTargetRect, 120)
}

const waitForTargetElement = async () => {
  for (let attempt = 0; attempt < 14; attempt += 1) {
    await nextTick()
    const element = getTargetElement()
    if (element) {
      const rect = element.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) return element
    }
    await wait(120)
  }
  return null
}

const getScrollContainer = (element: HTMLElement): HTMLElement | Window => {
  let parent = element.parentElement
  while (parent && parent !== document.body) {
    const style = window.getComputedStyle(parent)
    const canScrollY = /(auto|scroll|overlay)/.test(style.overflowY)
    if (canScrollY && parent.scrollHeight > parent.clientHeight) {
      return parent
    }
    parent = parent.parentElement
  }
  return window
}

const centerElementInScrollContainer = (element: HTMLElement) => {
  const scrollContainer = getScrollContainer(element)
  const rect = element.getBoundingClientRect()

  if (scrollContainer === window) {
    const targetTop = window.scrollY + rect.top - (window.innerHeight - rect.height) / 2
    window.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' })
    return
  }

  const container = scrollContainer as HTMLElement
  const containerRect = container.getBoundingClientRect()
  const targetTop = container.scrollTop + rect.top - containerRect.top - (container.clientHeight - rect.height) / 2
  container.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' })
}

const scrollTargetIntoView = async () => {
  await nextTick()
  const element = await waitForTargetElement()
  if (!element) {
    queueTargetRefresh()
    return
  }
  centerElementInScrollContainer(element)
  ;[80, 220, 420, 700].forEach(delay => {
    window.setTimeout(updateTargetRect, delay)
  })
}

const activateCurrentStep = async () => {
  const step = currentStep.value
  if (!step) return
  await step.prepare?.()
  if (step.route && route.path !== step.route) {
    await router.push(step.route)
  }
  await wait(120)
  await scrollTargetIntoView()
}

const completeGuide = () => {
  localStorage.setItem(storageKey.value, 'completed')
  localStorage.removeItem(newRegistrationKey.value)
  isActive.value = false
  targetRect.value = null
}

const skipGuide = () => {
  localStorage.setItem(storageKey.value, 'skipped')
  localStorage.removeItem(newRegistrationKey.value)
  isActive.value = false
  targetRect.value = null
  ElMessage.info('已跳过新手引导。之后可从左侧「帮助与支持」里的「系统引导」再次打开。')
}

const goToNextStep = async () => {
  if (isLastStep.value) {
    completeGuide()
    return
  }
  activeIndex.value += 1
  await activateCurrentStep()
}

const goToPreviousStep = async () => {
  if (activeIndex.value === 0) return
  activeIndex.value -= 1
  await activateCurrentStep()
}

const handleDocumentClick = (event: MouseEvent) => {
  if (!isActive.value || !currentStep.value?.completeOnTargetClick) return
  const target = event.target as HTMLElement | null
  if (!target?.closest(currentStep.value.target)) return
  window.setTimeout(completeGuide, 220)
}

const startGuide = async (force = false) => {
  if (!authStore.isAuthenticated() || !authStore.isUser()) return
  const hasFinishedGuide = Boolean(localStorage.getItem(storageKey.value))
  const isNewRegistration = Boolean(localStorage.getItem(newRegistrationKey.value))
  if (!force && (hasFinishedGuide || !isNewRegistration)) return
  isActive.value = true
  activeIndex.value = 0
  targetRect.value = null
  await activateCurrentStep()
}

const startGuideIfNeeded = async () => {
  await startGuide(false)
}

const handleManualStart = () => {
  void startGuide(true)
}

watch(() => route.fullPath, () => {
  if (!isActive.value) return
  window.setTimeout(updateTargetRect, 220)
})

watch(() => authStore.user?.id, () => {
  if (isActive.value) return
  void startGuideIfNeeded()
})

onMounted(() => {
  startTimer = setTimeout(startGuideIfNeeded, 700)
  window.addEventListener('resize', updateTargetRect)
  window.addEventListener('scroll', updateTargetRect, true)
  window.addEventListener(START_GUIDE_EVENT, handleManualStart)
  document.addEventListener('click', handleDocumentClick, true)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearTimeout(refreshTimer)
  if (startTimer) clearTimeout(startTimer)
  window.removeEventListener('resize', updateTargetRect)
  window.removeEventListener('scroll', updateTargetRect, true)
  window.removeEventListener(START_GUIDE_EVENT, handleManualStart)
  document.removeEventListener('click', handleDocumentClick, true)
})
</script>

<style scoped>
.onboarding-guide {
  position: fixed;
  inset: 0;
  z-index: 3000;
  pointer-events: none;
}

.guide-highlight {
  position: fixed;
  border: 2px solid var(--uv-ws-action-button-bg, #A0522D);
  box-shadow:
    0 0 0 9999px rgba(15, 15, 16, 0.58),
    0 0 0 4px rgba(160, 82, 45, 0.2),
    0 14px 42px rgba(0, 0, 0, 0.18);
  pointer-events: none;
  transition:
    top 0.24s cubic-bezier(0.22, 1, 0.36, 1),
    left 0.24s cubic-bezier(0.22, 1, 0.36, 1),
    width 0.24s cubic-bezier(0.22, 1, 0.36, 1),
    height 0.24s cubic-bezier(0.22, 1, 0.36, 1),
    border-radius 0.24s cubic-bezier(0.22, 1, 0.36, 1);
}

.guide-card {
  position: fixed;
  width: 320px;
  box-sizing: border-box;
  padding: 18px;
  background: #ffffff;
  border: 1px solid rgba(27, 27, 28, 0.08);
  border-radius: 8px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.18);
  color: #1b1b1c;
  pointer-events: auto;
  transition: top 0.24s cubic-bezier(0.22, 1, 0.36, 1), left 0.24s cubic-bezier(0.22, 1, 0.36, 1);
}

.guide-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  color: #747474;
  font-size: 12px;
}

.guide-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0;
}

.guide-card p {
  margin: 0;
  color: #52565f;
  font-size: 13px;
  line-height: 1.65;
}

.guide-progress {
  display: grid;
  gap: 5px;
  margin: 16px 0;
}

.guide-progress span {
  height: 3px;
  border-radius: 999px;
  background: #e7e2df;
}

.guide-progress span.active {
  background: var(--uv-ws-action-button-bg, #A0522D);
}

.guide-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.guide-action-group {
  display: flex;
  gap: 8px;
}

.guide-text-btn,
.guide-secondary-btn,
.guide-primary-btn {
  height: 34px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.guide-text-btn {
  padding: 0;
  border: none;
  background: transparent;
  color: #747474;
}

.guide-secondary-btn {
  padding: 0 12px;
  border: 1px solid rgba(27, 27, 28, 0.12);
  background: #fff;
  color: #414754;
}

.guide-primary-btn {
  padding: 0 14px;
  border: none;
  background: var(--uv-ws-action-button-bg, #A0522D);
  color: #fff;
}

@media (max-width: 720px) {
  .guide-card {
    left: 16px !important;
    right: 16px;
    bottom: 16px;
    top: auto !important;
    width: auto;
  }
}
</style>
