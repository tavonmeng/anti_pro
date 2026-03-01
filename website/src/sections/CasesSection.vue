<template>
  <section id="cases" class="cases-section" ref="sectionRef">
    <!-- 堆叠状态栏: 处于页面最上方，且随滑动堆叠 -->
    <div class="sticky-headers-stack">
      <div 
        v-for="(item, index) in cases" 
        :key="'sticky-' + item.id"
        class="sticky-header"
        :ref="el => { if (el) headerRefs[index] = el }"
        :style="{ zIndex: 100 + index }"
      >
        <div class="header-inner">
          <div class="case-meta-left">
            <span class="case-id">{{ item.id }}</span>
          </div>
          <div class="case-title-center">
            <h3 class="case-title">{{ item.title }}</h3>
          </div>
          <div class="case-meta-right">
            <span class="case-arrow">↗</span>
          </div>
        </div>
      </div>
    </div>

    <div class="cases-container">
      <div class="cases-stack" ref="stackRef">
        <article 
          v-for="(item, index) in cases" 
          :key="item.id" 
          class="case-item"
          :ref="el => { if (el) itemRefs[index] = el }"
          :style="{ zIndex: index + 1 }"
          @mouseenter="handleMouseEnter(index)"
          @mouseleave="handleMouseLeave(index)"
          @click="emit('open-detail', item)"
        >
          <div class="media-wrapper">
            <video 
              v-if="item.video" 
              muted 
              loop 
              playsinline 
              :src="item.video"
              :poster="item.detail?.gallery?.[0]"
              :ref="el => { if (el) videoRefs[index] = el }"
            ></video>
            <div v-else class="placeholder-image">
              <span>Case {{ item.id }} Image</span>
            </div>
            
            <!-- 案例描述：随着卡片移动 -->
            <div class="case-details">
              <p class="case-desc">{{ item.desc }}</p>
            </div>

            <div class="case-overlay"></div>
            <div class="view-btn-wrapper">
              <span class="view-btn">View Project</span>
            </div>
          </div>
        </article>
      </div>
    </div>

    <!-- 底部进度条 -->
    <div class="cases-progress-container">
      <div class="progress-info">
        <span class="progress-type">{{ currentCaseType }}</span>
        <div class="progress-divider"></div>
        <span class="progress-name">{{ currentCaseTitle }}</span>
      </div>
      <div class="progress-track-wrapper">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: 'calc(25% + ' + (progressPercent * 0.7) + '%)' }"></div>
          <div 
            class="progress-dot cursor-pointer" 
            v-for="(item, i) in cases" 
            :key="'dot-' + i"
            :class="{ active: progressPercent >= (i / (cases.length - 1)) * 100 - 1 }"
            :style="{ left: 'calc(25% + ' + ((i / (cases.length - 1)) * 70) + '%)' }"
            @click.stop="scrollToCase(i)"
          ></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

const emit = defineEmits(['open-detail'])

gsap.registerPlugin(ScrollTrigger)

import { cases } from '../data/cases'

const sectionRef = ref(null)
const stackRef = ref(null)
const itemRefs = ref([])
const videoRefs = ref([])
const headerRefs = ref([])
const timers = ref({})

const progressPercent = ref(0)
const currentCaseIndex = ref(0)
const currentCaseTitle = computed(() => cases[currentCaseIndex.value]?.title || '')
const currentCaseType = computed(() => cases[currentCaseIndex.value]?.detail?.type || cases[currentCaseIndex.value]?.category || '')

let ctx

const scrollToCase = (index) => {
  const st = ScrollTrigger.getById('casesTrigger')
  if (st) {
    const start = st.start
    const end = st.end
    const progressSpan = end - start
    const targetScroll = start + (index / (cases.length - 1)) * progressSpan
    window.scrollTo({ top: targetScroll, behavior: 'smooth' })
  }
}

const handleMouseEnter = (index) => {
  // 清除旧定时器
  if (timers.value[index]) clearTimeout(timers.value[index])
  
  // 设置10秒延迟播放
  timers.value[index] = setTimeout(() => {
    const video = videoRefs.value[index]
    if (video) {
      video.play().catch(e => console.log('Video play failed:', e))
    }
  }, 10000)
}

const handleMouseLeave = (index) => {
  // 鼠标移开立即清除定时器并暂停
  if (timers.value[index]) {
    clearTimeout(timers.value[index])
    delete timers.value[index]
  }
  const video = videoRefs.value[index]
  if (video) {
    video.pause()
  }
}

onMounted(() => {
  ctx = gsap.context(() => {
    const cards = itemRefs.value
    const headers = headerRefs.value
    if (cards.length <= 1) return

    // 设置初始状态 - 使用 force3D
    cards.forEach((card, index) => {
      if (index !== 0) {
        gsap.set(card, { yPercent: 100, force3D: true })
      } else {
        gsap.set(card, { force3D: true })
      }
    })

    headers.forEach((header, index) => {
      if (index === 0) {
        gsap.set(header, { y: 0, opacity: 1, force3D: true })
      } else {
        // 其他标题初始位置在下方
        gsap.set(header, { y: 100, opacity: 0, force3D: true })
      }
    })

    const tl = gsap.timeline({
      scrollTrigger: {
        id: 'casesTrigger',
        trigger: sectionRef.value,
        start: 'top top',
        end: `+=${cards.length * 250}%`, // 极度放大每一个案例需要的物理滚动距离（从 100% 增加到 250%），以稀释触控板的惯性
        pin: true,
        scrub: 1, // 降低滞留感，让反馈更直接
        snap: {
          snapTo: 1 / (cards.length - 1),
          duration: { min: 0.3, max: 0.6 },
          delay: 0.15, // 吸附延迟微微加大，吸收掉触控板滚动结束后的末端惯性
          ease: 'power2.out'
        },
        onUpdate: (self) => {
          progressPercent.value = self.progress * 100
          currentCaseIndex.value = Math.min(
            Math.round(self.progress * (cards.length - 1)),
            cards.length - 1
          )
        }
      }
    })

    // 跨组件检测：当下方Contact页面（关于我们）进入时，将进度条无缝淡出
    setTimeout(() => {
      const contactEl = document.querySelector('.contact-section')
      if (contactEl && ctx) {
        ctx.add(() => {
          ScrollTrigger.create({
            trigger: contactEl,
            start: 'top 95%', // 当关于我们要出现在底边上方时开始隐藏
            end: 'top 65%',   // 滚动此距离后完全隐藏
            scrub: true,
            animation: gsap.to('.cases-progress-container', { opacity: 0, ease: 'none' })
          })
        })
      }
    }, 100)

    cards.forEach((card, index) => {
      if (index === 0) return

      const scrollPos = index - 1

      // 当前卡片滑入
      tl.to(card, {
        yPercent: 0,
        ease: 'none',
        force3D: true
      }, scrollPos)

      // 当前标题滑入并堆叠 (每个标题堆叠高度修减为 20px)
      tl.to(headers[index], {
        y: index * 20,
        opacity: 1,
        ease: 'none',
        force3D: true
      }, scrollPos)

      // 前一个卡片稍微缩小并变暗
      tl.to(cards[index - 1], {
        scale: 0.95,
        opacity: 0.5,
        ease: 'none',
        force3D: true
      }, scrollPos)
      
      // 前一个标题稍微变淡（可选，保持堆叠感）
      tl.to(headers[index - 1], {
        opacity: 0.6,
        ease: 'none',
        force3D: true
      }, scrollPos)
    })

  }, sectionRef.value)
})

onUnmounted(() => {
  if (ctx) ctx.revert()
  // 清除所有定时器
  Object.values(timers.value).forEach(clearTimeout)
})
</script>

<style scoped>
.cases-section {
  background-color: #fff;
  width: 100%;
  position: relative;
}

.sticky-headers-stack {
  position: absolute;
  top: 68px; /* 紧贴菜单栏 */
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 200;
}

.sticky-header {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 20px; /* 标题栏高度更小 */
  padding: 0 5%;
  display: flex;
  align-items: center;
  background: #000; /* 黑底标题栏 */
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  will-change: transform, opacity;
}

.header-inner {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.case-meta-left {
  flex: 1;
  display: flex;
  justify-content: flex-start;
}

.case-title-center {
  flex: 2;
  display: flex;
  justify-content: center;
}

.case-meta-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.case-id {
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  font-size: 10px; /* 更小字体 */
  color: #fff; /* 白字 */
  letter-spacing: 1px;
}

.case-title {
  font-size: 10px; /* 更小字体 */
  font-weight: 500;
  color: #fff; /* 白字 */
  margin: 0;
  letter-spacing: 1px;
}

.case-arrow {
  font-size: 12px;
  color: #fff; /* 白字 */
}

.cases-container {
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.cases-stack {
  position: relative;
  width: 100%;
  height: 100%;
}

.case-item {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  will-change: transform, opacity;
}

.case-details {
  position: absolute;
  bottom: 22%; /* Moved up slightly to make room for progress bar */
  right: 5%;
  max-width: 400px;
  text-align: right;
  z-index: 10;
  pointer-events: none;
}

.case-desc {
  font-size: 14px;
  color: rgba(255,255,255,0.7);
  line-height: 1.8;
  font-weight: 300;
  text-shadow: 0 2px 10px rgba(0,0,0,0.5);
}

.media-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.media-wrapper video,
.media-wrapper .placeholder-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 1.2s cubic-bezier(0.2, 0, 0.2, 1);
  will-change: transform;
}

.case-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(0,0,0,0) 50%, rgba(0,0,0,0.8));
  pointer-events: none;
}

.view-btn-wrapper {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.view-btn {
  padding: 15px 40px;
  border: 1px solid rgba(255,255,255,0.4);
  border-radius: 40px;
  color: #fff;
  font-size: 14px;
  letter-spacing: 2px;
  text-transform: uppercase;
  backdrop-filter: blur(5px);
  background: rgba(255,255,255,0.05);
}

.case-item:hover .media-wrapper video,
.case-item:hover .media-wrapper .placeholder-image {
  transform: scale(1.05);
}

.case-item:hover .view-btn-wrapper {
  opacity: 1;
}

.case-item {
  cursor: pointer; /* Add pointer cursor to indicate clickability */
}

/* Bottom Progress Bar */
.cases-progress-container {
  position: absolute;
  bottom: 30px; /* 距离底边一定间距 */
  left: 0;
  right: 0;
  z-index: 500;
  display: flex;
  flex-direction: column;
  pointer-events: none; /* Make click-through to underlying cards */
}

.progress-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 24px; /* 放在进度条上方 */
  padding-left: 5%; /* 向右缩进到第一段上方 */
  color: #fff;
  font-size: 11px; /* Decreased font size */
  letter-spacing: 1px;
}

.progress-type {
  opacity: 0.6;
  text-transform: uppercase;
}

.progress-divider {
  width: 20px; /* Reduced to match smaller font */
  height: 1px;
  background-color: #fff;
  opacity: 0.7;
  margin: 6px 0;
}

.progress-name {
  font-weight: 500;
  text-transform: uppercase;
}

.progress-track-wrapper {
  width: 100%;
}

.progress-track {
  position: relative;
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.2);
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: #fff;
  transition: width 0.1s linear;
}

.progress-dot {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  transition: background 0.3s ease, transform 0.3s ease;
  pointer-events: auto; /* Allow dots to be clicked */
  cursor: pointer;
}

.progress-dot::after {
  content: '';
  position: absolute;
  top: -10px; left: -10px; right: -10px; bottom: -10px; /* Expand click area */
}

.progress-dot.active {
  background: #fff;
  transform: translate(-50%, -50%) scale(1.4);
}

@media (max-width: 768px) {
  .sticky-header {
    height: 40px;
    padding: 0 20px;
  }
  
  .case-title {
    font-size: 14px;
  }
  
  .case-details {
    bottom: 10%;
    right: 20px;
    left: 20px;
    text-align: left;
  }
}
</style>
