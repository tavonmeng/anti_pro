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
        
        <p class="hero-subtitle hover-target">
          Digital Experience & Creative 3D Engineering
        </p>

        <div class="scroll-indicator">
          <span class="hover-target">Scroll Down</span>
        </div>
      </div>
    </div>
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
  cursor: none; /* 隐藏系统鼠标 */
  display: flex;
  align-items: center;
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
  max-width: 1400px;
  padding: 0 4vw;
  z-index: 10;
}

.hero-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.hero-title {
  font-family: 'Outfit', sans-serif;
  font-size: 10vw;
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
  font-size: 1.5rem;
  margin-top: 40px;
  font-weight: 500;
  max-width: 500px;
  line-height: 1.4;
  opacity: 0.9;
}

.scroll-indicator {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 2px;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 15vw;
  }
}
</style>
