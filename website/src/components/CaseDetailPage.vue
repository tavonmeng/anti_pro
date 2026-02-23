<template>
  <div class="case-detail-page" ref="pageRef">
    <!-- Removed Back Button, using custom footer/header if needed -->

    <div class="scroll-container">
      
      <!-- Section 1: Header -->
      <section class="case-header">
        <div class="header-left">
          <h1 class="project-title">{{ mainTitle }}</h1>
        </div>
        <div class="header-right">
          <div class="meta-line"></div>
          <div class="meta-info">
            <span class="meta-item">项目类型：{{ typeStr }}</span>
            <span class="meta-item">客户：{{ clientStr }}</span>
            <span class="meta-item">上线时间：{{ yearStr }}</span>
          </div>
        </div>
      </section>

      <!-- Section 2: Video -->
      <section class="video-section" 
        @mousemove="onMouseMove" 
        @mouseenter="showCursor = true" 
        @mouseleave="showCursor = false"
        @click="toggleVideo"
      >
        <video 
          ref="videoRef"
          class="hero-video"
          :src="caseData.video" 
          muted 
          loop 
          playsinline
        ></video>
        <!-- Custom Play Cursor -->
        <div class="custom-play-cursor" 
          v-if="showCursor"
          :class="{ 'playing': isPlaying }"
          :style="{ transform: `translate(${mouseX}px, ${mouseY}px)` }"
        >
          {{ isPlaying ? '暂停' : '播放' }}
        </div>
      </section>

      <!-- Section 3: Details Content -->
      <section class="content-section">
        
        <!-- Top part: Text & Image 1 on left, Image 2 on right -->
        <div class="detail-top-grid">
          <div class="top-left-col">
            <h2 class="section-title">{{ mainTitle }}</h2>
            <p class="section-desc">
              {{ caseData.detail?.narrative || '蛇在东方文化中象征智慧与重生，本项目以数字艺术重构蛇的意象，通过流畅的动态轨迹、冷色调与金属质感的结合，剥离其传统恐怖色彩，赋予神秘与神圣并存的视觉表达。传递出数字艺术的共情性与叙事深度。' }}
            </p>
            <div class="img-wrapper img-left" v-if="gallery[0]">
              <img :src="gallery[0]" alt="Image 1" />
            </div>
          </div>
          
          <div class="top-right-col">
            <div class="img-wrapper img-right" v-if="gallery[1]">
              <img :src="gallery[1]" alt="Image 2" />
            </div>
          </div>
        </div>

        <!-- Stats Section -->
        <div class="stats-container">
          <div class="stats-header-line">
            <span class="stats-label">传播效应 <span class="arrow-left">←</span></span>
          </div>
          <div class="stats-line-divider"></div>
          
          <div class="stats-content">
            <div class="stats-row-main">
              <div class="stat-block">
                <span class="small-txt">上线仅在</span>
                <span class="big-txt">{{ durationNum }}</span>
                <span class="small-txt">日内</span>
              </div>
              <div class="stat-block">
                <span class="small-txt">累计流量</span>
                <span class="big-txt">{{ trafficNum }}</span>
                <span class="small-txt">亿+</span>
              </div>
            </div>
            
            <div class="stats-row-sub">
              <span class="rank-item" v-for="(rank, idx) in rankings" :key="idx">
                {{ rank }}
              </span>
            </div>
            
            <div class="stats-paragraph hover-target">
              致敬快速迭代的新媒体时代，本项目以“融媒体”为叙事场景，构建一条穿梭于二维与三维之间的数字巨蛇。
              <br><br>
              巨蛇在信息、图像、数据、影像的交融中不断演变形态，展示出媒介裂变中的动态生命力。融媒体时代，我们不再只是观众，而是沉浸其中的体验者。在信息交错与重塑的过程中，感受数字化叙事带来的商业吸引力与品牌价值升维。
            </div>
          </div>
        </div>

        <!-- Two Images Row -->
        <div class="twin-images-row" v-if="gallery[2] || gallery[3]">
          <div class="img-wrapper twin-img">
            <img :src="gallery[2]" v-if="gallery[2]" alt="Image 3" />
          </div>
          <div class="img-wrapper twin-img right-twin">
            <img :src="gallery[3]" v-if="gallery[3]" alt="Image 4" />
          </div>
        </div>

        <!-- Bottom Image -->
        <div class="single-image-row" v-if="gallery[4]">
          <img :src="gallery[4]" alt="Image 5" />
        </div>
      </section>

      <!-- Section 4: Contact Us -->
      <ContactSection />
      
      <TheFooter />

    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import gsap from 'gsap'
import ContactSection from '../sections/ContactSection.vue'
import TheFooter from '../sections/TheFooter.vue'

const props = defineProps({
  caseData: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])
const pageRef = ref(null)

// Video states
const videoRef = ref(null)
const showCursor = ref(false)
const isPlaying = ref(false)
const mouseX = ref(0)
const mouseY = ref(0)

const onMouseMove = (e) => {
  const rect = e.currentTarget.getBoundingClientRect()
  mouseX.value = e.clientX - rect.left
  mouseY.value = e.clientY - rect.top
}

const toggleVideo = () => {
  if (videoRef.value) {
    if (videoRef.value.paused) {
      videoRef.value.play()
      isPlaying.value = true
    } else {
      videoRef.value.pause()
      isPlaying.value = false
    }
  }
}

const handleBack = () => {
  emit('close')
}

// Data Parsing
const mainTitle = computed(() => {
  if (!props.caseData.title) return ''
  return props.caseData.title.split(' / ')[0].replace('·', '').trim()
})

const typeStr = computed(() => props.caseData.detail?.type || '裸眼3D')
const clientStr = computed(() => props.caseData.detail?.client || '未知客户')
const yearStr = computed(() => props.caseData.detail?.year || '2025')

const gallery = computed(() => props.caseData.detail?.gallery || [])

const durationNum = computed(() => {
  return props.caseData.detail?.metrics?.duration?.replace(/[^0-9]/g, '') || '15'
})

const trafficNum = computed(() => {
  return props.caseData.detail?.metrics?.traffic?.replace(/[^0-9]/g, '') || '10'
})

const rankings = computed(() => {
  let list = props.caseData.detail?.metrics?.rankings || []
  if (list.length === 0) list = ['抖音同城热搜', '成都本地榜', '全国热度榜']
  return list.map((r, i) => `NO.${i+1}-${r}`)
})

onMounted(() => {
  gsap.fromTo(pageRef.value, 
    { x: '100%' },
    { x: '0%', duration: 0.8, ease: 'power3.out' }
  )
})
</script>

<style scoped>
.case-detail-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  background: #fff;
  z-index: 5000;
  overflow-y: auto;
  overflow-x: hidden;
}


/* HEADER */
.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 80px 5% 40px;
  background: #fff;
}
.header-left {
  flex: 1;
}
.project-title {
  font-size: 5rem;
  font-weight: 300;
  color: #000;
  margin: 0;
  line-height: 1;
}
.header-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-bottom: 5px;
}
.meta-line {
  height: 1px;
  background: #000;
  width: 100%;
  margin-bottom: 15px;
}
.meta-info {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #666;
}

/* VIDEO */
.video-section {
  position: relative;
  width: 100%;
  height: 80vh;
  background: #000;
  cursor: none; /* hide native cursor */
  overflow: hidden;
}
.hero-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.custom-play-cursor {
  position: absolute;
  top: 0; left: 0;
  width: 80px; height: 80px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  pointer-events: none;
  border: 1px solid rgba(255,255,255,0.3);
  backdrop-filter: blur(4px);
  margin-top: -40px;
  margin-left: -40px;
  z-index: 10;
  transition: opacity 0.3s ease;
}
.custom-play-cursor.playing {
  opacity: 0.5;
}

/* DETAILS CONTENT */
.content-section {
  background: #fff;
  padding: 40px 5% calc(80px + 15vh);
  color: #000;
}
.detail-top-grid {
  display: flex;
  justify-content: space-between;
  margin-bottom: 40px;
}
.top-left-col {
  flex: 5.5;
  padding-right: 40px;
}
.section-title {
  font-size: 3rem;
  font-weight: 300;
  margin-bottom: 20px;
}
.section-desc {
  font-size: 14px;
  color: #333;
  line-height: 1.8;
  margin-bottom: 40px;
  max-width: 600px;
}
.img-left {
  width: 100%;
}
.top-right-col {
  flex: 4.5;
}
.img-right {
  width: 100%;
}

.img-wrapper {
  position: relative;
  overflow: hidden;
  cursor: pointer;
}
.img-wrapper img {
  width: 100%;
  display: block;
  transition: transform 0.8s ease;
}
.img-wrapper:hover img {
  transform: scale(1.03);
}

/* STATS */
.stats-container {
  margin-top: 60px;
  margin-bottom: 60px;
}
.stats-header-line {
  text-align: right;
  margin-bottom: 10px;
  margin-left: 15%;
  margin-right: 15%;
}
.stats-label {
  font-size: 16px;
  color: #000;
}
.stats-line-divider {
  height: 1px;
  background: #000;
  width: 100%;
  margin-bottom: 30px;
}

.stats-row-main {
  display: flex;
  gap: 60px;
  margin-bottom: 20px;
  margin-left: 15%;
  margin-right: 15%;
}
.stat-block {
  display: flex;
  align-items: baseline;
}
.stat-block .small-txt { 
  font-size: 14px; 
  color: #000; 
}
.stat-block .big-txt { 
  font-size: 2.5rem; 
  font-weight: 300; 
  margin: 0 5px; 
}

.stats-row-sub {
  display: flex;
  gap: 30px;
  margin-bottom: 30px;
  margin-left: 15%;
  margin-right: 15%;
}
.rank-item {
  font-size: 13px;
  color: #000;
  text-transform: uppercase;
}

.stats-paragraph {
  font-size: 13px;
  color: #444;
  line-height: 1.8;
  margin-left: 15%;
  margin-right: 15%;
}

/* TWIN IMAGES */
.twin-images-row {
  display: flex;
  gap: 20px;
  margin-bottom: 40px;
}
.twin-img {
  flex: 1;
}

/* BOTTOM SINGLE IMAGE */
.single-image-row img {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  display: block;
}
/* RESPONSIVE */
@media (max-width: 768px) {
  .case-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .header-right {
    margin-top: 20px;
    width: 100%;
  }
  .project-title { font-size: 3rem; }
  .detail-top-grid { flex-direction: column; }
  .top-left-col { padding-right: 0; margin-bottom: 20px; }
  .twin-images-row { flex-direction: column; }
  .stats-row-main { flex-direction: column; gap: 10px; }
  .stats-row-sub { flex-direction: column; gap: 10px; }
}
</style>
