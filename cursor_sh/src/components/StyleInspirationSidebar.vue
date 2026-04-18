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
      <transition-group 
        appear
        @before-enter="beforeEnter"
        @enter="onEnter"
        @leave="onLeave"
        :css="false"
        tag="div" 
        class="styles-list">
        <div 
          v-for="(item, index) in visibleStyles" 
          :key="item.id" 
          class="style-card"
          :data-index="index"
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
import gsap from 'gsap'

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

// GSAP transition hooks
const beforeEnter = (el: any) => {
  el.style.opacity = 0
  el.style.transform = 'translateY(15px)'
  el.style.position = 'absolute'
  el.style.width = '100%'
}

const onEnter = (el: any, done: () => void) => {
  const index = parseInt(el.dataset.index) || 0
  gsap.to(el, {
    opacity: 1,
    y: 0,
    duration: 0.6,
    ease: "power3.out",
    delay: index * 0.15,
    onComplete: () => {
      el.style.position = 'relative'
      el.style.transform = 'none' /* Clear transform so hover continues to work cleanly */
      done()
    }
  })
}

const onLeave = (el: any, done: () => void) => {
  el.style.position = 'absolute'
  el.style.width = '100%'
  gsap.to(el, {
    opacity: 0,
    y: -15,
    duration: 0.4,
    ease: "power2.in",
    onComplete: done
  })
}
</script>

<style scoped>
.style-inspiration-sidebar {
  width: 260px;
  background: #ffffff;
  border-left: 1px solid rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  padding: 0; /* Remove wrapper padding so header reaches edges */
  box-sizing: border-box;
  flex-shrink: 0;
  height: 100vh; /* Stretch full height to resolve background visual gap */
}

.sidebar-header {
  height: 56px; /* Align perfectly with ai-chat-assistant header height */
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 24px;
  position: relative;
  flex-shrink: 0;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
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

/* Base divider line spanning the full width of the sidebar exactly at the bottom of the 56px header */
.timer-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: rgba(0,0,0,0.06); /* Gray tracking line that visually acts as the divider */
  overflow: visible;
}

/* The active progress overlays perfectly on top of the divider */
.timer-progress {
  height: 100%;
  background: #1a1c1c; /* Distinct dark progress so it stands out */
  transition: width 0.016s linear;
}

.styles-container {
  flex: 1;
  padding: 24px 20px; /* Restore padding strictly to content area */
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


</style>
