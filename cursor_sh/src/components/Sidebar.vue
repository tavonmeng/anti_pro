<template>
  <el-menu
    :default-active="activeMenu"
    class="sidebar-menu"
    :collapse="isCollapse"
    @select="handleMenuSelect"
  >
    <div class="sidebar-header">
      <h2 class="sidebar-title">{{ isAdmin ? '订单管理系统' : isStaff ? '服务工作台' : '用户工作台' }}</h2>
      <NotificationBell class="notification-bell-sidebar" />
    </div>
    
    <!-- 管理员菜单 -->
    <template v-if="isAdmin">
      <el-menu-item index="orders">
        <el-icon><Document /></el-icon>
        <template #title>订单管理</template>
      </el-menu-item>
      
      <el-menu-item index="staff">
        <el-icon><User /></el-icon>
        <template #title>负责人管理</template>
      </el-menu-item>
    </template>
    
    <!-- 负责人菜单 -->
    <template v-else-if="isStaff">
      <el-menu-item index="orders">
        <el-icon><Document /></el-icon>
        <template #title>我的订单</template>
      </el-menu-item>
      
      <el-menu-item index="profile">
        <el-icon><Setting /></el-icon>
        <template #title>个人设置</template>
      </el-menu-item>
    </template>
    
    <!-- 用户菜单 -->
    <template v-else>
      <el-menu-item index="workspace">
        <el-icon><Grid /></el-icon>
        <template #title>工作台</template>
      </el-menu-item>
      
      <el-menu-item index="orders">
        <el-icon><Document /></el-icon>
        <template #title>我的订单</template>
      </el-menu-item>
      
      <el-menu-item index="profile">
        <el-icon><Setting /></el-icon>
        <template #title>个人设置</template>
      </el-menu-item>
    </template>
    
    <el-menu-item index="logout" class="logout-item">
      <el-icon><SwitchButton /></el-icon>
      <template #title>退出登录</template>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Grid, Document, User, Setting, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import NotificationBell from './NotificationBell.vue'

interface Props {
  isCollapse?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isCollapse: false
})

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isAdmin = computed(() => authStore.isAdmin())
const isStaff = computed(() => authStore.isStaff())

const activeMenu = computed(() => {
  const path = route.path
  if (path.includes('/workspace')) {
    return 'workspace'
  } else if (path.includes('/orders') || path.includes('/create-order')) {
    return 'orders'
  } else if (path.includes('/profile')) {
    return 'profile'
  } else if (path.includes('/staff') && isAdmin.value) {
    return 'staff'
  } else if (path.includes('/admin')) {
    return 'orders' // 管理员默认订单管理
  } else if (path.includes('/staff')) {
    return 'orders' // 负责人默认订单列表
  } else if (path.includes('/user')) {
    return 'workspace' // 用户默认工作台
  }
  return route.name as string
})

const handleMenuSelect = (index: string) => {
  if (index === 'logout') {
    handleLogout()
  } else if (index === 'workspace') {
    router.push('/user/workspace')
  } else if (index === 'orders') {
    if (authStore.isAdmin()) {
      router.push('/admin/orders')
    } else if (authStore.isStaff()) {
      router.push('/staff/orders')
    } else {
      router.push('/user/orders')
    }
  } else if (index === 'profile') {
    if (authStore.isStaff()) {
      router.push('/staff/profile')
    } else {
      router.push('/user/profile')
    }
  } else if (index === 'staff') {
    router.push('/admin/staff')
  }
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.sidebar-menu {
  height: 100%;
  border-right: 1px solid #E5E7EB;
  background: #FFFFFF;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.sidebar-title {
  font-size: 20px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0;
  flex: 1;
  min-width: 0;
}

.notification-bell-sidebar {
  flex-shrink: 0;
}

.logout-item {
  position: absolute;
  bottom: 0;
  width: 100%;
  color: #FF3B30;
  
  :deep(.el-menu-item) {
    color: #FF3B30;
    
    &:hover {
      background-color: #FFF5F5;
    }
  }
}
</style>

