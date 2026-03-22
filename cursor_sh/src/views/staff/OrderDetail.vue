<template>
  <div class="staff-order-detail-page">
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>
    
    <div v-else-if="!order" class="empty-state">
      <el-empty description="订单不存在或无权访问" />
      <el-button type="primary" @click="goBack">返回订单列表</el-button>
    </div>
    
    <div v-else class="order-detail-content">
      <div class="page-header">
        <el-button :icon="ArrowLeft" @click="goBack">返回订单列表</el-button>
        <div class="header-actions">
          <el-button 
            :icon="Upload" 
            type="primary"
            @click="handleUploadPreview"
            :disabled="order.status === 'pending_assign' || order.status === 'completed' || order.status === 'cancelled' || order.status === 'pending_review'"
          >
            上传预览文件
          </el-button>
        </div>
      </div>
      
      <el-card class="detail-card">
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
        
        <!-- 时间线（预览记录和反馈记录） -->
        <div v-if="timelineItems.length > 0" class="timeline-section">
          <h3>订单进度</h3>
          <el-timeline>
            <el-timeline-item
              v-for="item in timelineItems"
              :key="item.type === 'preview' ? `preview-${item.data.id}` : `feedback-${item.data.id}`"
              :timestamp="formatTime(item.data.createdAt)"
              placement="top"
            >
              <!-- 预览记录 -->
              <el-card v-if="item.type === 'preview'" class="timeline-card preview-card">
                <div class="timeline-header">
                  <div class="tag-group">
                  <el-tag type="info" size="small">
                    {{ item.data.previewType === 'final' ? '终稿预览' : '初稿预览' }}
                  </el-tag>
                    <el-tag :type="reviewTagType(item.data.reviewStatus)" size="small">
                      {{ reviewStatusText(item.data.reviewStatus) }}
                    </el-tag>
                  </div>
                  <span class="timeline-user">{{ item.data.createdByName }}</span>
                </div>
                <div v-if="item.data.files && item.data.files.length > 0" class="preview-files">
                  <div v-for="file in item.data.files" :key="file.id" class="file-item preview-file">
                    <el-icon><VideoPlay /></el-icon>
                    <span>{{ file.name }}</span>
                    <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  </div>
                </div>
                <div v-if="item.data.note" class="preview-note-content">
                  <p class="note-text">{{ item.data.note }}</p>
                </div>
                <div v-if="item.data.reviewStatus !== 'pending'" class="review-info">
                  <p>
                    审核结果：{{ reviewStatusText(item.data.reviewStatus) }}
                    <span v-if="item.data.reviewedAt">（{{ formatTime(item.data.reviewedAt) }}）</span>
                  </p>
                  <p v-if="item.data.reviewNote">审核备注：{{ item.data.reviewNote }}</p>
                </div>
                <div v-else class="review-pending-tip">
                  <el-icon :size="16" style="color: #FFB300;"><View /></el-icon>
                  <span>预览已提交，等待管理员审核</span>
                </div>
              </el-card>
              
              <!-- 反馈记录 -->
              <el-card v-else class="timeline-card feedback-card">
                <div class="timeline-header">
                  <el-tag :type="item.data.type === 'approval' ? 'success' : 'warning'" size="small">
                    {{ item.data.type === 'approval' ? '确认通过' : '需要修改' }}
                  </el-tag>
                  <span class="timeline-user">{{ item.data.createdByName }}</span>
                </div>
                <p class="feedback-content">{{ item.data.content }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
      </el-card>
    </div>
    
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
import { ArrowLeft, Upload, ArrowDown, Picture, Document as DocumentIcon, VideoPlay, View } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useOrderStore } from '@/stores/order'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import UploadPreviewDialog from '@/components/UploadPreviewDialog.vue'
import type { Order, OrderStatus, VideoPurchaseOrder, DigitalArtOrder, UploadedFile, TimelineItem } from '@/types'

const router = useRouter()
const route = useRoute()
const orderStore = useOrderStore()

const order = ref<Order | null>(null)
const loading = ref(true)
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

// 合并预览历史和反馈记录，按时间排序
const timelineItems = computed<TimelineItem[]>(() => {
  if (!order.value) return []
  
  const items: TimelineItem[] = []
  
  // 添加预览历史记录
  if (order.value.previewHistory && order.value.previewHistory.length > 0) {
    order.value.previewHistory.forEach(preview => {
      items.push({ type: 'preview', data: preview })
    })
  }
  
  // 添加反馈记录
  if (order.value.feedbacks && order.value.feedbacks.length > 0) {
    order.value.feedbacks.forEach(feedback => {
      items.push({ type: 'feedback', data: feedback })
    })
  }
  
  // 按时间排序（从早到晚）
  return items.sort((a, b) => {
    const timeA = new Date(a.data.createdAt).getTime()
    const timeB = new Date(b.data.createdAt).getTime()
    return timeA - timeB
  })
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
  // 解析时间字符串（支持带时区和不带时区的格式）
  const date = new Date(timeString)
  
  // 检查日期是否有效
  if (isNaN(date.getTime())) {
    return timeString
  }
  
  // 使用北京时间（UTC+8）格式化时间
  // 将 UTC 时间转换为北京时间显示
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

const handleUploadPreview = () => {
  uploadDialogVisible.value = true
}

const handleUploadConfirm = async (files: UploadedFile[], previewType: string, note: string) => {
  if (!order.value) return
  
  await orderStore.uploadPreview(order.value.id, files, previewType === 'final' ? 'final' : 'initial', note)
  order.value = await orderStore.getOrderDetail(order.value.id)
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

const goBack = () => {
  router.push('/staff/orders')
}
</script>

<style lang="scss" scoped>
.staff-order-detail-page {
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
.timeline-section {
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

.timeline-card {
  margin-bottom: 0;
  
  .timeline-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .tag-group {
      display: flex;
      gap: 8px;
    }
  }
  
  .timeline-user {
    font-size: 13px;
    color: #86868B;
  }
  
  .preview-files {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  
  .file-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #F5F5F7;
    border-radius: 8px;
    
    .file-size {
      color: #86868B;
      font-size: 12px;
    }
  }
  
  .preview-note-content {
    margin-top: 12px;
    padding: 12px;
    background: #F0F9FF;
    border-left: 3px solid #007AFF;
    border-radius: 4px;
    
    .note-text {
      margin: 0;
      white-space: pre-wrap;
      line-height: 1.6;
      color: #515154;
      font-size: 14px;
    }
  }

  .review-info {
    margin-top: 12px;
    font-size: 13px;
    color: #515154;

    p {
      margin: 4px 0;
    }
  }

  .review-pending-tip {
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #FF9800;
  }
  
  .feedback-content {
    margin: 0;
    font-size: 14px;
    color: #515154;
    line-height: 1.6;
  }
}

.preview-card {
  border-left: 3px solid #007AFF;
}

.feedback-card {
  border-left: 3px solid #E6A23C;
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

.preview-file {
  background: #E8F5E9;
  
  .el-icon {
    color: #4CAF50;
  }
}

.preview-note {
  margin-top: 16px;
  padding: 12px;
  background: #F0F9FF;
  border-left: 3px solid #007AFF;
  border-radius: 4px;
  
  h4 {
    font-size: 16px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 0 0 8px 0;
  }
  
  .note-content {
    margin: 0;
    white-space: pre-wrap;
    line-height: 1.6;
    color: #515154;
    font-size: 14px;
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


