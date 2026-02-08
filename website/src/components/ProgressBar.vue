<template>
  <div class="progress-container">
    <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
  </div>
</template>

<script setup>
defineProps({
  progress: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.progress-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  z-index: var(--z-progress);
  pointer-events: none;
}

.progress-bar {
  height: 100%;
  background: #fff;
  width: 0%;
  transition: width 0.1s linear;
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}
</style>
