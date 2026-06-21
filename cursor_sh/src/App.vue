<template>
  <router-view />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const refreshProfileWhenActive = () => {
  if (document.visibilityState === 'hidden') return
  if (!authStore.isAuthenticated()) return
  void authStore.refreshCurrentUser()
}

onMounted(() => {
  refreshProfileWhenActive()
  window.addEventListener('focus', refreshProfileWhenActive)
  document.addEventListener('visibilitychange', refreshProfileWhenActive)
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', refreshProfileWhenActive)
  document.removeEventListener('visibilitychange', refreshProfileWhenActive)
})
</script>

<style lang="scss">
#app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}
</style>
