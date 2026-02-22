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
    <p class="hero-subtitle hover-target">
      Digital Experience &<br>Creative 3D Engineering
    </p>

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
  font-family: 'Outfit', sans-serif;
  font-size: 8vw;
  line-height: 0.9;
  font-weight: 800;
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

.hero-subtitle {
  position: absolute;
  right: 4vw;
  bottom: 5.5vh;
  font-size: 1.5rem; /* 仅进一步缩小副标题，变得极度克制小巧 */
  font-weight: 300;
  line-height: 1.5;
  opacity: 0.7;
  text-align: right;
  z-index: 10;
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
    font-size: 15vw;
  }
}
</style>
