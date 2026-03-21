<template>
  <div class="task-list-page">
    <div class="page-header">
      <div class="header-left">
        <el-button text type="primary" :icon="ArrowLeft" @click="goToWorkspace" class="back-button">
          返回工作台
        </el-button>
        <div class="header-text">
          <h1 class="page-title">任务列表</h1>
          <p class="page-subtitle">管理您的所有任务</p>
        </div>
      </div>
      <el-button type="primary" :icon="Plus" @click="showCreateForm">
        创建任务
      </el-button>
    </div>
    
    <div class="page-filters">
      <el-radio-group v-model="statusFilter" size="large" @change="handleFilterChange">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="pending">待处理</el-radio-button>
        <el-radio-button label="in_progress">进行中</el-radio-button>
        <el-radio-button label="completed">已完成</el-radio-button>
        <el-radio-button label="rejected">已拒绝</el-radio-button>
      </el-radio-group>
    </div>
    
    <div class="page-content">
      <el-empty
        v-if="!taskStore.loading && filteredTasks.length === 0"
        description="暂无任务"
        :image-size="120"
      />
      
      <div v-else class="task-grid">
        <TaskCard
          v-for="task in filteredTasks"
          :key="task.id"
          :task="task"
          @edit="handleEdit"
          @delete="handleDelete"
        />
      </div>
      
      <el-skeleton v-if="taskStore.loading" :rows="3" animated />
    </div>
    
    <TaskForm
      v-model="formVisible"
      :task="editingTask"
      @submit="handleFormSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import TaskCard from '@/components/TaskCard.vue'
import TaskForm from '@/components/TaskForm.vue'
import { useTaskStore } from '@/stores/task'
import type { Task, TaskStatus } from '@/types'

const router = useRouter()
const taskStore = useTaskStore()

const formVisible = ref(false)
const editingTask = ref<Task | undefined>()
const statusFilter = ref<TaskStatus | 'all'>('all')

const filteredTasks = computed(() => {
  return taskStore.filteredTasks
})

onMounted(() => {
  taskStore.fetchTasks()
})

const showCreateForm = () => {
  editingTask.value = undefined
  formVisible.value = true
}

const handleEdit = (task: Task) => {
  editingTask.value = task
  formVisible.value = true
}

const handleDelete = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务"${task.title}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await taskStore.deleteTask(task.id)
  } catch (error) {
    // 用户取消删除
  }
}

const handleFormSubmit = async (data: any) => {
  try {
    if (editingTask.value) {
      await taskStore.updateTask(editingTask.value.id, data)
    } else {
      await taskStore.createTask(data)
    }
    await taskStore.fetchTasks(true)
    formVisible.value = false
    editingTask.value = undefined
  } catch (error: any) {
    console.error('提交失败:', error)
  }
}

const handleFilterChange = (value: TaskStatus | 'all') => {
  taskStore.setStatusFilter(value)
  taskStore.fetchTasks(true)
}

const goToWorkspace = () => {
  router.push('/user/workspace')
}
</script>

<style lang="scss" scoped>
.task-list-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-button {
  margin-right: 8px;
}

.header-text {
  flex: 1;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #86868B;
  margin: 0;
}

.page-filters {
  margin-bottom: 24px;
  padding: 20px;
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.page-content {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
}
</style>

