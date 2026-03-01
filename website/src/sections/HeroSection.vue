<template>
  <section id="hero" class="hero-section">
    
    <!-- 视频背景 -->
    <div class="video-container" ref="bgRef">
      <video class="hero-video" autoplay muted loop playsinline>
        <source src="/video1.mp4" type="video/mp4">
        Your browser does not support the video tag.
      </video>
      <div class="video-overlay"></div>
    </div>
    
    <div class="hero-container">
      <div class="hero-content">
        <h1 class="hero-title hover-target">
          <span class="line-wrap"><span class="line-text" ref="textLine1">Let's Create</span></span>
          <span class="line-wrap"><span class="outline-text hover-target line-text" ref="textLine2">Something</span></span>
          <span class="line-wrap"><span class="hover-target line-text" ref="textLine3">Extraordinary</span></span>
        </h1>
      </div>
    </div>

    <!-- Detached subtitle: Bottom Right -->
    <div class="subtitle-group">
      <div class="line-wrap" style="margin-bottom: 20px;">
        <p class="hero-subtitle hover-target line-text" ref="textLine4" style="margin: 0;">
          DIGITAL EXPERIENCE & CREATIVE 3D<br>ENGINEERING
        </p>
      </div>
      
      <!-- Arrow line indicator -->
      <div class="line-wrap" style="width: 100%;">
        <div class="scroll-line-container line-text" ref="textLine5">
          <div class="scroll-line"></div>
          <div class="scroll-arrow">↓</div>
        </div>
      </div>
    </div>

    <!-- Scroll Indicator Detached to sit perfectly at bottom center -->
    <!-- <div class="scroll-indicator">
      <span class="hover-target">Scroll Down</span>
    </div> -->
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import gsap from 'gsap'

const props = defineProps({
  isLoaded: {
    type: Boolean,
    default: false
  }
})

const bgRef = ref(null)
const textLine1 = ref(null)
const textLine2 = ref(null)
const textLine3 = ref(null)
const textLine4 = ref(null)
const textLine5 = ref(null)

const playHeroAnimation = () => {
  const lines = [textLine1.value, textLine2.value, textLine3.value, textLine4.value, textLine5.value]
  
  const tl = gsap.timeline()
  
  // 视频背景在进度条展开的瞬间从小拉伸出场
  tl.fromTo(bgRef.value,
    { scale: 1.15, opacity: 0 },
    { scale: 1, opacity: 1, duration: 1.5, ease: 'power3.out' }
  )

  // 文字错落拉起遮罩显现
  tl.fromTo(lines,
    { y: '120%', opacity: 0 }, // 或者纯y位移不使用opacity以完全贴合硬件clip感觉，这里结合使用更柔和
    { y: '0%', opacity: 1, duration: 1.2, ease: 'power4.out', stagger: 0.15 },
    '-=1.0' // 在背景动画执行了一部分之后插入文字动画
  )
}

watch(() => props.isLoaded, (newVal) => {
  if (newVal) {
    playHeroAnimation()
  }
})

onMounted(() => {
  if (props.isLoaded) {
    playHeroAnimation()
  } else {
    // Hide initially until loader completes
    gsap.set([textLine1.value, textLine2.value, textLine3.value, textLine4.value, textLine5.value], { y: '120%', opacity: 0 })
    gsap.set(bgRef.value, { scale: 1.15, opacity: 0 })
  }
})
</script>

<style scoped>
.hero-section {
  position: relative;
  width: 100vw;
  height: 100vh;
  background-color: #000; /* Video fallback */
  color: #fff; /* White text on video */
  overflow: hidden;
  display: flex;
  align-items: flex-end; /* Align bottom to bring text down */
  justify-content: center;
}

.line-wrap {
  display: block;
  overflow: hidden;
  position: relative;
}

.line-text {
  display: block;
  transform: translateY(120%); /* Fallback default before JS kicks in */
  opacity: 0;
}

.video-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.hero-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Optional overlay for better text contrast if video is too bright */
.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.3); 
}

.hero-container {
  position: relative;
  width: 100%;
  max-width: 100%; /* Removing 1400px restriction to push to the real edge */
  padding: 0 2vw 4vh 2vw; /* 再砍一半底部留白（8vh -> 4vh），以及左侧留白（4vw -> 2vw），彻底推到最角落 */
  z-index: 10;
}

.hero-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.hero-title {
  font-family: 'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif;
  font-size: 7.5vw; /* Smaller by one size */
  line-height: 0.9;
  font-weight: 1000; /* Extra bold */
  text-transform: uppercase;
  margin: 0;
  letter-spacing: -0.02em;
  color: #fff; /* White text */
  mix-blend-mode: normal;
}

/* 轮廓文字样式 - Adjusted for dark background */
.outline-text {
  color: transparent;
  -webkit-text-stroke: 2px #fff; /* White stroke */
  transition: all 0.3s ease;
}

.outline-text:hover {
  color: #fff; /* Fill white on hover */
}

.subtitle-group {
  position: absolute;
  right: 6vw; /* Moved right slightly from 8vw */
  bottom: 6vh; /* Explicitly set to 6vh */
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  z-index: 10;
}

.hero-subtitle {
  font-family: 'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif;
  font-size: 1.0rem;
  font-weight: 600;
  line-height: 1.5;
  opacity: 0.7;
  text-align: left; /* Left align text */
  margin: 0 0 20px 0;
}

.scroll-line-container {
  display: flex;
  align-items: center;
  position: relative;
  opacity: 0.6;
  width: 100%; /* Matches exactly the width of the text */
}

.scroll-line {
  width: 100%; /* Exact line length matching the text width */
  height: 2px;
  background-color: #fff;
}

.scroll-arrow {
  position: absolute;
  left: calc(100% + 15px); /* Placed completely outside the text alignment */
  font-size: 1.6rem; /* Make arrow taller/larger */
  line-height: 1;
  color: #fff;
  animation: bounceDown 2s infinite;
}

@keyframes bounceDown {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-5px);
  }
  60% {
    transform: translateY(-3px);
  }
}

.scroll-indicator {
  position: absolute;
  bottom: 4vh;
  left: 4vw; /* Move to bottom left below the heading, or keep centered? Centered is usually better. Wait, I will keep it centered as before */
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 2px;
  z-index: 20;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 12vw;
  }
}
</style>
