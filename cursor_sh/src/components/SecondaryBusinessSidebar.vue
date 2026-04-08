<template>
  <div class="secondary-sidebar">
    <div class="secondary-header">
      <h3>业务菜单</h3>
    </div>
    <div class="module-list">
      <div 
        class="module-item"
        :class="{ active: currentModule === 'video_purchase' }"
        @click="goToService('video_purchase')"
      >
        <span class="module-name">裸眼3D成片购买</span>
      </div>
      <div 
        class="module-item"
        :class="{ active: currentModule === 'ai_3d_custom' }"
        @click="goToService('ai_3d_custom')"
      >
        <span class="module-name">AI裸眼3D内容定制</span>
      </div>
      <div 
        class="module-item"
        :class="{ active: currentModule === 'digital_art' }"
        @click="goToService('digital_art')"
      >
        <span class="module-name">数字艺术内容定制</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const uiStore = useUiStore()

const currentModule = computed(() => uiStore.activeModule)

const goToService = async (type: string) => {
  if (type === 'video_purchase') {
    await router.push('/user/video-marketplace')
  } else {
    await router.push(`/user/create-order/${type}`)
  }
}
</script>

<style scoped>
.secondary-sidebar {
  width: 240px;
  background: #ffffff;
  border-right: 1px solid #eae7e7;
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  box-sizing: border-box;
  flex-shrink: 0;
  overflow: hidden;
  animation: sidebar-expand 0.45s cubic-bezier(0.25, 1, 0.3, 1) both;
}

@keyframes sidebar-expand {
  from {
    width: 0;
    padding: 24px 0;
    opacity: 0;
  }
  to {
    width: 240px;
    padding: 24px 0;
    opacity: 1;
  }
}

.secondary-header {
  padding: 0 24px;
  margin-bottom: 16px;
}

.secondary-header h3 {
  font-size: 14px;
  font-weight: 700;
  color: #1b1b1c;
  margin: 0;
}

.module-list {
  display: flex;
  flex-direction: column;
  padding: 0 16px;
  gap: 8px;
}

.module-item {
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  background: #f6f3f2;
  transition: all 0.2s;
  color: #414754;
  font-size: 13px;
  font-weight: 500;
}

.module-item:hover {
  background: #eae7e7;
}

.module-item.active {
  background: #ffffff;
  color: #1b1b1c;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

</style>
