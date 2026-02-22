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
      document.body.classList.remove('no-cursor')
    } else {
      isVisible = true // Always visible globally now
      document.body.classList.add('no-cursor')
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
    gsap.to(cursor.value, {
      scale: 3,
      backgroundColor: '#fff', 
      borderWidth: 0,
      duration: 0.3
    })
  }

  const onLeave = () => {
    gsap.to(cursor.value, {
      scale: 1,
      backgroundColor: 'transparent',
      borderColor: '#fff',
      borderWidth: '2px',
      duration: 0.3
    })
  }

  const onMouseOver = (e) => {
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
  z-index: 1500; /* Below menu (2000) but above most content */
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
