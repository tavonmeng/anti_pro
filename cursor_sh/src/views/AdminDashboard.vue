<template>
  <div class="admin-dashboard">
    <header class="mobile-admin-bar">
      <el-button
        class="mobile-menu-button"
        :icon="Menu"
        circle
        aria-label="打开菜单"
        @click="mobileMenuVisible = true"
      />
      <div class="mobile-title-block">
        <span class="mobile-kicker">管理后台</span>
        <strong>{{ currentPageTitle }}</strong>
      </div>
    </header>

    <div class="dashboard-container">
      <Sidebar class="dashboard-sidebar" />
      
      <div class="dashboard-content">
        <router-view />
      </div>
    </div>

    <el-drawer
      v-model="mobileMenuVisible"
      direction="ltr"
      size="282px"
      :with-header="false"
      class="admin-mobile-drawer"
    >
      <Sidebar class="mobile-sidebar" @select="mobileMenuVisible = false" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'
import Sidebar from '@/components/Sidebar.vue'

const route = useRoute()
const mobileMenuVisible = ref(false)

const pageTitleMap: Record<string, string> = {
  '/admin/orders': '订单管理',
  '/admin/customers': '客户 Memory',
  '/admin/business-data': '业务数据看板',
  '/admin/staff': '负责人管理',
  '/admin/announcements': '公告管理',
  '/admin/enterprise-review': '企业认证审核',
  '/admin/contractors': '邀请与承包商',
  '/admin/workflow-config': '工作流配置',
  '/admin/chat-records': 'AI 聊天记录',
  '/admin/human-handoffs': '转人工客户',
}

const currentPageTitle = computed(() => {
  if (route.path.startsWith('/admin/orders/') && route.path !== '/admin/orders') return '订单详情'
  return pageTitleMap[route.path] || '系统管理'
})
</script>

<style lang="scss" scoped>
.admin-dashboard {
  height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
  box-sizing: border-box;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
}

.mobile-admin-bar {
  display: none;
}

.dashboard-container {
  display: flex;
  width: 100%;
  flex: 1;
  min-height: 0;
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

:deep(.admin-mobile-drawer .el-drawer__body) {
  padding: 0;
}

.mobile-sidebar {
  width: 100%;
  height: 100%;
}

@media (max-width: 768px) {
  .admin-dashboard {
    height: 100dvh;
  }

  .mobile-admin-bar {
    height: calc(56px + env(safe-area-inset-top));
    padding: env(safe-area-inset-top) 14px 0;
    display: flex;
    align-items: center;
    gap: 12px;
    background: #fff;
    border-bottom: 1px solid #E5E7EB;
    box-shadow: 0 1px 8px rgba(15, 23, 42, 0.04);
    flex-shrink: 0;
    z-index: 20;
  }

  .mobile-menu-button {
    flex: 0 0 auto;
  }

  .mobile-title-block {
    min-width: 0;
    display: flex;
    flex-direction: column;
    line-height: 1.15;

    .mobile-kicker {
      font-size: 11px;
      color: #86868B;
      margin-bottom: 3px;
    }

    strong {
      font-size: 16px;
      font-weight: 700;
      color: #1D1D1F;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .dashboard-sidebar {
    display: none;
  }

  .dashboard-content {
    padding: 12px;
    height: 100%;
    -webkit-overflow-scrolling: touch;
  }
}
</style>
