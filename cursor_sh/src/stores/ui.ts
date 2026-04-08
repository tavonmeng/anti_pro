import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const isSidebarCollapsed = ref(false)
  const isSecondarySidebarVisible = ref(false)
  const activeModule = ref<string>('')
  const isAiExpanded = ref(false)

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

  return {
    isSidebarCollapsed,
    isSecondarySidebarVisible,
    activeModule,
    isAiExpanded,
    toggleSidebar,
    setSecondarySidebar,
    setActiveModule,
    setIsAiExpanded
  }
})
