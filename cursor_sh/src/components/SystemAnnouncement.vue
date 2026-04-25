<template>
  <div class="announcement-wrapper">
    <div @click="togglePopover" style="display: contents;">
      <slot name="reference" :hasUnread="hasUnread">
        <div class="announcement-btn">
          <el-icon :size="20" class="announcement-icon" :class="{ 'is-unread': hasUnread }">
            <ChatDotRound />
          </el-icon>
          <span v-if="showText" :class="{ 'text-unread': hasUnread }">系统公告</span>
        </div>
      </slot>
    </div>

    <!-- Centered Dialog -->
    <el-dialog
      v-model="visible"
      title="系统公告"
      width="480px"
      append-to-body
      @open="handleShow"
      class="announcement-dialog"
    >
      <div class="announcement-panel">
        <div class="announcement-list">
          <template v-if="announcements.length > 0">
            <div
              v-for="item in announcements"
              :key="item.id"
              class="announcement-item"
            >
              <div class="announcement-header">
                <span class="announcement-title">{{ item.title }}</span>
                <span class="announcement-time">{{ formatTime(item.created_at) }}</span>
              </div>
              <div class="announcement-content">
                {{ item.content }}
              </div>
            </div>
          </template>
          <el-empty v-else description="暂无公告" :image-size="80" />
        </div>

        <div class="announcement-footer">
          <el-button type="primary" size="small" @click="visible = false">我知道了</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { announcementApi } from '@/utils/api'
import type { Announcement } from '@/utils/api'

const props = defineProps({
  showText: {
    type: Boolean,
    default: false
  }
})

const visible = ref(false)
const hasUnread = ref(false)

const announcements = ref<Announcement[]>([])

const formatTime = (timeString: string) => {
  if (!timeString) return '-'
  const date = new Date(timeString)
  if (isNaN(date.getTime())) return timeString
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const togglePopover = () => {
  visible.value = !visible.value
}

const handleShow = () => {
  if (hasUnread.value) {
    hasUnread.value = false
    const latestId = announcements.value[0]?.id
    if (latestId) {
      localStorage.setItem('last_read_announcement_id', latestId)
    }
  }
}

const fetchAnnouncements = async () => {
  try {
    const data = await announcementApi.getAnnouncements(true)
    announcements.value = Array.isArray(data) ? data : []
    if (announcements.value.length > 0) {
      const latestId = announcements.value[0].id
      const lastReadId = localStorage.getItem('last_read_announcement_id')
      if (lastReadId !== latestId) {
        hasUnread.value = true
      }
    }
  } catch (error) {
    console.error('Failed to fetch announcements:', error)
  }
}

onMounted(() => {
  fetchAnnouncements()
})

</script>

<style lang="scss" scoped>
.announcement-btn {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #86868b;
  transition: color 0.3s;
  
  &:hover {
    color: #1d1d1f;
  }
}

.announcement-icon {
  color: #86868b;
  transition: all 0.3s ease;
  
  &.is-unread {
    color: #f56c6c; /* 未读时显红色 */
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

.announcement-panel {
  .announcement-list {
    max-height: 400px;
    overflow-y: auto;
    
    .announcement-item {
      padding: 16px;
      margin-bottom: 12px;
      background-color: #f8f9fa;
      border-radius: 8px;
      border: 1px solid #ebeef5;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .announcement-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        
        .announcement-title {
          font-size: 15px;
          font-weight: 600;
          color: #303133;
        }
        
        .announcement-time {
          font-size: 12px;
          color: #909399;
        }
      }
      
      .announcement-content {
        font-size: 13px;
        color: #606266;
        line-height: 1.6;
        white-space: pre-line;
      }
    }
  }
  
  .announcement-footer {
    display: flex;
    justify-content: center;
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid #f0f0f0;
  }
}
</style>
