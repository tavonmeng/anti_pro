<template>
  <section id="cases" class="cases-section" ref="sectionRef">
    <div class="cases-container">
      <div class="cases-stack" ref="stackRef">
        <article 
          v-for="(item, index) in cases" 
          :key="item.id" 
          class="case-item"
          :ref="el => { if (el) itemRefs[index] = el }"
          :style="{ zIndex: index + 1 }"
          @click="emit('open-showcase', item)"
        >
          <!-- 标题栏独立出来，保证缩放时不被影响，全宽覆盖黑色底 -->
          <div class="sticky-header">
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

          <div class="media-wrapper">

            <!-- 优化：视频使用 preload="none"，由 JS 控制播放/暂停，避免 4 路同时解码 -->
            <video 
              v-if="item.video" 
              muted 
              loop 
              playsinline
              preload="none"
              :data-src="item.video"
              :ref="el => { if (el) videoRefs[index] = el }"
              class="case-video"
            ></video>
            <img 
              v-else-if="item.detail?.gallery?.[0]" 
              :src="item.detail.gallery[0]" 
              :alt="item.title"
              class="case-image"
            />
            <div v-else class="placeholder-image">
              <span>Case {{ item.id }} Image</span>
            </div>
            
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
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

const emit = defineEmits(['open-showcase'])

gsap.registerPlugin(ScrollTrigger)

import { cases } from '../data/cases'

const sectionRef = ref(null)
const stackRef = ref(null)
const itemRefs = ref([])
const videoRefs = ref([])

// 当前处于最顶层（可见）的卡片索引
const activeCardIndex = ref(0)

let ctx

// ========== 一次一张翻页状态 ==========
let currentCardIndex = 0
let isAnimating = false
let wheelHandler = null
let touchStartY = 0
let touchHandler = null
let touchEndHandler = null

/**
 * 视频懒加载管理：只加载并播放当前可见卡片的视频，
 * 其余卡片的视频暂停并释放资源。
 */
function updateActiveVideo(index) {
  if (activeCardIndex.value === index) return
  activeCardIndex.value = index

  videoRefs.value.forEach((video, i) => {
    if (!video) return
    if (i === index) {
      // 懒加载：首次激活时才设置 src
      if (!video.src && video.dataset.src) {
        video.src = video.dataset.src
      }
      video.play().catch(() => {})
    } else {
      // 暂停非活跃视频，释放解码资源
      if (!video.paused) {
        video.pause()
      }
    }
  })
}

onMounted(() => {
  // 首帧：只加载并播放第一个视频
  nextTick(() => {
    updateActiveVideo(0)
  })

  ctx = gsap.context(() => {
    const cards = gsap.utils.toArray(sectionRef.value.querySelectorAll('.case-item'))
    
    if (cards.length <= 1) return

    const headerHeight = 20
    const totalCards = cards.length

    // 初始化状态，设定顶部中心缩放以便精准叠放
    cards.forEach((card, index) => {
      const media = card.querySelector('.media-wrapper')
      gsap.set(card, { transformOrigin: "top center" })
      if(media) gsap.set(media, { transformOrigin: "top center" })
      
      if (index !== 0) {
        gsap.set(card, { yPercent: 100, force3D: true })
      } else {
        gsap.set(card, { y: 0, force3D: true })
      }
    })

    const tl = gsap.timeline({
      scrollTrigger: {
        id: 'casesTrigger',
        trigger: sectionRef.value,
        start: 'top 68px',
        end: `+=${cards.length * 100}%`,
        pin: true,
        scrub: true,  // 直接追踪，无延迟 — 丝滑感由我们的手动滚动动画提供
        // 不使用 snap — 由 wheel/touch 拦截器手动控制翻页
        onUpdate: (self) => {
          const progress = self.progress
          const rawIndex = Math.round(progress * (totalCards - 1))
          const clampedIndex = Math.max(0, Math.min(totalCards - 1, rawIndex))
          updateActiveVideo(clampedIndex)
          // 同步卡片索引（用于重新进入 pin 区域时）
          if (!isAnimating) {
            currentCardIndex = clampedIndex
          }
        }
      }
    })

    // 构建卡片堆叠动画
    cards.forEach((card, index) => {
      if (index === 0) return

      const scrollPos = index - 1

      // 卡片往上滑，正好压住前一张卡片
      tl.to(card, {
        yPercent: 0,
        y: index * headerHeight,
        ease: 'none',
        force3D: true
      }, scrollPos)

      // 仅仅让前一张卡片的图片内容部分（media-wrapper）微缩变暗，标题栏保持全宽
      const prevMedia = cards[index - 1].querySelector('.media-wrapper')
      const prevHeader = cards[index - 1].querySelector('.sticky-header')
      
      if (prevMedia) {
        tl.to(prevMedia, {
          scale: 0.95,
          opacity: 0.4,
          ease: 'none',
          force3D: true
        }, scrollPos)
      }
      // 标题栏在下面一层变暗一点以增加堆叠效果，但不缩小
      if (prevHeader) {
        tl.to(prevHeader, {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          ease: 'none',
        }, scrollPos)
      }
    })

    // ========== 一次一张翻页：平滑导航到目标卡片 ==========
    function navigateToCard(targetIndex) {
      if (isAnimating) return
      if (targetIndex < 0 || targetIndex >= totalCards) return
      if (targetIndex === currentCardIndex) return
      
      isAnimating = true
      currentCardIndex = targetIndex

      const st = ScrollTrigger.getById('casesTrigger')
      if (!st) { isAnimating = false; return }

      const progress = targetIndex / (totalCards - 1)
      const targetScroll = st.start + (st.end - st.start) * progress

      // 用自定义对象驱动 scrollTo，无需额外插件
      const scrollObj = { value: window.scrollY }
      gsap.to(scrollObj, {
        value: targetScroll,
        duration: 1,
        ease: 'power3.inOut',
        onUpdate: () => {
          window.scrollTo(0, scrollObj.value)
        },
        onComplete: () => {
          isAnimating = false
          updateActiveVideo(targetIndex)
        }
      })
    }

    // ========== Wheel 拦截：一次只翻一张 ==========
    wheelHandler = (e) => {
      const st = ScrollTrigger.getById('casesTrigger')
      if (!st || !st.isActive) return  // 仅在 pin 激活时拦截

      const direction = e.deltaY > 0 ? 1 : -1
      const nextIndex = currentCardIndex + direction

      // 边界：第一张向上滚 或 最后一张向下滚 → 不拦截，让原生滚动脱离 pin
      if (nextIndex < 0 || nextIndex >= totalCards) {
        return
      }

      // 中间区域：拦截原生滚动，手动翻一张
      e.preventDefault()
      e.stopPropagation()

      if (isAnimating) return
      navigateToCard(nextIndex)
    }

    // ========== Touch 支持（移动端） ==========
    touchHandler = (e) => {
      touchStartY = e.touches[0].clientY
    }

    touchEndHandler = (e) => {
      const st = ScrollTrigger.getById('casesTrigger')
      if (!st || !st.isActive) return

      const touchEndY = e.changedTouches[0].clientY
      const diff = touchStartY - touchEndY

      if (Math.abs(diff) < 50) return  // 忽略微小滑动

      const direction = diff > 0 ? 1 : -1
      const nextIndex = currentCardIndex + direction

      if (nextIndex < 0 || nextIndex >= totalCards) return

      e.preventDefault()
      if (isAnimating) return
      navigateToCard(nextIndex)
    }

    // 挂载事件 — 在 window 上监听以确保 pinned 元素也能捕获
    window.addEventListener('wheel', wheelHandler, { passive: false })
    window.addEventListener('touchstart', touchHandler, { passive: true })
    window.addEventListener('touchend', touchEndHandler, { passive: false })

  }, sectionRef.value)
})

onUnmounted(() => {
  // 清理视频
  videoRefs.value.forEach(video => {
    if (video && !video.paused) video.pause()
  })
  // 清理事件监听
  if (wheelHandler) window.removeEventListener('wheel', wheelHandler)
  if (touchHandler) window.removeEventListener('touchstart', touchHandler)
  if (touchEndHandler) window.removeEventListener('touchend', touchEndHandler)
  if (ctx) ctx.revert()
})
</script>

<style>
/* 非scoped：强制 GSAP pin-spacer 包裹层也显示黑色背景，防止滚动时边缘露出底色 */
.pin-spacer {
  background-color: #000 !important;
}
</style>

<style scoped>
.cases-section {
  background-color: #000;
  width: 100%;
  height: calc(100vh - 68px);
  position: relative;
  box-sizing: border-box;
  overflow: hidden;
}

.cases-container {
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: #000 !important;
}

.cases-stack {
  position: relative;
  width: 100%;
  height: 100%;
  background-color: #000;
}

.case-item {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #000 !important;
  /* 优化：移除 will-change，由 GSAP force3D 动态管理合成层 */
}

.media-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  overflow: hidden;
  background-color: #000 !important;
  /* 优化：移除 will-change，减少常驻合成层数量 */
  /* Safari edge bleed & subpixel ghosting fix for transformed contents */
  -webkit-mask-image: -webkit-radial-gradient(white, black);
  mask-image: radial-gradient(white, black);
  transform: translateZ(0);
}

/* 改变 sticky-header 位置：因为现在与 media-wrapper 是同级元素了 */
.sticky-header {
  position: relative; /* 换成 relative 以便堆叠，防止随图片缩小 */
  width: 100%;
  height: 20px; 
  padding: 0 5%;
  display: flex;
  align-items: center;
  /* 优化：移除 backdrop-filter blur(15px)，在视频背景上 blur 每帧都要重新计算，极其昂贵 */
  background: rgba(0, 0, 0, 0.75);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 200;
  box-sizing: border-box;
  flex-shrink: 0;
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
  font-size: 10px;
  color: #fff;
  letter-spacing: 1px;
}

.case-title {
  font-size: 10px;
  font-weight: 500;
  color: #fff;
  margin: 0;
  letter-spacing: 1px;
}

.case-arrow {
  font-size: 12px;
  color: #fff;
}

.media-wrapper img,
.media-wrapper video,
.media-wrapper .placeholder-image {
  width: 100%;
  height: 100%;
  object-fit: fill; /* 强制填满，避免原图比例不一 */
  transform: scale(1.02); /* 默认轻微放大掩盖边缘瑕疵 */
  transition: transform 1.2s cubic-bezier(0.2, 0, 0.2, 1);
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.case-details {
  position: absolute;
  bottom: 22%;
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
  z-index: 50;
}

.view-btn {
  padding: 15px 40px;
  border: 1px solid rgba(255,255,255,0.4);
  border-radius: 40px;
  color: #fff;
  font-size: 14px;
  letter-spacing: 2px;
  text-transform: uppercase;
  /* 优化：移除 backdrop-filter，使用纯色背景减少重绘 */
  background: rgba(255,255,255,0.1);
}

.case-item:hover .media-wrapper img,
.case-item:hover .media-wrapper video,
.case-item:hover .media-wrapper .placeholder-image {
  transform: scale(1.05);
}

.case-item:hover .view-btn-wrapper {
  opacity: 1;
}

.case-item {
  cursor: pointer;
}

@media (max-width: 768px) {
  .case-title {
    font-size: 12px;
  }
  .case-details {
    bottom: 10%;
    right: 20px;
    left: 20px;
    text-align: left;
  }
}
</style>
