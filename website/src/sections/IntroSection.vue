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
      
      <!-- 右侧动画滑块内容 -->
      <div class="right-content">
        <!-- 团队介绍：固定位置 -->
        <div class="team-block-top">
          <p class="team-lead section-heading">
            国内最早的裸眼3D项目核心团队，具有完善的AI数字艺术全流程项目环节，成员多毕业于海外TOP级艺术学院，专业覆盖创意广告学、公共艺术设计、雕塑、影视导演、动画、三维特效设计、视觉传达等领域
          </p>
          <p class="team-desc section-heading">
            对户外媒体的艺术表现与内容营销具有丰富的经验，项目涉及三维CG、AIGC、实拍、数字艺术、艺术家联名、创意IP开发、室内互动屏项目、各地异形屏、AI视觉系统运用等......................
          </p>
        </div>

        <div class="slides-wrapper">
          <!-- Slide 0: 服务1 -->
          <div class="slide first" ref="slide0">
            <div class="outer">
              <div class="inner">
                <div class="bg">
                  <div class="content-block service-block">
                    <div class="service-header">
                      <h3 class="service-title section-heading">裸眼3D成片配订</h3>
                    </div>
                    <p class="service-desc section-heading">
                      为每一块屏幕，适配引爆媒体的裸眼3D内容<br/>
                      快速、高效、低成本获取高质量成片。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Slide 1: 服务2 -->
          <div class="slide second" ref="slide1">
            <div class="outer">
              <div class="inner">
                <div class="bg">
                  <div class="content-block service-block">
                    <div class="service-header">
                      <h3 class="service-title section-heading">AI裸眼3D自主化定制</h3>
                    </div>
                    <p class="service-desc section-heading">
                      从创意到上屏，一站式AI制片<br/>
                      自研AI专业内容打造模型，大幅缩短制作周期。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Slide 2: 服务3 -->
          <div class="slide third" ref="slide2">
            <div class="outer">
              <div class="inner">
                <div class="bg">
                  <div class="content-block service-block">
                    <div class="service-header">
                      <h3 class="service-title section-heading">泛商业数字艺术打造</h3>
                    </div>
                    <p class="service-desc section-heading">
                      你的屏幕，需要新的艺术<br/>
                      为商业空间打造独一无二的沉浸式视觉体验。
                    </p>
                  </div>
                </div>
              </div>
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
import SplitType from 'split-type'

gsap.registerPlugin(ScrollTrigger)

const sectionRef = ref(null)
const slide0 = ref(null)
const slide1 = ref(null)
const slide2 = ref(null)

let ctx
let splitContext = []

onMounted(() => {
  ctx = gsap.context(() => {
    const slides = [slide0.value, slide1.value, slide2.value]
    
    // 初始化 SplitType，将文本分割为行、单词和字符
    const headings = gsap.utils.toArray('.section-heading')
    headings.forEach(heading => {
      splitContext.push(new SplitType(heading, { types: 'lines,words,chars', lineClass: 'clip-text' }))
    })

    // 创建单向Timeline，通过scrub驱动幻灯片切换
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.value,
        start: 'top top',
        end: '+=300%', // 预留滚动空间用于体验幻灯片
        pin: true,
        scrub: 1, // 增加平滑缓冲
        snap: {
          snapTo: 1 / (slides.length - 1),
          duration: { min: 0.2, max: 0.8 },
          delay: 0.1,
          ease: 'power1.inOut'
        }
      }
    })

    // 设置初始状态
    slides.forEach((slide, i) => {
      const outer = slide.querySelector('.outer')
      const inner = slide.querySelector('.inner')
      const bg = slide.querySelector('.bg')
      
      if (i > 0) {
        gsap.set(outer, { yPercent: 100 })
        gsap.set(inner, { yPercent: -100 })
        gsap.set(bg, { yPercent: 15 })
        // 除了第一张，其余内容的字一开始是隐藏的，因为第一页进入时不带字符飞入动画
        const chars = slide.querySelectorAll('.char')
        gsap.set(chars, { autoAlpha: 0, yPercent: 150 })
      }
    })
    
    // 构建幻灯片洗牌时间轴
    slides.forEach((slide, i) => {
      if (i === 0) return
      
      const prevSlide = slides[i - 1]
      const prevBg = prevSlide.querySelector('.bg')
      
      const outer = slide.querySelector('.outer')
      const inner = slide.querySelector('.inner')
      const bg = slide.querySelector('.bg')
      
      // 注意：必须通过 slide 定位它内部的 chars，来让字有逐个飞入特效
      const chars = slide.querySelectorAll('.char')

      const transLabel = `trans${i}`
      tl.addLabel(transLabel)
      
      // 旧幻灯片离开
      tl.to(prevBg, { yPercent: -15, duration: 1, ease: 'none' }, transLabel)
        .to(prevSlide, { autoAlpha: 0, duration: 1, ease: 'none' }, transLabel)
        
      // 新幻灯片进入（模拟GSAP Observer CodePen里的 parallax 面板运动）
      tl.set(slide, { autoAlpha: 1, zIndex: 1 }, transLabel)
        .fromTo([outer, inner], 
          // gsap里 index 函数有三个参数 (i, target, targets)，
          // target 是当前处理的DOM元素。
          // 当 i=0 是 outer，所以 -100；当 i=1 是 inner，所以 100
          { yPercent: index => index ? -100 : 100 }, 
          { yPercent: 0, duration: 1, ease: 'power1.inOut' }, transLabel)
        .fromTo(bg, { yPercent: 15 }, { yPercent: 0, duration: 1, ease: 'power1.inOut' }, transLabel)
        
      // 文本字符动画
      if (chars.length > 0) {
        tl.to(chars, { 
          autoAlpha: 1, 
          yPercent: 0, 
          duration: 0.8, 
          ease: 'power2.out', 
          stagger: 0.02 
        }, `${transLabel}+=0.2`)
      }
    })
    
  }, sectionRef.value)
})

onUnmounted(() => {
  if (ctx) ctx.revert()
  splitContext.forEach(sc => sc.revert())
})
</script>

<style scoped>
.intro-section {
  padding: 120px 40px;
  background-color: var(--color-bg-primary);
  color: #fff;
  min-height: 100vh;
  position: relative;
  /* Ensure parent allows z-index context */
  z-index: 10;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 80px;
  align-items: center; /* keep everything centered horizontally to avoid stretching bug */
  height: calc(100vh - 240px); /* Fill the viewport minus padding */
}

.left-content {
  will-change: transform;
}

.main-heading {
  font-size: 48px;
  line-height: 1.2;
  font-weight: 700;
  color: #fff;
  margin-bottom: 20px;
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

/* ==================
   Right Slider Area 
   ================== */
   
.right-content {
  position: relative;
  width: 100%;
  height: calc(100vh - 240px);
  display: flex;
  flex-direction: column;
}

.team-block-top {
  position: relative;
  z-index: 20;
  margin-bottom: 50px;
}

.slides-wrapper {
  position: relative;
  width: 100%;
  flex: 1; /* Take remaining space */
  border-radius: 20px;
}

.slide {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  visibility: hidden;
  z-index: 0;
}

.slide.first {
  visibility: visible;
  z-index: 1;
}

.outer, .inner {
  width: 100%;
  height: 100%;
  overflow-y: hidden; /* Critical for the GSAP Demo wipe effect */
}

.bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding: 0;
  box-sizing: border-box;
  background-color: var(--color-bg-primary);
  /* The CodePen effect relies on the background overlaying properly */
}

/* --- Slide Content Styling --- */

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

.service-block {
  padding: 0;
}

.service-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.service-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.service-desc {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  line-height: 1.8;
}

/* GSAP SplitType Masking Class */
:deep(.clip-text) {
  overflow: hidden;
  padding: 2px 0; /* Add slight padding so character descenders don't get cut off */
}

@media (max-width: 900px) {
  .container {
    grid-template-columns: 1fr;
    gap: 40px;
    height: auto;
  }
  
  .right-content {
    height: 60vh;
  }
}
</style>
