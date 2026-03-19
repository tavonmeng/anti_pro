<template>
  <div ref="cursor" class="custom-cursor"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'

const cursor = ref(null)

onMounted(() => {
  gsap.set(cursor.value, { xPercent: -50, yPercent: -50, opacity: 0 })

  const onMouseMove = (e) => {
    // Check if mouse is over Header
    const isOverHeader = !!e.target.closest('.header-bar')
    
    let isVisible = false
    
    if (isOverHeader) {
      isVisible = false // Do not show cursor effect on header
    } else {
      isVisible = true // Always visible globally now
    }

    gsap.to(cursor.value, {
      x: e.clientX,
      y: e.clientY,
      opacity: isVisible ? 1 : 0,
      duration: 0.6,
      ease: 'power3.out'
    })
  }

  const onHover = () => {
    document.body.classList.add('no-cursor') // Hide native cursor when hovering interactive items
  }

  const onLeave = () => {
    document.body.classList.remove('no-cursor') // Show native cursor when not hovering interactive items
  }

  const onMouseOver = (e) => {
    // If the mouse is over the header, ensure we show the native cursor
    const isOverHeader = !!e.target.closest('.header-bar')
    if (isOverHeader) {
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
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseover', onMouseOver)
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
