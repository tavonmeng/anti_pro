<template>
  <div class="system-sidebar" :class="{ 'is-collapsed': uiStore.isSidebarCollapsed }">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-text">欢迎来到Unique Video<br>AI设计平台</span>
      </div>
    </div>
    
    <div class="user-profile-top">
      <el-avatar :size="32" class="user-avatar" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png">{{ userInitial }}</el-avatar>
      <div class="user-info" v-if="!uiStore.isSidebarCollapsed">
        <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
      </div>
    </div>
    
    <div class="sidebar-content">
      <div class="nav-section">
        <div 
          class="nav-item" 
          :class="{ active: activeMenu === 'workspace' }" 
          @click="navigate('workspace')"
        >
          <el-icon><House /></el-icon>
          <span v-if="!uiStore.isSidebarCollapsed">Home</span>
        </div>
        <div 
          class="nav-item" 
          :class="{ active: activeMenu === 'orders' }" 
          @click="navigate('orders')"
        >
          <el-icon><Grid /></el-icon>
          <span v-if="!uiStore.isSidebarCollapsed">My Orders</span>
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      <div class="bottom-nav">
        <div 
          class="nav-item" 
          :class="{ active: activeMenu === 'profile' }" 
          @click="navigate('profile')"
        >
          <el-icon><Setting /></el-icon>
          <span v-if="!uiStore.isSidebarCollapsed">User Settings</span>
        </div>
        <NotificationBell>
          <template #reference="{ unreadCount }">
            <div class="nav-item">
              <el-badge :value="unreadCount" :max="99" :hidden="!unreadCount || unreadCount === 0">
                <el-icon><Bell /></el-icon>
              </el-badge>
              <span v-if="!uiStore.isSidebarCollapsed">Notifications</span>
            </div>
          </template>
        </NotificationBell>
        <div class="nav-item" @click="showHelp">
          <el-icon><Help /></el-icon>
          <span v-if="!uiStore.isSidebarCollapsed">Help</span>
        </div>
        <div class="nav-item logout-nav" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          <span v-if="!uiStore.isSidebarCollapsed">Logout</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Grid, Setting, Bell, Help, House, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'
import NotificationBell from '@/components/NotificationBell.vue'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()

const userInitial = computed(() => {
  const name = authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const activeMenu = computed(() => {
  const path = route.path
  if (path.includes('/workspace')) return 'workspace'
  if (path.includes('/orders') || path.includes('/create-order')) return 'orders'
  if (path.includes('/profile')) return 'profile'
  return route.name as string
})

const navigate = async (name: string) => {
  if (name === 'workspace') {
    uiStore.setSecondarySidebar(false)
    uiStore.toggleSidebar(false)
    uiStore.setActiveModule('')
    uiStore.setIsAiExpanded(false)
    await router.push('/user/workspace')
  }
  else if (name === 'orders') router.push('/user/orders')
  else if (name === 'profile') router.push('/user/profile')
}

const showHelp = () => {
  ElMessageBox.alert(
    '请您联系我们的设计专家<br>电话：400-888-8888<br>邮件：support@uniquevideo.com',
    '帮助与支持',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '确定'
    }
  )
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    // catch cancel action gracefully
  }
}
</script>

<style scoped>
.system-sidebar {
  width: 220px; /* Compressed width */
  height: 100vh;
  background: #f6f3f2; /* surface-container-low */
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-right: none; /* No-line rule */
  padding: 24px 0;
  box-sizing: border-box;
  transition: width 0.3s cubic-bezier(0.25, 1, 0.3, 1);
  overflow-x: hidden;
}

.system-sidebar.is-collapsed {
  width: 80px;
}

.system-sidebar.is-collapsed .logo-text {
  display: none;
}

.system-sidebar.is-collapsed .sidebar-header {
  padding: 0 8px;
}

.system-sidebar.is-collapsed .user-profile-top {
  padding: 4px;
  justify-content: center;
  border-radius: 50%;
  box-shadow: none;
  background: transparent;
  margin: 0 16px 20px 16px;
}

.system-sidebar.is-collapsed .nav-item {
  padding: 0;
  justify-content: center;
  border-radius: 50%;
  width: 40px;
  margin: 0 auto;
}

.system-sidebar.is-collapsed .el-badge__content.is-fixed {
  right: 4px;
}

.sidebar-header {
  padding: 0 24px;
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.logo-text {
  font-size: 12px; /* Set smaller to fit */
  font-weight: 700;
  color: #1b1b1c; /* on_surface */
  letter-spacing: -0.01em;
  display: block;
  text-align: center;
  line-height: 1.4;
}

.user-profile-top {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  margin: 0 16px 20px 16px;
  border-radius: 20px; /* matched nav-item pill style */
  background: #ffffff; /* Lifted user profile card */
  box-shadow: 0 2px 8px rgba(27, 27, 28, 0.04); /* Reduced shadow and gap */
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 13px; /* Reduced */
  font-weight: 600;
  color: #1b1b1c;
}

.sidebar-content {
  flex: 1;
  padding: 0 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 4px; /* Compressed gap */
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 40px; /* Thinner height */
  padding: 0 16px;
  border-radius: 20px; /* Pill shape adjusted to height */
  cursor: pointer;
  color: #414754; /* on_surface_variant */
  font-size: 13px; /* Smaller more elegant text */
  font-weight: 500;
  transition: all 0.2s ease;
}

.nav-item .el-icon {
  font-size: 16px; /* Smaller icon */
  color: #1b1b1c; /* Black by default */
  transition: color 0.2s ease;
}

.nav-item:hover {
  background: rgba(234, 231, 231, 0.5); /* surface-container-high hover */
  color: #1b1b1c;
}

.nav-item.active {
  background: #ffffff; /* Let the active pill pop via lowest container */
  color: #0058bc; /* Primary */
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(27, 27, 28, 0.02); /* Subtle shadow for active pill */
}

.nav-item.active .el-icon {
  color: #0058bc; /* Primary color when active */
}

.sidebar-footer {
  padding: 0 16px 24px 16px;
  margin-top: auto;
}

.bottom-nav {
  display: flex;
  flex-direction: column;
  gap: 4px; /* Compressed */
}

.bottom-nav .nav-item .el-icon {
  /* color: #414754; */
  /* Remove explicit color override so it inherits from base/active rules above */
}

:deep(.nav-item .el-badge__content.is-fixed) {
  top: 8px;
  right: 14px;
}

:deep(.nav-item .el-badge) {
  display: flex;
  align-items: center;
}

.logout-nav {
  margin-top: 8px;
  color: #ba1a1a; /* Error color for distinct exit action */
}
.logout-nav:hover {
  background: #ffeeec;
  color: #ba1a1a;
}
.logout-nav .el-icon {
  color: #ba1a1a !important;
}
</style>
