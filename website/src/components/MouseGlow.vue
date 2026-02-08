<template>
  <div class="mouse-glow" :style="glowStyle"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  active: { type: Boolean, default: false }
})

const glowStyle = computed(() => ({
  left: `${props.x}px`,
  top: `${props.y}px`,
  opacity: props.active ? 1 : 0
}))
</script>

<style scoped>
.mouse-glow {
  position: fixed; /* 或 absolute，取决于使用场景 */
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--color-glow) 0%, transparent 70%);
  transform: translate(-50%, -50%); /* 居中 */
  pointer-events: none; /* 不阻挡鼠标事件 */
  transition: opacity 0.3s ease;
  z-index: var(--z-glow);
  mix-blend-mode: screen; /* 增强光晕效果 */
}
</style>
