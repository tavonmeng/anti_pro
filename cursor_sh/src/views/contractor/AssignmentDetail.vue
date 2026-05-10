<template>
  <div class="assignment-detail" v-if="assignment">
    <!-- 返回按钮 -->
    <div class="back-bar">
      <el-button text @click="router.push('/contractor/assignments')">
        <el-icon><ArrowLeft /></el-icon> 返回派单列表
      </el-button>
    </div>

    <!-- 顶部信息 -->
    <div class="detail-header">
      <div class="header-left">
        <h1 class="detail-title">{{ assignment.order?.orderNumber || '—' }}</h1>
        <el-tag :type="statusTagType(assignment.status)" effect="dark" size="small">
          {{ statusLabel(assignment.status) }}
        </el-tag>
      </div>
    </div>

    <div class="detail-grid">
      <!-- 左栏：订单信息 + 排期 -->
      <div class="detail-left">
        <el-collapse v-model="activeNames" class="custom-collapse">
          
          <!-- 订单需求信息 -->
          <el-collapse-item name="requirements" class="info-card">
            <template #title>
              <h3 class="card-title" style="margin: 0; width: 100%;">订单需求</h3>
            </template>
            <div class="info-grid" style="margin-top: 16px;">
              <div class="info-item" v-for="item in orderFields" :key="item.key">
                <span class="info-label">{{ item.label }}</span>
                <span class="info-value">{{ item.value || '—' }}</span>
              </div>
            </div>
          </el-collapse-item>

          <!-- 排期时间线 -->
          <el-collapse-item name="schedule" class="info-card">
            <template #title>
              <h3 class="card-title" style="margin: 0; width: 100%;">工作流排期</h3>
            </template>
            <div class="timeline" style="margin-top: 16px;">
              <div
                v-for="(stage, idx) in (assignment.schedule || [])"
                :key="idx"
                class="timeline-item"
                :class="{
                  active: stage.display_order === currentStageOrder,
                  completed: stage.status === 'completed',
                  pending: stage.status === 'pending' && stage.display_order !== currentStageOrder,
                }"
              >
                <div class="timeline-dot">
                  <el-icon v-if="stage.status === 'completed'" :size="14"><Check /></el-icon>
                  <span v-else>{{ stage.display_order }}</span>
                </div>
                <div class="timeline-content">
                  <div class="stage-name">{{ stage.name }}</div>
                  <div class="stage-meta">{{ stage.days }} 天 · 截止 {{ stage.deadline }}</div>
                </div>
                <el-tag v-if="stage.display_order === currentStageOrder" type="primary" size="small" effect="plain">当前</el-tag>
                <el-tag v-else-if="stage.status === 'completed'" type="success" size="small" effect="plain">完成</el-tag>
              </div>
            </div>
          </el-collapse-item>

          <!-- AI设计方案 -->
          <el-collapse-item name="aiPlan" class="info-card" v-if="assignment.order?.designPlan?.content">
            <template #title>
              <h3 class="card-title" style="margin: 0; width: 100%; display: flex; align-items: center; gap: 8px;">
                <span>📐 AI设计方案</span>
                <el-tag v-if="assignment.order.designPlan.status === 'completed'" type="success" size="small" effect="dark">已完成</el-tag>
              </h3>
            </template>
            <div style="margin-top: 16px;">
              <div class="design-plan-content">
                <p class="plan-text">{{ assignment.order.designPlan.content }}</p>
              </div>
              <div v-if="assignment.order.designPlan.files?.length" class="plan-files">
                <h4 class="sub-title">参考文件</h4>
                <div v-for="(file, idx) in assignment.order.designPlan.files" :key="idx" class="plan-file-item">
                  <a :href="file.url" target="_blank" class="plan-file-link">{{ file.filename || '文件' }}</a>
                </div>
              </div>
            </div>
          </el-collapse-item>

          <!-- 现场实拍图 -->
          <el-collapse-item name="photos" class="info-card" v-if="assignment.order?.site_photos?.length">
            <template #title>
              <h3 class="card-title" style="margin: 0; width: 100%;">现场实拍图</h3>
            </template>
            <div class="site-photos" style="margin-top: 16px;">
              <a v-for="(photo, idx) in assignment.order.site_photos" :key="idx"
                :href="photo.url || photo.file_url" target="_blank" class="photo-link">
                {{ photo.name || photo.filename || `照片 ${idx + 1}` }}
              </a>
            </div>
          </el-collapse-item>

        </el-collapse>
      </div>

      <!-- 右栏：交付物上传 -->
      <div class="detail-right">
        <div class="info-card" v-if="assignment.status === 'in_progress'">
          <h3 class="card-title">
            交付环节 — {{ currentStageName }}
            <el-tag type="info" size="small" style="margin-left:8px">第 {{ currentStageOrder }} 环节</el-tag>
          </h3>

          <div v-if="stageDeliverables.length > 0" class="deliverable-history">
            <h4 class="sub-title">历史提交记录</h4>
            <div v-for="d in stageDeliverables" :key="d.id" class="history-item">
              <div class="history-header">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span>V{{ d.version }}</span>
                  <el-tag :type="deliverableStatusType(d.status)" size="small">{{ deliverableStatusLabel(d.status) }}</el-tag>
                </div>
                <span v-if="d.createdAt" class="history-time">{{ formatDate(d.createdAt) }}</span>
              </div>
              <p v-if="d.adminReviewNote" class="review-note">
                <strong>管理员备注 ({{ formatDate(d.adminReviewedAt) || '暂无时间' }})：</strong>
                {{ d.adminReviewNote }}
              </p>
              <!-- 管理员评论列表 -->
              <div v-if="d.adminComments && d.adminComments.length > 0" class="admin-comments-section">
                <strong class="admin-comments-title">💬 管理员评论：</strong>
                <div v-for="comment in d.adminComments" :key="comment.id" class="admin-comment-item">
                  <span class="admin-comment-content">{{ comment.content }}</span>
                  <span class="admin-comment-meta">{{ comment.createdByName }} · {{ formatDate(comment.createdAt) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 上传表单 -->
          <div class="upload-section">
            <div class="upload-area">
              <el-upload
                ref="uploadRef"
                action="/api/upload/file"
                :headers="uploadHeaders"
                :on-success="handleUploadSuccess"
                :on-error="handleUploadError"
                :before-upload="beforeUpload"
                :file-list="fileList"
                multiple
                drag
              >
                <el-icon class="el-icon--upload" :size="40"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
                <template #tip>
                  <div class="el-upload__tip">支持图片、视频、文档，单个文件不超过 50MB</div>
                </template>
              </el-upload>
            </div>

            <el-form-item label="说明" style="margin-top:16px">
              <el-input v-model="deliverableForm.description" type="textarea" :rows="3" placeholder="请描述本次交付的内容" />
            </el-form-item>

            <!-- 自审核检查项 -->
            <div class="self-review-section">
              <div class="review-header">
                <h4 class="review-title">
                  <el-icon color="#E6A23C"><WarningFilled /></el-icon>
                  安全与品质审核
                </h4>
                <span class="review-progress" :class="{ complete: allChecked }">
                  {{ checkedCount }}/{{ totalItems }} 已确认
                </span>
              </div>

              <div
                v-for="(category, cIdx) in reviewCategories"
                :key="cIdx"
                class="review-category"
              >
                <div class="category-header">
                  <span class="category-index" :class="{ done: isCategoryAllChecked(category) }">
                    <el-icon v-if="isCategoryAllChecked(category)" :size="12"><Check /></el-icon>
                    <span v-else>{{ cIdx + 1 }}</span>
                  </span>
                  <span class="category-title">{{ category.title }}</span>
                  <el-tag
                    :type="isCategoryAllChecked(category) ? 'success' : 'info'"
                    size="small"
                    effect="plain"
                  >
                    {{ getCategoryCheckedCount(category) }}/{{ category.items.length }}
                  </el-tag>
                </div>

                <div class="review-checklist">
                  <div
                    v-for="(item, idx) in category.items"
                    :key="item"
                    class="review-step"
                    :class="{
                      confirmed: deliverableForm.selfReviewChecks[item],
                      active: getGlobalIndex(cIdx, idx) === currentReviewStep,
                      locked: getGlobalIndex(cIdx, idx) > currentReviewStep,
                    }"
                  >
                    <!-- 已确认：折叠态 -->
                    <div
                      v-if="deliverableForm.selfReviewChecks[item]"
                      class="step-confirmed"
                      @click="uncheckItem(item)"
                    >
                      <div class="step-left">
                        <span class="step-check-icon"><el-icon :size="14" color="#52C41A"><Check /></el-icon></span>
                        <span class="step-number">{{ cIdx + 1 }}.{{ idx + 1 }}</span>
                        <span class="step-text-short">{{ item }}</span>
                      </div>
                      <span class="step-undo">撤回</span>
                    </div>

                    <!-- 当前项：展开态 -->
                    <div
                      v-else-if="getGlobalIndex(cIdx, idx) === currentReviewStep"
                      class="step-active"
                    >
                      <div class="step-active-header">
                        <span class="step-number-active">{{ cIdx + 1 }}.{{ idx + 1 }}</span>
                        <span class="step-label">请确认以下事项</span>
                      </div>
                      <div class="step-active-body">
                        <div class="step-content-text">{{ item }}</div>
                        <div class="step-confirm-row">
                          <el-checkbox
                            :model-value="false"
                            @change="confirmItem(item)"
                            class="confirm-checkbox"
                          >
                            本人已仔细核查，确认上述事项无问题
                          </el-checkbox>
                        </div>
                      </div>
                    </div>

                    <!-- 未到达：锁定态 -->
                    <div v-else class="step-locked">
                      <span class="step-lock-icon"><el-icon :size="14" color="#C0C4CC"><Lock /></el-icon></span>
                      <span class="step-number">{{ cIdx + 1 }}.{{ idx + 1 }}</span>
                      <span class="step-text-locked">{{ item }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="submit-actions">
              <el-button @click="saveDraft" :loading="saving">保存草稿</el-button>
              <el-button
                type="primary"
                :disabled="!allChecked || uploadedFiles.length === 0"
                :loading="submitting"
                @click="submitDeliverable"
              >
                提交审核
              </el-button>
            </div>
          </div>
        </div>

        <!-- 非进行中状态提示 -->
        <div class="info-card" v-else-if="assignment.status === 'pending'">
          <div class="pending-notice">
            <el-icon :size="40" color="#E6A23C"><InfoFilled /></el-icon>
            <h3>请先接受此派单</h3>
            <p>接单后即可进入交付环节</p>
            <el-button type="primary" @click="handleAccept">接受派单</el-button>
          </div>
        </div>

        <div class="info-card" v-else-if="assignment.status === 'completed'">
          <div class="pending-notice">
            <el-icon :size="40" color="#67C23A"><CircleCheckFilled /></el-icon>
            <h3>所有环节已完成</h3>
            <p>该项目已圆满完成，感谢您的参与</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 加载中 -->
  <div v-else class="loading-state">
    <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
    <p>加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Check, UploadFilled, WarningFilled,
  InfoFilled, CircleCheckFilled, Loading, Lock, ArrowDown, ArrowRight
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const assignment = ref<any>(null)
const saving = ref(false)
const submitting = ref(false)
const uploadRef = ref()
const fileList = ref<any[]>([])
const uploadedFiles = ref<any[]>([])
const currentDeliverableId = ref<string | null>(null)

const deliverableForm = reactive({
  description: '',
  selfReviewChecks: {} as Record<string, boolean>,
})

// 卡片折叠状态
const activeNames = ref<string[]>(['requirements', 'schedule', 'aiPlan', 'photos'])

// 当前环节
const currentStageOrder = computed(() => parseInt(assignment.value?.currentStageOrder || '1'))
const currentStage = computed(() =>
  (assignment.value?.schedule || []).find((s: any) => s.display_order === currentStageOrder.value)
)
const currentStageName = computed(() => currentStage.value?.name || '—')

// 审核检查项（按类别分组）
const reviewCategories = computed(() => [
  {
    title: '安全审核',
    items: [
      '确认不存在违反国家法律法规及地方性规定的内容',
      '确认不存在意识形态及政治敏感内容',
      '确认不存在违背社会价值观及公序良俗的内容',
      '确认不存在侵犯第三方权益及知识产权的问题',
    ]
  },
  {
    title: '品质审核',
    items: [
      '确认风格与品牌调性一致',
      '确认技术规格达标',
    ]
  }
])

// 所有检查项（展平）
const allReviewItems = computed(() =>
  reviewCategories.value.flatMap(c => c.items)
)

const allChecked = computed(() =>
  allReviewItems.value.length > 0 && allReviewItems.value.every(item => deliverableForm.selfReviewChecks[item])
)

// 类别级别进度
const isCategoryAllChecked = (category: { items: string[] }) =>
  category.items.every(item => deliverableForm.selfReviewChecks[item])

const getCategoryCheckedCount = (category: { items: string[] }) =>
  category.items.filter(item => deliverableForm.selfReviewChecks[item]).length

// 当前环节的交付物历史
const stageDeliverables = computed(() =>
  (assignment.value?.deliverables || []).filter(
    (d: any) => d.stageOrder === currentStageOrder.value
  )
)

// 订单信息展示
const orderFields = computed(() => {
  const o = assignment.value?.order || {} as any
  return [
    { key: 'brand', label: '品牌', value: o.brand },
    { key: 'brand_tone', label: '品牌调性', value: o.brand_tone },
    { key: 'city', label: '投放城市', value: o.city },
    { key: 'content', label: '内容需求', value: o.content },
    { key: 'style', label: '风格偏好', value: o.style },
    { key: 'target_group', label: '目标受众', value: o.target_group },
    { key: 'media_size', label: '媒体尺寸', value: o.media_size },
    { key: 'time_number', label: '投放时长/数量', value: o.time_number },
    { key: 'technology', label: '技术需求', value: o.technology },
    { key: 'online_time', label: '上刊时间', value: o.online_time },
    { key: 'background', label: '项目背景', value: o.background },
    { key: 'prohibited_content', label: '品牌禁忌内容', value: o.prohibited_content },
    { key: 'special_requirements', label: '其他特殊合作要求', value: o.special_requirements },
    { key: 'remarks', label: '备注', value: o.remarks },
  ].filter(f => f.value !== undefined && f.value !== null)
})

const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`,
}))

const statusLabel = (s: string) => ({
  pending: '待处理', in_progress: '进行中', completed: '已完成', rejected: '已拒绝',
}[s] || s)

const statusTagType = (s: string) => ({
  pending: 'warning', in_progress: '', completed: 'success', rejected: 'danger',
}[s] || 'info')

const deliverableStatusLabel = (s: string) => ({
  draft: '草稿', submitted: '待审核', admin_approved: '已通过', admin_rejected: '已驳回',
}[s] || s)

const deliverableStatusType = (s: string) => ({
  draft: 'info', submitted: 'warning', admin_approved: 'success', admin_rejected: 'danger',
}[s] || 'info')

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const fetchDetail = async () => {
  try {
    const id = route.params.id
    const res: any = await request.get(`/contractor/assignments/${id}`)
    assignment.value = res
    
    // 如果已经上传过交付物（有记录），默认折叠信息区，重点展示流程
    if (assignment.value?.deliverables && assignment.value.deliverables.length > 0) {
      activeNames.value = []
    }
    
    // 初始化审核检查项
    allReviewItems.value.forEach(item => {
      deliverableForm.selfReviewChecks[item] = false
    })
  } catch (e: any) {
    ElMessage.error('加载失败')
    router.push('/contractor/assignments')
  }
}

const handleAccept = async () => {
  try {
    await request.put(`/contractor/assignments/${assignment.value.id}/accept`)
    ElMessage.success('接单成功')
    fetchDetail()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const beforeUpload = (file: File) => {
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

const handleUploadSuccess = (res: any, file: any) => {
  // el-upload 的 res 是原始 HTTP 响应体，不经过 axios 拦截器
  const url = res?.data?.url || res?.url
  if (url) {
    uploadedFiles.value.push({
      name: file.name,
      url: url,
      size: file.size,
      mime_type: file.raw?.type || '',
    })
  }
}

const handleUploadError = () => {
  ElMessage.error('文件上传失败')
}

// 当前审核步骤（第一个未确认的项）
const currentReviewStep = computed(() => {
  let idx = 0
  for (const cat of reviewCategories.value) {
    for (const item of cat.items) {
      if (!deliverableForm.selfReviewChecks[item]) return idx
      idx++
    }
  }
  return idx // 全部完成
})

const checkedCount = computed(() =>
  allReviewItems.value.filter(item => deliverableForm.selfReviewChecks[item]).length
)
const totalItems = computed(() => allReviewItems.value.length)

// 获取全局顺序索引
const getGlobalIndex = (cIdx: number, idx: number): number => {
  let offset = 0
  for (let i = 0; i < cIdx; i++) {
    offset += reviewCategories.value[i].items.length
  }
  return offset + idx
}

// 确认当前项
const confirmItem = (item: string) => {
  deliverableForm.selfReviewChecks[item] = true
}

// 撤回确认（只允许撤回最后一个已确认的项，防止跳过）
const uncheckItem = (item: string) => {
  const globalIdx = allReviewItems.value.indexOf(item)
  // 只允许撤回最后确认的那一项（即 currentReviewStep - 1）
  if (globalIdx === currentReviewStep.value - 1) {
    deliverableForm.selfReviewChecks[item] = false
  } else {
    ElMessage.warning('请按顺序撤回，只能撤回最近确认的一项')
  }
}

const saveDraft = async () => {
  saving.value = true
  try {
    const stage = currentStage.value
    if (!stage) return

    if (currentDeliverableId.value) {
      await request.put(`/contractor/deliverables/${currentDeliverableId.value}`, {
        description: deliverableForm.description,
        files: uploadedFiles.value,
        self_review_checks: deliverableForm.selfReviewChecks,
      })
    } else {
      const res: any = await request.post('/contractor/deliverables', {
        assignment_id: assignment.value.id,
        stage_config_id: stage.stage_config_id,
        stage_name: stage.name,
        stage_order: stage.display_order,
        description: deliverableForm.description,
        files: uploadedFiles.value,
        self_review_checks: deliverableForm.selfReviewChecks,
      })
      currentDeliverableId.value = res?.id
    }
    ElMessage.success('草稿已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const submitDeliverable = async () => {
  if (!allChecked.value) {
    ElMessage.warning('请先完成所有审核检查项')
    return
  }
  if (uploadedFiles.value.length === 0) {
    ElMessage.warning('请至少上传一个文件')
    return
  }

  submitting.value = true
  try {
    // 先保存
    await saveDraft()
    if (!currentDeliverableId.value) return

    // 提交审核
    await request.put(`/contractor/deliverables/${currentDeliverableId.value}/submit`)
    ElMessage.success('交付物已提交审核')
    fetchDetail()
    // 重置表单
    deliverableForm.description = ''
    deliverableForm.selfReviewChecks = {}
    uploadedFiles.value = []
    fileList.value = []
    currentDeliverableId.value = null
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchDetail)
</script>

<style lang="scss" scoped>
.assignment-detail { max-width: 900px; margin: 0 auto; }
.back-bar { margin-bottom: 16px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 12px; }
.detail-title { font-size: 22px; font-weight: 700; color: #1D1D1F; margin: 0; }

/* 改为单列布局，并将左侧参考信息移至下方 */
.detail-grid { display: flex; flex-direction: column; gap: 24px; }
.detail-left { order: 2; }
.detail-right { order: 1; }

.info-card {
  background: #fff; border-radius: 12px; padding: 24px;
  border: 1px solid #E5E7EB;
}
.card-title { font-size: 16px; font-weight: 600; color: #1D1D1F; margin: 0 0 16px; display: flex; align-items: center; }

/* 覆盖 el-collapse 样式 */
:deep(.custom-collapse) {
  border: none;
  .el-collapse-item { margin-bottom: 24px; }
  .el-collapse-item__header {
    border-bottom: none;
    height: auto;
    line-height: normal;
    background: transparent;
  }
  .el-collapse-item__wrap {
    border-bottom: none;
    background: transparent;
  }
  .el-collapse-item__content {
    padding-bottom: 0;
  }
}

.sub-title { font-size: 14px; font-weight: 500; color: #86868B; margin: 0 0 12px; }
.info-grid { display: flex; flex-direction: column; gap: 10px; }
.info-item { display: flex; gap: 12px; }
.info-label { color: #86868B; font-size: 13px; min-width: 70px; flex-shrink: 0; }
.info-value { color: #1D1D1F; font-size: 13px; word-break: break-all; }

/* AI设计方案 */
.design-plan-content {
  background: #F0F7FF; border-radius: 8px; padding: 16px; margin-bottom: 12px;
  border-left: 3px solid #409eff;
}
.plan-text { margin: 0; font-size: 14px; color: #1D1D1F; line-height: 1.7; white-space: pre-wrap; }
.plan-files { margin-top: 8px; }
.plan-file-item { margin-bottom: 6px; }
.plan-file-link {
  font-size: 13px; color: #409eff; text-decoration: none;
  &:hover { text-decoration: underline; }
}
.site-photos { display: flex; flex-wrap: wrap; gap: 8px; }
.photo-link {
  font-size: 13px; color: #409eff; padding: 6px 12px;
  background: #F0F7FF; border-radius: 6px; text-decoration: none;
  &:hover { background: #E0EFFF; }
}

/* 时间线 */
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 0;
  border-left: 2px solid #E5E7EB; margin-left: 12px; padding-left: 20px;
  position: relative;
  &.active { border-left-color: #409eff; }
  &.completed { border-left-color: #67C23A; }
}
.timeline-dot {
  position: absolute; left: -13px;
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
  background: #E5E7EB; color: #86868B;
  .timeline-item.active & { background: #409eff; color: #fff; }
  .timeline-item.completed & { background: #67C23A; color: #fff; }
}
.stage-name { font-size: 14px; font-weight: 500; color: #1D1D1F; }
.stage-meta { font-size: 12px; color: #86868B; margin-top: 2px; }

/* 交付物历史 */
.deliverable-history { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #F0F0F0; }
.history-item {
  padding: 8px 12px; background: #F9F9F9; border-radius: 8px; margin-bottom: 8px;
}
.history-header { display: flex; justify-content: space-between; align-items: center; }
.history-time { font-size: 12px; color: #86868B; }
.review-note { font-size: 13px; color: #E6A23C; margin: 6px 0 0; line-height: 1.5; }

/* 自审核 */
.self-review-section { margin-top: 20px; padding: 20px; background: #FFFBE6; border-radius: 10px; border: 1px solid #FFF1B8; }
.review-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
}
.review-title {
  font-size: 14px; font-weight: 600; color: #D48806; margin: 0;
  display: flex; align-items: center; gap: 6px;
}
.review-progress {
  font-size: 13px; color: #8C6D1F; font-weight: 500;
  padding: 2px 10px; border-radius: 10px; background: rgba(214,158,6,0.1);
  &.complete { color: #52C41A; background: rgba(82,196,26,0.1); }
}
.review-category { margin-bottom: 16px; &:last-child { margin-bottom: 0; } }
.category-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
  padding-bottom: 8px; border-bottom: 1px solid #FFF1B8;
}
.category-index {
  width: 22px; height: 22px; border-radius: 50%; background: #D48806; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
  transition: background 0.3s;
  &.done { background: #52C41A; }
}
.category-title { font-size: 14px; font-weight: 600; color: #8C6D1F; }
.review-checklist { display: flex; flex-direction: column; gap: 6px; }

/* 审核步骤卡片 */
.review-step { border-radius: 8px; overflow: hidden; transition: all 0.3s ease; }

/* 已确认态 */
.step-confirmed {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #F6FFED; border: 1px solid #B7EB8F;
  border-radius: 8px; cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #95DE64; }
  &:hover .step-undo { opacity: 1; }
}
.step-left { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.step-check-icon { display: flex; align-items: center; flex-shrink: 0; }
.step-number { font-weight: 600; color: #52C41A; font-size: 13px; flex-shrink: 0; }
.step-text-short { color: #389E0D; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.step-undo { font-size: 12px; color: #FAAD14; opacity: 0; transition: opacity 0.2s; flex-shrink: 0; cursor: pointer; }

/* 当前项展开态 */
.step-active {
  background: #fff; border: 2px solid #FAAD14; border-radius: 8px;
  animation: stepPulse 0.3s ease;
}
@keyframes stepPulse {
  0% { transform: scale(0.98); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
}
.step-active-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px 8px; border-bottom: 1px dashed #FFF1B8;
}
.step-number-active {
  font-size: 14px; font-weight: 700; color: #D48806;
  background: #FFFBE6; padding: 2px 8px; border-radius: 4px;
}
.step-label { font-size: 12px; color: #8C6D1F; }
.step-active-body { padding: 12px 16px 16px; }
.step-content-text {
  font-size: 15px; font-weight: 500; color: #1D1D1F; line-height: 1.6;
  padding: 12px; background: #FFFBE6; border-radius: 6px; margin-bottom: 14px;
  border-left: 3px solid #FAAD14;
}
.step-confirm-row { display: flex; align-items: center; }
.confirm-checkbox {
  :deep(.el-checkbox__label) { font-size: 13px; color: #D48806; font-weight: 500; }
  :deep(.el-checkbox__input.is-checked .el-checkbox__inner) { background-color: #52C41A; border-color: #52C41A; }
}

/* 锁定态 */
.step-locked {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; background: #FAFAFA; border: 1px solid #F0F0F0;
  border-radius: 8px; opacity: 0.55; cursor: not-allowed;
}
.step-lock-icon { display: flex; align-items: center; flex-shrink: 0; }
.step-text-locked { color: #8C8C8C; font-size: 13px; }

/* 提交按钮 */
.submit-actions { margin-top: 20px; display: flex; justify-content: flex-end; gap: 12px; }

/* 待处理/已完成提示 */
.pending-notice { text-align: center; padding: 40px 0; color: #86868B;
  h3 { color: #1D1D1F; margin: 12px 0 8px; }
}

.loading-state {
  text-align: center; padding: 80px 0; color: #86868B;
  .loading-icon { animation: spin 1s linear infinite; }
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 管理员评论样式 */
.admin-comments-section {
  margin-top: 10px;
  padding: 10px 12px;
  background: #ECF5FF;
  border-radius: 6px;
  border-left: 3px solid #409EFF;
}

.admin-comments-title {
  font-size: 13px;
  color: #409EFF;
  display: block;
  margin-bottom: 6px;
}

.admin-comment-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px dashed #D9ECFF;
  &:last-child { border-bottom: none; }
}

.admin-comment-content {
  flex: 1;
  color: #303133;
  line-height: 1.5;
}

.admin-comment-meta {
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
