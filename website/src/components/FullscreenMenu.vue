<template>
  <transition name="menu-fade">
    <div 
      v-if="visible" 
      class="horizontal-menu"
      :class="{ 'scrolled': isScrolled }"
      @mouseleave="$emit('update:visible', false)"
    >
      <nav class="menu-nav">
        <a href="#hero" @click="handleLinkClick($event, 'hero')">首页</a>
        <a href="#intro" @click="handleLinkClick($event, 'intro')">产品介绍</a>
        <a href="#cases" @click="handleLinkClick($event, 'cases')">案例作品</a>
        <a href="#about" @click="handleLinkClick($event, 'about')">关于我们</a>
        <a href="#business" @click="handleLinkClick($event, 'business')">业务合作</a>
        <a href="#contact" @click="handleLinkClick($event, 'contact')">联系我们</a>
      </nav>
    </div>
  </transition>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  visible: Boolean
})

const emit = defineEmits(['update:visible'])
const isScrolled = ref(false)

const handleLinkClick = (e, id) => {
  e.preventDefault();
  const element = document.getElementById(id);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' });
  }
  emit('update:visible', false);
}

const handleScroll = () => {
  isScrolled.value = window.scrollY > 50
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.horizontal-menu {
  position: fixed;
  top: 0;
  right: 100px; /* 留出触发按钮的位置 */
  height: 80px;
  background: transparent !important;
  z-index: 5000; /* Higher than cursor (1500) to ensure clickability */
  display: flex;
  align-items: center;
  overflow: visible; /* 允许阴影或微调溢出 */
}

.menu-nav {
  display: flex;
  flex-direction: row;
  gap: 12px;
  padding: 0 20px;
  white-space: nowrap;
  transition: opacity 0.5s ease, transform 0.5s ease;
}

/* Scroll-hide behavior: menu hides when scrolled, but reappears on hover */
.horizontal-menu.scrolled .menu-nav {
  opacity: 0;
  transform: translateX(10px);
  pointer-events: none;
}

.horizontal-menu.scrolled:hover .menu-nav {
  opacity: 1;
  transform: translateX(0);
  pointer-events: auto;
}

.menu-nav a {
  font-size: 16px;
  color: #fff; /* 确保高亮可读 */
  font-weight: 500;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 8px 16px;
  border-radius: 20px;
  text-decoration: none;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5); /* 增加文字阴影以防背景太亮 */
}

.menu-nav a:hover {
  color: var(--color-accent, #00d2ff); /* 悬浮时变色 */
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

/* 简约淡入淡出动画 */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.menu-fade-enter-to,
.menu-fade-leave-from {
  opacity: 1;
  transform: translateX(0);
}

@media (max-width: 768px) {
  .horizontal-menu {
    height: 60px;
    right: 80px;
  }
  .menu-nav {
    gap: 8px;
    padding: 0 10px;
  }
  .menu-nav a {
    font-size: 14px;
    padding: 6px 12px;
  }
}
</style>
