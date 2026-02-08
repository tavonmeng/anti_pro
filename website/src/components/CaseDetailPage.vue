<template>
  <div class="case-detail-page" ref="pageRef">
    <!-- Removed Back Button as requested -->

    <div class="scroll-container">
      <!-- Section 1: Video Hero (Dark) -->
      <section class="hero-section">
        <video 
          class="hero-video"
          :src="caseData.video" 
          autoplay 
          muted 
          loop 
          playsinline
        ></video>
        <div class="hero-overlay"></div>
      </section>

      <!-- Section 2: Detailed Content (Light) -->
      <section class="content-section light-theme">
        <div class="content-wrapper">
          
          <!-- Editorial Header -->
          <div class="editorial-header reveal-item">
            <h1 class="project-title hover-target">{{ caseData.title }}</h1>
            <!-- Removed Creative Badge -->
          </div>

          <!-- Staggered Layout Grid (Compacted) -->
          <div class="editorial-grid">
            
            <!-- Block A: Intro Text -->
            <div class="layout-block align-right reveal-item text-block-main">
              <p class="intro-text">
                {{ caseData.detail?.narrative || '此项目通过数字艺术重构意象，通过流畅的动态轨迹、冷色调与金属质感的结合，剥离其传统恐怖色彩，赋予神秘与神圣并存的视觉表达。' }}
              </p>
            </div>

            <!-- Block B: Hero Image -->
            <div class="layout-block align-left reveal-item large-image-block" v-if="caseData.detail?.gallery?.[0]">
              <div class="image-wrapper hover-target shadow-hover">
                <img :src="caseData.detail.gallery[0]" alt="Featured" />
              </div>
            </div>

            <!-- Block C: Metrics (Tighter spacing) -->
            <div class="layout-block align-center reveal-item metrics-floating">
               <div class="metrics-content">
                 <div class="metric-row">
                   <div class="metric-group">
                     <span class="m-label">上线仅在</span>
                     <span class="m-value">{{ caseData.detail?.metrics?.duration?.replace(/[^0-9]/g, '') || '15' }}</span>
                     <span class="m-unit">日内</span>
                   </div>
                   <div class="metric-divider">/</div>
                   <div class="metric-group">
                     <span class="m-label">累计流量</span>
                     <span class="m-value">{{ caseData.detail?.metrics?.traffic?.replace(/[^0-9]/g, '') || '10' }}</span>
                     <span class="m-unit">亿+</span>
                   </div>
                 </div>
                 <div class="rankings-row">
                   <span v-for="(rank, idx) in caseData.detail?.metrics?.rankings" :key="idx" class="rank-item hover-target">
                     {{ rank }}
                   </span>
                 </div>
               </div>
            </div>

            <!-- Block D: Secondary Image -->
            <div class="layout-block align-right reveal-item portrait-image-block" v-if="caseData.detail?.gallery?.[1]">
               <div class="image-wrapper portrait-ratio hover-target shadow-hover">
                 <img :src="caseData.detail.gallery[1]" alt="Detail 1" />
                 <span class="img-caption">Visual Detail 01</span>
               </div>
            </div>

            <!-- Block E: Narrative Extension -->
            <div class="layout-block align-left reveal-item text-block-secondary">
               <p>
                致敬快速迭代的新媒体时代，本项目以“融媒体”为叙事场景，构建一条穿梭于二维与三维之间的数字巨蛇。
                <br><br>
                巨蛇在信息、图像、数据、影像的交融中不断演变形态，展示出媒介裂变中的动态生命力。融媒体时代，我们不再只是观众，而是沉浸其中的体验者。
              </p>
            </div>

            <!-- Block F: Asymmetrical Grid -->
            <div class="layout-block full-width reveal-item mixed-grid">
               <div class="grid-item item-low hover-target shadow-hover" v-if="caseData.detail?.gallery?.[2]">
                 <img :src="caseData.detail.gallery[2]" alt="Detail 2" />
               </div>
               <div class="grid-item item-high hover-target shadow-hover" v-if="caseData.detail?.gallery?.[3]">
                 <img :src="caseData.detail.gallery[3]" alt="Detail 3" />
               </div>
            </div>

            <!-- Block G: Footer Image -->
             <div class="layout-block full-width reveal-item footer-image-block" v-if="caseData.detail?.gallery?.[4]">
               <div class="image-wrapper hover-target">
                 <img :src="caseData.detail.gallery[4]" alt="Footer Image" />
               </div>
             </div>

          </div>

          <!-- Footer Navigation -->
          <div class="footer-nav reveal-item hover-target" @click="handleBack">
            <span class="nav-arrow">←</span>
            <div class="nav-text">
              <span>返回主页</span>
              <span class="sub">BACK TO HOME</span>
            </div>
          </div>

        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

const props = defineProps({
  caseData: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])
const pageRef = ref(null)

const handleBack = () => {
  emit('close')
}

onMounted(async () => {
  // Page Entry Animation
  gsap.fromTo(pageRef.value, 
    { x: '100%' },
    { x: '0%', duration: 0.8, ease: 'power3.out' }
  )

  await nextTick()

  // Staggered Reveal Animation for Content
  setTimeout(() => {
    const items = pageRef.value.querySelectorAll('.reveal-item')
    items.forEach((item, index) => {
      // Shorter delay for tighter feel
      const delay = index * 0.05
      
      gsap.fromTo(item, 
        { y: 60, opacity: 0 },
        {
          y: 0, 
          opacity: 1,
          duration: 0.8,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: item,
            scroller: pageRef.value,
            start: 'top 95%',
            toggleActions: 'play none none reverse'
          },
          delay: delay
        }
      )
    })
  }, 200)
})

</script>

<style scoped>
.case-detail-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: #fff;
  z-index: 1000;
  overflow-y: auto;
  overflow-x: hidden;
  cursor: none; /* Hide default cursor to use custom one */
}

/* HERO SECTION */
.hero-section {
  height: 100vh;
  width: 100%;
  position: relative;
  background: #000;
  overflow: hidden;
}

.hero-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 60%, rgba(255,255,255,0.05) 100%);
}

/* CONTENT SECTION */
.content-section {
  background: #fff;
  color: #000;
  padding: 60px 5%; /* Even less top padding */
  min-height: 100vh;
}

.content-wrapper {
  max-width: 1200px; /* More compact container */
  margin: 0 auto;
  position: relative;
}

/* Editorial Header */
.editorial-header {
  position: relative;
  margin-bottom: 5vh; /* Reduced more */
  padding-left: 0; /* Align left */
}

.project-title {
  font-size: 7vw; /* Slightly smaller */
  font-weight: 300;
  letter-spacing: -0.01em;
  margin: 0;
  line-height: 1;
  position: relative;
  z-index: 2;
}

/* GRID SYSTEM - Compacted */
.editorial-grid {
  display: flex;
  flex-direction: column;
  gap: 4vh; /* Reduced more */
}

.layout-block {
  width: 100%;
  position: relative;
}

.align-left {
  display: flex;
  justify-content: flex-start;
}

.align-right {
  display: flex;
  justify-content: flex-end;
}

.align-center {
  display: flex;
  justify-content: center;
}

.full-width {
  width: 100%;
}

/* TEXT BLOCKS */
.text-block-main {
  width: 50%; /* Wider */
  margin-left: auto;
  margin-right: 0;
  margin-top: -2vh;
}

.text-block-secondary {
  width: 45%;
  margin-left: 0;
}

.intro-text, .text-block-secondary p {
  font-size: 16px;
  line-height: 1.6; /* Tighter line height */
  color: #444;
  text-align: left;
}

/* IMAGES */
.large-image-block {
  width: 100%; /* Full within container */
}

.image-wrapper {
  width: 100%;
  overflow: hidden;
  position: relative;
}

.shadow-hover {
  box-shadow: 0 0 0 rgba(0,0,0,0);
  transition: box-shadow 0.6s ease;
}

.shadow-hover:hover {
  box-shadow: 0 20px 40px rgba(0,0,0,0.1);
}

.image-wrapper img {
  width: 100%;
  height: auto;
  display: block;
  transition: transform 1.2s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.layout-block:hover .image-wrapper img {
  transform: scale(1.02);
}

.portrait-image-block {
  width: 30%;
  margin-right: 5%;
  margin-top: -6vh; /* Reduced pull up */
}

.portrait-ratio {
  aspect-ratio: 4/5;
}

.portrait-ratio img {
  height: 100%;
  object-fit: cover;
}

.img-caption {
  display: block;
  font-size: 11px;
  color: #aaa;
  margin-top: 6px;
  text-align: right;
  letter-spacing: 1px;
}

.footer-image-block {
  margin-top: 2vh;
}

/* METRICS - Compacted */
.metrics-floating {
  margin: 4vh 0; /* Reduced from 10vh */
}

.metrics-content {
  text-align: center;
}

.metric-row {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 20px;
  margin-bottom: 15px;
}

.metric-group {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.m-value {
  font-size: 60px; /* Slightly smaller for compactness */
  font-weight: 200;
  line-height: 1;
}

.m-unit {
  font-size: 13px;
  color: #888;
  margin-top: 5px;
}

.m-label {
  font-size: 10px;
  color: #bbb;
  letter-spacing: 2px;
  margin-bottom: 5px;
  text-transform: uppercase;
}

.metric-divider {
  font-size: 40px;
  font-weight: 100;
  color: #eee;
}

.rankings-row {
  display: flex;
  justify-content: center;
  gap: 10px;
  font-size: 11px;
  color: #888;
  flex-wrap: wrap;
}

.rank-item {
  padding: 3px 10px;
  border: 1px solid #f0f0f0;
  border-radius: 20px;
  transition: all 0.3s ease;
}

.rank-item:hover {
  background: #000;
  color: #fff;
  border-color: #000;
}

/* MIXED GRID - Compacted */
.mixed-grid {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 15px;
  padding: 0;
}

.grid-item {
  flex: 1;
  overflow: hidden;
}

.item-low {
  margin-bottom: 0;
}

.item-high {
  margin-bottom: 6vh; /* Reduced offset */
}

.grid-item img {
  width: 100%;
  display: block;
  transition: transform 1s ease;
}

.grid-item:hover img {
  transform: scale(1.03);
}

/* FOOTER */
.footer-nav {
  margin-top: 8vh; /* Reduced */
  padding-top: 25px;
  border-top: 1px solid #eee;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.footer-nav:hover {
  transform: translateX(-5px);
}

.nav-arrow {
  font-size: 24px;
  font-weight: 100;
}

.nav-text span {
  font-size: 18px;
  font-weight: 400;
}

.nav-text .sub {
  font-size: 10px;
  color: #bbb;
  letter-spacing: 1px;
}

@media (max-width: 768px) {
  .project-title { font-size: 12vw; }
  .text-block-main, .text-block-secondary, .large-image-block, .portrait-image-block {
    width: 100%;
    margin: 0;
  }
  .editorial-grid { gap: 30px; }
  .mixed-grid { flex-direction: column; gap: 20px; }
  .item-high { margin-bottom: 0; }
  .metric-row { flex-direction: column; gap: 20px; }
  .metric-divider { display: none; }
  .intro-text { text-align: left; }
}
</style>
