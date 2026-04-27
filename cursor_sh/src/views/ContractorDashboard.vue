<template>
  <div class="contractor-dashboard">
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
.contractor-dashboard {
  width: 100%;
  min-height: 100vh;
  background: #F5F5F7;
}

.dashboard-container {
  display: flex;
  height: 100vh;
}

.dashboard-sidebar {
  width: 240px;
  flex-shrink: 0;
}

.dashboard-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
