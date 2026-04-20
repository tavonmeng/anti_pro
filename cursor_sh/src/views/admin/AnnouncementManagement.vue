<template>
  <div class="announcement-management">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">公告管理</h1>
        <p class="page-subtitle">发布和管理系统对所有用户可见的公告内容</p>
      </div>
      <el-button type="primary" @click="handleAdd">
        发布新公告
      </el-button>
    </div>

    <!-- 数据表格 -->
    <el-card class="data-card">
      <el-table :data="announcements" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="title" label="公告标题" min-width="250" />
        <el-table-column prop="is_active" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '展示中' : '已归档' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="发布时间" width="200">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">
               编辑
            </el-button>
            <el-button v-if="row.is_active" link type="warning" size="small" @click="handleToggleStatus(row)">
               归档
            </el-button>
            <el-button v-else link type="success" size="small" @click="handleToggleStatus(row)">
               恢复展示
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
               删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 公告表单弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑公告' : '发布新公告'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="formData.title" placeholder="请输入公告标题（限200字内）" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="formData.content"
            type="textarea"
            :rows="8"
            placeholder="请输入公告正文..."
          />
        </el-form-item>
        <el-form-item label="立即展示" prop="is_active">
          <el-switch v-model="formData.is_active" />
          <span class="status-tip">开启后用户立即可见</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting">
            确认
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { announcementApi } from '@/utils/api'
import type { Announcement } from '@/utils/api'

const loading = ref(false)
const announcements = ref<Announcement[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const formData = reactive({
  id: '',
  title: '',
  content: '',
  is_active: true
})

const rules = reactive<FormRules>({
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }]
})

// 格式化时间
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

// 获取公告列表 (管理员获取所有)
const fetchAnnouncements = async () => {
  loading.value = true
  try {
    const data = await announcementApi.getAnnouncements(false)
    announcements.value = data
  } catch (error: any) {
    ElMessage.error(error.message || '获取列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAnnouncements()
})

const handleAdd = () => {
  isEdit.value = false
  formData.id = ''
  formData.title = ''
  formData.content = ''
  formData.is_active = true
  dialogVisible.value = true
}

const handleEdit = (row: Announcement) => {
  isEdit.value = true
  formData.id = row.id
  formData.title = row.title
  formData.content = row.content
  formData.is_active = row.is_active
  dialogVisible.value = true
}

const handleToggleStatus = async (row: Announcement) => {
  try {
    await announcementApi.updateAnnouncement(row.id, { is_active: !row.is_active })
    ElMessage.success('状态更新成功')
    fetchAnnouncements()
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
  }
}

const handleDelete = async (row: Announcement) => {
  await ElMessageBox.confirm('确认要删除这条公告吗？', '提示', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消'
  })
  try {
    await announcementApi.deleteAnnouncement(row.id)
    ElMessage.success('删除成功')
    fetchAnnouncements()
  } catch (error: any) {
    ElMessage.error(error.message || '删除失败')
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        await announcementApi.updateAnnouncement(formData.id, {
          title: formData.title,
          content: formData.content,
          is_active: formData.is_active
        })
        ElMessage.success('更新成功')
      } else {
        await announcementApi.createAnnouncement({
          title: formData.title,
          content: formData.content,
          is_active: formData.is_active
        })
        ElMessage.success('发布成功')
      }
      dialogVisible.value = false
      fetchAnnouncements()
    } catch (error: any) {
      ElMessage.error(error.message || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
}
</script>

<style scoped>
.announcement-management {
  padding: 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px;
}
.page-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}
.data-card {
  border-radius: 12px;
}
.status-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #999;
}
</style>
