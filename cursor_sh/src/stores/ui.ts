import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const isSidebarCollapsed = ref(false)
  const isSecondarySidebarVisible = ref(false)
  const activeModule = ref<string>('')
  const isAiExpanded = ref(false)
  const activeAIChatSessionId = ref<string>('')
  const pendingAIChatSessionId = ref<string>('')
  const aiChatHistoryVersion = ref(0)

  const toggleSidebar = (collapse?: boolean) => {
    isSidebarCollapsed.value = collapse ?? !isSidebarCollapsed.value
  }

  const setSecondarySidebar = (visible: boolean) => {
    isSecondarySidebarVisible.value = visible
  }

  const setActiveModule = (module: string) => {
    activeModule.value = module
  }

  const setIsAiExpanded = (expanded: boolean) => {
    isAiExpanded.value = expanded
  }

  const setActiveAIChatSession = (sessionId: string) => {
    activeAIChatSessionId.value = sessionId
  }

  const requestAIChatSessionRestore = (sessionId: string) => {
    pendingAIChatSessionId.value = sessionId
    isAiExpanded.value = true
    isSecondarySidebarVisible.value = true
    isSidebarCollapsed.value = true
  }

  const clearPendingAIChatSession = () => {
    pendingAIChatSessionId.value = ''
  }

  const markAIChatHistoryChanged = () => {
    aiChatHistoryVersion.value += 1
  }

  return {
    isSidebarCollapsed,
    isSecondarySidebarVisible,
    activeModule,
    isAiExpanded,
    activeAIChatSessionId,
    pendingAIChatSessionId,
    aiChatHistoryVersion,
    toggleSidebar,
    setSecondarySidebar,
    setActiveModule,
    setIsAiExpanded,
    setActiveAIChatSession,
    requestAIChatSessionRestore,
    clearPendingAIChatSession,
    markAIChatHistoryChanged
  }
})
