<template>
  <div class="experiment-modal" @wheel.prevent="onWheel">
    <!-- Close Button -->
    <div class="close-btn" @click="$emit('close')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
      <span>Back</span>
    </div>

    <!-- Scroll container -->
    <div class="scroll-container" ref="scrollContainerRef">
      <!-- Intro -->
      <section class="section-intro">
        <h1>Unique Video 案例展示</h1>
        <p>Scroll to explore</p>
      </section>

      <!-- Projects grid -->
      <section class="projects" ref="sectionRef">
        <div
          v-for="(row, rowIndex) in rowsData"
          :key="rowIndex"
          class="projects-row"
          :ref="el => { if (el) rowEls[rowIndex] = el }"
        >
          <div
            v-for="(item, colIndex) in row"
            :key="colIndex"
            class="project"
            @click="openLightbox(item.src, item.label)"
          >
            <div class="project-img">
              <img :src="item.src" :alt="item.label" />
            </div>
            <div class="project-info">
              <p>{{ item.name }}</p>
              <p>{{ item.year }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Outro -->
      <section class="section-outro">
        <h2>THE END OF TUNNEL</h2>
      </section>
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
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import gsap from 'gsap'

const emit = defineEmits(['close'])

// ======= Refs =======
const scrollContainerRef = ref(null)
const sectionRef = ref(null)
const rowEls = reactive({})

// ======= Constants (same as reference) =======
const PROJECTS_PER_ROW = 9
const TOTAL_ROWS = 10
const ROW_START_WIDTH = 125  // %
const ROW_END_WIDTH = 500    // %

// ======= Image data =======
const pics = [
  { src: '/pic/20a69413b2033fc4dabeca13a8fdfab9.jpg', name: 'Aethel Unit', year: '2024' },
  { src: '/pic/42ba05238c238a52ae5653ad2fb32027.jpg', name: 'Pressure Suit', year: '2023' },
  { src: '/pic/7aa43a1533cec10c05e9f80e34c5e292.jpg', name: 'Cybertron', year: '2024' },
  { src: '/pic/7e456b2c4d4a127bab98aac2fc36b1d9.jpg', name: 'Desert Scout', year: '2022' },
  { src: '/pic/969382b6ee1d410cd38e86c61c909596.jpg', name: 'Terminate', year: '2023' },
  { src: '/pic/be6db41b4a3679f16c1f0e9b987d8b40.jpg', name: 'Explorer', year: '2024' },
  { src: '/pic/c67ec27b4eec4e1a786af8aac51ace74.jpg', name: 'Pilot', year: '2023' },
  { src: '/pic/c73653708752c3501a8fa2f4c63567e4.jpg', name: 'Mech Unit', year: '2022' },
  { src: '/pic/d9e70ccc770aea92c3e8aaa4f5b2e400.jpg', name: 'Outpost', year: '2024' },
  { src: '/pic/e3eb318b75ae146c5caad4eb93e9f9d6.jpg', name: 'Wanderer', year: '2023' },
]

// Build row data (cycle through images, same as reference)
const rowsData = []
let idx = 0
for (let r = 0; r < TOTAL_ROWS; r++) {
  const row = []
  for (let c = 0; c < PROJECTS_PER_ROW; c++) {
    const p = pics[idx % pics.length]
    row.push({
      src: p.src,
      name: p.name,
      year: p.year,
      label: `${p.name} · ${p.year}`,
    })
    idx++
  }
  rowsData.push(row)
}

// ======= Lightbox =======
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
    if (lightboxOpen.value) closeLightbox()
    else emit('close')
  }
}

// ======= Smooth scroll engine (replaces Lenis) =======
let targetScroll = 0
let currentScroll = 0
const LERP = 0.075  // lower = smoother/slower , higher = snappier

function onWheel(e) {
  if (lightboxOpen.value) return
  const container = scrollContainerRef.value
  if (!container) return
  targetScroll += e.deltaY
  const maxScroll = container.scrollHeight - container.clientHeight
  targetScroll = Math.max(0, Math.min(targetScroll, maxScroll))
}

// ======= Per-frame update =======
let tickerFn = null

onMounted(async () => {
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', onKeydown)

  await nextTick()

  const container = scrollContainerRef.value
  const section = sectionRef.current || sectionRef.value
  if (!container || !section) return

  const rows = []
  for (let i = 0; i < TOTAL_ROWS; i++) {
    if (rowEls[i]) rows.push(rowEls[i])
  }
  if (!rows.length) return

  // Pre-calculate expanded section height (same as reference, lines 28-44)
  const firstRow = rows[0]
  firstRow.style.width = `${ROW_END_WIDTH}%`
  const expandedRowHeight = firstRow.offsetHeight
  firstRow.style.width = ''

  const sectionGap = parseFloat(getComputedStyle(section).gap) || 0
  const sectionPadding = parseFloat(getComputedStyle(section).paddingTop) || 0
  const expandedSectionHeight =
    expandedRowHeight * rows.length +
    sectionGap * (rows.length - 1) +
    sectionPadding * 2

  section.style.height = `${expandedSectionHeight}px`

  // Main update loop (runs every frame via gsap.ticker)
  function onTick() {
    // 1. Smooth scroll interpolation (this is what Lenis does)
    currentScroll += (targetScroll - currentScroll) * LERP

    // Snap to target when close enough to avoid infinite micro-updates
    if (Math.abs(targetScroll - currentScroll) < 0.5) {
      currentScroll = targetScroll
    }

    // 2. Apply scroll position
    container.scrollTop = currentScroll

    // 3. Update each row's width based on its scroll progress (reference lines 46-69)
    const scrollY = currentScroll
    const viewportHeight = container.clientHeight
    const containerRect = container.getBoundingClientRect()

    rows.forEach((row) => {
      const rect = row.getBoundingClientRect()

      const rowTop = rect.top - containerRect.top + scrollY
      const rowBottom = rowTop + rect.height

      const scrollStart = rowTop - viewportHeight
      const scrollEnd = rowBottom

      let progress = (scrollY - scrollStart) / (scrollEnd - scrollStart)
      progress = Math.max(0, Math.min(1, progress))

      const width =
        ROW_START_WIDTH +
        (ROW_END_WIDTH - ROW_START_WIDTH) * progress

      row.style.width = `${width}%`
    })
  }

  tickerFn = onTick
  gsap.ticker.add(onTick)
  gsap.ticker.lagSmoothing(0) // Critical: same as reference (line 18)
})

onUnmounted(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKeydown)
  if (tickerFn) gsap.ticker.remove(tickerFn)
})
</script>

<style scoped>
/* ====== Modal Shell ====== */
.experiment-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  background-color: #f5f3ef;
  color: #111;
  font-family: 'Inter', 'PP Neue Montreal', sans-serif;
  overflow: hidden;
}

.scroll-container {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  /* Hide scrollbar for cleaner look */
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scroll-container::-webkit-scrollbar {
  display: none;
}

/* ====== Intro & Outro ====== */
.section-intro {
  position: relative;
  width: 100%;
  height: 50vh; /* Reduced from 100vh so first row is visible by default */
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding-top: 15vh; /* Moves title upwards */
  align-items: center;
  overflow: hidden;
}

.section-outro {
  position: relative;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.section-intro h1 {
  font-size: clamp(32px, 6vw, 80px);
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: -0.02em;
  color: #111;
}

.section-intro p {
  margin-top: 12px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #888;
}

.section-outro h2 {
  font-size: clamp(24px, 5vw, 64px);
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: linear-gradient(135deg, #111, #888);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* ====== Projects Section (same as reference globals.css) ====== */
.projects {
  position: relative;
  width: 100%;
  padding: 0.5rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
}

.projects-row {
  width: 125%;
  display: flex;
  gap: 1rem;
}

.project {
  flex: 1;
  aspect-ratio: 7 / 5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  cursor: pointer;
}

.project-img {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 6px;
  background: #ddd;
}

.project-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}

.project:hover .project-img img {
  transform: scale(1.04);
}

.project-info {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
}

.project-info p {
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: -0.02rem;
  line-height: 1;
  color: #555;
}

/* ====== Close Button ====== */
.close-btn {
  position: fixed;
  top: 28px;
  left: 28px;
  z-index: 100000;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  opacity: 0.5;
  transition: opacity 0.2s;
  color: #222;
}

.close-btn:hover {
  opacity: 1;
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

/* ====== Lightbox ====== */
.lightbox-overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  z-index: 200000;
  background: rgba(0, 0, 0, 0.88);
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.lightbox-close {
  position: absolute;
  top: 28px; right: 28px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s;
  color: #fff;
}

.lightbox-close:hover { opacity: 1; }

.lightbox-close svg {
  width: 28px; height: 28px;
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
  border-radius: 8px;
  box-shadow: 0 16px 60px rgba(0, 0, 0, 0.5);
}

.lightbox-label {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: rgba(255, 255, 255, 0.6);
}

/* Lightbox transition */
.lightbox-enter-active { transition: opacity 0.3s ease; }
.lightbox-leave-active { transition: opacity 0.2s ease; }
.lightbox-enter-from, .lightbox-leave-to { opacity: 0; }
</style>
