<template>
  <section id="hero" class="hero-section">
    
    <!-- 视频背景 -->
    <div class="video-container">
      <video class="hero-video" autoplay muted loop playsinline>
        <source src="/video1.mp4" type="video/mp4">
        Your browser does not support the video tag.
      </video>
      <div class="video-overlay"></div>
    </div>
    
    <div class="hero-container">
      <div class="hero-content">
        <h1 class="hero-title hover-target">
          Let's Create<br>
          <span class="outline-text hover-target">Something</span><br>
          <span class="hover-target">Extraordinary</span>
        </h1>
      </div>
    </div>

    <!-- Detached subtitle: Bottom Right -->
    <div class="subtitle-group">
      <p class="hero-subtitle hover-target">
        DIGITAL EXPERIENCE & CREATIVE 3D<br>ENGINEERING
      </p>
      
      <!-- Arrow line indicator -->
      <div class="scroll-line-container">
        <div class="scroll-line"></div>
        <div class="scroll-arrow">↓</div>
      </div>
    </div>

    <!-- Scroll Indicator Detached to sit perfectly at bottom center -->
    <!-- <div class="scroll-indicator">
      <span class="hover-target">Scroll Down</span>
    </div> -->
  </section>
</template>

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  // Hero Section mounted
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
