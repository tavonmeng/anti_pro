<template>
  <div class="announcement-management">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">公告管理</h1>
        <p class="page-subtitle">发布系统公告，并配置官网首页的重点运营入口</p>
      </div>
      <el-button type="primary" @click="handleAdd">
        发布新公告
      </el-button>
    </div>

    <el-card class="marketing-card" v-loading="barLoading">
      <template #header>
        <div class="card-header">
          <div>
            <h2 class="section-title">官网顶部运营条</h2>
            <p class="section-subtitle">展示在官网首页顶部，可用于引导访客下载服务与案例 PDF</p>
          </div>
          <el-switch
            v-model="barForm.is_active"
            active-text="展示"
            inactive-text="隐藏"
          />
        </div>
      </template>

      <el-form class="marketing-form" label-width="86px">
        <el-form-item label="标题">
          <el-input
            v-model="barForm.title"
            maxlength="200"
            show-word-limit
            placeholder="快速了解我们的服务和案例，点此处下载 PDF"
          />
        </el-form-item>
        <el-form-item label="按钮文案">
          <el-input
            v-model="barForm.button_text"
            maxlength="60"
            placeholder="下载 PDF"
          />
        </el-form-item>
        <el-form-item label="配图">
          <div class="asset-row">
            <div class="asset-preview image-preview" v-if="barForm.image_url">
              <img :src="barForm.image_url" alt="" />
            </div>
            <span class="asset-name">{{ barForm.image_url ? '已上传配图' : '未上传配图' }}</span>
            <el-button @click="imageInputRef?.click()" :loading="imageUploading">上传配图</el-button>
            <el-button v-if="barForm.image_url" link type="danger" @click="clearImage">移除</el-button>
            <input
              ref="imageInputRef"
              type="file"
              accept="image/*"
              class="hidden-file-input"
              @change="handleImageSelected"
            />
          </div>
        </el-form-item>
        <el-form-item label="PDF">
          <div class="asset-row">
            <span class="pdf-pill" v-if="barForm.pdf_url">PDF</span>
            <span class="asset-name">{{ barForm.pdf_name || (barForm.pdf_url ? '已上传 PDF' : '未上传 PDF') }}</span>
            <el-button @click="pdfInputRef?.click()" :loading="pdfUploading">上传 PDF</el-button>
            <el-button v-if="barForm.pdf_url" link type="primary" @click="previewPdf">预览</el-button>
            <el-button v-if="barForm.pdf_url" link type="danger" @click="clearPdf">移除</el-button>
            <input
              ref="pdfInputRef"
              type="file"
              accept="application/pdf,.pdf"
              class="hidden-file-input"
              @change="handlePdfSelected"
            />
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveHomepageBar" :loading="barSaving">
            保存官网运营条
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

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
import { announcementApi, homepageBarApi } from '@/utils/api'
import type { Announcement } from '@/utils/api'
import { formatServerTime } from '@/utils/time'

const loading = ref(false)
const announcements = ref<Announcement[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const barLoading = ref(false)
const barSaving = ref(false)
const imageUploading = ref(false)
const pdfUploading = ref(false)
const imageInputRef = ref<HTMLInputElement | null>(null)
const pdfInputRef = ref<HTMLInputElement | null>(null)

const formData = reactive({
  id: '',
  title: '',
  content: '',
  is_active: true
})

const barForm = reactive({
  title: '快速了解我们的服务和案例，点此处下载 PDF',
  button_text: '下载 PDF',
  pdf_url: '',
  pdf_name: '',
  pdf_object_key: '',
  image_url: '',
  image_object_key: '',
  is_active: false
})

const rules = reactive<FormRules>({
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }]
})

// 格式化时间
const formatTime = (timeString: string) => {
  return formatServerTime(timeString)
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
  fetchHomepageBar()
})

const fetchHomepageBar = async () => {
  barLoading.value = true
  try {
    const config = await homepageBarApi.getConfig()
    Object.assign(barForm, {
      title: config.title || '快速了解我们的服务和案例，点此处下载 PDF',
      button_text: config.button_text || '下载 PDF',
      pdf_url: config.pdf_url || '',
      pdf_name: config.pdf_name || '',
      pdf_object_key: config.pdf_object_key || '',
      image_url: config.image_url || '',
      image_object_key: config.image_object_key || '',
      is_active: config.is_active
    })
  } catch (error: any) {
    ElMessage.error(error.message || '获取官网运营条失败')
  } finally {
    barLoading.value = false
  }
}

const uploadMarketingAsset = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  const token = localStorage.getItem('token')
  const response = await fetch('/api/upload/site-photo', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || '上传失败')
  }
  const payload = await response.json()
  return payload.data || payload
}

const handleImageSelected = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请上传图片文件')
    input.value = ''
    return
  }
  imageUploading.value = true
  try {
    const data = await uploadMarketingAsset(file)
    barForm.image_url = data.url || data.file_url || ''
    barForm.image_object_key = data.object_key || ''
    ElMessage.success('配图上传成功')
  } catch (error: any) {
    ElMessage.error(error.message || '配图上传失败')
  } finally {
    imageUploading.value = false
    input.value = ''
  }
}

const handlePdfSelected = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!/\.pdf$/i.test(file.name)) {
    ElMessage.warning('请上传 PDF 文件')
    input.value = ''
    return
  }
  pdfUploading.value = true
  try {
    const data = await uploadMarketingAsset(file)
    barForm.pdf_url = data.url || data.file_url || ''
    barForm.pdf_name = data.filename || file.name
    barForm.pdf_object_key = data.object_key || ''
    ElMessage.success('PDF 上传成功')
  } catch (error: any) {
    ElMessage.error(error.message || 'PDF 上传失败')
  } finally {
    pdfUploading.value = false
    input.value = ''
  }
}

const clearImage = () => {
  barForm.image_url = ''
  barForm.image_object_key = ''
}

const clearPdf = () => {
  barForm.pdf_url = ''
  barForm.pdf_name = ''
  barForm.pdf_object_key = ''
}

const previewPdf = () => {
  if (barForm.pdf_url) {
    window.open(barForm.pdf_url, '_blank', 'noopener,noreferrer')
  }
}

const saveHomepageBar = async () => {
  if (!barForm.title.trim()) {
    ElMessage.warning('请输入运营条标题')
    return
  }
  if (barForm.is_active && !barForm.pdf_url) {
    ElMessage.warning('展示运营条前请先上传 PDF')
    return
  }

  barSaving.value = true
  try {
    await homepageBarApi.updateConfig({
      title: barForm.title.trim(),
      button_text: barForm.button_text.trim() || '下载 PDF',
      pdf_url: barForm.pdf_url,
      pdf_name: barForm.pdf_name,
      pdf_object_key: barForm.pdf_object_key,
      image_url: barForm.image_url,
      image_object_key: barForm.image_object_key,
      is_active: barForm.is_active
    })
    ElMessage.success('官网运营条已保存')
    fetchHomepageBar()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    barSaving.value = false
  }
}

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
.marketing-card {
  margin-bottom: 24px;
  border-radius: 12px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 6px;
}
.section-subtitle {
  font-size: 13px;
  color: #777;
  margin: 0;
}
.marketing-form {
  max-width: 860px;
}
.asset-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}
.asset-preview {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  background: #f5f7fa;
}
.asset-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.asset-name {
  color: #606266;
  font-size: 13px;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pdf-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 24px;
  border-radius: 4px;
  background: #111;
  color: #d7ff3f;
  font-size: 12px;
  font-weight: 700;
}
.hidden-file-input {
  display: none;
}
.status-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #999;
}
</style>
