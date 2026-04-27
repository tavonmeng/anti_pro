<template>
  <div class="system-sidebar" :class="{ 'is-collapsed': uiStore.isSidebarCollapsed }">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-text">欢迎来到Unique Video<br>AI设计平台</span>
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
        <div 
          class="nav-item" 
          :class="{ active: activeMenu === 'drafts' }" 
          @click="navigate('drafts')"
        >
          <el-icon><EditPen /></el-icon>
          <span v-if="!uiStore.isSidebarCollapsed">Drafts</span>
          <el-badge v-if="draftCount > 0 && !uiStore.isSidebarCollapsed" :value="draftCount" :max="99" class="draft-nav-badge" />
        </div>
        
        <!-- Ongoing projects listing when in overview -->
        <div class="ongoing-projects-nav" v-if="!uiStore.isSidebarCollapsed && uiStore.activeModule === '' && ongoingOrders.length > 0">
          <div class="orders-stack-container" @mouseenter="pauseRotation" @mouseleave="resumeRotation">
            <div 
              v-for="order in ongoingOrders"
              :key="order.id"
              class="active-order-box figma-upgrade-card" 
              :style="getStackStyle(order)"
              @click="handleStackClick(order)"
            >
              <div class="card-icon-wrap" :style="{ opacity: getVisualIndex(order) === 0 ? 1 : 0.5 }">
                <el-icon><Document /></el-icon>
              </div>
              <div class="card-text-wrap">
                <div class="card-title truncate">{{ getOrderName(order) }}</div>
                <div class="card-subtitle">
                  <span class="status-dot"></span>
                  {{ getStatusText(order.status) }}
                </div>
              </div>
              <button class="card-action-btn" @click.stop="router.push(`/user/orders/${order.id}`)">View order</button>
            </div>

            <!-- Pagination dots over stack -->
            <div class="stack-pagination" v-if="ongoingOrders.length > 1">
              <span 
                v-for="(_, idx) in ongoingOrders" 
                :key="idx" 
                class="stack-dot"
                :class="{ active: idx === currentOrderIndex }"
                @click.stop="goToIndex(idx)"
              ></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      <div class="bottom-nav">
        <!-- 企业认证提示模块（已认证后消失） -->
        <div class="auth-prompt-card" v-if="!uiStore.isSidebarCollapsed && authStore.user?.enterprise_status !== 'approved'">
          <div class="auth-icon-wrap">
            <el-icon><Top /></el-icon>
          </div>
          <div class="auth-text" v-if="!authStore.user?.enterprise_status || authStore.user?.enterprise_status === 'none'">
            完成企业认证，解锁更多功能。
          </div>
          <div class="auth-text" v-else-if="authStore.user?.enterprise_status === 'pending'">
            企业认证审核中，请耐心等待。
          </div>
          <div class="auth-text" v-else-if="authStore.user?.enterprise_status === 'rejected'">
            认证被退回，请修正后重新提交。
          </div>
          <button class="auth-btn" @click="handleAuthClick">
            {{ authStore.user?.enterprise_status === 'pending' ? '查看进度' : '去认证' }}
          </button>
        </div>

        <!-- 公告 -->
        <SystemAnnouncement :show-text="!uiStore.isSidebarCollapsed">
          <template #reference="{ hasUnread }">
            <div class="nav-item">
              <el-icon class="announcement-icon-btn" :class="{ 'is-unread': hasUnread }">
                <ChatDotRound />
              </el-icon>
              <span v-if="!uiStore.isSidebarCollapsed" :class="{ 'text-unread': hasUnread }">Announcements</span>
            </div>
          </template>
        </SystemAnnouncement>


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
        <div class="nav-item" @click="navigate('profile')" style="margin-top: 8px;">
          <div class="avatar-wrap" style="width: 16px; display: flex; justify-content: center; align-items: center; position: relative;">
            <el-avatar :size="24" class="user-avatar" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png">{{ userInitial }}</el-avatar>
            <span v-if="authStore.isEnterprise()" class="enterprise-star">★</span>
          </div>
          <span v-if="!uiStore.isSidebarCollapsed">{{ authStore.user?.username || '用户' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Grid, Bell, Help, House, SwitchButton, EditPen, ChatDotRound, MoreFilled, User, Top } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'
import NotificationBell from '@/components/NotificationBell.vue'
import SystemAnnouncement from '@/components/SystemAnnouncement.vue'
import { useUiStore } from '@/stores/ui'
import { useOrderStore } from '@/stores/order'
import { Document } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()
const orderStore = useOrderStore()

const ongoingOrders = computed(() => {
  return orderStore.orders.filter(o => o.status !== 'completed' && o.status !== 'cancelled' && o.status !== 'draft')
})

const draftCount = computed(() => orderStore.orderStats.draft)

const currentOrderIndex = ref(0)
const animatingOutId = ref<string | null>(null)
let orderInterval: any = null

const advanceToNext = () => {
  const currentList = ongoingOrders.value;
  if (currentList.length <= 1) return;
  
  animatingOutId.value = currentList[currentOrderIndex.value].id;
  currentOrderIndex.value = (currentOrderIndex.value + 1) % currentList.length;

  setTimeout(() => {
    animatingOutId.value = null; // Snap back quietly
  }, 400); 
}

const goToIndex = (idx: number) => {
  if (idx === currentOrderIndex.value) return;
  const currentList = ongoingOrders.value;
  animatingOutId.value = currentList[currentOrderIndex.value].id;
  currentOrderIndex.value = idx;
  
  setTimeout(() => {
    animatingOutId.value = null; 
  }, 400);
}

const startRotation = () => {
  if (orderInterval) clearInterval(orderInterval)
  orderInterval = setInterval(() => {
     advanceToNext();
  }, 10000) // Much slower rotation (10s)
}

const pauseRotation = () => {
  if (orderInterval) clearInterval(orderInterval)
}

const resumeRotation = () => {
  startRotation()
}

onMounted(() => {
  startRotation()
})

onUnmounted(() => {
   if (orderInterval) clearInterval(orderInterval)
})

// Visual stacking logic for horizontal right-stack display
const getVisualIndex = (order: any) => {
  if (order.id === animatingOutId.value) return -100; // Special magic index for sliding out
  
  const list = ongoingOrders.value;
  if (!list.length) return -1;
  const realIndex = list.findIndex(o => o.id === order.id);
  // Calculate index offset simulating a cyclic deck of cards
  const rawDiff = realIndex - currentOrderIndex.value;
  return rawDiff >= 0 ? rawDiff : rawDiff + list.length;
}

const getStackStyle = (order: any) => {
  const vIndex = getVisualIndex(order);
  
  if (vIndex === -100) {
    return {
       position: 'absolute', top: 0, left: 0, right: 0,
       transform: 'translateX(-120%) scale(0.85) rotate(-4deg)', /* Swipe Left Out */
       opacity: 0,
       zIndex: 20, /* Keep top precedence during animation */
       pointerEvents: 'none',
       transition: 'all 0.4s cubic-bezier(0.25, 1, 0.3, 1)',
       visibility: 'visible'
    }
  }

  if (vIndex === -1) return { display: 'none' };
  
  if (vIndex > 2) {
    return {
      position: 'absolute', top: 0, left: 0, right: 0,
      opacity: 0,
      transform: 'translateY(24px) scale(0.8)',
      pointerEvents: 'none',
      zIndex: 0,
      transition: animatingOutId.value === order.id ? 'none' : 'all 0.4s cubic-bezier(0.25, 1, 0.3, 1)',
      visibility: 'hidden'
    }
  }
  
  // Top card: vIndex = 0. Further cards shift strictly downward and scale down to reveal edge.
  const yOffset = vIndex * 14; // Push downwards
  const scale = 1 - (vIndex * 0.05); 
  const zIndex = 10 - vIndex; 
  const opacity = vIndex === 0 ? 1 : (vIndex === 1 ? 0.8 : 0.4)

  return {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    transform: `translateY(${yOffset}px) scale(${scale})`,
    transformOrigin: 'top center', /* Pin top scaling so translation pushes it cleanly downwards */
    zIndex,
    opacity,
    pointerEvents: vIndex === 0 ? 'auto' : (vIndex === 1 ? 'auto' : 'none'),
    visibility: 'visible',
    transition: animatingOutId.value === order.id ? 'none' : 'all 0.4s cubic-bezier(0.25, 1, 0.3, 1)'
  }
}

const handleStackClick = (order: any) => {
  const vIndex = getVisualIndex(order);
  if (vIndex === 1 || vIndex === 2) {
    advanceToNext();
  }
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    'draft': '草稿',
    'pending_assign': '等待接单',
    'pending_contract': '合同与付款',
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
  if (path.includes('/drafts')) return 'drafts'
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
  else if (name === 'drafts') router.push('/user/drafts')
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

const handleAuthClick = () => {
  // Enterprise authentication logic can be implemented here
  router.push('/user/profile') // Navigate to profile or specific auth page
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
  padding: 0; /* Fully flushed with the container for a tighter look */
  margin-top: 12px;
}

.orders-stack-container {
  position: relative;
  height: 140px; /* Base height for the stacked cards area */
  cursor: pointer;
  perspective: 1000px;
}

.active-order-box.figma-upgrade-card {
  background: #f7f7f8; /* Soft light gray similar to the Figma upgrade card */
  border: 1px solid rgba(0, 0, 0, 0.05); 
  border-radius: 12px;
  padding: 12px 10px; /* Reduced internal padding to keep the box sleek */
  cursor: default; /* Action is handled by the button */
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;
  position: relative;
  text-align: center;
}

.active-order-box.figma-upgrade-card:hover {
  border-color: rgba(0, 0, 0, 0.1);
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}

.card-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0,0,0,0.08); /* Distinct circular outline */
  color: #0d99ff; /* Use primary blue inside the icon circle */
  font-size: 16px;
}

.card-text-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 100%;
}

.card-title {
  font-size: 12px;
  font-weight: 500;
  color: #1a1c1c;
  width: 100%;
}

.card-subtitle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 11px;
  color: #747474;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #0071e3; 
}

.card-action-btn {
  width: 100%;
  background: #0d99ff; /* Figma blue */
  color: #ffffff;
  border: none;
  padding: 6px 0; /* Flatter button */
  border-radius: 6px;
  font-size: 11px; /* More refined typography */
  font-weight: 600;
  cursor: pointer;
  margin-top: 2px;
  transition: transform 0.15s ease, background 0.2s ease;
}

.card-action-btn:hover {
  background: #0a8bed;
  transform: scale(0.98);
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

.stack-pagination {
  position: absolute;
  bottom: -16px;
  left: 0;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
}

.stack-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: all 0.2s ease;
}

.stack-dot.active {
  background: #000000;
  transform: scale(1.2);
}

.sidebar-footer {
  padding: 0 16px 32px 16px;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}
.bottom-nav {
  display: flex;
  flex-direction: column;
  gap: 4px; /* Compressed */
}

/* Auth Prompt Card */
.auth-prompt-card {
  background: #f4f4f5;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 12px;
}

.auth-icon-wrap {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid #1a1a1a;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 12px;
}

.auth-icon-wrap .el-icon {
  font-size: 14px;
  color: #1a1a1a;
}

.auth-text {
  font-size: 13px;
  color: #1a1a1a;
  line-height: 1.4;
  margin-bottom: 16px;
}

.auth-btn {
  width: 100%;
  background: #0d99ff; /* Bright blue */
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.auth-btn:hover {
  opacity: 0.9;
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



.draft-nav-badge {
  margin-left: auto;
  :deep(.el-badge__content) {
    font-size: 10px;
    height: 16px;
    line-height: 16px;
    padding: 0 5px;
    background: #0071e3;
  }
}

.announcement-icon-btn {
  transition: all 0.3s ease;
  
  &.is-unread {
    color: #f56c6c !important;
    animation: heartbeat 2s infinite;
  }
}

.text-unread {
  color: #f56c6c;
  font-weight: 500;
}

@keyframes heartbeat {
  0% { transform: scale(1); }
  10% { transform: scale(1.15); }
  20% { transform: scale(1); }
  30% { transform: scale(1.15); }
  40% { transform: scale(1); }
  100% { transform: scale(1); }
}

.enterprise-star {
  position: absolute;
  bottom: -2px;
  right: -6px;
  font-size: 10px;
  color: #f5a623;
  text-shadow: 0 0 2px rgba(0,0,0,0.2);
  line-height: 1;
}
</style>
