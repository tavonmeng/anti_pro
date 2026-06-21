<template>
  <div class="contractor-dashboard">
    <div class="dashboard-container">
      <Sidebar class="dashboard-sidebar" />
      <div class="dashboard-content">
        <header class="contractor-topbar">
          <div class="topbar-actions">
            <div class="date-pill">
              <span class="date-number">{{ currentDay }}</span>
              <span class="date-copy">{{ currentMonth }}<br>{{ currentWeekday }}</span>
              <el-icon class="date-icon" :size="18"><Calendar /></el-icon>
            </div>
            <NotificationBell class="contractor-notification" />
            <button class="user-pill" type="button" @click="router.push('/contractor/profile')">
              <span class="avatar-mark">{{ userInitial }}</span>
              <span>
                <strong>{{ displayName }}</strong>
                <small>承包商伙伴</small>
              </span>
            </button>
          </div>
        </header>

        <main class="contractor-workspace">
          <router-view />
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Calendar } from '@element-plus/icons-vue'
import Sidebar from '@/components/Sidebar.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const now = new Date()
const currentDay = computed(() => String(now.getDate()).padStart(2, '0'))
const currentMonth = computed(() => now.toLocaleDateString('zh-CN', { month: 'long' }))
const currentWeekday = computed(() => now.toLocaleDateString('zh-CN', { weekday: 'long' }))
const displayName = computed(() =>
  authStore.user?.realName ||
  authStore.user?.username ||
  authStore.user?.phone ||
  '承包商'
)
const userInitial = computed(() => displayName.value.slice(0, 1).toUpperCase())
</script>

<style lang="scss" scoped>
.contractor-dashboard {
  width: 100%;
  min-height: 100vh;
  background: #FFFFFF;
}

.dashboard-container {
  display: flex;
  height: 100vh;
}

.dashboard-sidebar {
  width: 292px;
  flex-shrink: 0;
}

.dashboard-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0 0 28px;
  background: #FFFFFF;
}

.contractor-topbar {
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 24px;
  padding-right: 28px;
  margin-bottom: 18px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.date-pill {
  height: 58px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px 0 8px;
  border-radius: 29px;
  background: #F8F7F5;
  color: #121212;
}

.date-number {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #FFFFFF;
  border: 1px solid rgba(18, 18, 18, 0.08);
  font-size: 22px;
  font-weight: 800;
}

.date-copy {
  min-width: 78px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.15;
}

.date-icon {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid rgba(18, 18, 18, 0.18);
  color: #121212;
}

.contractor-notification {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #FFFFFF;
  box-shadow: 0 12px 28px rgba(54, 46, 39, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.user-pill {
  height: 58px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 0;
  background: transparent;
  color: #161412;
  cursor: pointer;
  padding: 0;
  text-align: left;

  strong {
    display: block;
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
    line-height: 1.15;
  }

  small {
    display: block;
    color: #7D7872;
    font-size: 12px;
    line-height: 1.2;
  }
}

.avatar-mark {
  width: 48px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #D9C8BA;
  color: #4F2F22;
  font-weight: 800;
  box-shadow: inset 0 0 0 5px #E8DDD4;
}

.contractor-workspace {
  min-height: calc(100vh - 126px);
  background: #F8F7F5;
  border-radius: 34px 0 0 0;
  overflow: hidden;
}

@media (max-width: 960px) {
  .dashboard-sidebar {
    width: 240px;
  }

  .contractor-topbar {
    align-items: stretch;
    flex-direction: column;
  }

  .topbar-actions {
    justify-content: space-between;
  }
}

@media (max-width: 720px) {
  .dashboard-container {
    height: auto;
    min-height: 100vh;
  }

  .dashboard-sidebar {
    display: none;
  }

  .dashboard-content {
    padding: 16px 0 0 16px;
  }

  .date-pill,
  .user-pill {
    display: none;
  }
}
</style>
