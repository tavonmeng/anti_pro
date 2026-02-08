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
          <p class="desc-highlight">
            更快获得优质内容。
          </p>
        </div>
      </div>
      
      <!-- 右侧滚动淡出内容 -->
      <div class="right-content" ref="contentRef">
        <!-- 团队介绍 -->
        <div class="content-block" ref="block1">
          <p class="team-lead">
            国内最早的裸眼3D项目核心团队，具有完善的AI数字艺术全流程项目环节，成员多毕业于海外TOP级艺术学院，专业覆盖创意广告学、公共艺术设计、雕塑、影视导演、动画、三维特效设计、视觉传达等领域
          </p>
          <p class="team-desc">
            对户外媒体的艺术表现与内容营销具有丰富的经验，项目涉及三维CG、AIGC、实拍、数字艺术、艺术家联名、创意IP开发、室内互动屏项目、各地异形屏、AI视觉系统运用等......................
          </p>
        </div>

        <!-- 服务介绍1 -->
        <div class="content-block service-block" ref="block2">
          <div class="service-header">
            <span class="service-index">01</span>
            <h3 class="service-title">裸眼3D成片配订</h3>
          </div>
          <p class="service-desc">
            为每一块屏幕，适配引爆媒体的裸眼3D内容<br/>
            快速、高效、低成本获取高质量成片。
          </p>
          <div class="hover-glow"></div>
        </div>

        <!-- 服务介绍2 -->
        <div class="content-block service-block" ref="block3">
          <div class="service-header">
            <span class="service-index">02</span>
            <h3 class="service-title">AI裸眼3D自主化定制</h3>
          </div>
          <p class="service-desc">
            从创意到上屏，一站式AI制片<br/>
            自研AI专业内容打造模型，大幅缩短制作周期。
          </p>
          <div class="hover-glow"></div>
        </div>

        <!-- 服务介绍3 -->
        <div class="content-block service-block" ref="block4">
          <div class="service-header">
            <span class="service-index">03</span>
            <h3 class="service-title">泛商业数字艺术打造</h3>
          </div>
          <p class="service-desc">
            你的屏幕，需要新的艺术<br/>
            为商业空间打造独一无二的沉浸式视觉体验。
          </p>
          <div class="hover-glow"></div>
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
const block4 = ref(null)

let ctx

onMounted(() => {
  ctx = gsap.context(() => {
    // 1. PIN THE LEFT CONTENT
    ScrollTrigger.create({
      trigger: sectionRef.value,
      pin: leftContentRef.value,
      start: 'top top',
      end: 'bottom bottom',
      pinSpacing: false, // Don't add padding to the pinned element
      // onRefresh: self => {
      //   // Optional: Handle refresh logic
      // }
    })

    // 2. RIGHT BLOCKS ANIMATIONS
    const blocks = [block1.value, block2.value, block3.value, block4.value]
    blocks.forEach((block) => {
      if (block) {
        gsap.fromTo(block, 
          { opacity: 0.3, y: 50 },
          {
            opacity: 1,
            y: 0,
            scrollTrigger: {
              trigger: block,
              start: 'top 80%',
              end: 'top 40%',
              scrub: true,
              toggleActions: 'play reverse play reverse'
            }
          }
        )
        
        // Also add a fade out when leaving
        gsap.to(block, {
          opacity: 0,
          y: -50,
          scrollTrigger: {
            trigger: block,
            start: 'top 10%',
            end: 'top -10%',
            scrub: true
          }
        })
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
  padding-top: 40px; /* Offset for top-of-page feel */
  /* Remove position: sticky, GSAP handles pinning */
  will-change: transform;
}

.main-heading {
  font-size: 48px;
  line-height: 1.2;
  font-weight: 700;
  color: #fff;
  margin-bottom: 40px;
}

.highlight {
  color: var(--color-accent);
  text-shadow: 0 0 15px var(--color-glow);
}

.description-block {
  margin-top: 40px;
}

.desc-text {
  font-size: 20px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
  font-weight: 300;
}

.desc-highlight {
  color: #fff;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 1px;
}

.right-content {
  display: flex;
  flex-direction: column;
  gap: 30vh; /* Scalable gap for scrolling experience */
  padding-bottom: 100px;
  margin-left: auto;
  width: 100%;
}

.content-block {
  will-change: transform, opacity;
}

.team-lead {
  font-size: 22px;
  color: #fff;
  margin-bottom: 24px;
  line-height: 1.8;
  font-weight: 500;
}

.team-desc {
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
  line-height: 1.8;
}

.service-block {
  padding: 60px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  transition: transform 0.3s ease;
}

.service-block:hover {
  transform: translateX(10px);
}

.service-header {
  display: flex;
  align-items: baseline;
  gap: 24px;
  margin-bottom: 16px;
}

.service-index {
  font-family: 'Inter', monospace;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-accent);
  opacity: 0.7;
}

.service-title {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.service-desc {
  margin-left: 0;
  padding-left: 40px; 
  color: rgba(255, 255, 255, 0.5);
  font-size: 16px;
  line-height: 1.6;
  max-width: 90%;
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
  }
}
</style>
