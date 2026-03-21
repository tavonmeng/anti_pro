<template>
  <div class="top-navbar">
    <div class="nav-left">
      <div class="logo">
        <svg viewBox="0 0 100 100" class="logo-svg">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#1D1D1F" stroke-width="2" />
          <path d="M 30 50 L 45 65 L 70 35" fill="none" stroke="#1D1D1F" stroke-width="3" />
        </svg>
        <span class="logo-text">AI设计任务管理系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        mode="horizontal"
        class="main-menu"
        :ellipsis="false"
        @select="handleMenuSelect"
      >
        <el-menu-item index="workspace">
          <el-icon><Grid /></el-icon>工作台
        </el-menu-item>
        <el-menu-item index="orders">
          <el-icon><Document /></el-icon>我的订单
        </el-menu-item>
      </el-menu>
    </div>
    
    <div class="nav-right">
      <NotificationBell class="notification-bell" />
      
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-profile">
          <el-avatar :size="36" class="user-avatar">{{ userInitial }}</el-avatar>
          <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
          <el-icon class="dropdown-icon"><CaretBottom /></el-icon>
        </div>
        
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><Setting /></el-icon>个人设置
            </el-dropdown-item>
            <el-dropdown-item divided command="logout" class="logout-text">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Grid, Document, Setting, SwitchButton, CaretBottom } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import NotificationBell from './NotificationBell.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const userInitial = computed(() => {
  const name = authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const activeMenu = computed(() => {
  const path = route.path
  if (path.includes('/workspace')) return 'workspace'
  if (path.includes('/orders') || path.includes('/create-order')) return 'orders'
  return route.name as string
})

const handleMenuSelect = (index: string) => {
  if (index === 'workspace') {
    router.push('/user/workspace')
  } else if (index === 'orders') {
    router.push('/user/orders')
  }
}

const handleCommand = async (command: string) => {
  if (command === 'profile') {
    router.push('/user/profile')
  } else if (command === 'logout') {
    await authStore.logout()
    router.push('/login')
  }
}
</script>

<style lang="scss" scoped>
.top-navbar {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0,0,0,0.02);
}

.nav-left {
  display: flex;
  align-items: center;
  flex: 1;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-right: 48px;
  
  .logo-svg {
    width: 28px;
    height: 28px;
  }
  
  .logo-text {
    font-size: 18px;
    font-weight: 700;
    color: #1D1D1F;
    letter-spacing: 0.5px;
  }
}

.main-menu {
  border-bottom: none;
  flex: 1;
  height: 64px;
  
  :deep(.el-menu-item) {
    font-size: 15px;
    font-weight: 500;
    height: 64px;
    line-height: 64px;
    color: #4B5563;
    padding: 0 20px;
    
    &.is-active {
      color: #1D1D1F;
      border-bottom: 2px solid #1D1D1F;
      font-weight: 600;
    }
    
    &:hover {
      color: #1D1D1F;
      background-color: transparent;
    }
  }
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.notification-bell {
  margin-right: 8px;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: all 0.2s ease;
  
  &:hover {
    background: #F3F4F6;
  }
}

.user-avatar {
  background: #1D1D1F;
  color: #fff;
  font-weight: 600;
  font-size: 16px;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #1D1D1F;
}

.dropdown-icon {
  font-size: 12px;
  color: #6B7280;
}

.logout-text {
  color: #FF3B30;
}
</style>
