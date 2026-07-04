<template>
  <div class="user-dashboard" :class="{ 'is-workspace-route': isWorkspaceRoute }">
    <SystemLeftSidebar />
    <SecondaryBusinessSidebar v-if="uiStore.isSecondarySidebarVisible" />
    <div class="dashboard-content">
      <router-view v-slot="{ Component, route: childRoute }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="childRoute.fullPath" />
        </transition>
      </router-view>
    </div>
    <UserOnboardingGuide />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import SystemLeftSidebar from '@/components/SystemLeftSidebar.vue'
import SecondaryBusinessSidebar from '@/components/SecondaryBusinessSidebar.vue'
import UserOnboardingGuide from '@/components/UserOnboardingGuide.vue'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const uiStore = useUiStore()
const isWorkspaceRoute = computed(() => route.path.includes('/workspace'))

watch(() => route.path, (newPath) => {
  if (
    newPath.includes('/create-order') || 
    newPath.includes('/video-marketplace')
  ) {
    uiStore.setIsAiExpanded(false)
    uiStore.setSecondarySidebar(true)
    uiStore.toggleSidebar(true) // Squish primary sidebar
    
    if (newPath.includes('/video-marketplace')) {
      uiStore.setActiveModule('video_purchase')
    } else if (newPath.includes('/create-order/')) {
      uiStore.setActiveModule(String(route.params.type || ''))
    }
  } else if (!newPath.includes('/workspace')) {
    uiStore.setIsAiExpanded(false)
    uiStore.setSecondarySidebar(false)
    uiStore.toggleSidebar(false)
    uiStore.setActiveModule('')
  }
}, { immediate: true })
</script>

<style lang="scss" scoped>
.user-dashboard {
  height: 100vh;
  display: flex;
  flex-direction: row; /* SystemUI Left-Right layout */
  background-color: #fcf9f8; /* SystemUI base level */
  box-sizing: border-box;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.dashboard-content {
  flex: 1;
  overflow-y: auto;
  min-width: 0; /* Important for flex children with auto overflow */
  position: relative; /* necessary for out-in transitions */
}

/* Page Fade Animation */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 768px) {
  .user-dashboard.is-workspace-route {
    height: 100vh;
    height: 100svh;
    min-height: 100vh;
    min-height: 100svh;
    overflow: hidden;
  }

  .user-dashboard.is-workspace-route :deep(.system-sidebar),
  .user-dashboard.is-workspace-route :deep(.secondary-sidebar) {
    display: none !important;
  }

  .user-dashboard.is-workspace-route .dashboard-content {
    width: 100%;
    height: 100vh;
    height: 100svh;
    min-width: 0;
    overflow: hidden;
  }
}
</style>
