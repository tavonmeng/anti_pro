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
        <div>
          <h1 class="detail-title">{{ orderTitle }}</h1>
          <p class="detail-breadcrumb">工作台 <span></span> {{ assignment.order?.orderNumber || '—' }}</p>
        </div>
        <span class="detail-status">{{ statusLabel(assignment.status) }}</span>
      </div>
    </div>

    <section class="detail-cockpit">
      <article class="cockpit-card stage-card">
        <div class="cockpit-topline">
          <span class="cockpit-icon"><el-icon><Timer /></el-icon></span>
          <span class="stage-chip">第 {{ currentStageOrder }} 环节</span>
        </div>
        <h2>{{ currentStageName }}</h2>
        <p>当前交付阶段</p>
        <div class="stage-actions" v-if="canAcceptAssignment">
          <button type="button" class="dark-pill" @click="handleAccept">接受派单</button>
        </div>
      </article>

      <article class="cockpit-card calendar-card">
        <div class="cockpit-topline">
          <span class="cockpit-icon"><el-icon><Calendar /></el-icon></span>
          <span class="stage-chip">{{ detailTotalDays }} 天</span>
        </div>
        <div class="detail-dot-grid">
          <span v-for="(dot, index) in detailCalendarDots" :key="index" :class="dot"></span>
        </div>
        <p>订单排期日历</p>
      </article>

      <article class="cockpit-card review-meter-card">
        <div class="cockpit-topline">
          <span class="cockpit-icon"><el-icon><WarningFilled /></el-icon></span>
        </div>
        <strong>{{ checkedCount }}/{{ totalItems }}</strong>
        <span>自审核</span>
        <div class="meter-track">
          <i :style="{ width: `${reviewPercent}%` }"></i>
        </div>
      </article>

      <article class="cockpit-card history-meter-card">
        <div class="cockpit-topline">
          <span class="cockpit-icon"><el-icon><Document /></el-icon></span>
        </div>
        <strong>{{ stageDeliverables.length }}</strong>
        <span>提交记录</span>
        <div class="history-bars">
          <i v-for="n in 9" :key="n" :style="{ height: `${18 + (n % 5) * 8}px` }"></i>
        </div>
      </article>
    </section>

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
                <el-icon><Document /></el-icon>
                <span>AI设计方案</span>
                <el-tag v-if="assignment.order.designPlan.status === 'completed'" type="success" size="small" effect="dark">已完成</el-tag>
              </h3>
            </template>
            <div style="margin-top: 16px;">
              <div class="design-plan-content">
                <p class="plan-text">{{ assignment.order.designPlan.content }}</p>
              </div>
              <div v-if="assignment.order.designPlan.files?.length" class="plan-files">
                <h4 class="sub-title">参考文件</h4>
                <div class="asset-grid">
                  <button
                    v-for="(file, idx) in assignment.order.designPlan.files"
                    :key="fileKey(file, idx)"
                    type="button"
                    class="asset-card"
                    @click="openPreviewAttachment(file)"
                  >
                    <span class="asset-thumb" :class="`is-${previewAttachmentKind(file)}`">
                      <img
                        v-if="previewAttachmentKind(file) === 'image' && fileUrl(file)"
                        :src="fileUrl(file)"
                        :alt="previewAttachmentName(file, `方案附件 ${idx + 1}`)"
                        loading="lazy"
                      />
                      <el-icon v-else :size="22"><component :is="previewAttachmentIcon(file)" /></el-icon>
                    </span>
                    <span class="asset-info">
                      <strong>{{ previewAttachmentName(file, `方案附件 ${idx + 1}`) }}</strong>
                      <small>{{ assetKindLabel(previewAttachmentKind(file)) }}</small>
                    </span>
                    <span class="asset-action">{{ previewAttachmentActionText(file) }}</span>
                  </button>
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
              <div class="asset-grid">
                <button
                  v-for="(photo, idx) in assignment.order.site_photos"
                  :key="fileKey(photo, idx)"
                  type="button"
                  class="asset-card"
                  @click="openPreviewAttachment(photo)"
                >
                  <span class="asset-thumb" :class="`is-${previewAttachmentKind(photo)}`">
                    <img
                      v-if="previewAttachmentKind(photo) === 'image' && fileUrl(photo)"
                      :src="fileUrl(photo)"
                      :alt="previewAttachmentName(photo, `现场文件 ${idx + 1}`)"
                      loading="lazy"
                    />
                    <el-icon v-else :size="22"><component :is="previewAttachmentIcon(photo)" /></el-icon>
                  </span>
                  <span class="asset-info">
                    <strong>{{ previewAttachmentName(photo, `现场文件 ${idx + 1}`) }}</strong>
                    <small>{{ assetKindLabel(previewAttachmentKind(photo)) }}</small>
                  </span>
                  <span class="asset-action">{{ previewAttachmentActionText(photo) }}</span>
                </button>
              </div>
            </div>
          </el-collapse-item>

          <!-- 制作素材 -->
          <el-collapse-item name="assets" class="info-card" v-if="productionAssetGroups.length">
            <template #title>
              <h3 class="card-title" style="margin: 0; width: 100%;">需求素材</h3>
            </template>
            <div class="production-assets" style="margin-top: 16px;">
              <div
                v-for="group in productionAssetGroups"
                :key="group.label"
                class="asset-group"
              >
                <div class="asset-group-title">
                  <span>{{ group.label }}</span>
                  <el-tag size="small" effect="plain">{{ group.assets.length }} 个</el-tag>
                </div>
                <div class="asset-grid">
                  <button
                    v-for="asset in group.assets"
                    :key="assetKey(asset)"
                    type="button"
                    class="asset-card"
                    @click="openProductionAssetPreview(asset)"
                  >
                    <span class="asset-thumb" :class="`is-${previewAttachmentKind(asset)}`">
                      <img
                        v-if="previewAttachmentKind(asset) === 'image' && fileUrl(asset)"
                        :src="fileUrl(asset)"
                        :alt="assetName(asset)"
                        loading="lazy"
                      />
                      <el-icon v-else :size="22"><component :is="assetIcon(asset)" /></el-icon>
                    </span>
                    <span class="asset-info">
                      <strong>{{ assetName(asset) }}</strong>
                      <small>{{ assetKindLabel(previewAttachmentKind(asset)) }}</small>
                    </span>
                    <span class="asset-action">{{ productionAssetActionText(asset) }}</span>
                  </button>
                </div>
              </div>
            </div>
          </el-collapse-item>

        </el-collapse>
      </div>

      <!-- 右栏：交付物上传 -->
      <div class="detail-right">
        <div class="info-card" v-if="canSubmitDeliverable">
          <h3 class="card-title">
            交付环节 — {{ currentStageName }}
            <el-tag type="info" size="small" style="margin-left:8px">第 {{ currentStageOrder }} 环节</el-tag>
          </h3>

          <div v-if="stageDeliverables.length > 0" class="deliverable-history">
            <h4 class="sub-title">历史提交记录</h4>
            <div
              v-for="(d, dlvIndex) in stageDeliverables"
              :key="d.id"
              class="history-item"
              :class="{ 'is-alt': dlvIndex % 2 === 1 }"
            >
              <div class="history-header">
                <div class="history-title-row">
                  <span class="history-stage-label">{{ getDeliverableStageLabel(d) }}</span>
                  <span>V{{ d.version }}</span>
                  <el-tag :type="deliverableStatusType(d.status)" size="small">{{ deliverableStatusLabel(d.status) }}</el-tag>
                  <el-tag v-if="isCurrentStageDeliverable(d)" type="primary" size="small" effect="plain">当前环节</el-tag>
                </div>
                <span v-if="d.createdAt" class="history-time">{{ formatDate(d.createdAt) }}</span>
              </div>
              <p v-if="d.adminReviewNote" class="review-note">
                <strong>管理员备注 ({{ formatDate(d.adminReviewedAt) || '暂无时间' }})：</strong>
                {{ d.adminReviewNote }}
              </p>
              <div v-if="d.files && d.files.length" class="history-files">
                <a
                  v-for="(file, fileIndex) in d.files"
                  :key="fileKey(file, fileIndex)"
                  :href="fileUrl(file)"
                  class="history-file-link"
                  target="_blank"
                  @click.prevent="openFilePreview(file)"
                >
                  {{ file.name || file.filename || file.originalName || '交付文件' }}
                </a>
              </div>
              <!-- 管理员评论列表 -->
              <div v-if="d.adminComments && d.adminComments.length > 0" class="admin-comments-section">
                <strong class="admin-comments-title">管理员评论：</strong>
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
        <div class="info-card" v-else-if="canAcceptAssignment">
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
  <FilePreviewDialog v-model="filePreviewVisible" :file="previewingFile" />
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Check, UploadFilled, WarningFilled,
  InfoFilled, CircleCheckFilled, Loading, Lock,
  Calendar, Document, Picture, Timer, VideoPlay
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import { useAuthStore } from '@/stores/auth'
import { formatServerTime, parseServerTime } from '@/utils/time'
import FilePreviewDialog from '@/components/FilePreviewDialog.vue'
import {
  getFilePreviewKind,
  getFilePreviewOpenTarget,
  getPdfPreviewProxyUrl,
  getPreviewFileName,
  getPreviewFileUrl,
} from '@/utils/filePreview'
import {
  assetKindLabel,
  groupProductionAssets,
  productionAssetActionText,
  productionAssetKind,
  productionAssetPreviewTarget,
  type ProductionAsset,
} from '@/utils/productionAssets'

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
const filePreviewVisible = ref(false)
const previewingFile = ref<Record<string, any> | null>(null)
const previewBlobUrl = ref<string | null>(null)

const deliverableForm = reactive({
  description: '',
  selfReviewChecks: {} as Record<string, boolean>,
})

// 卡片折叠状态
const activeNames = ref<string[]>(['requirements', 'schedule', 'aiPlan', 'photos', 'assets'])

// 当前环节
const currentStageOrder = computed(() => parseInt(assignment.value?.currentStageOrder || '1'))
const currentStage = computed(() =>
  (assignment.value?.schedule || []).find((s: any) => s.display_order === currentStageOrder.value)
)
const currentStageName = computed(() => currentStage.value?.name || '—')

const detailTotalDays = computed(() =>
  (assignment.value?.schedule || []).reduce((sum: number, stage: any) => sum + Number(stage.days || 0), 0)
)

const detailCalendarDots = computed(() => {
  const days = Math.max(12, Math.min(24, detailTotalDays.value || 12))
  const completedStages = (assignment.value?.schedule || []).filter((stage: any) => stage.status === 'completed').length
  const completed = Math.min(days, completedStages * 4)
  const active = Math.min(days - 1, Math.max(completed, completed + 2))
  return Array.from({ length: days }, (_, index) => {
    if (index < completed) return 'done'
    if (index === active) return 'active'
    return 'muted'
  })
})

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

const deliverableSortTime = (deliverable: any) => {
  return parseServerTime(deliverable?.createdAt || deliverable?.adminReviewedAt)?.getTime() || 0
}

// 展示全部环节的交付物历史，避免进入下一环节后看不到上一环节信息
const stageDeliverables = computed(() =>
  [...(assignment.value?.deliverables || [])]
    .sort((a: any, b: any) => {
      const timeDiff = deliverableSortTime(b) - deliverableSortTime(a)
      if (timeDiff !== 0) return timeDiff
      const stageDiff = Number(b.stageOrder || 0) - Number(a.stageOrder || 0)
      if (stageDiff !== 0) return stageDiff
      return Number(b.version || 0) - Number(a.version || 0)
    })
)

const getDeliverableStageLabel = (deliverable: any) => {
  const stageOrder = Number(deliverable?.stageOrder || 0)
  const stage = (assignment.value?.schedule || []).find(
    (item: any) => Number(item.display_order || 0) === stageOrder
  )
  const stageName = deliverable?.stageName || stage?.name || '交付环节'
  return stageOrder ? `第 ${stageOrder} 环节 · ${stageName}` : stageName
}

const isCurrentStageDeliverable = (deliverable: any) =>
  Number(deliverable?.stageOrder || 0) === currentStageOrder.value

const fileUrl = (file: any) => file?.url || file?.file_url || file?.fileUrl || file?.href || ''
const fileKey = (file: any, index = 0) =>
  file?.id || file?.url || file?.file_url || file?.fileUrl || file?.href || file?.object_key || file?.filename || file?.name || index

const revokePreviewBlobUrl = () => {
  if (previewBlobUrl.value) {
    URL.revokeObjectURL(previewBlobUrl.value)
    previewBlobUrl.value = null
  }
}

const openAuthenticatedPdfPreview = async (file: any, targetUrl: string) => {
  try {
    const response = await fetch(targetUrl, { headers: uploadHeaders.value })
    if (!response.ok) {
      throw new Error(`PDF preview failed: ${response.status}`)
    }
    const blob = await response.blob()
    revokePreviewBlobUrl()
    const pdfBlob = blob.type === 'application/pdf' ? blob : new Blob([blob], { type: 'application/pdf' })
    const blobUrl = URL.createObjectURL(pdfBlob)
    previewBlobUrl.value = blobUrl
    previewingFile.value = {
      ...file,
      url: blobUrl,
      previewUrl: blobUrl,
      file_url: blobUrl,
      type: 'application/pdf',
      mime_type: 'application/pdf',
      kind: 'pdf',
    }
    filePreviewVisible.value = true
  } catch (error) {
    console.error('PDF preview failed:', error)
    ElMessage.error('PDF 预览失败，请稍后重试')
  }
}

const openFilePreview = async (
  file: any,
  options: { forceDialog?: boolean; authenticatedPdf?: boolean } = {},
) => {
  const kind = file?.kind === 'pdf' ? 'pdf' : getFilePreviewKind(file)
  const targetUrl = kind === 'pdf'
    ? (getPdfPreviewProxyUrl(file) || getPreviewFileUrl(file))
    : getPreviewFileUrl(file)

  if (!targetUrl) {
    ElMessage.warning('文件地址为空，无法预览')
    return
  }

  if (kind === 'pdf' && options.authenticatedPdf) {
    await openAuthenticatedPdfPreview(file, targetUrl)
    return
  }

  if (!options.forceDialog && (kind === 'pdf' || getFilePreviewOpenTarget(file) === 'new-tab')) {
    window.open(targetUrl, '_blank', 'noopener,noreferrer')
    return
  }

  previewingFile.value = file
  filePreviewVisible.value = true
}

const previewAttachmentKind = (file: ProductionAsset) => productionAssetKind(file)

const previewAttachmentName = (file: ProductionAsset, fallback = '文件') =>
  getPreviewFileName(file, fallback)

const previewAttachmentActionText = (file: ProductionAsset) =>
  productionAssetActionText(file)

const previewAttachmentIcon = (file: ProductionAsset) => {
  const kind = previewAttachmentKind(file)
  if (kind === 'image') return Picture
  if (kind === 'video') return VideoPlay
  return Document
}

const openPreviewAttachment = (file: ProductionAsset) => {
  const kind = previewAttachmentKind(file)
  const inferredType = kind === 'pdf'
    ? 'application/pdf'
    : kind === 'image'
      ? 'image/*'
      : kind === 'video'
        ? 'video/*'
        : file.type
  const normalized = { ...file, kind, type: file.type || inferredType, mime_type: file.mime_type || inferredType }
  const target = productionAssetPreviewTarget(normalized)
  openFilePreview(normalized, {
    forceDialog: target === 'dialog',
    authenticatedPdf: kind === 'pdf',
  })
}

const openProductionAssetPreview = (asset: ProductionAsset) => openPreviewAttachment(asset)

const productionAssetGroups = computed(() =>
  groupProductionAssets(assignment.value?.order?.productionAssets || [])
)

const canAcceptAssignment = computed(() =>
  assignment.value?.canAccept === true || (
    assignment.value?.creatorType !== 'staff' && assignment.value?.status === 'pending'
  )
)

const canSubmitDeliverable = computed(() =>
  assignment.value?.canSubmitDeliverable === true || (
    assignment.value?.canSubmitDeliverable !== false && assignment.value?.status === 'in_progress'
  )
)

const assetKey = (asset: ProductionAsset) =>
  asset.id || asset.object_key || asset.url || asset.file_url || asset.fileUrl || asset.name || asset.filename || JSON.stringify(asset)

const assetName = (asset: ProductionAsset) => getPreviewFileName(asset, '制作素材')

const assetIcon = (asset: ProductionAsset) => {
  return previewAttachmentIcon(asset)
}

// 订单信息展示
const orderFields = computed(() => {
  const o = assignment.value?.order || {} as any
  return [
    { key: 'projectName', label: '项目名称', value: o.projectName || o.project_name },
    { key: 'brand', label: '品牌', value: o.brand },
    { key: 'brand_tone', label: '品牌调性', value: o.brand_tone },
    { key: 'city', label: '投放城市/位置', value: o.city_location || o.city },
    { key: 'media_size', label: '媒体尺寸/物理规格', value: o.media_specs || o.media_size },
    { key: 'time_number', label: '投放时长/数量', value: o.timing_number || o.time_number },
    { key: 'online_time', label: '预计上刊时间', value: o.online_time },
    { key: 'theme_concept', label: '主题与核心表达', value: o.theme_concept },
    { key: 'art_direction', label: '艺术方向/风格', value: o.art_direction || o.style },
    { key: 'technology', label: '技术需求', value: o.tech_delivery || o.technology },
    { key: 'background', label: '项目背景', value: o.resource_background || o.background },
    { key: 'audience_scene', label: '受众/场景', value: o.audience_scene || o.target_group },
    { key: 'media_positioning', label: '媒体定位', value: o.media_positioning },
    { key: 'viewing_path', label: '观看路径', value: o.viewing_path },
    { key: 'content', label: '内容需求', value: o.content },
    { key: 'content_review', label: '内容审核要求', value: o.content_review },
    { key: 'special_requirements', label: '特殊要求', value: o.special_requirements },
    { key: 'prohibited_content', label: '品牌禁忌内容', value: o.prohibited_content },
    { key: 'remarks', label: '备注', value: o.remarks },
  ].filter(f => f.value !== undefined && f.value !== null)
})

const orderTitle = computed(() => {
  const o = assignment.value?.order || {}
  return o.projectName || o.project_name || o.brand || o.orderNumber || '派单详情'
})

const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`,
}))

const statusLabel = (s: string) => ({
  pending: '待处理', accepted: '已接单', in_progress: '进行中', completed: '已完成', rejected: '已拒绝', cancelled: '已取消',
}[s] || s)

const deliverableStatusLabel = (s: string) => ({
  draft: '草稿', submitted: '待审核', admin_approved: '已通过', admin_rejected: '已驳回',
}[s] || s)

const deliverableStatusType = (s: string) => ({
  draft: 'info', submitted: 'warning', admin_approved: 'success', admin_rejected: 'danger',
}[s] || 'info')

const formatDate = (dateStr: string) => {
  return formatServerTime(dateStr, '')
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
  if (!canAcceptAssignment.value) {
    ElMessage.warning('当前任务无需接单')
    return
  }

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
  const data = res?.data || res || {}
  const url = data.url
  if (url) {
    uploadedFiles.value.push({
      name: file.name,
      url: url,
      object_key: data.object_key || '',
      filename: data.filename || file.name,
      size: file.size,
      mime_type: data.mime_type || file.raw?.type || '',
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
const reviewPercent = computed(() =>
  totalItems.value ? Math.round((checkedCount.value / totalItems.value) * 100) : 0
)

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
onBeforeUnmount(revokePreviewBlobUrl)
</script>

<style lang="scss" scoped>
.assignment-detail { max-width: 1320px; margin: 0 auto; }
.back-bar { margin-bottom: 18px; }
.back-bar :deep(.el-button) {
  height: 40px;
  padding: 0 16px;
  border-radius: 20px;
  color: #4B4640;
  font-weight: 750;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 44px 52px 24px;
  border-radius: 34px 34px 0 0;
  background: #ECEAE7;
}
.header-left { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; width: 100%; }
.detail-title {
  font-size: clamp(34px, 4vw, 52px);
  font-weight: 850;
  line-height: 1;
  letter-spacing: 0;
  color: #121212;
  margin: 0 0 16px;
}
.detail-breadcrumb {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  color: #5E5954;
  font-size: 16px;
  font-weight: 750;

  span {
    width: 8px;
    height: 8px;
    border-top: 2px solid #4B4640;
    border-right: 2px solid #4B4640;
    transform: rotate(45deg);
  }
}
.detail-status {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  padding: 0 18px;
  border-radius: 20px;
  background: #111111;
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
}

.detail-cockpit {
  display: grid;
  grid-template-columns: minmax(280px, 1.3fr) minmax(220px, 0.9fr) minmax(180px, 0.65fr) minmax(180px, 0.65fr);
  gap: 18px;
  padding: 20px 52px 30px;
  border-radius: 0 0 34px 34px;
  background: #ECEAE7;
  margin-bottom: 24px;
}

.cockpit-card {
  min-height: 210px;
  padding: 26px 28px;
  border-radius: 30px;
  background: #FFFFFF;
}

.stage-card {
  background:
    linear-gradient(135deg, rgba(139, 94, 60, 0.09), transparent 54%),
    #FFFFFF;

  h2 {
    margin: 34px 0 8px;
    color: #151515;
    font-size: 34px;
    font-weight: 850;
    line-height: 1;
  }

  p {
    margin: 0;
    color: #9B948C;
    font-size: 14px;
    font-weight: 700;
  }
}

.cockpit-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cockpit-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #F4F2EF;
  color: #121212;
  border: 1px solid rgba(18, 18, 18, 0.08);
}

.stage-chip {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  padding: 0 16px;
  border-radius: 17px;
  background: #F7F6F4;
  color: #4B4640;
  font-size: 12px;
  font-weight: 800;
}

.stage-actions { margin-top: 24px; }
.dark-pill {
  height: 42px;
  padding: 0 28px;
  border: 0;
  border-radius: 21px;
  background: #080808;
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.detail-dot-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 7px;
  margin: 30px 0 20px;

  span {
    aspect-ratio: 1;
    border-radius: 50%;
    background: #E5E0DA;
  }

  .done {
    background: #BA957C;
  }

  .active {
    background: #8B5E3C;
    box-shadow: 0 0 0 5px rgba(139, 94, 60, 0.12);
  }
}

.calendar-card p {
  margin: 0;
  color: #9B948C;
  font-size: 14px;
  font-weight: 750;
}

.review-meter-card,
.history-meter-card {
  display: flex;
  flex-direction: column;

  strong {
    margin-top: 30px;
    color: #151515;
    font-size: 36px;
    font-weight: 850;
    line-height: 1;
  }

  > span:not(.cockpit-icon) {
    margin-top: 8px;
    color: #89827A;
    font-size: 14px;
    font-weight: 750;
  }
}

.meter-track {
  height: 10px;
  margin-top: auto;
  border-radius: 10px;
  background: #E5E0DA;
  overflow: hidden;

  i {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: #8B5E3C;
  }
}

.history-bars {
  min-height: 74px;
  display: flex;
  align-items: flex-end;
  gap: 7px;
  margin-top: auto;

  i {
    width: 10px;
    border-radius: 10px;
    background: #DDD7D0;

    &:nth-child(4),
    &:nth-child(7) {
      background: #8B5E3C;
    }
  }
}

/* 改为单列布局，并将左侧参考信息移至下方 */
.detail-grid { display: flex; flex-direction: column; gap: 24px; }
.detail-left { order: 2; }
.detail-right { order: 1; }

.info-card {
  background: #fff; border-radius: 28px; padding: 26px;
  border: 1px solid #EFEDE9;
  box-shadow: 0 1px 0 rgba(42, 37, 31, 0.04);
}
.card-title { font-size: 18px; font-weight: 850; color: #1D1D1F; margin: 0 0 16px; display: flex; align-items: center; }

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
  background: #F4F1ED; border-radius: 18px; padding: 16px; margin-bottom: 12px;
  border-left: 3px solid #8B5E3C;
}
.plan-text { margin: 0; font-size: 14px; color: #1D1D1F; line-height: 1.7; white-space: pre-wrap; }
.plan-files { margin-top: 12px; }
.site-photos { display: block; }

.production-assets {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.asset-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.asset-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #4B4640;
  font-size: 13px;
  font-weight: 800;
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.asset-card {
  min-width: 0;
  min-height: 66px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid #ECE7E1;
  border-radius: 8px;
  background: #FBFAF8;
  color: #1D1D1F;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;

  &:hover {
    border-color: #D8C9BC;
    background: #F6F1EC;
    transform: translateY(-1px);
  }
}

.asset-thumb {
  width: 46px;
  height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #EFEAE4;
  color: #8B5E3C;
  overflow: hidden;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  &.is-pdf {
    background: #FFF0EC;
    color: #C14B32;
  }

  &.is-video {
    background: #EEF3FF;
    color: #315EAA;
  }
}

.asset-info {
  min-width: 0;

  strong,
  small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  strong {
    color: #24211F;
    font-size: 13px;
    font-weight: 800;
    line-height: 1.3;
  }

  small {
    margin-top: 4px;
    color: #8B837C;
    font-size: 12px;
  }
}

.asset-action {
  color: #8B5E3C;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

/* 时间线 */
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 0;
  border-left: 2px solid #E5E7EB; margin-left: 12px; padding-left: 20px;
  position: relative;
  &.active { border-left-color: #8B5E3C; }
  &.completed { border-left-color: #111111; }
}
.timeline-dot {
  position: absolute; left: -13px;
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
  background: #E5E7EB; color: #86868B;
  .timeline-item.active & { background: #8B5E3C; color: #fff; }
  .timeline-item.completed & { background: #111111; color: #fff; }
}
.stage-name { font-size: 14px; font-weight: 500; color: #1D1D1F; }
.stage-meta { font-size: 12px; color: #86868B; margin-top: 2px; }

/* 交付物历史 */
.deliverable-history { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #F0F0F0; }
.history-item {
  padding: 10px 12px; background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; margin-bottom: 8px;
  &.is-alt { background: #F6F7F9; border-color: #D9DDE4; }
}
.history-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.history-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex-wrap: wrap;
}
.history-stage-label {
  font-size: 12px;
  font-weight: 600;
  color: #A0522D;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(160, 82, 45, 0.1);
  max-width: 100%;
  overflow-wrap: anywhere;
}
.history-time { font-size: 12px; color: #86868B; }
.review-note { font-size: 13px; color: #E6A23C; margin: 6px 0 0; line-height: 1.5; }
.history-files { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.history-file-link {
  font-size: 13px;
  color: var(--uv-ws-action-button-bg, #A0522D);
  text-decoration: none;
  padding: 5px 9px;
  border-radius: 6px;
  background: rgba(160, 82, 45, 0.08);
  &:hover { text-decoration: underline; background: rgba(160, 82, 45, 0.14); }
}

/* 自审核 */
.self-review-section { margin-top: 20px; padding: 20px; background: #F7F2ED; border-radius: 24px; border: 1px solid #E1CFC0; }
.review-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
}
.review-title {
  font-size: 14px; font-weight: 800; color: #8B5E3C; margin: 0;
  display: flex; align-items: center; gap: 6px;
}
.review-progress {
  font-size: 13px; color: #6D4A32; font-weight: 750;
  padding: 2px 10px; border-radius: 10px; background: rgba(139,94,60,0.1);
  &.complete { color: #52C41A; background: rgba(82,196,26,0.1); }
}
.review-category { margin-bottom: 16px; &:last-child { margin-bottom: 0; } }
.category-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
  padding-bottom: 8px; border-bottom: 1px solid #E1CFC0;
}
.category-index {
  width: 22px; height: 22px; border-radius: 50%; background: #8B5E3C; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
  transition: background 0.3s;
  &.done { background: #52C41A; }
}
.category-title { font-size: 14px; font-weight: 750; color: #6D4A32; }
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
  background: #fff; border: 2px solid #8B5E3C; border-radius: 16px;
  animation: stepPulse 0.3s ease;
}
@keyframes stepPulse {
  0% { transform: scale(0.98); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
}
.step-active-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px 8px; border-bottom: 1px dashed #E1CFC0;
}
.step-number-active {
  font-size: 14px; font-weight: 800; color: #8B5E3C;
  background: #F7F2ED; padding: 2px 8px; border-radius: 10px;
}
.step-label { font-size: 12px; color: #6D4A32; }
.step-active-body { padding: 12px 16px 16px; }
.step-content-text {
  font-size: 15px; font-weight: 500; color: #1D1D1F; line-height: 1.6;
  padding: 12px; background: #F7F2ED; border-radius: 14px; margin-bottom: 14px;
  border-left: 3px solid #8B5E3C;
}
.step-confirm-row { display: flex; align-items: center; }
.confirm-checkbox {
  :deep(.el-checkbox__label) { font-size: 13px; color: #8B5E3C; font-weight: 650; }
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
  background: #F4F1ED;
  border-radius: 16px;
  border-left: 3px solid #8B5E3C;
}

.admin-comments-title {
  font-size: 13px;
  color: #8B5E3C;
  display: block;
  margin-bottom: 6px;
}

.admin-comment-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px dashed #E1CFC0;
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

:deep(.el-button--primary) {
  --el-button-bg-color: #111111;
  --el-button-border-color: #111111;
  --el-button-hover-bg-color: #8B5E3C;
  --el-button-hover-border-color: #8B5E3C;
}

@media (max-width: 1180px) {
  .detail-cockpit {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .detail-header,
  .detail-cockpit {
    padding-left: 20px;
    padding-right: 20px;
  }

  .detail-cockpit {
    grid-template-columns: 1fr;
  }

  .header-left {
    flex-direction: column;
  }
}
</style>
