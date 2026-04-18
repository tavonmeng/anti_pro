<template>
  <div class="case-showcase-page" ref="pageRef">
    <!-- Slider container -->
    <div class="showcase-slider">
      <Transition name="slide">
        <!-- We use currentIndex as key to trigger the slide transition on change -->
        <div 
          :key="'showcase-' + currentIndex"
          class="showcase-slide"
          @click="openDetail(currentCase)"
        >
          <!-- 优先使用视频作为封面展示 -->
          <video 
            v-if="currentCase.video" 
            muted 
            loop 
            playsinline
            autoplay
            :src="currentCase.video"
            class="media-layer"
          ></video>
          <img 
            v-else-if="currentCase.detail?.gallery?.[0]" 
            :src="currentCase.detail.gallery[0]"
            :alt="currentCase.title"
          />
          <div class="slide-overlay"></div>
        </div>
      </Transition>
    </div>

    <!-- Slide Navigation Arrows -->
    <div class="nav-arrow left-arrow hover-target" @click.stop="prevSlide">
      <span class="arrow-icon">〈</span>
    </div>
    <div class="nav-arrow right-arrow hover-target" @click.stop="nextSlide">
      <span class="arrow-icon">〉</span>
    </div>

    <!-- Info text at bottom left -->
    <div class="showcase-info">
      <span>项目类型：</span>
      <span class="type-text">
        {{ currentCase.detail?.type || currentCase.category }}&nbsp;&nbsp;{{ currentCase.title }}
      </span>
    </div>

    <!-- Dots navigator (18 items generated computationally) -->
    <div class="showcase-dots">
       <span 
         v-for="(item, index) in displayCases" 
         :key="'dot-' + index"
         class="dot hover-target"
         :class="{ active: currentIndex === index }"
         @click.stop="goToSlide(index)"
       ></span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'

const props = defineProps({
  cases: {
    type: Array,
    required: true
  },
  initialCaseId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['open-detail', 'close'])

const pageRef = ref(null)
const currentIndex = ref(0)
const totalDots = 18

// Create a visual array of 18 items by repeating cases
const displayCases = computed(() => {
  return Array.from({ length: totalDots }).map((_, i) => props.cases[i % props.cases.length])
})

onMounted(() => {
  // Try to find the initial case
  let index = props.cases.findIndex(c => c.id === props.initialCaseId)
  if (index !== -1) {
    currentIndex.value = index
  }

  // Showcase Entry Animation (Dynamically reveals the page like a cinematic curtain opening from bottom to top)
  gsap.from(pageRef.value, {
    clipPath: 'inset(100% 0 0 0)',
    opacity: 0,
    scale: 0.95,
    duration: 1.4,
    ease: 'power4.inOut'
  })
})

// Sync if props change
watch(() => props.initialCaseId, (newId) => {
  const index = props.cases.findIndex(c => c.id === newId)
  if (index !== -1) {
    currentIndex.value = index
  }
})

const currentCase = computed(() => displayCases.value[currentIndex.value] || props.cases[0])

const goToSlide = (index) => {
  currentIndex.value = index
}

const nextSlide = () => {
  currentIndex.value = (currentIndex.value + 1) % displayCases.value.length
}

const prevSlide = () => {
  currentIndex.value = (currentIndex.value - 1 + displayCases.value.length) % displayCases.value.length
}

const openDetail = (item) => {
  emit('open-detail', item)
}

// Global scroll prevention
onMounted(() => {
  document.body.style.overflow = 'hidden'
})
onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<style scoped>
.case-showcase-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: #000;
  z-index: 4000;
  color: #fff;
  display: flex;
  flex-direction: column;
  /* Ensure the page entry animation centers the scale effect nicely */
  transform-origin: center center;
}

.showcase-slider {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.showcase-slide {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  outline: none !important;
  overflow: hidden; /* prevent scale(1.05) from bleeding past edges */
  background: #000;
  -webkit-tap-highlight-color: transparent;
}

/* ─── 从右到左 拉开特效 (Wipe from right to left) ─── */
.slide-enter-active,
.slide-leave-active {
  transition: clip-path 1.2s cubic-bezier(0.77, 0, 0.175, 1), transform 1.2s cubic-bezier(0.77, 0, 0.175, 1);
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  z-index: 10;
}
.slide-leave-active {
  z-index: 5;
}

.slide-enter-from {
  clip-path: inset(0 0 0 100%); /* Masked out moving towards full */
  transform: translateX(40px);
}
.slide-enter-to {
  clip-path: inset(0 0 0 0%);
  transform: translateX(0);
}
.slide-leave-from {
  clip-path: inset(0 0 0 0%);
  transform: translateX(0);
}
.slide-leave-to {
  clip-path: inset(0 100% 0 0); /* Wipe out away to the left */
  transform: translateX(-40px);
}

.showcase-slide img,
.showcase-slide video {
  width: 100%;
  height: 100%;
  object-fit: fill; /* 强制拉伸铺满，消除任何边缘间隙 */
  transform: scale(1.02); /* 微量放大，确保完全覆盖边缘 */
  outline: none !important;
  -webkit-tap-highlight-color: transparent;
}

.slide-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  /* Removed inset box-shadow that was causing blue edge artifacts */
}

/* 左右切换箭头 */
.nav-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 30;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.3s;
}

.nav-arrow:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  backdrop-filter: blur(4px);
}

.arrow-icon {
  font-size: 32px;
  font-weight: 300;
}

.left-arrow {
  left: 20px;
}

.right-arrow {
  right: 20px;
}

.showcase-info {
  position: absolute;
  bottom: 60px;
  left: 5%;
  font-size: 14px;
  font-family: inherit;
  display: flex;
  align-items: center;
  z-index: 20;
  opacity: 0.9;
  letter-spacing: 1px;
}

.showcase-info .type-text {
  font-weight: 500;
  letter-spacing: 1px;
}

/* ─── Emulate the UI of many dots timeline ─── */
.showcase-dots {
  position: absolute;
  bottom: 25px;
  left: 5%;
  width: 90%;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 20;
}

.showcase-dots::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  height: 1px;
  background: rgba(255, 255, 255, 0.3);
  z-index: -1;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  position: relative;
  transition: all 0.3s;
  box-shadow: 0 0 0 4px rgba(0,0,0,0); /* Hit area expansion */
}

.dot:hover {
  background: rgba(255, 255, 255, 1);
  transform: scale(1.8);
}

.dot.active {
  background: #fff;
  transform: scale(1.8);
}
</style>
