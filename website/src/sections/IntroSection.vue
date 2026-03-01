<template>
  <section id="intro" class="intro-section" ref="sectionRef">
    <div class="container">
      <!-- 左侧固定内容 -->
      <div class="left-content" ref="leftContentRef">
        <h2 class="main-heading">
          这是一个<br>
          <span class="desc-highlight">idea+AI驱动的</span><br>
          3D OOH内容平台
        </h2>
        
        <div class="description-block">
          <p class="desc-text">
            高效率、低成本、提升视觉质量<br>
            让全球数字媒体
          </p>
          <p class="desc-highlight" style="margin-bottom: 40px;">
            更快获得优质内容。
          </p>
        </div>

      </div>
      
      <!-- 右侧滚动淡出内容 -->
      <div class="right-content" ref="contentRef">
        <!-- 团队介绍：固定在右侧顶部 -->
        <div class="team-block-wrapper">
          <div class="team-block" ref="teamBlockRef">
            <p class="team-lead">
              国内最早的裸眼3D项目核心团队，具有完善的AI数字艺术全流程项目环节，成员多毕业于海外TOP级艺术学院，专业覆盖创意广告学、公共艺术设计、雕塑、影视导演、动画、三维特效设计、视觉传达等领域
            </p>
            <p class="team-desc">
              对户外媒体的艺术表现与内容营销具有丰富的经验，项目涉及三维CG、AIGC、实拍、数字艺术、艺术家联名、创意IP开发、室内互动屏项目、各地异形屏、AI视觉系统运用等......................
            </p>
          </div>
        </div>

        <!-- 服务介绍模块及其固定箭头框 -->
        <div class="services-container">
          <div class="fixed-arrow-wrapper" ref="arrowWrapperRef">
            <span class="service-arrow shared-arrow" :class="{ 'arrow-hovered': isServiceHovered }">←</span>
          </div>

          <div class="services-wrapper">
            <!-- 服务介绍1 -->
            <div class="content-block service-block" ref="block1" @mouseenter="isServiceHovered = true" @mouseleave="isServiceHovered = false">
              <div class="service-header">
                <h3 class="service-title">裸眼3D成片配订</h3>
              </div>
            <p class="service-desc">
              为每一块屏幕，适配引爆媒体的裸眼3D内容<br/>
              快速、高效、低成本获取高质量成片。
            </p>
            <div class="hover-glow"></div>
          </div>

          <!-- 服务介绍2 -->
          <div class="content-block service-block" ref="block2" @mouseenter="isServiceHovered = true" @mouseleave="isServiceHovered = false">
            <div class="service-header">
              <h3 class="service-title">AI裸眼3D自主化定制</h3>
            </div>
            <p class="service-desc">
              从创意到上屏，一站式AI制片<br/>
              自研AI专业内容打造模型，大幅缩短制作周期。
            </p>
            <div class="hover-glow"></div>
          </div>

          <!-- 服务介绍3 -->
          <div class="content-block service-block" ref="block3" @mouseenter="isServiceHovered = true" @mouseleave="isServiceHovered = false">
            <div class="service-header">
              <h3 class="service-title">泛商业数字艺术打造</h3>
            </div>
            <p class="service-desc">
              你的屏幕，需要新的艺术<br/>
              为商业空间打造独一无二的沉浸式视觉体验。
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const sectionRef = ref(null)
const leftContentRef = ref(null)
const block1 = ref(null)
const block2 = ref(null)
const block3 = ref(null)
const teamBlockRef = ref(null)
const arrowWrapperRef = ref(null)

const isServiceHovered = ref(false)

let ctx

onMounted(() => {
  ctx = gsap.context(() => {
    // 1. PIN THE LEFT CONTENT AND TEAM BLOCK
    ScrollTrigger.create({
      trigger: sectionRef.value,
      pin: leftContentRef.value,
      start: 'top 80px',
      end: 'bottom bottom',
      pinSpacing: false,
    })

    ScrollTrigger.create({
      trigger: sectionRef.value,
      pin: teamBlockRef.value,
      start: 'top 80px',
      end: 'bottom bottom',
      pinSpacing: false,
    })

    ScrollTrigger.create({
      trigger: sectionRef.value,
      pin: arrowWrapperRef.value,
      start: 'top top', // 让箭头随整体内容滚动到底边
      end: 'bottom bottom',
      pinSpacing: false,
    })

    // 2. RIGHT BLOCKS ANIMATIONS (Only the 3 service blocks)
    const blocks = [block1.value, block2.value, block3.value]
    blocks.forEach((block) => {
      if (block) {
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: block,
            start: 'top 95%', // 使模块从更低的位置开始进入
            end: 'top 60%',   // 使模块停留在画布下方红框对应的高度
            scrub: true
          }
        })
        
        tl.fromTo(block, 
          { autoAlpha: 0, y: 50 },
          { autoAlpha: 1, y: 0, duration: 0.4 } // Fade in and move into place
        )
        // hold
        .to(block, { autoAlpha: 1, duration: 0.3 })
        // fade out and translate up completely before the timeline ends
        .to(block, { autoAlpha: 0, y: -20, duration: 0.3 })
      }
    })
  }, sectionRef.value)
})

onUnmounted(() => {
  if (ctx) ctx.revert()
})
</script>

<style scoped>
.intro-section {
  padding: 120px 40px;
  background-color: var(--color-bg-primary);
  color: #fff;
  min-height: 100vh;
  position: relative; /* Required for pinning logic bounds */
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 80px;
  align-items: start;
}

.left-content {
  padding-top: 20px;
  will-change: transform;
}

.main-heading {
  font-size: 48px;
  line-height: 1.2;
  font-weight: 700;
  color: #fff;
  margin-bottom: 20px;
}

.highlight {
  color: var(--color-accent);
  text-shadow: 0 0 15px var(--color-glow);
}

.description-block {
  margin-top: 30px;
}

.desc-text {
  font-size: 20px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 12px;
  font-weight: 300;
}

.desc-highlight {
  color: #fff;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 1px;
}

.right-content {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
  margin-left: auto;
  width: 100%;
}

.team-block-wrapper, .services-wrapper {
  grid-column: 1 / 2;
  grid-row: 1 / 2;
}

.team-block-wrapper {
  z-index: 20;
  margin-top: -30px; /* 位置再往上调整 */
  position: relative; /* 建立层叠上下文 */
}

.team-block {
  /* No position: sticky needed anymore, GSAP pins it perfectly */
  background: var(--color-bg-primary);
  padding-bottom: 40px;
  margin-bottom: 0;
  /* 确保自身堆叠也在最前面 */
  position: relative;
  z-index: 20;
}

.services-container {
  position: relative;
  width: 100%;
}

.fixed-arrow-wrapper {
  position: absolute;
  top: 20vh; /* 下调到与下方大红框相匹配的水平线中心位置 */
  right: 0;
  width: 100%;
  height: 0; 
  display: flex;
  justify-content: flex-end;
  align-items: center; /* 确保自身容器能够包含箭头 */
  z-index: 30;
  pointer-events: none; /* 让它悬浮在层之上但不阻挡事件 */
}

.services-wrapper {
  display: flex;
  flex-direction: column;
  gap: 30vh; /* Scalable gap for scrolling experience */
  margin-top: 50vh; /* Start far below the team text */
  padding-bottom: 300px;
  position: relative;
  z-index: 5; /* 确保它永远在 team-block-wrapper 的下方 */
}

.content-block {
  will-change: transform, opacity;
}

.team-lead {
  font-size: 16px;
  color: #fff;
  margin-bottom: 20px;
  line-height: 1.8;
  font-weight: 400;
}

.team-desc {
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  line-height: 1.8;
}

/* Removed duplicate .right-content and .content-block */

.service-block {
  padding: 40px 0;
  cursor: pointer;
}

.service-header, .service-desc {
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.service-block:hover .service-header,
.service-block:hover .service-desc {
  transform: translateX(-10px);
}

.service-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.service-title {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.service-arrow {
  font-size: 28px;
  color: rgba(255, 255, 255, 0.3);
  font-weight: 300;
  display: inline-block;
  transition: color 0.3s ease, transform 0.3s ease;
  transform: translateX(0);
}

.service-arrow.arrow-hovered {
  color: #fff;
  transform: translateX(-10px);
}

.service-desc {
  color: rgba(255, 255, 255, 0.6);
  font-size: 16px;
  line-height: 1.8;
}

.hover-glow {
  display: none;
}

@media (max-width: 900px) {
  .container {
    grid-template-columns: 1fr;
    gap: 60px;
  }
  
  .left-content {
    position: relative !important; /* Force unpin on mobile */
    top: 0 !important;
    transform: none !important;
    padding-top: 0;
    margin-bottom: 40px;
  }

  .main-heading {
    font-size: 36px;
  }

  .right-content {
    gap: 80px;
    padding-top: 0;
  }
}
</style>
