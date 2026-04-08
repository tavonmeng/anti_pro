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
  height: 72px; /* Increased for breathing room */
  background: rgba(246, 243, 242, 0.7); /* surface-container-low with opacity */
  backdrop-filter: blur(12px); /* Glassmorphism */
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 4px 24px rgba(27, 27, 28, 0.02); /* Ambient shadow */
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
    color: #1b1b1c; /* on_surface */
    letter-spacing: -0.02em; /* Editorial hook */
  }
}

.main-menu {
  border-bottom: none;
  background: transparent;
  flex: 1;
  height: 72px;
  
  :deep(.el-menu-item) {
    font-size: 14px;
    font-weight: 500;
    height: 72px;
    line-height: 72px;
    color: #414754; /* on_surface_variant */
    padding: 0 20px;
    border-bottom: none;
    
    &.is-active {
      color: #0058bc; /* Primary */
      background: transparent;
      font-weight: 600;
      position: relative;
      
      &::after {
        content: '';
        position: absolute;
        bottom: 12px;
        left: 20px;
        right: 20px;
        height: 3px;
        border-radius: 9999px;
        background: #0058bc;
      }
    }
    
    &:hover {
      color: #1b1b1c; /* on_surface */
      background-color: rgba(234, 231, 231, 0.5); /* surface-container-high pill shape hover */
      border-radius: 8px;
      margin: 8px 0;
      height: 56px;
      line-height: 56px;
    }
    
    &.is-active:hover {
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
  gap: 12px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px; /* DEFAULT rounding */
  transition: all 0.2s ease;
  
  &:hover {
    background: #eae7e7; /* surface_container_high */
  }
}

.user-avatar {
  background: #0058bc; /* Primary */
  color: #ffffff;
  font-weight: 600;
  font-size: 16px;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #1b1b1c; /* on_surface */
}

.dropdown-icon {
  font-size: 12px;
  color: #727785; /* outline */
}

.logout-text {
  color: #ba1a1a; /* error */
}
</style>
