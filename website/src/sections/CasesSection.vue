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

            <img 
              v-if="item.detail?.gallery?.[0]" 
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
import { onMounted, onUnmounted, ref } from 'vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

const emit = defineEmits(['open-showcase'])

gsap.registerPlugin(ScrollTrigger)

import { cases } from '../data/cases'

const sectionRef = ref(null)
const stackRef = ref(null)
const itemRefs = ref([])

let ctx

onMounted(() => {
  ctx = gsap.context(() => {
    const cards = gsap.utils.toArray(sectionRef.value.querySelectorAll('.case-item'))
    
    if (cards.length <= 1) return

    const headerHeight = 20; // 恢复堆叠高度为原来小巧的20px

    // 初始化状态，设定顶部中心缩放以便精准叠放
    cards.forEach((card, index) => {
      // 设定顶部中心缩放
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
        scrub: 0.5,
        snap: {
          snapTo: 1 / (cards.length - 1),
          duration: { min: 0.2, max: 0.5 },
          delay: 0.05,
          ease: 'power3.inOut'
        }
      }
    })

    cards.forEach((card, index) => {
      if (index === 0) return

      const scrollPos = index - 1

      // 卡片往上滑，正好压住前一张卡片
      tl.to(card, {
        yPercent: 0,
        y: index * headerHeight, // 顶部留出之前的标题空间
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

  }, sectionRef.value)
})

onUnmounted(() => {
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
  will-change: transform, opacity;
}

.media-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  overflow: hidden;
  background-color: #000 !important;
  will-change: transform, opacity;
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
  background: rgba(0, 0, 0, 0.4); 
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
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
.media-wrapper .placeholder-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 1.2s cubic-bezier(0.2, 0, 0.2, 1);
  will-change: transform;
  transform: translateZ(0); /* Hardware acceleration to prevent edge ghosting */
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
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  background: rgba(255,255,255,0.05);
}

.case-item:hover .media-wrapper img,
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
