<template>
  <el-menu
    :default-active="activeMenu"
    class="sidebar-menu"
    :class="{ 'contractor-menu': isCreator }"
    :collapse="isCollapse"
    @select="handleMenuSelect"
  >
    <div class="sidebar-header" :class="{ 'contractor-header': isCreator }">
      <template v-if="isCreator">
        <div class="contractor-brand-mark">
          <img src="/landing/logo/official-mark-black.svg" alt="Unique Vision" />
        </div>
        <div class="contractor-brand-copy">
          <h2 class="sidebar-title">{{ creatorSidebarTitle(authStore.user?.role) }}</h2>
          <p>{{ creatorWorkspaceSubtitle(authStore.user?.role) }}</p>
        </div>
      </template>
      <h2 v-else class="sidebar-title">{{ isAdmin ? 'unique vision后端管理系统' : isStaff ? '服务工作台' : '用户工作台' }}</h2>
      <NotificationBell v-if="!isCreator" class="notification-bell-sidebar" />
    </div>

    <!-- 管理员菜单 -->
    <template v-if="isAdmin">
      <el-menu-item index="orders">
        <el-icon><Document /></el-icon>
        <template #title>订单管理</template>
      </el-menu-item>

      <el-menu-item index="customers">
        <el-icon><UserFilled /></el-icon>
        <template #title>客户 Memory</template>
      </el-menu-item>

      <el-menu-item index="creative-agent">
        <el-icon><EditPen /></el-icon>
        <template #title>创意 Agent</template>
      </el-menu-item>

      <el-menu-item index="business-data">
        <el-icon><DataAnalysis /></el-icon>
        <template #title>业务数据看板</template>
      </el-menu-item>
      
      <el-menu-item index="staff">
        <el-icon><User /></el-icon>
        <template #title>负责人管理</template>
      </el-menu-item>
      
      <el-menu-item index="announcements">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>公告管理</template>
      </el-menu-item>
      
      <el-menu-item index="enterprise-review">
        <el-icon><OfficeBuilding /></el-icon>
        <template #title>企业认证审核</template>
      </el-menu-item>
      
      <el-menu-item index="contractors">
        <el-icon><Suitcase /></el-icon>
        <template #title>承包商和用户邀请管理</template>
      </el-menu-item>
      
      <el-menu-item index="workflow-config">
        <el-icon><SetUp /></el-icon>
        <template #title>工作流配置</template>
      </el-menu-item>
      
      <el-menu-item index="chat-records">
        <el-icon><ChatLineSquare /></el-icon>
        <template #title>AI 聊天记录</template>
      </el-menu-item>

      <el-menu-item index="human-handoffs">
        <el-icon><ChatLineSquare /></el-icon>
        <template #title>转人工客户</template>
      </el-menu-item>
      
    </template>
    
    <!-- 制作者菜单（外部承包商 / 内部制作者共用） -->
    <template v-else-if="isCreator">
      <div class="menu-section-label">工作</div>
      <el-menu-item index="assignments" class="assignment-nav-item">
        <el-icon><Document /></el-icon>
        <template #title>我的派单</template>
      </el-menu-item>

      <div class="creator-account-menu">
        <div class="menu-section-label">账户</div>
        <el-menu-item index="profile">
          <el-icon><Setting /></el-icon>
          <template #title>个人设置</template>
        </el-menu-item>

        <div
          v-if="isContractor && profileCardVisible"
          class="contractor-profile-card"
          @click="router.push('/contractor/profile')"
        >
          <div class="profile-progress-row">
            <div class="profile-pie" :style="{ '--progress': `${profileCompletion}%` }">
              <span>{{ profileCompletion }}%</span>
            </div>
            <div>
              <strong>完善资料</strong>
              <p>补充案例与专业方向，提升接单匹配度。</p>
            </div>
          </div>
          <button type="button">查看资料</button>
        </div>

        <el-menu-item index="logout" class="logout-item">
          <el-icon><SwitchButton /></el-icon>
          <template #title>退出登录</template>
        </el-menu-item>
      </div>
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

      <el-menu-item index="drafts">
        <el-icon><EditPen /></el-icon>
        <template #title>
          <span>{{ orderDraftCopy.navLabel }}</span>
          <el-badge v-if="draftCount > 0" :value="draftCount" :max="99" class="draft-badge" />
        </template>
      </el-menu-item>
      
      <el-menu-item index="profile">
        <el-icon><Setting /></el-icon>
        <template #title>个人设置</template>
      </el-menu-item>
    </template>
    
    <el-menu-item v-if="!isCreator" index="logout" class="logout-item">
      <el-icon><SwitchButton /></el-icon>
      <template #title>退出登录</template>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Grid, Document, User, Setting, SwitchButton, EditPen, ChatDotRound, OfficeBuilding, Suitcase, SetUp, ChatLineSquare, UserFilled, DataAnalysis } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useOrderStore } from '@/stores/order'
import {
  creatorMenuRoute,
  creatorSidebarTitle,
  creatorWorkspaceSubtitle,
  isCreatorRole,
} from '@/utils/creatorAccess'
import { loginPathForRole } from '@/utils/deployment'
import { orderDraftCopy } from '@/utils/orderDraftCopy'
import request from '@/utils/request'
import NotificationBell from './NotificationBell.vue'

interface Props {
  isCollapse?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isCollapse: false
})
const emit = defineEmits<{
  (event: 'select', index: string): void
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const orderStore = useOrderStore()

const isAdmin = computed(() => authStore.isAdmin())
const isStaff = computed(() => authStore.isStaff())
const isContractor = computed(() => authStore.isContractor())
const isCreator = computed(() => isCreatorRole(authStore.user?.role))
const draftCount = computed(() => orderStore.orderStats.draft)
const profileLoaded = ref(false)
const profileCompletion = ref(0)
const profileCardVisible = computed(() => profileLoaded.value && profileCompletion.value < 100)

const isFilled = (value: unknown) => {
  if (Array.isArray(value)) return value.length > 0
  return String(value || '').trim().length > 0
}

const calculateProfileCompletion = (profile: any) => {
  const fields = [
    profile?.realName || profile?.real_name,
    profile?.company,
    profile?.specialty,
    profile?.expertise,
    profile?.email,
    profile?.address,
  ]
  const fieldScore = fields.filter(isFilled).length
  const showcaseCases = profile?.showcaseCases || profile?.showcase_cases || []
  const showcaseScore = Math.min(
    showcaseCases.filter((item: any) => item?.url && !item?.uploading).length,
    2
  )
  return Math.round(((fieldScore + showcaseScore) / 8) * 100)
}

const fetchProfileCompletion = async () => {
  if (!authStore.isContractor()) {
    profileLoaded.value = false
    profileCompletion.value = 0
    return
  }

  try {
    const profile: any = await request.get('/contractor/profile')
    profileCompletion.value = calculateProfileCompletion(profile)
  } catch {
    profileCompletion.value = 0
  } finally {
    profileLoaded.value = true
  }
}

const handleContractorProfileUpdated = () => {
  fetchProfileCompletion()
}

const activeMenu = computed(() => {
  const path = route.path
  if (path.includes('/workspace')) {
    return 'workspace'
  } else if (path.includes('/drafts')) {
    return 'drafts'
  } else if (path.includes('/orders') || path.includes('/create-order')) {
    return 'orders'
  } else if (path.includes('/profile')) {
    return 'profile'
  } else if (path.includes('/staff') && isAdmin.value) {
    return 'staff'
  } else if (path.includes('/announcements') && isAdmin.value) {
    return 'announcements'
  } else if (path.includes('/enterprise-review') && isAdmin.value) {
    return 'enterprise-review'
  } else if (path.includes('/contractors') && isAdmin.value) {
    return 'contractors'
  } else if (path.includes('/workflow-config') && isAdmin.value) {
    return 'workflow-config'
  } else if (path.includes('/chat-records') && isAdmin.value) {
    return 'chat-records'
  } else if (path.includes('/human-handoffs') && isAdmin.value) {
    return 'human-handoffs'
  } else if (path.includes('/customers') && isAdmin.value) {
    return 'customers'
  } else if (path.includes('/creative-agent') && isAdmin.value) {
    return 'creative-agent'
  } else if (path.includes('/business-data') && isAdmin.value) {
    return 'business-data'
  } else if (path.includes('/assignments') && isCreator.value) {
    return 'assignments'
  } else if (path.includes('/admin')) {
    return 'orders'
  } else if (path.includes('/staff')) {
    return 'orders'
  } else if (path.includes('/user')) {
    return 'workspace'
  }
  return route.name as string
})

const handleMenuSelect = (index: string) => {
  emit('select', index)
  if (index === 'logout') {
    handleLogout()
  } else if (index === 'workspace') {
    router.push('/user/workspace')
  } else if (index === 'orders') {
    if (authStore.isAdmin()) {
      router.push('/admin/orders')
    } else if (isCreatorRole(authStore.user?.role)) {
      router.push(creatorMenuRoute(index, authStore.user?.role))
    } else {
      router.push('/user/orders')
    }
  } else if (index === 'profile') {
    const creatorRoute = creatorMenuRoute(index, authStore.user?.role)
    if (creatorRoute) {
      router.push(creatorRoute)
    } else {
      router.push('/user/profile')
    }
  } else if (index === 'drafts') {
    router.push('/user/drafts')
  } else if (index === 'staff') {
    router.push('/admin/staff')
  } else if (index === 'announcements') {
    router.push('/admin/announcements')
  } else if (index === 'enterprise-review') {
    router.push('/admin/enterprise-review')
  } else if (index === 'contractors') {
    router.push('/admin/contractors')
  } else if (index === 'workflow-config') {
    router.push('/admin/workflow-config')
  } else if (index === 'chat-records') {
    router.push('/admin/chat-records')
  } else if (index === 'human-handoffs') {
    router.push('/admin/human-handoffs')
  } else if (index === 'customers') {
    router.push('/admin/customers')
  } else if (index === 'creative-agent') {
    router.push('/admin/creative-agent')
  } else if (index === 'business-data') {
    router.push('/admin/business-data')
  } else if (index === 'assignments') {
    router.push(creatorMenuRoute(index, authStore.user?.role) || '/contractor/assignments')
  }
}

const handleLogout = async () => {
  const previousRole = authStore.user?.role
  await authStore.logout()
  router.push(loginPathForRole(previousRole))
}

onMounted(() => {
  fetchProfileCompletion()
  window.addEventListener('contractor-profile-updated', handleContractorProfileUpdated)
})

onBeforeUnmount(() => {
  window.removeEventListener('contractor-profile-updated', handleContractorProfileUpdated)
})
</script>

<style lang="scss" scoped>
.sidebar-menu {
  height: 100%;
  border-right: 1px solid #E5E7EB;
  background: #FFFFFF;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
}

.sidebar-menu.contractor-menu {
  border-right: 0;
  background: #FFFFFF;
  padding: 26px 28px 24px;
  gap: 0;

  :deep(.el-menu-item) {
    height: 56px;
    margin: 6px 0;
    padding: 0 22px !important;
    border-radius: 28px;
    color: #494541;
    font-size: 15px;
    font-weight: 650;
    transition: all 0.2s ease;

    .el-icon {
      width: 22px;
      height: 22px;
      margin-right: 12px;
      color: inherit;
    }

    &:hover {
      background: #F3F0EC;
      color: #161412;
    }

    &.is-active {
      position: relative;
      background: #8B5E3C;
      color: #FFFFFF;
      box-shadow: 0 14px 30px rgba(139, 94, 60, 0.2);

      &::after {
        content: '';
        position: absolute;
        right: 20px;
        top: 50%;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #F3E4D7;
        transform: translateY(-50%);
      }
    }
  }

  :deep(.el-menu-item.assignment-nav-item) {
    width: 204px;
    height: 44px;
    margin: 4px 0;
    padding: 0 16px !important;
    border-radius: 22px;
    font-size: 14px;

    .el-icon {
      width: 18px;
      height: 18px;
      margin-right: 10px;
    }

    &.is-active {
      box-shadow: 0 10px 22px rgba(139, 94, 60, 0.18);

      &::after {
        right: 14px;
        width: 7px;
        height: 7px;
      }
    }
  }

  .logout-item {
    color: #7B3225;

    &:hover {
      background: #F7EFEB;
    }
  }
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.sidebar-header.contractor-header {
  padding: 0;
  border-bottom: 0;
  justify-content: flex-start;
  margin-bottom: 48px;
}

.contractor-brand-mark {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #F4F1ED;
  border: 1px solid rgba(18, 18, 18, 0.08);
  overflow: hidden;

  img {
    width: 34px;
    height: 34px;
    object-fit: contain;
    display: block;
  }
}

.contractor-brand-copy {
  min-width: 0;

  .sidebar-title {
    font-size: 22px;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: 0;
  }

  p {
    margin: 2px 0 0;
    color: #504B46;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.1;
  }
}

.sidebar-title {
  font-size: 20px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0;
  flex: 1;
  min-width: 0;
}

.menu-section-label {
  margin: 28px 0 10px;
  color: #2B2825;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0;
}

.creator-account-menu {
  width: 204px;
  margin-top: auto;
  padding-top: 18px;

  .menu-section-label {
    margin-top: 0;
  }
}

.notification-bell-sidebar {
  flex-shrink: 0;
}

.contractor-menu {
  .notification-bell-sidebar {
    margin-left: auto;
    transform: scale(0.82);
  }
}

.contractor-profile-card {
  width: 204px;
  box-sizing: border-box;
  margin: 14px 0 12px;
  padding: 16px;
  border-radius: 24px;
  background: #F4F1ED;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 36px rgba(55, 45, 38, 0.1);
  }

  strong {
    display: block;
    color: #161412;
    font-size: 20px;
    font-weight: 800;
    line-height: 1.05;
  }

  p {
    margin: 8px 0 14px;
    color: #6D6760;
    font-size: 13px;
    line-height: 1.45;
  }

  button {
    height: 40px;
    margin-top: 14px;
    padding: 0 18px;
    border: 0;
    border-radius: 20px;
    background: #8B5E3C;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }
}

.profile-progress-row {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
}

.profile-pie {
  --progress: 0%;
  width: 72px;
  height: 72px;
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: conic-gradient(#8B5E3C var(--progress), #DDD4CA 0);
  box-shadow: inset 0 0 0 1px rgba(78, 56, 40, 0.08);

  &::after {
    content: '';
    position: absolute;
    inset: 11px;
    border-radius: 50%;
    background: #F4F1ED;
  }

  span {
    position: relative;
    z-index: 1;
    color: #4F2F22;
    font-size: 16px;
    font-weight: 850;
    line-height: 1;
  }
}

.logout-item {
  margin-top: auto;
  width: 100%;
  color: #FF3B30;
  
  :deep(.el-menu-item) {
    color: #FF3B30;
    
    &:hover {
      background-color: #FFF5F5;
    }
  }
}

.draft-badge {
  margin-left: 8px;
  :deep(.el-badge__content) {
    font-size: 10px;
    height: 16px;
    line-height: 16px;
    padding: 0 5px;
    background-color: var(--uv-ws-notification-badge, #A0522D) !important;
    border-color: var(--uv-ws-notification-badge, #A0522D) !important;
  }
}
</style>
