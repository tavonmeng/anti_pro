<template>
  <header class="header" :class="{ 'scrolled': isScrolled }">
    <div class="logo">
      <span class="logo-icon">🛡️</span>
      <span class="logo-text">Unique Vision</span>
    </div>
    <div 
      class="menu-trigger-area"
      @mouseenter="$emit('show-menu')"
      aria-label="菜单"
    >
      <span class="menu-icon">☰</span>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const isScrolled = ref(false)

const handleScroll = () => {
  isScrolled.value = window.scrollY > 50
}

onMounted(() => window.addEventListener('scroll', handleScroll))
onUnmounted(() => window.removeEventListener('scroll', handleScroll))
</script>

<style scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 80px;
  padding: 0 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: transparent;
  z-index: 5001; /* Above menu (5000) and cursor (1500) */
  transition: background-color 0.3s ease, backdrop-filter 0.3s ease;
}

.header.scrolled {
  background: transparent !important;
  backdrop-filter: none !important;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text-primary);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-text {
  font-family: var(--font-primary);
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.header.scrolled .logo-text {
  opacity: 0;
  transform: translateX(-10px);
  pointer-events: none;
}

.menu-trigger-area {
  font-size: 24px;
  color: #fff;
  padding: 16px;
  cursor: pointer;
  transition: transform 0.2s, background 0.3s;
  border-radius: 8px;
}

.menu-trigger-area:hover {
  transform: scale(1.1);
  background: rgba(255, 255, 255, 0.1);
}

@media (max-width: 768px) {
  .header {
    padding: 0 20px;
    height: 60px;
  }
}
</style>
