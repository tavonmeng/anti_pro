<template>
  <div class="task-card" :class="statusClass">
    <div class="task-header">
      <h3 class="task-title">{{ task.title }}</h3>
      <el-tag :type="statusTagType" size="small">{{ statusText }}</el-tag>
    </div>
    
    <p class="task-description">{{ task.description }}</p>
    
    <!-- 设计信息 -->
    <div v-if="task.designShape || task.designSize || task.is3D !== undefined || task.isCurved !== undefined" class="task-design-info">
      <div class="design-tags">
        <el-tag v-if="task.designShape" size="small" type="info">
          <el-icon><Grid /></el-icon>
          {{ getShapeText(task.designShape) }}
          <span v-if="task.designShape === 'custom' && task.customShapeText">
            ({{ task.customShapeText }})
          </span>
        </el-tag>
        <el-tag v-if="task.designSize" size="small" type="info">
          <el-icon><FullScreen /></el-icon>
          {{ getSizeText(task.designSize) }}
        </el-tag>
        <el-tag v-if="task.is3D" size="small" type="warning">
          <el-icon><View /></el-icon>
          3D
        </el-tag>
        <el-tag v-if="task.isCurved" size="small" type="success">
          <el-icon><Connection /></el-icon>
          曲面
        </el-tag>
      </div>
    </div>
    
    <div v-if="task.images && task.images.length > 0" class="task-images">
      <el-image
        v-for="(image, index) in task.images.slice(0, 3)"
        :key="index"
        :src="image"
        :preview-src-list="task.images"
        fit="cover"
        class="task-image"
      />
      <div v-if="task.images.length > 3" class="image-more">
        +{{ task.images.length - 3 }}
      </div>
    </div>
    
    <div class="task-footer">
      <div class="task-meta">
        <span class="task-user">{{ task.userName || '用户' }}</span>
        <span class="task-time">{{ formatTime(task.createdAt) }}</span>
      </div>
      
      <div class="task-actions">
        <el-button
          v-if="canEdit"
          size="small"
          text
          @click="$emit('edit', task)"
        >
          编辑
        </el-button>
        <el-button
          v-if="canDelete"
          size="small"
          text
          type="danger"
          @click="$emit('delete', task)"
        >
          删除
        </el-button>
        <el-button
          v-if="canUpdateStatus && isAdmin"
          size="small"
          text
          type="primary"
          @click="$emit('update-status', task)"
        >
          更新状态
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Grid, FullScreen, View, Connection } from '@element-plus/icons-vue'
import type { Task, DesignShape, DesignSize } from '@/types'
import { useAuthStore } from '@/stores/auth'

interface Props {
  task: Task
}

const props = defineProps<Props>()

defineEmits<{
  edit: [task: Task]
  delete: [task: Task]
  'update-status': [task: Task]
}>()

const authStore = useAuthStore()

const statusTextMap = {
  pending: '待处理',
  in_progress: '进行中',
  completed: '已完成',
  rejected: '已拒绝'
}

const statusText = computed(() => statusTextMap[props.task.status])

const statusTagType = computed(() => {
  const map: Record<string, any> = {
    pending: 'info',
    in_progress: 'warning',
    completed: 'success',
    rejected: 'danger'
  }
  return map[props.task.status] || 'info'
})

const statusClass = computed(() => `task-status-${props.task.status}`)

const canEdit = computed(() => {
  if (authStore.isAdmin()) return true
  return authStore.user?.id === props.task.userId
})

const canDelete = computed(() => {
  if (authStore.isAdmin()) return true
  return authStore.user?.id === props.task.userId && props.task.status === 'pending'
})

const canUpdateStatus = computed(() => {
  return authStore.isAdmin() && props.task.status !== 'completed'
})

const isAdmin = computed(() => authStore.isAdmin())

const getShapeText = (shape?: DesignShape) => {
  const map: Record<DesignShape, string> = {
    circle: '圆形',
    square: '正方形',
    rectangle: '长方形',
    triangle: '三角形',
    custom: '自定义'
  }
  return shape ? map[shape] : ''
}

const getSizeText = (size?: DesignSize | string) => {
  if (!size) return ''
  
  // 如果是自定义格式 custom:width*height
  if (typeof size === 'string' && size.startsWith('custom:')) {
    const dimensions = size.replace('custom:', '')
    return `自定义 ${dimensions}`
  }
  
  // 预设尺寸
  const map: Record<string, string> = {
    '1024*768': '1024 × 768',
    '800*600': '800 × 600',
    '640*680': '640 × 680',
    '1920*1080': '1920 × 1080',
    'custom': '自定义'
  }
  
  return map[size] || size
}

const formatTime = (time: string) => {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60))
      return `${minutes}分钟前`
    }
    return `${hours}小时前`
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}
</script>

<style lang="scss" scoped>
.task-card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
  border-left: 4px solid #E5E7EB;
  
  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }
  
  &.task-status-pending {
    border-left-color: #5AC8FA;
  }
  
  &.task-status-in_progress {
    border-left-color: #FF9500;
  }
  
  &.task-status-completed {
    border-left-color: #34C759;
  }
  
  &.task-status-rejected {
    border-left-color: #FF3B30;
  }
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-title {
  font-size: 18px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0;
  flex: 1;
}

.task-description {
  font-size: 14px;
  color: #86868B;
  line-height: 1.6;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.task-design-info {
  margin-bottom: 16px;
}

.design-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  
  :deep(.el-tag) {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    font-size: 12px;
    
    .el-icon {
      font-size: 14px;
    }
  }
}

.task-images {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.task-image {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  cursor: pointer;
  object-fit: cover;
}

.image-more {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  background: #F5F5F7;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #86868B;
  font-size: 14px;
  font-weight: 500;
}

.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #E5E7EB;
}

.task-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #A1A1A6;
}

.task-actions {
  display: flex;
  gap: 8px;
}
</style>

