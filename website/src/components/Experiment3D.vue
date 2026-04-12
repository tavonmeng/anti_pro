<template>
  <div class="experiment-modal" ref="modalRef" @wheel.prevent="onWheel">
    <!-- Close Button -->
    <div class="close-btn" @click="$emit('close')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
      <span>Back</span>
    </div>

    <!-- Scroll Progress Indicator -->
    <div class="progress-bar">
      <div class="progress-fill" :style="{ height: progressPercent + '%' }"></div>
    </div>

    <!-- Title Overlay -->
    <div class="title-overlay" ref="titleRef">
      <h1>Infinite Dimension</h1>
      <p>Scroll to explore the depth ↓</p>
    </div>

    <!-- The camera viewport -->
    <div class="camera-viewport">

      <!-- Layer 1: Front -->
      <div class="tunnel-layer" ref="layer1Ref">
        <div class="grid-layout">
          <!-- Row 1: span1 + span2 + span1 = 4 -->
          <div class="grid-item span-1" @click="openLightbox('/pic/20a69413b2033fc4dabeca13a8fdfab9.jpg', 'December · Aethel Unit')">
            <img src="/pic/20a69413b2033fc4dabeca13a8fdfab9.jpg" alt="" />
            <span class="img-label">December · Aethel Unit</span>
          </div>
          <div class="grid-item span-2" @click="openLightbox('/pic/42ba05238c238a52ae5653ad2fb32027.jpg', 'July · Pressure Suit')">
            <img src="/pic/42ba05238c238a52ae5653ad2fb32027.jpg" alt="" />
            <span class="img-label">July · Pressure Suit</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/7aa43a1533cec10c05e9f80e34c5e292.jpg', 'March · Cybertron')">
            <img src="/pic/7aa43a1533cec10c05e9f80e34c5e292.jpg" alt="" />
            <span class="img-label">March · Cybertron</span>
          </div>
          <!-- Row 2: span2 + span1 + span1 = 4 -->
          <div class="grid-item span-2" @click="openLightbox('/pic/7e456b2c4d4a127bab98aac2fc36b1d9.jpg', 'August · Desert Scout')">
            <img src="/pic/7e456b2c4d4a127bab98aac2fc36b1d9.jpg" alt="" />
            <span class="img-label">August · Desert Scout</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/969382b6ee1d410cd38e86c61c909596.jpg', 'February · Terminate')">
            <img src="/pic/969382b6ee1d410cd38e86c61c909596.jpg" alt="" />
            <span class="img-label">February · Terminate</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/be6db41b4a3679f16c1f0e9b987d8b40.jpg', 'May · Explorer')">
            <img src="/pic/be6db41b4a3679f16c1f0e9b987d8b40.jpg" alt="" />
            <span class="img-label">May · Explorer</span>
          </div>
        </div>
      </div>

      <!-- Layer 2: Mid -->
      <div class="tunnel-layer" ref="layer2Ref">
        <div class="grid-layout">
          <!-- Row 1: span1 + span1 + span2 = 4 -->
          <div class="grid-item span-1" @click="openLightbox('/pic/c67ec27b4eec4e1a786af8aac51ace74.jpg', 'January · Pilot')">
            <img src="/pic/c67ec27b4eec4e1a786af8aac51ace74.jpg" alt="" />
            <span class="img-label">January · Pilot</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/c73653708752c3501a8fa2f4c63567e4.jpg', 'April · Mech Unit')">
            <img src="/pic/c73653708752c3501a8fa2f4c63567e4.jpg" alt="" />
            <span class="img-label">April · Mech Unit</span>
          </div>
          <div class="grid-item span-2" @click="openLightbox('/pic/d9e70ccc770aea92c3e8aaa4f5b2e400.jpg', 'September · Outpost')">
            <img src="/pic/d9e70ccc770aea92c3e8aaa4f5b2e400.jpg" alt="" />
            <span class="img-label">September · Outpost</span>
          </div>
          <!-- Row 2: span1 + span2 + span1 = 4 -->
          <div class="grid-item span-1" @click="openLightbox('/pic/e3eb318b75ae146c5caad4eb93e9f9d6.jpg', 'June · Wanderer')">
            <img src="/pic/e3eb318b75ae146c5caad4eb93e9f9d6.jpg" alt="" />
            <span class="img-label">June · Wanderer</span>
          </div>
          <div class="grid-item span-2" @click="openLightbox('/pic/20a69413b2033fc4dabeca13a8fdfab9.jpg', 'October · Forge')">
            <img src="/pic/20a69413b2033fc4dabeca13a8fdfab9.jpg" alt="" />
            <span class="img-label">October · Forge</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/42ba05238c238a52ae5653ad2fb32027.jpg', 'November · Basin')">
            <img src="/pic/42ba05238c238a52ae5653ad2fb32027.jpg" alt="" />
            <span class="img-label">November · Basin</span>
          </div>
        </div>
      </div>

      <!-- Layer 3: Back -->
      <div class="tunnel-layer" ref="layer3Ref">
        <div class="grid-layout">
          <!-- Row 1: span2 + span1 + span1 = 4 -->
          <div class="grid-item span-2" @click="openLightbox('/pic/969382b6ee1d410cd38e86c61c909596.jpg', 'February · Train')">
            <img src="/pic/969382b6ee1d410cd38e86c61c909596.jpg" alt="" />
            <span class="img-label">February · Train</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/be6db41b4a3679f16c1f0e9b987d8b40.jpg', 'August · Guardian')">
            <img src="/pic/be6db41b4a3679f16c1f0e9b987d8b40.jpg" alt="" />
            <span class="img-label">August · Guardian</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/7e456b2c4d4a127bab98aac2fc36b1d9.jpg', 'March · Override')">
            <img src="/pic/7e456b2c4d4a127bab98aac2fc36b1d9.jpg" alt="" />
            <span class="img-label">March · Override</span>
          </div>
          <!-- Row 2: span1 + span1 + span2 = 4 -->
          <div class="grid-item span-1" @click="openLightbox('/pic/c73653708752c3501a8fa2f4c63567e4.jpg', 'July · Sentinel')">
            <img src="/pic/c73653708752c3501a8fa2f4c63567e4.jpg" alt="" />
            <span class="img-label">July · Sentinel</span>
          </div>
          <div class="grid-item span-1" @click="openLightbox('/pic/e3eb318b75ae146c5caad4eb93e9f9d6.jpg', 'April · Horizon')">
            <img src="/pic/e3eb318b75ae146c5caad4eb93e9f9d6.jpg" alt="" />
            <span class="img-label">April · Horizon</span>
          </div>
          <div class="grid-item span-2" @click="openLightbox('/pic/c67ec27b4eec4e1a786af8aac51ace74.jpg', 'December · Station')">
            <img src="/pic/c67ec27b4eec4e1a786af8aac51ace74.jpg" alt="" />
            <span class="img-label">December · Station</span>
          </div>
        </div>
      </div>

      <!-- Final Text Layer -->
      <div class="tunnel-layer final-layer" ref="finalLayerRef">
        <h2 class="final-text">THE END OF TUNNEL</h2>
      </div>
    </div>

    <!-- Lightbox Overlay -->
    <Transition name="lightbox">
      <div v-if="lightboxOpen" class="lightbox-overlay" @click="closeLightbox" @wheel.prevent.stop>
        <div class="lightbox-close" @click.stop="closeLightbox">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </div>
        <div class="lightbox-content" @click.stop="closeLightbox">
          <img :src="lightboxSrc" :alt="lightboxLabel" />
          <p class="lightbox-label">{{ lightboxLabel }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'

const emit = defineEmits(['close'])

const modalRef = ref(null)
const layer1Ref = ref(null)
const layer2Ref = ref(null)
const layer3Ref = ref(null)
const finalLayerRef = ref(null)
const titleRef = ref(null)

// Virtual scroll progress: 0 → 1
const progress = ref(0)
const progressPercent = computed(() => Math.round(progress.value * 100))

// Lightbox state
const lightboxOpen = ref(false)
const lightboxSrc = ref('')
const lightboxLabel = ref('')

function openLightbox(src, label) {
  lightboxSrc.value = src
  lightboxLabel.value = label
  lightboxOpen.value = true
}

function closeLightbox() {
  lightboxOpen.value = false
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    if (lightboxOpen.value) {
      closeLightbox()
    } else {
      emit('close')
    }
  }
}

// Sensitivity
const SCROLL_SENSITIVITY = 0.0006

function onWheel(e) {
  if (lightboxOpen.value) return
  const delta = e.deltaY * SCROLL_SENSITIVITY
  progress.value = Math.max(0, Math.min(1, progress.value + delta))
  applyProgress(progress.value)
}

function applyProgress(p) {
  // --- Title ---
  const titleFade = gsap.utils.clamp(0, 1, 1 - p * 10)
  gsap.set(titleRef.value, { opacity: titleFade, scale: 1 + p * 1.5, yPercent: -p * 60 })

  // --- Layer 1 (exits upward) ---
  const exit1 = gsap.utils.clamp(0, 1, p / 0.35)
  gsap.set(layer1Ref.value, {
    scale: 1 + exit1 * 1.8,
    yPercent: -exit1 * 50,
    opacity: 1 - exit1,
    zIndex: 12,
    visibility: exit1 >= 1 ? 'hidden' : 'visible',
  })

  // --- Layer 2 (enters from below, then exits upward) ---
  const enter2 = gsap.utils.clamp(0, 1, (p - 0.20) / 0.15)
  const exit2 = gsap.utils.clamp(0, 1, (p - 0.35) / 0.33)
  const scale2 = gsap.utils.interpolate(0.5, 1, enter2) * (1 + exit2 * 1.8)
  const y2 = gsap.utils.interpolate(50, 0, enter2) + (exit2 * -50)
  const opacity2 = enter2 * (1 - exit2)
  gsap.set(layer2Ref.value, {
    scale: scale2,
    yPercent: y2,
    opacity: gsap.utils.clamp(0, 1, opacity2),
    zIndex: 11,
    visibility: (enter2 <= 0 || exit2 >= 1) ? 'hidden' : 'visible',
  })

  // --- Layer 3 (enters from below, then exits upward) ---
  const enter3 = gsap.utils.clamp(0, 1, (p - 0.52) / 0.15)
  const exit3 = gsap.utils.clamp(0, 1, (p - 0.68) / 0.32)
  const scale3 = gsap.utils.interpolate(0.5, 1, enter3) * (1 + exit3 * 1.8)
  const y3 = gsap.utils.interpolate(50, 0, enter3) + (exit3 * -50)
  const opacity3 = enter3 * (1 - exit3)
  gsap.set(layer3Ref.value, {
    scale: scale3,
    yPercent: y3,
    opacity: gsap.utils.clamp(0, 1, opacity3),
    zIndex: 10,
    visibility: (enter3 <= 0 || exit3 >= 1) ? 'hidden' : 'visible',
  })

  // --- Final Layer ---
  const pf = gsap.utils.clamp(0, 1, (p - 0.80) / 0.20)
  gsap.set(finalLayerRef.value, {
    scale: gsap.utils.interpolate(0.15, 1, pf),
    yPercent: gsap.utils.interpolate(60, 0, pf),
    opacity: pf,
    zIndex: 9,
    visibility: pf <= 0 ? 'hidden' : 'visible',
  })
}

onMounted(() => {
  applyProgress(0)
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.experiment-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  background-color: #050505;
  color: #fff;
  font-family: 'Inter', sans-serif;
  overflow: hidden;
  cursor: ns-resize;
}

.camera-viewport {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.tunnel-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  will-change: transform, opacity;
  transform-origin: center bottom;
}

/* ====== Grid Layout ====== */
.grid-layout {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: 1fr 1fr;
  gap: 6px;
  padding: 6px;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  background: #050505;
}

.grid-item {
  position: relative;
  overflow: hidden;
  border-radius: 6px;
  background: #111;
  cursor: pointer;
  transition: filter 0.3s ease;
}

.grid-item:hover {
  filter: brightness(1.15);
}

.grid-item.span-1 {
  grid-column: span 1;
}

.grid-item.span-2 {
  grid-column: span 2;
}

.grid-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}

.grid-item:hover img {
  transform: scale(1.05);
}

/* Small label at the bottom of each image */
.img-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 10px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: rgba(255, 255, 255, 0.75);
  background: linear-gradient(transparent, rgba(0,0,0,0.5));
  pointer-events: none;
}

/* ====== Close Button ====== */
.close-btn {
  position: fixed;
  top: 32px;
  left: 32px;
  z-index: 100000;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  opacity: 0.6;
  transition: opacity 0.2s;
  color: #fff;
}

.close-btn:hover {
  opacity: 1;
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

/* ====== Progress Indicator ====== */
.progress-bar {
  position: fixed;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100000;
  width: 3px;
  height: 120px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  width: 100%;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 2px;
  transition: height 0.15s ease-out;
}

/* ====== Title Overlay ====== */
.title-overlay {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 10001;
  pointer-events: none;
}

.title-overlay h1 {
  font-size: clamp(32px, 5vw, 72px);
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 0 0 12px;
  text-transform: uppercase;
  text-shadow: 0 4px 40px rgba(0, 0, 0, 0.6);
}

.title-overlay p {
  font-size: 16px;
  opacity: 0.5;
  letter-spacing: 0.1em;
}

/* ====== Final Layer ====== */
.final-layer {
  display: flex;
  justify-content: center;
  align-items: center;
}

.final-text {
  font-size: clamp(28px, 6vw, 80px);
  font-weight: 900;
  background: linear-gradient(135deg, #fff 0%, #666 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ====== Lightbox ====== */
.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 200000;
  background: rgba(0, 0, 0, 0.88);
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.lightbox-close {
  position: absolute;
  top: 32px;
  right: 32px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s;
  color: #fff;
}

.lightbox-close:hover {
  opacity: 1;
}

.lightbox-close svg {
  width: 28px;
  height: 28px;
}

.lightbox-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  max-width: 82vw;
  max-height: 88vh;
  cursor: pointer;
}

.lightbox-content img {
  max-width: 82vw;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 10px;
  box-shadow: 0 20px 80px rgba(0, 0, 0, 0.6);
}

.lightbox-label {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.65);
}

/* Lightbox transition */
.lightbox-enter-active {
  transition: opacity 0.3s ease;
}
.lightbox-leave-active {
  transition: opacity 0.25s ease;
}
.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}
</style>
