<template>
  <div class="admin-order-detail-page">
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>
    
    <div v-else-if="!order" class="empty-state">
      <el-empty description="订单不存在" />
      <el-button type="primary" @click="goBack">返回订单列表</el-button>
    </div>
    
    <div v-else class="order-detail-content">
      <div class="page-header">
        <el-button :icon="ArrowLeft" @click="goBack">返回订单列表</el-button>
        <div class="header-actions">
          <el-button 
            :icon="User" 
            @click="handleAssign"
            :disabled="order.status === 'completed' || order.status === 'cancelled'"
          >
            {{ (order.assignees && order.assignees.length > 0) ? '重新分配负责人' : '分配负责人' }}
          </el-button>
          <el-button 
            :icon="Upload" 
            type="primary"
            @click="handleUploadPreview"
            :disabled="order.status === 'pending_assign' || order.status === 'completed' || order.status === 'cancelled' || order.status === 'pending_review'"
          >
            上传预览文件
          </el-button>
          <el-dropdown trigger="click" @command="handlePdfDownload">
            <el-button :icon="Download">
              下载 PDF
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="confirmation">需求告知函</el-dropdown-item>
                <el-dropdown-item command="detail">订单详情报告</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      
      <el-card class="detail-card">
        <!-- 订单进度条 -->
        <div class="order-progress" style="margin-bottom: 30px; padding: 20px 10px; background: #fafafa; border-radius: 8px;">
          <el-steps :active="activeStep" :process-status="order.status === 'cancelled' ? 'error' : 'process'" finish-status="success" align-center>
            <el-step title="需求确认" description="收到订单，待分配" />
            <el-step title="内容制作" description="开发与设计环节" />
            <el-step title="初稿交付" description="内部审核与客户反馈" />
            <el-step title="终稿交付" description="内部审核与定稿" />
            <el-step title="项目完成" description="订单已结束" />
          </el-steps>
        </div>
        
        <template #header>
          <div class="card-header">
            <div>
              <h2 class="order-number">{{ order.orderNumber }}</h2>
              <p class="order-type-text">{{ orderTypeText }}</p>
            </div>
            <div class="header-right">
              <OrderStatusBadge :status="order.status" size="large" />
              <el-dropdown 
                @command="handleStatusChange" 
                v-if="order.status !== 'completed' && order.status !== 'cancelled' && order.status !== 'pending_review'"
              >
                <el-button>
                  更改状态
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="in_production" :disabled="order.status === 'in_production'">
                      制作中
                    </el-dropdown-item>
                    <el-dropdown-item command="preview_ready" :disabled="order.status === 'preview_ready'">
                      初稿预览
                    </el-dropdown-item>
                    <el-dropdown-item command="final_preview" :disabled="order.status === 'final_preview'">
                      终稿预览
                    </el-dropdown-item>
                    <el-dropdown-item command="completed">
                      已完成
                    </el-dropdown-item>
                    <el-dropdown-item command="cancelled" divided>
                      取消订单
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="创建时间">{{ formatTime(order.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(order.updatedAt) }}</el-descriptions-item>
          <el-descriptions-item label="提交用户">{{ order.userName }}</el-descriptions-item>
          <el-descriptions-item label="当前负责人">
            <div v-if="order.assignees && order.assignees.length > 0" class="assignees-list">
              <el-tag
                v-for="assignee in order.assignees"
                :key="assignee.id"
                size="small"
                class="assignee-tag"
              >
                {{ assignee.name }}
              </el-tag>
            </div>
            <el-tag v-else type="info" size="small">暂未分配</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="修改次数">
            <el-tag v-if="order.revisionCount > 0" type="warning">
              {{ order.revisionCount }}次
            </el-tag>
            <span v-else>0次</span>
          </el-descriptions-item>
          <el-descriptions-item label="反馈数量">{{ order.feedbacks.length }}条</el-descriptions-item>
        </el-descriptions>
        
        <!-- 订单详细信息 -->
        <div class="order-specific-info">
          <h3>订单详情</h3>
          <div v-if="order.orderType === 'video_purchase'">
            <el-row :gutter="20">
              <el-col :span="12"><p><strong>行业类型：</strong>{{ getIndustryText() }}</p></el-col>
              <el-col :span="12"><p><strong>视觉风格：</strong>{{ getStyleText() }}</p></el-col>
              <el-col :span="12"><p><strong>时长：</strong>{{ order.duration }}秒</p></el-col>
              <el-col :span="12"><p><strong>价格区间：</strong>¥{{ order.priceRange.min }} - ¥{{ order.priceRange.max }}</p></el-col>
              <el-col :span="12"><p><strong>分辨率：</strong>{{ order.resolution }}</p></el-col>
              <el-col :span="12"><p><strong>尺寸：</strong>{{ order.size }}</p></el-col>
              <el-col :span="12" v-if="order.curvature"><p><strong>曲率：</strong>{{ order.curvature }}</p></el-col>
            </el-row>
          </div>
          <div v-else-if="order.orderType === 'ai_3d_custom'">
            <el-descriptions :column="2" border size="small" style="margin-bottom: 20px;">
              <el-descriptions-item label="品牌与产品关键词">{{ order.brand || '-' }}</el-descriptions-item>
              <el-descriptions-item label="目标受众">{{ order.target_group || '-' }}</el-descriptions-item>
              <el-descriptions-item label="品牌调性">{{ order.brand_tone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="风格偏好">{{ order.style || '-' }}</el-descriptions-item>
              <el-descriptions-item label="投放城市/站点">{{ order.city || '-' }}</el-descriptions-item>
              <el-descriptions-item label="投放媒体尺寸">{{ order.media_size || '-' }}</el-descriptions-item>
              <el-descriptions-item label="投放时长数量">{{ order.time_number || '-' }}</el-descriptions-item>
              <el-descriptions-item label="技术需求">{{ order.technology || '-' }}</el-descriptions-item>
              <el-descriptions-item label="制作预算">{{ order.budget || '-' }}</el-descriptions-item>
              <el-descriptions-item label="预计上刊时间">{{ order.online_time || '-' }}</el-descriptions-item>
              <el-descriptions-item label="销售对接人">{{ order.sales_contact || '-' }}</el-descriptions-item>
            </el-descriptions>
            
            <p><strong>项目背景：</strong></p>
            <p class="description-text">{{ order.background || '-' }}</p>
            <p><strong>内容需求：</strong></p>
            <p class="description-text">{{ order.content || '-' }}</p>
            <p><strong>品牌禁忌内容：</strong></p>
            <p class="description-text">{{ order.prohibited_content || '-' }}</p>
            <div v-if="order.scenePhotos && order.scenePhotos.length > 0">
              <p><strong>现场实拍图（{{ order.scenePhotos.length }}张）：</strong></p>
              <div class="file-list">
                <div v-for="file in order.scenePhotos" :key="file.id" class="file-item">
                  <el-icon><Picture /></el-icon>
                  <span>{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="order.orderType === 'digital_art'">
            <p><strong>艺术方向：</strong>{{ getArtDirectionText() }}</p>
            <p><strong>说明文字：</strong></p>
            <p class="description-text">{{ order.description }}</p>
            <div v-if="order.materials.length > 0">
              <p><strong>相关材料（{{ order.materials.length }}个文件）：</strong></p>
              <div class="file-list">
                <div v-for="file in order.materials" :key="file.id" class="file-item">
                  <el-icon><Document /></el-icon>
                  <span>{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 预览审核记录 -->
        <div v-if="previewHistoryList.length" class="preview-history-section">
          <h3>预览审核记录</h3>
          <el-timeline>
            <el-timeline-item
              v-for="history in previewHistoryList"
              :key="history.id"
              :timestamp="formatTime(history.createdAt)"
              placement="top"
            >
              <el-card>
                <div class="preview-history-header">
                  <div class="preview-history-tags">
                    <el-tag type="info" size="small">
                      {{ history.previewType === 'final' ? '终稿预览' : '初稿预览' }}
                    </el-tag>
                    <el-tag :type="reviewTagType(history.reviewStatus)" size="small">
                      {{ reviewStatusText(history.reviewStatus) }}
                    </el-tag>
                  </div>
                  <span class="preview-history-user">{{ history.createdByName }}</span>
                </div>
                <div class="preview-files">
                  <div v-for="file in history.files" :key="file.id" class="file-item">
                    <a :href="file.url" target="_blank" class="file-link">
                      <el-icon><VideoPlay /></el-icon>
                      <span>{{ file.name }}</span>
                      <span class="file-size">{{ formatFileSize(file.size) }}</span>
                    </a>
                  </div>
                </div>
                <div v-if="history.note" class="preview-note-content">
                  <p class="note-text">{{ history.note }}</p>
                </div>
                <div v-if="history.reviewStatus !== 'pending'" class="review-info">
                  <p>
                    审核人：{{ history.reviewedByName || '管理员' }}
                    <span v-if="history.reviewedAt">（{{ formatTime(history.reviewedAt) }}）</span>
                  </p>
                  <p v-if="history.reviewNote">审核备注：{{ history.reviewNote }}</p>
                </div>
                <div v-else class="review-actions">
                  <el-button-group>
                    <el-button size="small" type="success" @click="handleReviewAction(history.id, 'approve')">
                      审核通过
                    </el-button>
                    <el-button size="small" type="danger" @click="handleReviewAction(history.id, 'reject')">
                      审核拒绝
                    </el-button>
                  </el-button-group>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
        
        <!-- 预览文件 -->
        <div v-if="hasPreviewFiles" class="preview-section">
          <h3>预览文件</h3>
          <div class="file-list">
            <div v-for="file in order.previewFiles" :key="file.id" class="file-item preview-file">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <span class="file-time">{{ formatTime(file.uploadTime) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 反馈记录 -->
        <div v-if="order.feedbacks.length > 0" class="feedback-section">
          <h3>客户反馈记录</h3>
          <el-timeline>
            <el-timeline-item
              v-for="feedback in order.feedbacks"
              :key="feedback.id"
              :timestamp="formatTime(feedback.createdAt)"
              placement="top"
            >
              <el-card>
                <div class="feedback-header">
                  <el-tag :type="feedback.type === 'approval' ? 'success' : 'warning'">
                    {{ feedback.type === 'approval' ? '确认通过' : '需要修改' }}
                  </el-tag>
                  <span class="feedback-user">{{ feedback.createdByName }}</span>
                </div>
                <p class="feedback-content">{{ feedback.content }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
      </el-card>
    </div>
    
    <!-- 分配负责人对话框 -->
    <AssigneeDialog
      v-model="assignDialogVisible"
      :current-assignee-id="order?.assignees?.[0]?.id"
      @confirm="handleAssignConfirm"
    />
    
    <!-- 上传预览对话框 -->
    <UploadPreviewDialog
      v-model="uploadDialogVisible"
      :order="order"
      @confirm="handleUploadConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, User, Upload, ArrowDown, Picture, Document as DocumentIcon, VideoPlay, Download } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useOrderStore } from '@/stores/order'
import { orderApi } from '@/utils/api'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import AssigneeDialog from '@/components/AssigneeDialog.vue'
import UploadPreviewDialog from '@/components/UploadPreviewDialog.vue'
import type { Order, OrderStatus, VideoPurchaseOrder, DigitalArtOrder, UploadedFile } from '@/types'

const router = useRouter()
const route = useRoute()
const orderStore = useOrderStore()

const order = ref<Order | null>(null)
const loading = ref(true)
const assignDialogVisible = ref(false)
const uploadDialogVisible = ref(false)

const orderTypeMap: Record<string, string> = {
  video_purchase: '裸眼3D成片购买适配',
  ai_3d_custom: 'AI裸眼3D内容定制',
  digital_art: '数字艺术内容定制'
}

const orderTypeText = computed(() => {
  return order.value ? orderTypeMap[order.value.orderType] || order.value.orderType : ''
})

const hasPreviewFiles = computed(() => {
  if (!order.value) return false
  if (order.value.orderType === 'ai_3d_custom' || order.value.orderType === 'digital_art') {
    return order.value.previewFiles && order.value.previewFiles.length > 0
  }
  return false
})

const previewHistoryList = computed(() => {
  if (!order.value?.previewHistory) return []
  return [...order.value.previewHistory].sort((a, b) => {
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })
})

const activeStep = computed(() => {
  if (!order.value) return 0
  const status = order.value.status
  switch(status) {
    case 'draft': return 0
    case 'pending_assign': return 0
    case 'in_production': return 1
    case 'pending_review': 
    case 'review_rejected':
    case 'preview_ready':
    case 'revision_needed':
      const isFinal = previewHistoryList.value.some(h => h.previewType === 'final')
      return isFinal ? 3 : 2
    case 'final_preview': return 3
    case 'completed': return 5
    case 'cancelled': return 0
    default: return 0
  }
})

onMounted(async () => {
  const orderId = route.params.id as string
  order.value = await orderStore.getOrderDetail(orderId)
  loading.value = false
})

const getIndustryText = () => {
  if (order.value && order.value.orderType === 'video_purchase') {
    const vOrder = order.value as VideoPurchaseOrder
    if (vOrder.industryType === 'custom') {
      return vOrder.customIndustry || '自定义'
    }
    const map: Record<string, string> = {
      movie: '电影',
      outdoor: '户外'
    }
    return map[vOrder.industryType] || vOrder.industryType
  }
  return '-'
}

const getStyleText = () => {
  if (order.value && order.value.orderType === 'video_purchase') {
    const vOrder = order.value as VideoPurchaseOrder
    if (vOrder.visualStyle === 'custom') {
      return vOrder.customStyle || '自定义'
    }
    const map: Record<string, string> = {
      scifi: '科幻',
      realistic: '写真'
    }
    return map[vOrder.visualStyle] || vOrder.visualStyle
  }
  return '-'
}

const getArtDirectionText = () => {
  if (order.value && order.value.orderType === 'digital_art') {
    const dOrder = order.value as DigitalArtOrder
    if (dOrder.artDirection === 'custom') {
      return dOrder.customDirection || '自定义'
    }
    const map: Record<string, string> = {
      abstract: '抽象',
      realistic: '写实',
      installation: '装置',
      dynamic: '动态艺术'
    }
    return map[dOrder.artDirection] || dOrder.artDirection
  }
  return '-'
}

const formatTime = (timeString: string) => {
  if (!timeString) return '-'
  const date = new Date(timeString)
  if (isNaN(date.getTime())) {
    return timeString
  }
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const handleAssign = () => {
  assignDialogVisible.value = true
}

const handleAssignConfirm = async (assignees: Array<{ id: string, name: string }>) => {
  if (!order.value) return
  
  if (assignees.length > 0) {
    await orderStore.assignOrder(order.value.id, assignees)
    order.value = await orderStore.getOrderDetail(order.value.id)
  }
}

const handleUploadPreview = () => {
  uploadDialogVisible.value = true
}

const handleUploadConfirm = async (files: UploadedFile[], previewType: string, note: string) => {
  if (!order.value) return
  
  await orderStore.uploadPreview(order.value.id, files, previewType === 'final' ? 'final' : 'initial', note)
  order.value = await orderStore.getOrderDetail(order.value.id)
}

const handleReviewAction = async (previewId: string, action: 'approve' | 'reject') => {
  if (!order.value) return
  
  try {
    if (action === 'reject') {
      const { value } = await ElMessageBox.prompt(
        '请输入拒绝原因（可选）',
        '审核拒绝',
        {
          confirmButtonText: '确认拒绝',
          cancelButtonText: '取消',
          inputType: 'textarea',
          inputPlaceholder: '请填写审核拒绝原因',
          inputValidator: (val: string) => val.length <= 500 || '拒绝原因长度不能超过500个字符'
        }
      )
      await orderStore.reviewPreview(order.value.id, { previewId, action, note: value })
    } else {
      await ElMessageBox.confirm(
        '确认通过该预览审核？',
        '确认审核',
        { type: 'success' }
      )
      await orderStore.reviewPreview(order.value.id, { previewId, action })
    }
  order.value = await orderStore.getOrderDetail(order.value.id)
  } catch {
    // 用户取消或审核失败
  }
}

const handleStatusChange = async (status: OrderStatus) => {
  if (!order.value) return
  
  try {
    await ElMessageBox.confirm(
      `确定要将订单状态更改为"${getStatusText(status)}"吗？`,
      '确认更改',
      {
        type: 'warning'
      }
    )
    
    await orderStore.updateOrderStatus(order.value.id, status)
    order.value = await orderStore.getOrderDetail(order.value.id)
  } catch {
    // 用户取消
  }
}

const getStatusText = (status: OrderStatus): string => {
  const map: Record<OrderStatus, string> = {
    pending_assign: '待分配',
    in_production: '制作中',
    pending_review: '待审核',
    preview_ready: '初稿预览',
    review_rejected: '审核拒绝',
    revision_needed: '需要修改',
    final_preview: '终稿预览',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status
}

const reviewStatusText = (status: 'pending' | 'approved' | 'rejected') => {
  const map: Record<typeof status, string> = {
    pending: '待审核',
    approved: '审核通过',
    rejected: '审核拒绝'
  }
  return map[status]
}

const reviewTagType = (status: 'pending' | 'approved' | 'rejected') => {
  const map: Record<typeof status, 'warning' | 'success' | 'danger'> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  }
  return map[status]
}

const handlePdfDownload = async (type: string) => {
  if (!order.value) return
  try {
    if (type === 'confirmation') {
      await orderApi.downloadConfirmationPdf(order.value.id)
    } else {
      await orderApi.downloadDetailPdf(order.value.id)
    }
    ElMessage.success('PDF 下载成功')
  } catch (error) {
    console.error('下载 PDF 失败:', error)
    ElMessage.error('下载 PDF 失败')
  }
}

const goBack = () => {
  router.push('/admin')
}
</script>

<style lang="scss" scoped>
.admin-order-detail-page {
  padding: 24px;
}

.loading-state,
.empty-state {
  padding: 60px 0;
  text-align: center;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.detail-card {
  border-radius: 12px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  .order-number {
    font-size: 24px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 0 0 4px 0;
  }
  
  .order-type-text {
    font-size: 14px;
    color: #86868B;
    margin: 0;
  }
}

.order-specific-info,
.preview-section,
.preview-history-section,
.feedback-section {
  margin-top: 32px;
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 0 0 16px 0;
  }
  
  p {
    margin: 8px 0;
    font-size: 14px;
    color: #515154;
    
    strong {
      color: #1D1D1F;
      font-weight: 500;
    }
  }
  
  .description-text {
    white-space: pre-wrap;
    line-height: 1.6;
    padding: 12px;
    background: #F5F5F7;
    border-radius: 8px;
  }
}

.preview-history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-history-tags {
  display: flex;
  gap: 8px;
}

.preview-history-user {
  font-size: 13px;
  color: #86868B;
}

.preview-note-content {
  margin-top: 12px;
  padding: 12px;
  background: #FFFBE6;
  border-radius: 8px;
  color: #8B7416;
  line-height: 1.6;
}

.review-info {
  margin-top: 12px;
  font-size: 13px;
  color: #515154;
  
  p {
    margin: 4px 0;
  }
}

.review-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #F5F5F7;
  border-radius: 8px;
  font-size: 14px;
  
  .el-icon {
    font-size: 20px;
    color: #667eea;
  }
  
  span:first-of-type {
    flex: 1;
    color: #1D1D1F;
  }
  
  .file-size,
  .file-time {
    color: #86868B;
    font-size: 13px;
  }
}

.file-link {
  display: flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
  flex: 1;
}

.preview-file {
  background: #E8F5E9;
  
  .el-icon {
    color: #4CAF50;
  }
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.feedback-user {
  font-size: 13px;
  color: #86868B;
}

.feedback-content {
  margin: 0;
  font-size: 14px;
  color: #515154;
  line-height: 1.6;
}

.assignees-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.assignee-tag {
  margin: 0;
}
</style>

