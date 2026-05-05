<template>
  <div class="contractor-profile">
    <div class="page-header">
      <h1 class="page-title">个人设置</h1>
      <p class="page-desc">管理您的承包商账户信息</p>
    </div>

    <!-- 资料未完善提示 -->
    <div v-if="showIncompleteAlert" class="incomplete-alert">
      <div class="alert-icon">⚠️</div>
      <div class="alert-content">
        <div class="alert-title">请完善您的资料信息</div>
        <div class="alert-desc">以下信息尚未填写，请尽快补充以便接收派单：<strong>{{ missingFields.join('、') }}</strong></div>
      </div>
    </div>

    <div class="profile-card">
      <el-form ref="formRef" :model="form" label-position="top" class="profile-form">
        <div class="section-title">基本信息</div>
        <div class="form-grid">
          <el-form-item label="用户名">
            <el-input :model-value="form.username" disabled />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input :model-value="form.phone" disabled />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="联系邮箱" />
          </el-form-item>
          <el-form-item label="真实姓名">
            <el-input v-model="form.realName" placeholder="真实姓名" />
            <div v-if="!form.realName" class="field-hint">🔴 未填写</div>
          </el-form-item>
        </div>

        <div class="section-title">公司信息</div>
        <div class="form-grid">
          <el-form-item label="公司名称">
            <el-input v-model="form.company" placeholder="所在公司" />
            <div v-if="!form.company" class="field-hint">🔴 未填写</div>
          </el-form-item>
          <el-form-item label="地址">
            <el-input v-model="form.address" placeholder="联系地址" />
          </el-form-item>
        </div>

        <div class="section-title">专业能力</div>
        <div class="form-grid">
          <el-form-item label="专业方向">
            <el-input v-model="form.specialty" placeholder="如：3D建模、视频后期" />
            <div v-if="!form.specialty" class="field-hint">🔴 未填写</div>
          </el-form-item>
          <el-form-item label="擅长领域">
            <el-input v-model="form.expertise" placeholder="如：裸眼3D广告、产品展示" />
            <div v-if="!form.expertise" class="field-hint">🔴 未填写</div>
          </el-form-item>
        </div>

        <!-- 优秀案例 -->
        <div class="section-title">
          优秀案例
          <span class="section-subtitle">（最多上传 2 个视频，每个不超过 200MB）</span>
        </div>

        <div class="showcase-grid">
          <div
            v-for="(item, index) in showcaseCases"
            :key="index"
            class="showcase-item"
          >
            <div class="showcase-card">
              <!-- 有视频 -->
              <template v-if="item.url">
                <video
                  :src="item.url"
                  class="showcase-video"
                  controls
                  preload="metadata"
                />
                <div class="showcase-info">
                  <el-input
                    v-model="item.title"
                    placeholder="案例标题（选填）"
                    size="small"
                    class="showcase-title-input"
                  />
                  <div class="showcase-meta">
                    <span class="file-size">{{ formatFileSize(item.size) }}</span>
                    <el-button
                      type="danger"
                      size="small"
                      text
                      @click="removeShowcase(index)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
              </template>

              <!-- 上传中 -->
              <template v-else-if="item.uploading">
                <div class="upload-progress">
                  <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
                  <p>上传中...</p>
                  <el-progress :percentage="item.progress || 0" :stroke-width="4" />
                </div>
              </template>
            </div>
          </div>

          <!-- 添加按钮 -->
          <div
            v-if="showcaseCases.length < 2"
            class="showcase-item showcase-add"
            @click="triggerUpload"
          >
            <div class="add-content">
              <el-icon :size="36"><Plus /></el-icon>
              <p>上传案例视频</p>
              <span class="add-hint">MP4/MOV 等，最大 200MB</span>
            </div>
          </div>
        </div>

        <input
          ref="fileInputRef"
          type="file"
          accept="video/*"
          style="display: none"
          @change="handleFileSelected"
        />

        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="handleSave" size="large">保存修改</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Loading } from '@element-plus/icons-vue'
import request from '@/utils/request'
import axios from 'axios'

interface ShowcaseCase {
  title: string
  url: string
  objectKey?: string
  filename?: string
  size?: number
  uploading?: boolean
  progress?: number
}

const formRef = ref()
const fileInputRef = ref<HTMLInputElement>()
const saving = ref(false)
const loaded = ref(false)

const form = reactive({
  username: '',
  phone: '',
  email: '',
  realName: '',
  company: '',
  address: '',
  specialty: '',
  expertise: '',
})

const showcaseCases = ref<ShowcaseCase[]>([])

const missingFields = computed(() => {
  const fields: string[] = []
  if (!form.realName) fields.push('真实姓名')
  if (!form.company) fields.push('公司名称')
  if (!form.specialty) fields.push('专业方向')
  if (!form.expertise) fields.push('擅长领域')
  return fields
})

const showIncompleteAlert = computed(() => loaded.value && missingFields.value.length > 0)

const formatFileSize = (bytes?: number) => {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const fetchProfile = async () => {
  try {
    const d: any = await request.get('/contractor/profile')
    form.username = d?.username || ''
    form.phone = d?.phone || ''
    form.email = d?.email || ''
    form.realName = d?.realName || d?.real_name || ''
    form.company = d?.company || ''
    form.address = d?.address || ''
    form.specialty = d?.specialty || ''
    form.expertise = d?.expertise || ''
    showcaseCases.value = (d?.showcaseCases || []).map((c: any) => ({
      title: c.title || '',
      url: c.url || '',
      objectKey: c.objectKey || '',
      filename: c.filename || '',
      size: c.size || 0,
    }))
    loaded.value = true
  } catch {
    ElMessage.error('加载个人信息失败')
  }
}

const triggerUpload = () => {
  fileInputRef.value?.click()
}

const handleFileSelected = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = '' // 允许重复选同一文件

  // 前端校验
  if (file.size > 200 * 1024 * 1024) {
    ElMessage.error('视频文件大小不能超过 200MB')
    return
  }
  if (showcaseCases.value.length >= 2) {
    ElMessage.error('最多上传 2 个案例视频')
    return
  }

  // 添加占位
  const idx = showcaseCases.value.length
  showcaseCases.value.push({
    title: '',
    url: '',
    uploading: true,
    progress: 0,
    filename: file.name,
    size: file.size,
  })

  try {
    const formData = new FormData()
    formData.append('file', file)

    const token = localStorage.getItem('token')
    const res = await axios.post('/api/upload/showcase-video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          showcaseCases.value[idx].progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
        }
      },
    })

    const data = res.data?.data || res.data
    showcaseCases.value[idx] = {
      title: '',
      url: data.url,
      objectKey: data.object_key || '',
      filename: data.filename || file.name,
      size: data.size || file.size,
      uploading: false,
    }
    ElMessage.success('视频上传成功')
  } catch (err: any) {
    showcaseCases.value.splice(idx, 1)
    const msg = err?.response?.data?.detail || '上传失败'
    ElMessage.error(msg)
  }
}

const removeShowcase = (index: number) => {
  showcaseCases.value.splice(index, 1)
}

const handleSave = async () => {
  saving.value = true
  try {
    // 只保存已上传完成的案例
    const casesToSave = showcaseCases.value
      .filter(c => c.url && !c.uploading)
      .map(c => ({
        title: c.title,
        url: c.url,
        objectKey: c.objectKey,
        filename: c.filename,
        size: c.size,
      }))

    await request.put('/contractor/profile', {
      email: form.email,
      real_name: form.realName,
      company: form.company,
      address: form.address,
      specialty: form.specialty,
      expertise: form.expertise,
      showcase_cases: casesToSave,
    })
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(fetchProfile)
</script>

<style lang="scss" scoped>
.contractor-profile { max-width: 800px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #1D1D1F; margin: 0 0 4px; }
.page-desc { font-size: 14px; color: #86868B; margin: 0; }

.incomplete-alert {
  display: flex; align-items: flex-start; gap: 12px;
  background: #FFF8E6; border: 1px solid #FFD666;
  border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;
}
.alert-icon { font-size: 24px; flex-shrink: 0; line-height: 1; }
.alert-content { flex: 1; }
.alert-title { font-size: 15px; font-weight: 600; color: #1D1D1F; margin-bottom: 4px; }
.alert-desc { font-size: 13px; color: #86868B; line-height: 1.5;
  strong { color: #E6770F; font-weight: 600; }
}

.profile-card {
  background: #fff; border-radius: 12px; padding: 32px;
  border: 1px solid #E5E7EB;
}

.section-title {
  font-size: 16px; font-weight: 600; color: #1D1D1F;
  margin: 24px 0 12px; padding-bottom: 8px;
  border-bottom: 1px solid #F0F0F0;
  &:first-child { margin-top: 0; }
}
.section-subtitle {
  font-size: 13px; font-weight: 400; color: #86868B;
}

.form-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
}
@media (max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }

.field-hint {
  font-size: 12px; color: #E6770F; margin-top: 4px;
}

/* ========== Showcase Cases ========== */
.showcase-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16px; margin-top: 8px;
}
@media (max-width: 600px) { .showcase-grid { grid-template-columns: 1fr; } }

.showcase-item {
  border: 1px solid #E5E7EB; border-radius: 12px;
  overflow: hidden; background: #FAFAFA;
  min-height: 200px; display: flex; flex-direction: column;
}

.showcase-card {
  flex: 1; display: flex; flex-direction: column;
}

.showcase-video {
  width: 100%; max-height: 220px; object-fit: cover;
  background: #000; display: block;
}

.showcase-info {
  padding: 10px 12px; display: flex; flex-direction: column; gap: 6px;
}

.showcase-title-input {
  :deep(.el-input__wrapper) {
    background: transparent !important; box-shadow: none !important;
    border-bottom: 1px solid #E5E7EB !important; border-radius: 0 !important;
    padding: 0 4px !important;
  }
  :deep(.el-input__inner) { font-size: 13px !important; }
}

.showcase-meta {
  display: flex; justify-content: space-between; align-items: center;
}
.file-size { font-size: 12px; color: #86868B; }

.showcase-add {
  cursor: pointer; border: 2px dashed #D0D0D5;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
  &:hover { border-color: #0071E3; background: #F0F7FF; }
}

.add-content {
  text-align: center; color: #86868B;
  p { margin: 8px 0 4px; font-size: 14px; font-weight: 500; }
}
.add-hint { font-size: 12px; color: #B0B0B5; }

.upload-progress {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 30px;
  p { margin: 12px 0; font-size: 14px; color: #86868B; }
  .el-progress { width: 80%; }
}

.loading-icon { animation: spin 1s linear infinite; color: #0071E3; }
@keyframes spin { to { transform: rotate(360deg); } }

.form-actions { margin-top: 28px; display: flex; justify-content: flex-end; }
</style>
