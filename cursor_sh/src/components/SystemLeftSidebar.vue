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
        
        <!-- Ongoing projects listing when in overview -->
        <div class="ongoing-projects-nav" v-if="!uiStore.isSidebarCollapsed && uiStore.activeModule === '' && ongoingOrders.length > 0">
          <transition name="fade" mode="out-in">
            <div 
              class="active-order-box" 
              :key="currentOrder?.id"
              v-if="currentOrder"
              @click="router.push(`/user/orders/${currentOrder.id}`)"
            >
              <div class="box-header">
                <el-icon><Document /></el-icon>
                <span class="truncate">{{ getOrderName(currentOrder) }}</span>
              </div>
              <div class="box-status">
                <span class="status-dot"></span>
                {{ getStatusText(currentOrder.status) }}
              </div>
            </div>
          </transition>
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
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Grid, Setting, Bell, Help, House, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'
import NotificationBell from '@/components/NotificationBell.vue'
import { useUiStore } from '@/stores/ui'
import { useOrderStore } from '@/stores/order'
import { Document } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()
const orderStore = useOrderStore()

const ongoingOrders = computed(() => {
  return orderStore.orders.filter(o => o.status !== 'completed' && o.status !== 'cancelled')
})

const currentOrderIndex = ref(0)
let orderInterval: any = null

onMounted(() => {
  orderInterval = setInterval(() => {
     if (ongoingOrders.value.length > 1) {
       currentOrderIndex.value = (currentOrderIndex.value + 1) % ongoingOrders.value.length
     } else {
       currentOrderIndex.value = 0
     }
  }, 4000) // Switch every 4 seconds
})

onUnmounted(() => {
   if (orderInterval) clearInterval(orderInterval)
})

const currentOrder = computed(() => {
   if (ongoingOrders.value.length === 0) return null
   if (currentOrderIndex.value >= ongoingOrders.value.length) {
     currentOrderIndex.value = 0
   }
   return ongoingOrders.value[currentOrderIndex.value]
})

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    'pending_assign': '等待接单',
    'in_production': '制作生产中',
    'pending_review': '内部待审核',
    'preview_ready': '初稿待您确认',
    'revision_needed': '修改中',
    'final_preview': '终稿确认'
  }
  return map[status] || status
}

const getOrderName = (order: any) => {
  if (order.title) return order.title
  const typeMap: Record<string, string> = {
    'video_purchase': '裸眼3D成片购买',
    'ai_3d_custom': 'AI裸眼3D定制',
    'digital_art': '数字艺术定制'
  }
  return typeMap[order.orderType] || order.id.slice(0, 8)
}

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
  width: 220px;
  height: 100vh;
  background: #f6f3f2;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-right: none;
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
  display: none; /* Hide header completely to pull icons up */
}

.system-sidebar.is-collapsed .user-profile-top {
  padding: 0;
  justify-content: center;
  border-radius: 50%;
  box-shadow: none;
  background: transparent;
  width: 40px;
  margin: 0 auto 16px auto; /* Reduce bottom margin, auto horizontal */
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
  font-size: 12px;
  font-weight: 700;
  color: #1b1b1c;
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
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(27, 27, 28, 0.04);
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 13px;
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
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 40px;
  padding: 0 16px;
  border-radius: 20px;
  cursor: pointer;
  color: #414754;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.nav-item .el-icon {
  font-size: 16px;
  color: #1b1b1c;
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

.ongoing-projects-nav {
  padding: 0 16px;
  margin-top: 12px;
}

.active-order-box {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.08); /* Clean Figma border */
  border-radius: 8px; /* Figma tile */
  padding: 10px 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.2s ease;
}

.active-order-box:hover {
  border-color: rgba(0, 0, 0, 0.25);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.box-header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #1b1b1c;
  font-size: 13px;
  font-weight: 600;
}

.box-header .el-icon {
  color: #0071e3; /* Apple active blue */
  font-size: 14px;
}

.box-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #646a78;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #0071e3; 
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
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
