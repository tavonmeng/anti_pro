<template>
  <div ref="cursor" class="custom-cursor"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'

const cursor = ref(null)

// 将事件处理器提升到模块作用域，确保 onUnmounted 可以正确移除
let onMouseMove = null
let onMouseOver = null

onMounted(() => {
  gsap.set(cursor.value, { xPercent: -50, yPercent: -50, opacity: 0 })

  const onHover = () => {
    document.body.classList.add('no-cursor')
  }

  const onLeave = () => {
    document.body.classList.remove('no-cursor')
  }

  onMouseMove = (e) => {
    // Check if mouse is over Header or Auth Modal
    const isOverHeader = !!e.target.closest('.header-bar')
    const isOverAuthModal = !!e.target.closest('.auth-modal-overlay')
    
    let isVisible = false
    
    if (isOverHeader || isOverAuthModal) {
      isVisible = false
    } else {
      isVisible = true
    }

    gsap.to(cursor.value, {
      x: e.clientX,
      y: e.clientY,
      opacity: isVisible ? 1 : 0,
      duration: 0.6,
      ease: 'power3.out'
    })
  }

  onMouseOver = (e) => {
    // If the mouse is over the header or auth modal, ensure normal cursor
    const isOverHeader = !!e.target.closest('.header-bar')
    const isOverAuthModal = !!e.target.closest('.auth-modal-overlay')
    
    if (isOverHeader || isOverAuthModal) {
      onLeave()
      return
    }

    const isInteractive = e.target.closest('.hover-target') || e.target.closest('button') || e.target.closest('a');
    
    // Check if on specific sections where text should trigger hover effect
    const isSubPage = !!document.querySelector('.case-detail-page');
    const isIntroPage = !!e.target.closest('.intro-section');
    const isTextElement = e.target.closest('p') || e.target.closest('span') || 
                         e.target.closest('h1') || e.target.closest('h2') || 
                         e.target.closest('h3') || e.target.closest('li');

    // Trigger hover if element is explicitly interactive, OR if it's text within the sub page / intro page
    if (isInteractive || ((isSubPage || isIntroPage) && isTextElement)) {
      onHover()
    } else {
      onLeave()
    }
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseover', onMouseOver)
})

onUnmounted(() => {
  // 正确移除事件监听器
  if (onMouseMove) window.removeEventListener('mousemove', onMouseMove)
  if (onMouseOver) window.removeEventListener('mouseover', onMouseOver)
  
  // 确保清除 body 上的自定义类
  document.body.classList.remove('no-cursor')
  
  // 清理 GSAP 对 cursor 元素的动画
  if (cursor.value) gsap.killTweensOf(cursor.value)
})
</script>

<style scoped>
.custom-cursor {
  position: fixed;
  top: 0;
  left: 0;
  width: 30px;
  height: 30px;
  border: 2px solid #fff;
  border-radius: 50%;
  pointer-events: none;
  z-index: 6000;
  mix-blend-mode: difference;
  transform-origin: center center;
  box-sizing: border-box;
}

/* 全局应用 cursor: none 当鼠标未处于 header 区域时生效 */
:global(body.no-cursor),
:global(body.no-cursor *) {
  cursor: none !important;
}
</style>
