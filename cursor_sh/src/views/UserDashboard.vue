<template>
  <div class="user-dashboard">
    <TopNavbar />
    
    <div class="dashboard-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import TopNavbar from '@/components/TopNavbar.vue'
</script>

<style lang="scss" scoped>
.user-dashboard {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
  box-sizing: border-box;
}

.dashboard-content {
  flex: 1;
  overflow-y: auto;
}
</style>

