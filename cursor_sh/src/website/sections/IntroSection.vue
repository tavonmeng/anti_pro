<template>
  <section id="intro" class="intro-section" ref="sectionRef">
    <!-- 包裹层用于入场淡入动画 -->
    <div class="intro-contents-wrapper" ref="wrapperRef">
      
      <!-- 1. 全屏动态背景和改变的服务介绍 -->
      <div class="full-screen-slides">
        <div
          v-for="(service, index) in platformServices"
          :key="service.title"
          class="slide"
          :class="{ first: index === 0 }"
          :ref="el => setSlideRef(el, index)"
        >
          <div class="outer">
            <div class="inner">
              <div class="bg" :class="service.bgClass">
                <!-- 内部对齐网格，与静态层完全吻合 -->
                <div class="slide-grid">
                  <div class="container">
                    <div class="left-empty"></div>
                    <div class="right-content relative-box">
                      <div class="service-block">
                        <div class="service-header">
                          <h3 class="service-title section-heading">{{ service.title }}</h3>
                        </div>
                        <p class="service-desc section-heading">
                          {{ service.line1 }}<br/>
                          {{ service.line2 }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. 全局静态覆盖层（左侧文本 + 右侧团队说明） -->
      <div class="static-overlay-layer">
        <div class="container">
          <div class="left-content static-left" ref="leftContentRef">
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
          
          <div class="right-content relative-box">
            <div class="team-block-top">
              <p class="team-lead static-heading">
                国内最早的裸眼3D项目核心团队，具有完善的AI数字艺术全流程项目环节，成员多毕业于海外TOP级艺术学院，专业覆盖创意广告学、公共艺术设计、雕塑、影视导演、动画、三维特效设计、视觉传达等领域
              </p>
              <p class="team-desc static-heading">
                对户外媒体的艺术表现与内容营销具有丰富的经验，项目涉及三维CG、AIGC、实拍、数字艺术、艺术家联名、创意IP开发、室内互动屏项目、各地异形屏、AI视觉系统运用等......................
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
import SplitType from 'split-type'

gsap.registerPlugin(ScrollTrigger)

const sectionRef = ref(null)
const wrapperRef = ref(null)
const slideRefs = ref([])

const platformServices = [
  {
    title: '3D OOH数字内容资源库',
    line1: '即用型裸眼3D数字内容资产',
    line2: '多屏适配内容方案 / 全球地标大屏内容规格适配',
    bgClass: 'slide-bg-1'
  },
  {
    title: 'AI驱动3D OOH内容定制',
    line1: 'AI创意内容开发 / 场景化裸眼3D空间适配',
    line2: '真实环境播放模拟 / 一站式DOOH内容制作',
    bgClass: 'slide-bg-2'
  },
  {
    title: '数字艺术与沉浸式视觉设计',
    line1: '艺术指导与视觉设计 / 虚拟装置艺术',
    line2: '沉浸式空间视觉 / 实验性数字艺术内容',
    bgClass: 'slide-bg-3'
  },
  {
    title: '广告视觉与动态影像制作',
    line1: '平面广告视觉设计 / TVC广告影片制作 / FOOH数字传播内容',
    line2: 'VJ视觉演出内容 / 动态视觉设计',
    bgClass: 'slide-bg-4'
  },
  {
    title: '户外媒体后期制作服务',
    line1: '高端精修图像处理 / 电影级视频精修 / CGI视觉增强',
    line2: '商业摄影与视频拍摄 / 航拍影像制作',
    bgClass: 'slide-bg-5'
  },
  {
    title: '广告投放分析与效果报告',
    line1: 'DOOH广告投放数据分析 / 受众效果分析报告',
    line2: '视觉传播效果评估 / 可下载数据报告系统',
    bgClass: 'slide-bg-6'
  }
]

const setSlideRef = (el, index) => {
  if (el) slideRefs.value[index] = el
}

let ctx
let splitContext = []

onMounted(() => {
  ctx = gsap.context(() => {
    // 提取静态呈现的文本并进行切割
    const staticHeadings = gsap.utils.toArray(sectionRef.value.querySelectorAll('.main-heading, .desc-text, .static-heading, .desc-highlight'))
    staticHeadings.forEach(heading => {
      splitContext.push(new SplitType(heading, { types: 'lines', lineClass: 'clip-text' }))
    })

    // 为所有的切割行初始设定为向下偏移且隐藏
    const staticLines = sectionRef.value.querySelectorAll('.static-overlay-layer .line')
    gsap.set(staticLines, { yPercent: 120, autoAlpha: 0 })

    const slides = slideRefs.value.filter(Boolean)
    const firstSlide = slides[0]

    // 第一张背景幻灯片放大并变暗作为入场初态
    gsap.set(firstSlide, { scale: 1.1, autoAlpha: 0 })
    gsap.set(wrapperRef.value, { autoAlpha: 1 }) // 不再隐藏整个外壳，而是隐藏内部元素

    // ---- 1. 入场淡入遮罩动效：当从 Hero 滑动到 Intro 时触发 ----
    const entranceTl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.value,
        start: 'top 85%',
        toggleActions: 'play none none reverse'
      }
    })

    // 第一张背景柔和浮现收缩
    entranceTl.to(firstSlide, {
      scale: 1,
      autoAlpha: 1,
      duration: 1.8,
      ease: 'power3.out'
    }, 0)

    // 文字应用 Text-Masking 特效：每一行从自身底部的遮罩区向上拨开
    entranceTl.to(staticLines, {
      yPercent: 0,
      autoAlpha: 1,
      duration: 1.2,
      stagger: 0.08,
      ease: 'power4.out'
    }, 0.2) // 在背景开始出现后立刻跟进文字拨开
    
    // ---- 2. 幻灯片 GSAP Observer 切换逻辑 ----
    // 修复 HMR 热重载下全局选取导致幽灵 DOM 冲突的严重 Bug
    const headings = gsap.utils.toArray(sectionRef.value.querySelectorAll('.section-heading'))
    headings.forEach(heading => {
      splitContext.push(new SplitType(heading, { types: 'lines,words,chars', lineClass: 'clip-text' }))
    })

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.value,
        start: 'top top',
        end: `+=${slides.length * 70}%`,
        pin: true,
        scrub: 0.5,
        snap: {
          snapTo: 1 / (slides.length - 1),
          duration: { min: 0.1, max: 0.4 },
          delay: 0.05,
          ease: 'power3.inOut'
        }
      }
    })

    slides.forEach((slide, i) => {
      const outer = slide.querySelector('.outer')
      const inner = slide.querySelector('.inner')
      const bg = slide.querySelector('.bg')
      
      if (i > 0) {
        gsap.set(outer, { yPercent: 100 })
        gsap.set(inner, { yPercent: -100 })
        gsap.set(bg, { yPercent: 15 })
        const chars = slide.querySelectorAll('.char')
        gsap.set(chars, { autoAlpha: 0, yPercent: 150 })
      }
    })
    
    slides.forEach((slide, i) => {
      if (i === 0) return
      
      const prevSlide = slides[i - 1]
      const prevBg = prevSlide.querySelector('.bg')
      
      const outer = slide.querySelector('.outer')
      const inner = slide.querySelector('.inner')
      const bg = slide.querySelector('.bg')
      const chars = slide.querySelectorAll('.char')

      const transLabel = `trans${i}`
      tl.addLabel(transLabel)
      
      tl.to(prevBg, { yPercent: -15, duration: 0.8, ease: 'none' }, transLabel)
        .to(prevSlide, { autoAlpha: 0, duration: 0.8, ease: 'none' }, transLabel)
        
      tl.set(slide, { autoAlpha: 1, zIndex: 1 }, transLabel)
        .fromTo([outer, inner], 
          { yPercent: index => index ? -100 : 100 }, 
          { yPercent: 0, duration: 0.8, ease: 'power2.inOut' }, transLabel)
        .fromTo(bg, { yPercent: 15 }, { yPercent: 0, duration: 0.8, ease: 'power2.inOut' }, transLabel)
        
      if (chars.length > 0) {
        tl.to(chars, { 
          autoAlpha: 1, 
          yPercent: 0, 
          duration: 0.5,
          ease: 'power3.out', 
          stagger: 0.01 
        }, `${transLabel}+=0.15`)
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
  background-color: var(--color-bg-primary); /* 原为黑色兜底 */
  color: #fff;
  width: 100vw !important; /* Force to always span the entire viewport to defeat GSAP pin-spacer resize bugs */
  height: 100vh;
  position: relative;
  z-index: 10;
  overflow: hidden;
}

.intro-contents-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  will-change: transform, opacity;
}

/* 1. 幻灯片占据全屏 */
.full-screen-slides {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
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
  overflow-y: hidden;
}

/* 背景扩展至全屏，并设置极致的高级渐变遮罩保护左侧文本阅读 */
.bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  /* padding 移除，外层通过 grid-container 精密挂载内容 */
}

/* 加深纯黑渐变：左侧95%纯黑以彻底保护静态白字，中部拉平，右侧微露 20% 原图光芒 */
.slide-bg-1 {
  background-image: linear-gradient(to right, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.8) 45%, rgba(0,0,0,0.2) 100%), 
                    url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop');
}

.slide-bg-2 {
  background-image: linear-gradient(to right, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.8) 45%, rgba(0,0,0,0.3) 100%), 
                    url('https://images.unsplash.com/photo-1634152962476-4b8a00e1915c?q=80&w=2121&auto=format&fit=crop');
}

.slide-bg-3 {
  background-image: linear-gradient(to right, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.8) 45%, rgba(0,0,0,0.4) 100%), 
                    url('https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2100&auto=format&fit=crop');
}

.slide-bg-4 {
  background-image: linear-gradient(to right, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.8) 45%, rgba(0,0,0,0.34) 100%),
                    url('https://images.unsplash.com/photo-1492684223066-81342ee5ff30?q=80&w=2070&auto=format&fit=crop');
}

.slide-bg-5 {
  background-image: linear-gradient(to right, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.8) 45%, rgba(0,0,0,0.36) 100%),
                    url('https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=2088&auto=format&fit=crop');
}

.slide-bg-6 {
  background-image: linear-gradient(to right, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.8) 45%, rgba(0,0,0,0.36) 100%),
                    url('https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2070&auto=format&fit=crop');
}

/* 幻灯片内的网格布局区域计算（和静态层完美重合） */
.slide-grid {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  padding: clamp(120px, 22vh, 450px) clamp(40px, 5vw, 200px);
  box-sizing: border-box;
}

/* 2. 静态覆盖层（位于背景最上方） */
.static-overlay-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  padding: clamp(120px, 22vh, 450px) clamp(40px, 5vw, 200px);
  box-sizing: border-box;
  z-index: 10;
  pointer-events: none;
}

.container {
  max-width: 2000px; /* 放宽更大屏幕下的宽度界限 */
  width: 100%;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: clamp(40px, 5vw, 80px);
  align-items: start;
}

.left-content {
  will-change: transform;
  pointer-events: auto; /* 收回交互控制权 */
}

.relative-box {
  position: relative;
  width: 100%;
  pointer-events: auto;
}

.main-heading {
  font-size: clamp(32px, 3.5vw, 96px); /* 大屏放大顶线上限 */
  line-height: 1.2;
  font-weight: 700;
  color: #fff;
  margin-bottom: 20px;
}

.description-block {
  margin-top: 30px;
}

.desc-text {
  font-size: clamp(18px, 1.3vw, 36px); /* 自适应字号上限提高 */
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: clamp(12px, 1vh, 20px);
  font-weight: 300;
}

.desc-highlight {
  color: #fff;
  font-size: clamp(22px, 1.8vw, 48px); /* 强调词放大上限提高 */
  font-weight: 600;
  letter-spacing: 1.5px;
}

/* 团队静止介绍放在右侧 */
.team-block-top {
  width: 100%;
  margin-bottom: clamp(24px, 4vh, 60px);
}

.team-lead {
  font-size: clamp(16px, 1.1vw, 28px); /* 增大上限 */
  color: #fff;
  margin-bottom: clamp(20px, 1.5vh, 32px);
  line-height: 1.8;
  font-weight: 400;
}

.team-desc {
  color: rgba(255, 255, 255, 0.5);
  font-size: clamp(14px, 0.95vw, 24px); /* 大屏幕不显得过小 */
  line-height: 1.8;
}

/* 动态服务块放在右侧底部 */
.service-block {
  width: 100%;
  max-width: 80%;
  margin-top: clamp(240px, 35vh, 650px); /* 让4K屏上也能保持充分底距 */
}

.service-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.service-title {
  font-size: clamp(26px, 1.8vw, 48px); /* 大屏冲击力上限加倍 */
  font-weight: 700;
  color: #fff;
  margin: 0;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.service-desc {
  color: rgba(255, 255, 255, 0.7);
  font-size: clamp(15px, 1vw, 26px); /* 说明文字更大最高限度 */
  line-height: 1.8;
}

/* GSAP SplitType Masking Class */
:deep(.clip-text) {
  overflow: hidden;
  padding: 2px 0; 
}

@media (max-width: 900px) {
  .container {
    grid-template-columns: 1fr;
    gap: 40px;
    height: auto;
  }
}
</style>
