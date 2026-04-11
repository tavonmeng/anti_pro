<template>
  <div class="style-inspiration-sidebar">
    <div class="sidebar-header">
      <div class="header-row">
        <h3 class="sidebar-title">灵感库</h3>
        <button class="close-btn" @click="emit('close')" title="关闭">×</button>
      </div>
      <div class="timer-line">
        <div class="timer-progress" :style="{ width: progress + '%' }"></div>
      </div>
    </div>
    
    <div class="styles-container" @mouseenter="isHovering = true" @mouseleave="isHovering = false" :class="{ 'is-paused': isHovering }">
      <transition-group name="fade-slide" tag="div" class="styles-list">
        <div 
          v-for="item in visibleStyles" 
          :key="item.id" 
          class="style-card"
        >
          <div class="style-image" :style="{ background: item.bg }">
             <span class="style-emoji">{{ item.emoji }}</span>
          </div>
          <div class="style-info">
            <h4 class="style-title">{{ item.title }}</h4>
            <p class="style-desc">{{ item.description }}</p>
          </div>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

const emit = defineEmits(['close'])

const styleMaterials = [
  { id: 1, emoji: '🌆', title: '赛博朋克霓虹', description: '极具科幻感的都市夜景，以高对比霓虹灯光衬托前卫科技产品。', bg: '#f3f3f4' },
  { id: 2, emoji: '🏺', title: '极简黏土风', description: '柔和漫反射光照下的纯粹质感，传递婴儿般温润的品牌调性。', bg: '#f3f3f4' },
  { id: 3, emoji: '💧', title: '液态金属', description: '变幻莫测的流体物理模拟，展现奢侈品或尖端硬件的冷艳高端。', bg: '#f3f3f4' },
  { id: 4, emoji: '✨', title: '全息数字幻影', description: '未来主义网格粒子特效，携微弱故障艺术提升前卫感。', bg: '#f3f3f4' },
  { id: 5, emoji: '🌿', title: '超写实微观生态', description: '极大放大的逼真自然生命切片，阳光水珠细节毫毫毕现。', bg: '#f3f3f4' },
  { id: 6, emoji: '🎨', title: '美漫卡通渲染', description: '粗犷色块与硬朗边线勾勒，将三维转为极具张力的二维视觉。', bg: '#f3f3f4' },
]

const currentIndex = ref(0)
const progress = ref(0)
const isHovering = ref(false)
let progressInterval: any = null

const visibleStyles = computed(() => {
  const styles = []
  styles.push(styleMaterials[currentIndex.value])
  styles.push(styleMaterials[(currentIndex.value + 1) % styleMaterials.length])
  return styles
})

const nextSlide = () => {
  currentIndex.value = (currentIndex.value + 2) % styleMaterials.length
}

onMounted(() => {
  // Sync the slide completely with the 20s progress bar allowing it to be paused
  progressInterval = setInterval(() => {
    if (!isHovering.value) {
      progress.value += (100 / (20000 / 16)) // 20s = 20000ms at ~60fps
      if (progress.value >= 100) {
        progress.value = 0
        nextSlide()
      }
    }
  }, 16)
})

onUnmounted(() => {
  if (progressInterval) clearInterval(progressInterval)
})
</script>

<style scoped>
.style-inspiration-sidebar {
  width: 260px;
  background: #ffffff;
  border-left: 1px solid rgba(0,0,0,0.04);
  display: flex;
  flex-direction: column;
  padding: 24px 20px;
  box-sizing: border-box;
  flex-shrink: 0;
}

.sidebar-header {
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-title {
  font-size: 11px; /* Stitch mono-tag style */
  font-weight: 500;
  color: #747474;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
}

.timer-line {
  height: 2px;
  background: rgba(0,0,0,0.05);
  border-radius: 2px;
  overflow: hidden;
}

.timer-progress {
  height: 100%;
  background: #c8c8cc; /* Subtle grey */
  transition: width 0.016s linear;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  color: #a0a4ae;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.close-btn:hover {
  color: #1a1c1c;
}

.styles-container {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.styles-list {
  display: flex;
  flex-direction: column;
  gap: 16px; /* Tighten gap */
  height: 100%;
}

.style-card {
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0,0,0,0.05); /* Stitch clean border */
  box-shadow: none; /* Strip drop shadows */
  display: flex;
  flex-direction: column;
  transition: transform 0.3s cubic-bezier(0.2, 0, 0, 1), box-shadow 0.3s ease, border-color 0.3s ease;
  cursor: pointer;
}

.style-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0,0,0,0.1);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06); /* Soft lift shadow */
}

.style-image {
  height: 100px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.style-emoji {
  font-size: 32px;
}

.style-info {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.style-title {
  font-size: 13px;
  font-weight: 500;
  color: #1a1c1c;
  margin: 0;
}

.style-desc {
  font-size: 11px;
  color: #646a78;
  margin: 0;
  line-height: 1.4;
}

/* Transitions */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.5s cubic-bezier(0.25, 1, 0.3, 1);
  position: absolute;
  width: 100%;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
