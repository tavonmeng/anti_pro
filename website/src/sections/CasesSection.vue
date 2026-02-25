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
  </section>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

const emit = defineEmits(['open-detail'])

gsap.registerPlugin(ScrollTrigger)

const cases = [
  { 
    id: '01', 
    year: '2025', 
    title: '蛇年 · 巨蛇献礼 / Year of the Snake', 
    category: 'Public Art', 
    video: '/video1.mp4',
    detail: {
      type: 'Naked-eye 3D',
      client: 'Taikoo Li',
      year: '2025',
      metrics: {
        duration: '15日内',
        traffic: '10亿+',
        rankings: ['抖音同城榜 Top 1', '成都本地热搜 Top 1', '全国热点榜 No.4']
      },
      narrative: '致敬快速迭代的新媒体时代，本项目以“融媒体”为叙事场景，构建一条穿梭于二维与三维之间的数字巨蛇。巨蛇在信息、图像、数据、影像的交融中不断演变形态，展示出媒介裂变中的动态生命力。',
      gallery: [
        '/cases/case01/f1.png',
        '/cases/case01/f2.png',
        '/cases/case01/f3.png',
        '/cases/case01/f4.png',
        '/cases/case01/f5.png'
      ]
    }
  },
  { 
    id: '02', 
    title: 'DIGITAL SCULPTURE / 数字雕塑', 
    video: '/video2.mp4', 
    desc: '探索三维空间与光影的无限可能。',
    detail: {
      type: '数字艺术',
      client: '未来博物馆',
      year: '2024',
      metrics: {
        duration: '15日内',
        traffic: '10亿+',
        rankings: ['抖音同城榜 Top 1', '成都本地热搜 Top 1', '全国热点榜 No.4']
      },
      narrative: '致敬快速迭代的新媒体时代，本项目以“融媒体”为叙事场景，构建一条穿梭于二维与三维之间的数字巨蛇。巨蛇在信息、图像、数据、影像的交融中不断演变形态，展示出媒介裂变中的动态生命力。',
      gallery: [
        '/cases/case02/f1.png',
        '/cases/case02/f2.png',
        '/cases/case02/f3.png',
        '/cases/case02/f4.png',
        '/cases/case02/f5.png'
      ]
    }
  },
  { 
    id: '03', 
    title: 'URBAN BEAT / 商业综合体视觉', 
    video: '/video3.mp4', 
    desc: '为现代商业空间注入艺术灵魂。',
    detail: {
      type: '商业视觉',
      client: '远洋太古里',
      year: '2024',
      metrics: {
        duration: '15日内',
        traffic: '10亿+',
        rankings: ['抖音同城榜 Top 1', '成都本地热搜 Top 1', '全国热点榜 No.4']
      },
      narrative: '致敬快速迭代的新媒体时代，本项目以“融媒体”为叙事场景，构建一条穿梭于二维与三维之间的数字巨蛇。巨蛇在信息、图像、数据、影像的交融中不断演变形态，展示出媒介裂变中的动态生命力。',
      gallery: [
        '/cases/case03/f1.png',
        '/cases/case03/f2.png',
        '/cases/case03/f3.png',
        '/cases/case03/f4.png',
        '/cases/case03/f5.png'
      ]
    }
  },
  { 
    id: '04', 
    title: 'IMMERSIVE VOID / 沉浸式空灵', 
    video: '/video4.mp4', 
    desc: '打破虚实边界，重构感知体验。',
    detail: {
      type: '沉浸式体验',
      client: '科技艺术周',
      year: '2024',
      metrics: {
        duration: '15日内',
        traffic: '10亿+',
        rankings: ['抖音同城榜 Top 1', '成都本地热搜 Top 1', '全国热点榜 No.4']
      },
      narrative: '致敬快速迭代的新媒体时代，本项目以“融媒体”为叙事场景，构建一条穿梭于二维与三维之间的数字巨蛇。巨蛇在信息、图像、数据、影像的交融中不断演变形态，展示出媒介裂变中的动态生命力。',
      gallery: [
        '/cases/case04/f1.png',
        '/cases/case04/f2.png',
        '/cases/case04/f3.png',
        '/cases/case04/f4.png',
        '/cases/case04/f5.png'
      ]
    }
  },
]

const sectionRef = ref(null)
const stackRef = ref(null)
const itemRefs = ref([])
const videoRefs = ref([])
const headerRefs = ref([])
const timers = ref({})

let ctx

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
        trigger: sectionRef.value,
        start: 'top top',
        end: `+=${cards.length * 100}%`,
        pin: true,
        scrub: 1,
      }
    })

    cards.forEach((card, index) => {
      if (index === 0) return

      const scrollPos = index - 1

      // 当前卡片滑入
      tl.to(card, {
        yPercent: 0,
        ease: 'none',
        force3D: true
      }, scrollPos)

      // 当前标题滑入并堆叠 (每个标题堆叠高度设为 28px)
      tl.to(headers[index], {
        y: index * 28,
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
  height: 28px; /* 面板高度更小 */
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
  font-size: 11px; /* 字体改小 */
  color: #fff; /* 白字 */
  letter-spacing: 1px;
}

.case-title {
  font-size: 12px; /* 字体改小 */
  font-weight: 500;
  color: #fff; /* 白字 */
  margin: 0;
  letter-spacing: 1px;
}

.case-arrow {
  font-size: 14px; /* 字体改小 */
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
  bottom: 15%;
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
