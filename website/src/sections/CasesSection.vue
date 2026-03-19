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
          <div class="media-wrapper">
            <!-- 标题栏现在放在这里，附属于自身的卡片，实现真正背景透视 -->
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
      gsap.set(card, { transformOrigin: "top center" })
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

      // 卡片往上滑，正好压住前一张卡片，并在顶部留出它的标题条
      tl.to(card, {
        yPercent: 0,
        y: index * headerHeight,
        ease: 'none',
        force3D: true
      }, scrollPos)

      // 前一张卡片微缩变暗
      tl.to(cards[index - 1], {
        scale: 0.95,
        opacity: 0.5,
        ease: 'none',
        force3D: true
      }, scrollPos)
    })

  }, sectionRef.value)
})

onUnmounted(() => {
  if (ctx) ctx.revert()
})
</script>

<style scoped>
.cases-section {
  background-color: #000;
  width: 100%;
  height: calc(100vh - 68px);
  position: relative;
  box-sizing: border-box;
}

.cases-container {
  height: 100%;
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
  background-color: #000;
  will-change: transform, opacity;
}

.media-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* 核心：现在的标题栏位于每张卡片的体系内，只模糊自身的图 */
.sticky-header {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 20px; 
  padding: 0 5%;
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.4); 
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  z-index: 200;
  box-sizing: border-box;
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
