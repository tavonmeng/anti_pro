<template>
  <section id="contact" class="contact-section">
    <div class="container">
      <p class="sub-label">有项目想法？</p>
      <h2 class="cta-heading" @mouseenter="isHover = true" @mouseleave="isHover = false">
        给我们留个消息<span class="dot" :class="{ active: isHover }">.</span>
      </h2>
      
      <div class="contact-card">
        <a href="mailto:mlm3344521@163.com" class="email-link">
          mlm3344521@163.com
        </a>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
const isHover = ref(false)
</script>

<style scoped>
.contact-section {
  padding: 160px 40px;
  background-color: #f5f5f5; /* 浅色背景 */
  color: #000;
  text-align: center;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.sub-label {
  font-size: 16px;
  color: #666;
  margin-bottom: 20px;
}

.cta-heading {
  font-size: 64px;
  font-weight: 700;
  margin-bottom: 60px;
  cursor: default;
}

.dot {
  color: var(--color-accent);
  display: inline-block;
  transition: transform 0.3s;
}

.dot.active {
  transform: translateY(-10px);
}

.contact-card {
  background: #000;
  padding: 20px 40px;
  border-radius: 4px;
  transition: transform 0.3s ease;
}

.contact-card:hover {
  transform: translateY(-5px);
}

.email-link {
  color: #fff;
  font-size: 24px;
  font-family: monospace;
}

@media (max-width: 768px) {
  .cta-heading {
    font-size: 40px;
  }
  
  .email-link {
    font-size: 18px;
  }
}
</style>
