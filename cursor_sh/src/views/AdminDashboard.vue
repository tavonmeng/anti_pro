<template>
  <div class="admin-dashboard">
    <div class="dashboard-container">
      <Sidebar class="dashboard-sidebar" />
      
      <div class="dashboard-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from '@/components/Sidebar.vue'
</script>

<style lang="scss" scoped>
.admin-dashboard {
  height: 100vh;
  width: 100%;
  display: flex;
  background-color: #f5f7fa;
  box-sizing: border-box;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
}

.dashboard-container {
  display: flex;
  width: 100%;
  height: 100%;
}

.dashboard-sidebar {
  width: 250px;
  height: 100%;
  background-color: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
  z-index: 10;
}

.dashboard-content {
  flex: 1;
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  box-sizing: border-box;
  min-width: 0;
}
</style>
