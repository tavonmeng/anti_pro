<template>
  <div class="order-detail-page">
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
      </div>
      
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <div>
              <h2 class="order-number">{{ order.orderNumber }}</h2>
              <p class="order-type-text">{{ orderTypeText }}</p>
            </div>
            <OrderStatusBadge :status="userVisibleStatus" size="large" />
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="创建时间">{{ formatTime(order.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(order.updatedAt) }}</el-descriptions-item>
          <el-descriptions-item label="提交用户">{{ order.userName }}</el-descriptions-item>
          <el-descriptions-item label="负责人">
            <span v-if="order.assignees && order.assignees.length > 0">
              {{ order.assignees.map(a => a.name).join('、') }}
            </span>
            <span v-else>暂未分配</span>
          </el-descriptions-item>
          <el-descriptions-item label="修改次数">{{ order.revisionCount }}次</el-descriptions-item>
        </el-descriptions>
        
        <!-- 订单详细信息根据类型显示 -->
        <div class="order-specific-info">
          <h3>订单详情</h3>
          <div v-if="order.orderType === 'video_purchase'">
            <p><strong>行业类型：</strong>{{ getIndustryText() }}</p>
            <p><strong>视觉风格：</strong>{{ getStyleText() }}</p>
            <p><strong>时长：</strong>{{ order.duration }}秒</p>
            <p><strong>价格区间：</strong>¥{{ order.priceRange.min }} - ¥{{ order.priceRange.max }}</p>
            <p><strong>分辨率：</strong>{{ order.resolution }}</p>
            <p><strong>尺寸：</strong>{{ order.size }}</p>
            <p v-if="order.curvature"><strong>曲率：</strong>{{ order.curvature }}</p>
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
            </el-descriptions>
            
            <p><strong>项目背景：</strong></p>
            <p class="description-text">{{ order.background || '-' }}</p>
            <p><strong>内容需求：</strong></p>
            <p class="description-text">{{ order.content || '-' }}</p>
            <p><strong>品牌禁忌内容：</strong></p>
            <p class="description-text">{{ order.prohibited_content || '-' }}</p>
            <p v-if="order.scenePhotos && order.scenePhotos.length"><strong>现场实拍图：</strong>{{ order.scenePhotos.length }}张</p>
          </div>
          <div v-else-if="order.orderType === 'digital_art'">
            <p><strong>艺术方向：</strong>{{ getArtDirectionText() }}</p>
            <p><strong>说明文字：</strong></p>
            <p class="description-text">{{ order.description }}</p>
            <p v-if="order.materials.length"><strong>相关材料：</strong>{{ order.materials.length }}个文件</p>
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
                  <el-tag type="info" size="small">
                    {{ item.data.previewType === 'final' ? '终稿预览' : '初稿预览' }}
                  </el-tag>
                  <span class="timeline-user">{{ item.data.createdByName }}</span>
                </div>
                <div v-if="item.data.files && item.data.files.length > 0" class="preview-files">
                  <div v-for="file in item.data.files" :key="file.id" class="file-item">
                    <a :href="file.url" target="_blank" class="file-link">
                      <el-icon><VideoPlay /></el-icon>
                      <span>{{ file.name }}</span>
                      <span class="file-size">{{ formatFileSize(file.size) }}</span>
                    </a>
                  </div>
                </div>
                <div v-if="item.data.note" class="preview-note-content">
                  <p class="note-text">{{ item.data.note }}</p>
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
        
        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button
            v-if="order.status !== 'draft'"
            :icon="Download"
            :loading="downloadingPdf"
            @click="handleDownloadPdf"
          >
            下载需求告知函
          </el-button>
          <el-button
            v-if="order.status === 'draft'"
            type="primary"
            @click="handleEdit"
          >
            继续编辑
          </el-button>
          <el-button
            v-if="order.status === 'draft'"
            type="success"
            @click="handleSubmitDraft"
          >
            提交订单
          </el-button>
          <el-button
            v-if="order.status === 'preview_ready' || order.status === 'final_preview'"
            type="success"
            @click="handleApprove"
          >
            确认通过
          </el-button>
          <el-button
            v-if="order.status === 'preview_ready' || order.status === 'final_preview'"
            type="warning"
            @click="handleRevision"
          >
            需要修改
          </el-button>
        </div>
      </el-card>
    </div>
    
    <!-- 需求告知函确认弹窗 -->
    <OrderConfirmationDialog
      v-if="order && showConfirmation"
      v-model="showConfirmation"
      :order-number="order.orderNumber"
      :order-type="order.orderType"
      :form-data="order"
      @confirm="handleConfirmOrder"
      @cancel="showConfirmation = false"
    />
    
    <!-- 反馈对话框 -->
    <el-dialog v-model="feedbackDialogVisible" :title="feedbackType === 'approval' ? '确认通过' : '提交修改意见'" width="500px">
      <el-form :model="feedbackForm" label-width="80px">
        <el-form-item label="反馈内容">
          <el-input
            v-model="feedbackForm.content"
            type="textarea"
            :rows="6"
            :placeholder="feedbackType === 'approval' ? '请输入您的确认意见（可选）' : '请详细说明需要修改的内容'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feedbackDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitFeedback" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, VideoPlay, Download } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { orderApi } from '@/utils/api'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import OrderConfirmationDialog from '@/components/OrderConfirmationDialog.vue'
import { ElMessage } from 'element-plus'
import type { Order, VideoPurchaseOrder, DigitalArtOrder, TimelineItem, OrderStatus } from '@/types'

const router = useRouter()
const route = useRoute()
const orderStore = useOrderStore()

const order = ref<Order | null>(null)
const loading = ref(true)
const feedbackDialogVisible = ref(false)
const feedbackType = ref<'approval' | 'revision'>('approval')
const submitting = ref(false)
const showConfirmation = ref(false)
const downloadingPdf = ref(false)

const feedbackForm = ref({
  content: ''
})

const orderTypeMap: Record<string, string> = {
  video_purchase: '裸眼3D成片购买适配',
  ai_3d_custom: 'AI裸眼3D内容定制',
  digital_art: '数字艺术内容定制'
}

const orderTypeText = computed(() => {
  return order.value ? orderTypeMap[order.value.orderType] || order.value.orderType : ''
})

// 用户可见的状态：将 pending_review / review_rejected 映射为 in_production
const userVisibleStatus = computed<OrderStatus>(() => {
  if (!order.value) return 'in_production'
  const s = order.value.status as OrderStatus
  return (s === 'pending_review' || s === 'review_rejected') ? 'in_production' : s
})
// 合并预览历史和反馈记录，按时间排序
const timelineItems = computed<TimelineItem[]>(() => {
  if (!order.value) return []
  
  const items: TimelineItem[] = []
  
  // 添加预览历史记录
  if (order.value.previewHistory && order.value.previewHistory.length > 0) {
    order.value.previewHistory
      .filter(preview => preview.reviewStatus === 'approved')
      .forEach(preview => {
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

const handleApprove = () => {
  feedbackType.value = 'approval'
  feedbackForm.value.content = ''
  feedbackDialogVisible.value = true
}

const handleRevision = () => {
  feedbackType.value = 'revision'
  feedbackForm.value.content = ''
  feedbackDialogVisible.value = true
}

const submitFeedback = async () => {
  if (!order.value) return
  
  submitting.value = true
  try {
    await orderStore.submitFeedback(order.value.id, {
      content: feedbackForm.value.content || (feedbackType.value === 'approval' ? '确认通过' : '需要修改'),
      type: feedbackType.value
    })
    
    // 刷新订单详情
    order.value = await orderStore.getOrderDetail(order.value.id)
    feedbackDialogVisible.value = false
  } finally {
    submitting.value = false
  }
}

const handleEdit = () => {
  if (!order.value) return
  // 跳转到编辑订单页面
  router.push(`/user/edit-order/${order.value.id}`)
}

const handleSubmitDraft = async () => {
  if (!order.value) return
  showConfirmation.value = true
}

const handleConfirmOrder = async (confirmData: { email: string; phone: string }) => {
  if (!order.value) return
  
  try {
    const finalData = {
      ...order.value,
      confirmEmail: confirmData.email,
      confirmPhone: confirmData.phone
    }
    
    // 更新订单数据并通过草稿状态提交
    await orderStore.updateOrder(order.value.id, {
      orderType: order.value.orderType,
      ...finalData
    })
    
    await orderStore.updateOrderStatus(order.value.id, 'pending_assign')
    showConfirmation.value = false
    ElMessage.success('订单已成功提交')
    order.value = await orderStore.getOrderDetail(order.value.id)
  } catch (error) {
    console.error('提交草稿失败:', error)
  }
}

const handleDownloadPdf = async () => {
  if (!order.value) return
  downloadingPdf.value = true
  try {
    await orderApi.downloadConfirmationPdf(order.value.id)
    ElMessage.success('PDF 下载成功')
  } catch (error) {
    console.error('下载 PDF 失败:', error)
    ElMessage.error('下载 PDF 失败，请稍后重试')
  } finally {
    downloadingPdf.value = false
  }
}

const goBack = () => {
  router.push('/user/orders')
}
</script>

<style lang="scss" scoped>
.order-detail-page {
  padding: 24px;
}

.loading-state,
.empty-state {
  padding: 60px 0;
  text-align: center;
}

.page-header {
  margin-bottom: 24px;
}

.detail-card {
  border-radius: 12px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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
    
    .file-link {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #007AFF;
      text-decoration: none;
      flex: 1;
      
      &:hover {
        text-decoration: underline;
      }
    }
    
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

.action-buttons {
  margin-top: 32px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>

