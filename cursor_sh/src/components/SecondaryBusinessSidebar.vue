<template>
  <div class="secondary-sidebar">
    <div class="module-list top-module-list">
      <!-- AI Agent Entry (Banner Style) -->
      <div
        class="ai-agent-banner"
        :class="{ active: uiStore.isAiExpanded }"
        role="button"
        tabindex="0"
        @click="goToService('ai_agent')"
        @keydown.enter.self.prevent="goToService('ai_agent')"
        @keydown.space.self.prevent="goToService('ai_agent')"
      >
        <h4 class="ai-banner-title">✨您的7×24小时AI创意合伙人</h4>
        <div class="ai-banner-input-mock">
          <span class="ai-mock-placeholder">有什么想法...</span>
          <div class="ai-mock-btn">发送 ✨</div>
        </div>
      </div>
    </div>

    <template v-if="recentSessions.length > 0">
      <div class="figma-full-divider compact-divider"></div>
      <div class="module-list recent-module-list">
        <div class="recent-chat-section">
          <div class="recent-chat-header">
            <span>最近对话</span>
            <button v-if="recentSessions.length > 4" class="recent-chat-toggle" @click.stop="showAllChats = !showAllChats">
              {{ showAllChats ? '收起' : '更多' }}
            </button>
          </div>
          <button
            v-for="session in visibleRecentSessions"
            :key="session.id"
            class="recent-chat-item"
            :class="{ 'is-active': session.id === uiStore.activeAIChatSessionId }"
            @click.stop="openChatSession(session.id)"
          >
            <span class="recent-chat-title">{{ session.title || '新的对话' }}</span>
            <span class="recent-chat-meta">{{ session.agentLabel || 'AI 对话' }}</span>
          </button>
        </div>
      </div>
    </template>

    <!-- 贯穿首尾的无空隙分割线 -->
    <div class="figma-full-divider"></div>

    <div class="module-list service-module-list">
      <div
        v-for="service in platformServices"
        :key="service.type"
        class="module-group"
        :class="{ active: currentModule === service.type }"
      >
        <div
          class="module-pill"
          :class="{ 'is-active': currentModule === service.type }"
          role="button"
          tabindex="0"
          @click="goToService(service.type)"
          @keydown.enter.self.prevent="goToService(service.type)"
          @keydown.space.self.prevent="goToService(service.type)"
        >
          <span class="module-name">{{ service.title }}</span>
          <el-icon class="expand-icon" :class="{ rotated: currentModule === service.type, 'is-active-icon': currentModule === service.type }"><ArrowDown /></el-icon>
        </div>
        <div class="module-intro" v-show="currentModule === service.type">
          <div class="intro-image" :style="{ background: service.gradient }">
            <div class="badge">{{ service.badge }}</div>
          </div>
          <div class="intro-subtitle">{{ service.subtitle }}</div>
          <p class="intro-desc">
            {{ service.description }}
          </p>
          <div class="intro-tags">
            <span v-for="feature in service.features" :key="feature">{{ feature }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { ArrowDown } from '@element-plus/icons-vue'
import { logger } from '@/utils/logger'
import { chatHistoryApi } from '@/utils/api'
import {
  AI_CHAT_HISTORY_EVENT,
  createAiChatSessionFromRemote,
  getSessionSortValue,
  loadAiChatSessions,
  saveAiChatSessions,
  type AiChatSavedSession,
  type AiChatRemoteSession,
} from '@/utils/aiChatSessions'
import { isOrderableServiceType, platformServices, type ServiceType } from '@/data/platformServices'

const router = useRouter()
const uiStore = useUiStore()
const authStore = useAuthStore()

const currentModule = computed(() => uiStore.activeModule)
const recentSessions = ref<AiChatSavedSession[]>([])
const showAllChats = ref(false)

const visibleRecentSessions = computed(() => {
  return showAllChats.value ? recentSessions.value : recentSessions.value.slice(0, 4)
})

const mergeRemoteSessions = (localSessions: AiChatSavedSession[], remoteSessions: AiChatSavedSession[]) => {
  const byId = new Map<string, AiChatSavedSession>()
  localSessions.forEach(session => byId.set(session.id, session))

  remoteSessions.forEach(remote => {
    const local = byId.get(remote.id)
    if (!local) {
      byId.set(remote.id, remote)
      return
    }

    const localUpdated = getSessionSortValue(local)
    const remoteUpdated = getSessionSortValue(remote)
    byId.set(remote.id, remoteUpdated >= localUpdated
      ? { ...local, ...remote, stateSnapshot: local.stateSnapshot || remote.stateSnapshot }
      : local
    )
  })

  return [...byId.values()].sort((a, b) => getSessionSortValue(b) - getSessionSortValue(a))
}

const fetchRemoteRecentSessions = async () => {
  if (!localStorage.getItem('token')) return []
  const summaries = await chatHistoryApi.getSessions(30) as AiChatRemoteSession[]
  if (!Array.isArray(summaries) || summaries.length === 0) return []

  const sessions = await Promise.all(summaries.map(async summary => {
    try {
      const messages = await chatHistoryApi.getSessionMessages(summary.id)
      return createAiChatSessionFromRemote(summary, Array.isArray(messages) ? messages : [])
    } catch (error) {
      console.warn('[ChatHistory] 拉取历史消息失败:', summary.id, error)
      return createAiChatSessionFromRemote(summary, [])
    }
  }))
  return sessions.filter(session => session.messages.length > 0)
}

const loadRecentSessions = async () => {
  const userId = authStore.user?.id || 'anonymous'
  const localSessions = loadAiChatSessions(userId)
  recentSessions.value = localSessions

  try {
    const remoteSessions = await fetchRemoteRecentSessions()
    if (remoteSessions.length === 0) return
    const merged = mergeRemoteSessions(localSessions, remoteSessions).slice(0, 30)
    recentSessions.value = saveAiChatSessions(userId, merged, false)
  } catch (error) {
    console.warn('[ChatHistory] 拉取后端历史失败:', error)
  }
}

const openChatSession = async (sessionId: string) => {
  uiStore.requestAIChatSessionRestore(sessionId)
  await router.push('/user/workspace')
}

onMounted(() => {
  loadRecentSessions()
  window.addEventListener(AI_CHAT_HISTORY_EVENT, loadRecentSessions)
})

onUnmounted(() => {
  window.removeEventListener(AI_CHAT_HISTORY_EVENT, loadRecentSessions)
})

watch(() => uiStore.aiChatHistoryVersion, loadRecentSessions)
watch(() => authStore.user?.id, loadRecentSessions)

const goToService = async (type: ServiceType | 'ai_agent') => {
  logger.logAction('Workspace', 'sidebar_navigate', { target: type })
  if (type === 'ai_agent') {
    uiStore.setIsAiExpanded(true)
    uiStore.setSecondarySidebar(true)
    uiStore.toggleSidebar(true)
    uiStore.setActiveModule('ai_agent')
    await router.push('/user/workspace')
    return
  }

  uiStore.setIsAiExpanded(false)
  uiStore.setSecondarySidebar(true)
  uiStore.toggleSidebar(true)
  uiStore.setActiveModule(type)
  if (type === 'video_purchase') {
    await router.push('/user/video-marketplace')
  } else if (isOrderableServiceType(type)) {
    await router.push(`/user/create-order/${type}`)
  } else {
    await router.push(`/user/create-order/${type}`)
  }
}
</script>

<style scoped>
.secondary-sidebar {
  width: 260px;
  background: #f3f3f4;
  border-left: 1px solid rgba(0,0,0,0.06);
  border-right: 1px solid rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  box-sizing: border-box;
  flex-shrink: 0;
  overflow-y: auto;
  animation: sidebar-expand 0.45s cubic-bezier(0.25, 1, 0.3, 1) both;
}

@keyframes sidebar-expand {
  from {
    width: 0;
    opacity: 0;
  }
  to {
    width: 260px;
    opacity: 1;
  }
}

.module-list {
  display: flex;
  flex-direction: column;
  padding: 0 8px; /* Was 24px, Figma uses tight padding so buttons stretch wide */
  gap: 0;
}

.figma-full-divider {
  width: 100%;
  height: 1px;
  background-color: #000000;
  opacity: 0.08; /* Strict black and white system */
  margin: 12px 0 0 0;
  flex-shrink: 0;
}

.compact-divider {
  margin-top: 8px;
}

/* AI Agent Banner Style */
.ai-agent-banner {
  background: transparent; /* No card background */
  padding: 12px 12px; /* Aligned with pill text */
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  border-radius: 12px; /* Smoother corner */
}

.ai-agent-banner:hover {
  background: rgba(0,0,0,0.03);
}

.ai-agent-banner:hover .ai-banner-title {
  color: #000;
}

.ai-agent-banner.active .ai-banner-title {
  color: #000;
}

.ai-banner-title {
  font-size: 13px;
  font-weight: 500;
  color: #1b1b1c;
  margin: 0 0 12px 0;
  letter-spacing: -0.01em;
  text-align: center;
}

.ai-banner-input-mock {
  background: #ffffff;
  border-radius: 99px; /* Stitch pill */
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 0 16px;
  border: 1px solid rgba(0,0,0,0.08);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.ai-agent-banner:hover .ai-banner-input-mock {
  border-color: rgba(0,0,0,0.15);
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.ai-mock-placeholder {
  font-size: 12px;
  color: #a0a4ae;
}

.ai-mock-btn {
  background: #f3f3f4; /* Softer background */
  color: #1b1b1c;
  font-weight: 500;
  padding: 0 12px;
  height: 28px;
  border-radius: 99px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.recent-chat-section {
  margin: 8px 4px 0;
  padding: 0 0 4px;
}

.service-module-list {
  margin-top: 16px;
}

.recent-chat-header {
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  font-size: 11px;
  color: #7a808a;
  font-weight: 500;
}

.recent-chat-toggle {
  border: none;
  background: transparent;
  color: #0d99ff;
  font-size: 11px;
  padding: 2px 4px;
  cursor: pointer;
  border-radius: 6px;
}

.recent-chat-toggle:hover {
  background: rgba(13, 153, 255, 0.08);
}

.recent-chat-item {
  width: 100%;
  min-height: 42px;
  border: 0;
  background: transparent;
  border-radius: 8px;
  padding: 7px 8px 7px 10px;
  cursor: pointer;
  text-align: left;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  position: relative;
  transition: background 0.18s ease, color 0.18s ease;
}

.recent-chat-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  bottom: 9px;
  width: 2px;
  border-radius: 2px;
  background: transparent;
}

.recent-chat-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.recent-chat-item.is-active {
  background: #e5f4ff;
}

.recent-chat-item.is-active::before {
  background: #0d99ff;
}

.recent-chat-title {
  font-size: 12px;
  line-height: 16px;
  color: #25282d;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.recent-chat-meta {
  font-size: 10px;
  line-height: 14px;
  color: #8a9099;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.module-group {
  background: transparent;
  transition: all 0.3s ease;
  overflow: hidden;
  border: none; /* No separator between items per user request */
  margin-bottom: 4px;
}

.module-pill {
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  color: #414754;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.2s;
  background: transparent;
}

.module-pill:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #1b1b1c;
}

.module-pill.is-active {
  background: #e5f4ff; /* Figma active item light blue */
  color: #1a1c1c; /* Text stays dark/black as in Figma */
  font-weight: 500;
  margin-bottom: 8px; /* space before intro drops down */
}

.expand-icon {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
  transition: transform 0.3s ease;
}

.expand-icon.is-active-icon {
  color: #0d99ff; /* The icon takes the Figma primary blue to pop */
}

.expand-icon.rotated {
  transform: rotate(180deg);
  color: #333;
}

/* Descriptive Intro inside accordion */
.module-intro {
  padding: 0 12px 24px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: slide-down 0.25s ease both;
}

@keyframes slide-down {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.intro-image {
  height: 100px;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.1);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 8px;
}

.intro-image .badge {
  background: rgba(0, 112, 235, 0.9);
  color: #fff;
  font-size: 10px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.intro-image .badge.creative { background: rgba(0, 112, 235, 0.9); }
.intro-image .badge.art { background: rgba(0, 112, 235, 0.9); }

.intro-subtitle {
  color: #1f2329;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
}

.intro-desc {
  margin: 0;
  font-size: 12px;
  color: #6c707d;
  line-height: 1.6;
}

.intro-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.intro-tags span {
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  color: #414754;
  font-size: 10px;
  line-height: 1;
  padding: 4px 6px;
}

</style>
