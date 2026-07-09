<template>
  <div class="contractor-profile">
    <section class="profile-overview" :class="{ 'is-internal': isInternalCreator }">
      <div class="profile-heading">
        <h1 class="page-title">{{ isInternalCreator ? '内部制作者资料' : '承包商资料' }}</h1>
        <p class="breadcrumb">工作台 <span></span> 个人设置</p>
      </div>
      <div v-if="!isInternalCreator" class="profile-meter-card">
        <div class="meter-copy">
          <span>资料完整度</span>
          <strong>{{ profileCompletion }}%</strong>
        </div>
        <div class="profile-bars">
          <i v-for="n in 10" :key="n" :class="{ on: n <= Math.round(profileCompletion / 10) }"></i>
        </div>
      </div>
    </section>

    <!-- 资料未完善提示 -->
    <div v-if="showIncompleteAlert" class="incomplete-alert">
      <div class="alert-icon"><el-icon><InfoFilled /></el-icon></div>
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

        <template v-if="!isInternalCreator">
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
        </template>

        <template v-if="!isInternalCreator">
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
        </template>

        <!-- 优秀案例 -->
        <div v-if="!isInternalCreator" class="section-title">
          优秀案例
          <span class="section-subtitle">（最多上传 2 个视频，每个不超过 200MB）</span>
        </div>

        <div v-if="!isInternalCreator" class="showcase-grid">
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
          v-if="!isInternalCreator"
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
import { InfoFilled, Plus, Loading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
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
const authStore = useAuthStore()
const isInternalCreator = computed(() => authStore.isStaff())

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

const showIncompleteAlert = computed(() =>
  !isInternalCreator.value && loaded.value && missingFields.value.length > 0
)
const profileCompletion = computed(() => {
  if (isInternalCreator.value) return 100
  const fields = [form.realName, form.company, form.specialty, form.expertise, form.email, form.address]
  const fieldScore = fields.filter(Boolean).length
  const showcaseScore = Math.min(showcaseCases.value.filter(c => c.url && !c.uploading).length, 2)
  return Math.round(((fieldScore + showcaseScore) / 8) * 100)
})

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
    const normalizedEmail = form.email.trim() || null

    const payload = isInternalCreator.value ? {
      email: normalizedEmail,
      real_name: form.realName,
    } : {
      email: normalizedEmail,
      real_name: form.realName,
      company: form.company,
      address: form.address,
      specialty: form.specialty,
      expertise: form.expertise,
      showcase_cases: casesToSave,
    }

    await request.put('/contractor/profile', payload)
    await authStore.refreshCurrentUser({ force: true }).catch(() => null)
    window.dispatchEvent(new CustomEvent('contractor-profile-updated'))
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
.contractor-profile { max-width: 1180px; margin: 0 auto; }

.profile-overview {
  min-height: 220px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  align-items: stretch;
  padding: 46px 52px 30px;
  border-radius: 34px;
  background: #ECEAE7;
  margin-bottom: 20px;
}

.profile-overview.is-internal {
  min-height: 160px;
  grid-template-columns: minmax(0, 1fr);
}

.profile-heading {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.page-title {
  font-size: clamp(36px, 4vw, 54px);
  font-weight: 850;
  line-height: 0.98;
  letter-spacing: 0;
  color: #121212;
  margin: 0 0 18px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #5E5954;
  font-size: 17px;
  font-weight: 750;
  margin: 0;

  span {
    width: 8px;
    height: 8px;
    border-top: 2px solid #4B4640;
    border-right: 2px solid #4B4640;
    transform: rotate(45deg);
  }
}

.profile-meter-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 26px;
  border-radius: 30px;
  background: #FFFFFF;
}

.meter-copy {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;

  span {
    color: #8F8780;
    font-size: 14px;
    font-weight: 750;
  }

  strong {
    color: #151515;
    font-size: 42px;
    font-weight: 850;
    line-height: 0.9;
  }
}

.profile-bars {
  min-height: 80px;
  display: flex;
  align-items: flex-end;
  gap: 8px;

  i {
    width: 14px;
    height: 28px;
    border-radius: 14px;
    background: #E5E0DA;

    &:nth-child(2n) { height: 42px; }
    &:nth-child(3n) { height: 58px; }

    &.on {
      background: #8B5E3C;
    }
  }
}

.incomplete-alert {
  display: flex; align-items: flex-start; gap: 12px;
  background: #F4EAE2; border: 1px solid #D8C4B4;
  border-radius: 24px; padding: 18px 22px; margin-bottom: 20px;
}
.alert-icon { font-size: 22px; flex-shrink: 0; line-height: 1; color: #8B5E3C; }
.alert-content { flex: 1; }
.alert-title { font-size: 15px; font-weight: 800; color: #1D1D1F; margin-bottom: 4px; }
.alert-desc { font-size: 13px; color: #86868B; line-height: 1.5;
  strong { color: #8B5E3C; font-weight: 700; }
}

.profile-card {
  background: #fff; border-radius: 30px; padding: 34px;
  border: 1px solid #EFEDE9;
  box-shadow: 0 1px 0 rgba(42, 37, 31, 0.04);
}

.section-title {
  font-size: 18px; font-weight: 850; color: #1D1D1F;
  margin: 28px 0 16px; padding-bottom: 10px;
  border-bottom: 1px solid #F1EFEC;
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
  font-size: 12px; color: #8B5E3C; margin-top: 4px; font-weight: 700;
}

/* ========== Showcase Cases ========== */
.showcase-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16px; margin-top: 8px;
}
@media (max-width: 600px) { .showcase-grid { grid-template-columns: 1fr; } }

.showcase-item {
  border: 1px solid #EFEDE9; border-radius: 28px;
  overflow: hidden; background: #F7F6F4;
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
  padding: 14px 16px; display: flex; flex-direction: column; gap: 8px;
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
  cursor: pointer; border: 2px dashed #D8C4B4;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
  &:hover { border-color: #8B5E3C; background: #F4EAE2; }
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

.loading-icon { animation: spin 1s linear infinite; color: #8B5E3C; }
@keyframes spin { to { transform: rotate(360deg); } }

.form-actions { margin-top: 28px; display: flex; justify-content: flex-end; }

:deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: 22px;
  background: #F7F6F4;
  box-shadow: none !important;
}

:deep(.el-form-item__label) {
  color: #5F5952;
  font-weight: 750;
}

:deep(.el-button--primary) {
  --el-button-bg-color: #111111;
  --el-button-border-color: #111111;
  --el-button-hover-bg-color: #8B5E3C;
  --el-button-hover-border-color: #8B5E3C;
  border-radius: 24px;
}

@media (max-width: 860px) {
  .profile-overview {
    grid-template-columns: 1fr;
    padding: 30px 24px;
  }
}
</style>
