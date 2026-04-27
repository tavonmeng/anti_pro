<template>
  <div class="user-dashboard">
    <SystemLeftSidebar />
    <SecondaryBusinessSidebar v-if="uiStore.isSecondarySidebarVisible" />
    <div class="dashboard-content">
      <router-view v-slot="{ Component, route: childRoute }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="childRoute.fullPath" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import SystemLeftSidebar from '@/components/SystemLeftSidebar.vue'
import SecondaryBusinessSidebar from '@/components/SecondaryBusinessSidebar.vue'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const uiStore = useUiStore()

watch(() => route.path, (newPath) => {
  if (
    newPath.includes('/create-order') || 
    newPath.includes('/video-marketplace')
  ) {
    uiStore.setSecondarySidebar(true)
    uiStore.toggleSidebar(true) // Squish primary sidebar
    
    if (newPath.includes('/video-marketplace')) {
      uiStore.setActiveModule('video_purchase')
    } else if (newPath.includes('/create-order/ai_3d_custom')) {
      uiStore.setActiveModule('ai_3d_custom')
    } else if (newPath.includes('/create-order/digital_art')) {
      uiStore.setActiveModule('digital_art')
    }
  } else if (!newPath.includes('/workspace')) {
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
</style>

