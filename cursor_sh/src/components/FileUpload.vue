<template>
  <div class="file-upload">
    <el-upload
      ref="uploadRef"
      :file-list="fileList"
      :on-change="handleFileChange"
      :on-remove="handleRemove"
      :before-upload="beforeUpload"
      :auto-upload="false"
      :multiple="multiple"
      :accept="accept"
      :limit="limit"
      :on-exceed="handleExceed"
      drag
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        拖拽文件到此处或 <em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">
          {{ tipText || `支持上传${accept || '所有类型'}文件${limit ? `，最多${limit}个` : ''}` }}
        </div>
      </template>
    </el-upload>
    
    <div v-if="uploadedFiles.length > 0" class="uploaded-files">
      <h4>已上传文件</h4>
      <div class="file-list">
        <div v-for="file in uploadedFiles" :key="file.id" class="file-item">
          <img
            v-if="isPreviewableImage(file)"
            class="file-thumb"
            :src="getPreviewSrc(file)"
            :alt="file.name"
          />
          <el-icon v-else class="file-icon"><Document /></el-icon>
          <div class="file-info">
            <div class="file-name">{{ file.name }}</div>
            <div class="file-meta">{{ formatFileSize(file.size) }} · {{ formatTime(file.uploadTime) }}</div>
          </div>
          <el-button 
            type="danger" 
            :icon="Delete" 
            circle 
            size="small"
            @click="removeUploadedFile(file.id)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, type UploadFile, type UploadInstance, type UploadUserFile } from 'element-plus'
import { UploadFilled, Document, Delete } from '@element-plus/icons-vue'
import { formatServerTime } from '@/utils/time'
import type { UploadedFile } from '@/types'

interface Props {
  modelValue: UploadedFile[]
  accept?: string
  limit?: number
  multiple?: boolean
  tipText?: string
}

const props = withDefaults(defineProps<Props>(), {
  accept: '',
  limit: 10,
  multiple: true,
  tipText: ''
})

const emit = defineEmits<{
  'update:modelValue': [files: UploadedFile[]]
}>()

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadUserFile[]>([])
const uploadedFiles = ref<UploadedFile[]>(props.modelValue || [])

watch(() => props.modelValue, (newVal) => {
  uploadedFiles.value = newVal || []
})

const uploadFile = async (file: File): Promise<UploadedFile> => {
  const formData = new FormData()
  formData.append('file', file)

  const headers: Record<string, string> = {}
  const token = localStorage.getItem('token')
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch('/api/upload/file', {
    method: 'POST',
    headers,
    body: formData
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok || payload?.code !== 200) {
    throw new Error(payload?.detail || payload?.message || '上传失败')
  }

  const data = payload.data || {}
  const isImage = isImageFile(data.filename || file.name, data.mime_type || file.type)
  return {
    id: data.object_key || data.url || `${file.name}-${Date.now()}`,
    name: data.filename || file.name,
    size: data.size ?? file.size,
    type: data.mime_type || file.type,
    isImage,
    uploadTime: data.uploadedAt || new Date().toISOString(),
    url: data.url,
    file_url: data.url,
    object_key: data.object_key || ''
  }
}

const handleFileChange = async (uploadFile: UploadFile) => {
  if (uploadFile.raw) {
    try {
      const uploaded = await uploadFile(uploadFile.raw)
      uploadedFiles.value.push(uploaded)
      emit('update:modelValue', uploadedFiles.value)
      ElMessage.success(`${uploadFile.name} 上传成功`)
      
      // 清空上传列表
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
    } catch (error) {
      ElMessage.error(`${uploadFile.name} 上传失败`)
    }
  }
}

const handleRemove = (uploadFile: UploadFile) => {
  // 从待上传列表中移除
  fileList.value = fileList.value.filter(f => f.uid !== uploadFile.uid)
}

const removeUploadedFile = (fileId: string) => {
  const removedFile = uploadedFiles.value.find(f => f.id === fileId)
  if (removedFile?.previewUrl?.startsWith('blob:')) {
    URL.revokeObjectURL(removedFile.previewUrl)
  }
  uploadedFiles.value = uploadedFiles.value.filter(f => f.id !== fileId)
  emit('update:modelValue', uploadedFiles.value)
  
  ElMessage.success('文件已删除')
}

const isImageFile = (name = '', type = '') => {
  return type.startsWith('image/') || /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(name)
}

const getPreviewSrc = (file: UploadedFile) => {
  const src = file.previewUrl || file.file_url || file.url || ''
  return src
}

const isPreviewableImage = (file: UploadedFile) => {
  return isImageFile(file.name, file.type) && !!getPreviewSrc(file)
}

const beforeUpload = (rawFile: File) => {
  // 可以在这里添加文件大小限制等验证
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (rawFile.size > maxSize) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

const handleExceed = () => {
  ElMessage.warning(`最多只能上传 ${props.limit} 个文件`)
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const formatTime = (timeString: string): string => {
  return formatServerTime(timeString)
}
</script>

<style lang="scss" scoped>
.file-upload {
  width: 100%;
}

.uploaded-files {
  margin-top: 24px;
  
  h4 {
    font-size: 14px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 0 0 12px 0;
  }
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #F5F5F7;
  border-radius: 8px;
  transition: all 0.3s ease;
  
  &:hover {
    background: #E8E8ED;
  }
}

.file-icon {
  font-size: 24px;
  color: var(--uv-ws-action-button-bg, #A0522D);
  flex-shrink: 0;
}

.file-thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  object-fit: cover;
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #1D1D1F;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 12px;
  color: #86868B;
  margin-top: 2px;
}

:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload-dragger) {
  padding: 40px 20px;
  border-radius: 12px;
  border: 2px dashed #D2D2D7;
  background: #F5F5F7;
  transition: all 0.3s ease;
  
  &:hover {
    border-color: var(--uv-ws-action-button-bg, #A0522D);
    background: var(--uv-ws-module-active-bg, #F3E7E1);
  }
}

:deep(.el-icon--upload) {
  font-size: 48px;
  color: var(--uv-ws-action-button-bg, #A0522D);
  margin-bottom: 16px;
}

:deep(.el-upload__text) {
  font-size: 14px;
  color: #1D1D1F;
  
  em {
    color: var(--uv-ws-action-button-bg, #A0522D);
    font-style: normal;
  }
}

:deep(.el-upload__tip) {
  font-size: 12px;
  color: #86868B;
  margin-top: 8px;
}
</style>
