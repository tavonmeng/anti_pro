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
        <!-- 订单需求信息 -->
        <div class="info-card">
          <h3 class="card-title">订单需求</h3>
          <div class="info-grid">
            <div class="info-item" v-for="item in orderFields" :key="item.key">
              <span class="info-label">{{ item.label }}</span>
              <span class="info-value">{{ item.value || '—' }}</span>
            </div>
          </div>
        </div>

        <!-- 排期时间线 -->
        <div class="info-card">
          <h3 class="card-title">工作流排期</h3>
          <div class="timeline">
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
        </div>
      </div>

      <!-- 右栏：交付物上传 -->
      <div class="detail-right">
        <div class="info-card" v-if="assignment.status === 'in_progress'">
          <h3 class="card-title">
            交付物上传 — {{ currentStageName }}
            <el-tag type="info" size="small" style="margin-left:8px">第 {{ currentStageOrder }} 环节</el-tag>
          </h3>

          <!-- 当前环节历史交付物 -->
          <div v-if="stageDeliverables.length > 0" class="deliverable-history">
            <h4 class="sub-title">历史提交记录</h4>
            <div v-for="d in stageDeliverables" :key="d.id" class="history-item">
              <div class="history-header">
                <span>V{{ d.version }}</span>
                <el-tag :type="deliverableStatusType(d.status)" size="small">{{ deliverableStatusLabel(d.status) }}</el-tag>
              </div>
              <p v-if="d.adminReviewNote" class="review-note">管理员备注：{{ d.adminReviewNote }}</p>
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
              <h4 class="review-title">
                <el-icon color="#E6A23C"><WarningFilled /></el-icon>
                提交前请逐项确认
              </h4>
              <div class="review-checklist">
                <div
                  v-for="item in reviewItems"
                  :key="item"
                  class="review-item"
                  :class="{ checked: deliverableForm.selfReviewChecks[item] }"
                  @click="toggleReviewCheck(item)"
                >
                  <el-checkbox
                    :model-value="deliverableForm.selfReviewChecks[item] || false"
                    @change="(val: boolean) => handleCheckChange(item, val)"
                  >
                    {{ item }}
                  </el-checkbox>
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
            <p>接单后即可开始上传交付物</p>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Check, UploadFilled, WarningFilled,
  InfoFilled, CircleCheckFilled, Loading
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

// 当前环节
const currentStageOrder = computed(() => parseInt(assignment.value?.currentStageOrder || '1'))
const currentStage = computed(() =>
  (assignment.value?.schedule || []).find((s: any) => s.display_order === currentStageOrder.value)
)
const currentStageName = computed(() => currentStage.value?.name || '—')

// 审核检查项
const reviewItems = computed(() => {
  // 从工作流配置获取，默认4项
  return ['内容安全合规性', '风格与品牌调性一致', '技术规格达标', '无版权/商标侵权风险']
})

const allChecked = computed(() =>
  reviewItems.value.length > 0 && reviewItems.value.every(item => deliverableForm.selfReviewChecks[item])
)

// 当前环节的交付物历史
const stageDeliverables = computed(() =>
  (assignment.value?.deliverables || []).filter(
    (d: any) => d.stageOrder === currentStageOrder.value
  )
)

// 订单信息展示
const orderFields = computed(() => {
  const o = assignment.value?.order || {}
  return [
    { key: 'brand', label: '品牌', value: o.brand },
    { key: 'city', label: '城市', value: o.city },
    { key: 'content', label: '内容需求', value: o.content },
    { key: 'style', label: '风格偏好', value: o.style },
    { key: 'target_group', label: '目标受众', value: o.target_group },
    { key: 'media_size', label: '媒体尺寸', value: o.media_size },
    { key: 'technology', label: '技术需求', value: o.technology },
    { key: 'budget', label: '预算', value: o.budget },
    { key: 'online_time', label: '上刊时间', value: o.online_time },
    { key: 'background', label: '项目背景', value: o.background },
  ].filter(f => f.value)
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

const fetchDetail = async () => {
  try {
    const id = route.params.id
    const res = await request.get(`/api/contractor/assignments/${id}`)
    assignment.value = res.data
    // 初始化审核检查项
    reviewItems.value.forEach(item => {
      deliverableForm.selfReviewChecks[item] = false
    })
  } catch (e: any) {
    ElMessage.error('加载失败')
    router.push('/contractor/assignments')
  }
}

const handleAccept = async () => {
  try {
    await request.put(`/api/contractor/assignments/${assignment.value.id}/accept`)
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
  if (res?.data?.url) {
    uploadedFiles.value.push({
      name: file.name,
      url: res.data.url,
      size: file.size,
      mime_type: file.raw?.type || '',
    })
  }
}

const handleUploadError = () => {
  ElMessage.error('文件上传失败')
}

const toggleReviewCheck = async (item: string) => {
  const current = deliverableForm.selfReviewChecks[item]
  if (!current) {
    // 点击勾选时弹出确认
    try {
      await ElMessageBox.confirm(
        `请确认此交付物已通过【${item}】审核`,
        '审核确认',
        { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'warning' }
      )
      deliverableForm.selfReviewChecks[item] = true
    } catch {
      // 用户取消
    }
  } else {
    deliverableForm.selfReviewChecks[item] = false
  }
}

const handleCheckChange = (item: string, val: boolean) => {
  if (val) {
    toggleReviewCheck(item)
  } else {
    deliverableForm.selfReviewChecks[item] = false
  }
}

const saveDraft = async () => {
  saving.value = true
  try {
    const stage = currentStage.value
    if (!stage) return

    if (currentDeliverableId.value) {
      await request.put(`/api/contractor/deliverables/${currentDeliverableId.value}`, {
        description: deliverableForm.description,
        files: uploadedFiles.value,
        self_review_checks: deliverableForm.selfReviewChecks,
      })
    } else {
      const res = await request.post('/api/contractor/deliverables', {
        assignment_id: assignment.value.id,
        stage_config_id: stage.stage_config_id,
        stage_name: stage.name,
        stage_order: stage.display_order,
        description: deliverableForm.description,
        files: uploadedFiles.value,
        self_review_checks: deliverableForm.selfReviewChecks,
      })
      currentDeliverableId.value = res.data?.id
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
    await request.put(`/api/contractor/deliverables/${currentDeliverableId.value}/submit`)
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
.assignment-detail { max-width: 1200px; margin: 0 auto; }
.back-bar { margin-bottom: 16px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 12px; }
.detail-title { font-size: 22px; font-weight: 700; color: #1D1D1F; margin: 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 900px) { .detail-grid { grid-template-columns: 1fr; } }

.info-card {
  background: #fff; border-radius: 12px; padding: 24px;
  border: 1px solid #E5E7EB;
}
.card-title { font-size: 16px; font-weight: 600; color: #1D1D1F; margin: 0 0 16px; display: flex; align-items: center; }
.sub-title { font-size: 14px; font-weight: 500; color: #86868B; margin: 0 0 12px; }
.info-grid { display: flex; flex-direction: column; gap: 10px; }
.info-item { display: flex; gap: 12px; }
.info-label { color: #86868B; font-size: 13px; min-width: 70px; flex-shrink: 0; }
.info-value { color: #1D1D1F; font-size: 13px; word-break: break-all; }

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
.review-note { font-size: 12px; color: #E6A23C; margin: 4px 0 0; }

/* 自审核 */
.self-review-section { margin-top: 20px; padding: 16px; background: #FFFBE6; border-radius: 8px; border: 1px solid #FFF1B8; }
.review-title {
  font-size: 14px; font-weight: 600; color: #D48806; margin: 0 0 12px;
  display: flex; align-items: center; gap: 6px;
}
.review-checklist { display: flex; flex-direction: column; gap: 8px; }
.review-item {
  padding: 8px 12px; border-radius: 6px; cursor: pointer;
  transition: all 0.2s; background: #fff; border: 1px solid #F0F0F0;
  &.checked { background: #F6FFED; border-color: #B7EB8F; }
  &:hover { border-color: #409eff; }
}

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
</style>
