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
            @click="showContractorAssignDialog = true"
            :disabled="order.status === 'completed' || order.status === 'cancelled'"
          >
            派单给承包商
          </el-button>
          <el-button 
            :icon="Upload" 
            type="primary"
            @click="handleUploadPreview"
            :disabled="order.status === 'pending_assign' || order.status === 'pending_contract' || order.status === 'completed' || order.status === 'cancelled' || order.status === 'pending_review'"
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
            <el-step title="需求确认" description="收到订单" />
            <el-step title="合同与付款" description="签订合同、收取首付款" />
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
                v-if="order.status !== 'completed' && order.status !== 'cancelled' && order.status !== 'pending_review' && order.status !== 'pending_contract'"
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
              <el-button 
                v-if="order.status === 'pending_contract'" 
                type="success" 
                @click="showContractDialog = true"
              >
                确认合同与付款
              </el-button>
              <el-button 
                v-if="order.status !== 'completed' && order.status !== 'cancelled'" 
                type="danger" 
                plain 
                @click="showCancelDialog = true"
              >
                取消订单
              </el-button>
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
        
        <!-- 承包商派单记录 -->
        <div v-if="contractorAssignments.length > 0" class="contractor-section">
          <h3>承包商派单记录</h3>
          <div v-for="assignment in contractorAssignments" :key="assignment.id" class="contractor-assignment-card">
            <div class="ca-header">
              <div>
                <strong>{{ assignment.contractorName }}</strong>
                <el-tag :type="caStatusType(assignment.status)" size="small" style="margin-left:8px">{{ caStatusLabel(assignment.status) }}</el-tag>
              </div>
              <div class="ca-actions">
                <el-button v-if="['accepted','in_progress'].includes(assignment.status)" size="small" type="primary" @click="handleAdvanceStage(assignment.id)">
                  推进到下一环节
                </el-button>
              </div>
            </div>
            <!-- 排期 -->
            <div class="ca-schedule" v-if="assignment.schedule">
              <div v-for="(stage, idx) in assignment.schedule" :key="idx" class="ca-stage"
                :class="{ active: stage.display_order === parseInt(assignment.currentStageOrder || '1'), completed: stage.status === 'completed' }">
                <span class="ca-stage-name">{{ stage.name }}</span>
                <span class="ca-stage-days">{{ stage.days }}天</span>
                <el-tag v-if="stage.status === 'completed'" type="success" size="small">完成</el-tag>
                <el-tag v-else-if="stage.status === 'active'" type="primary" size="small">当前</el-tag>
              </div>
            </div>
            <!-- 交付物 -->
            <div v-if="assignment.deliverables && assignment.deliverables.length > 0" class="ca-deliverables">
              <h4>交付物</h4>
              <div v-for="d in assignment.deliverables" :key="d.id" class="ca-deliverable-item">
                <div class="ca-dlv-header">
                  <span>{{ d.stageName }} V{{ d.version }}</span>
                  <el-tag :type="dlvStatusType(d.status)" size="small">{{ dlvStatusLabel(d.status) }}</el-tag>
                </div>
                <div v-if="d.files && d.files.length" class="ca-dlv-files">
                  <a v-for="f in d.files" :key="f.url" :href="f.url" target="_blank" class="ca-dlv-file">
                    {{ f.name || f.filename }}
                  </a>
                </div>
                <p v-if="d.description" class="ca-dlv-desc">{{ d.description }}</p>
                <!-- 审核操作 -->
                <div v-if="d.status === 'submitted'" class="ca-dlv-actions">
                  <el-button size="small" type="success" @click="handleReviewDlv(d.id, true)">审核通过</el-button>
                  <el-button size="small" type="danger" @click="handleReviewDlv(d.id, false)">驳回</el-button>
                </div>
                <!-- 推送操作 -->
                <div v-if="d.status === 'admin_approved' && !d.isPublishedToUser" class="ca-dlv-actions">
                  <el-button size="small" type="primary" @click="handlePublishDlv(d.id)">推送给用户</el-button>
                </div>
                <div v-if="d.adminReviewNote" class="ca-dlv-note">审核备注：{{ d.adminReviewNote }}</div>
              </div>
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
    
    <!-- 合同与付款确认对话框 -->
    <el-dialog v-model="showContractDialog" title="确认合同与付款" width="520px" destroy-on-close>
      <el-form :model="contractForm" label-width="100px" label-position="top">
        <el-form-item label="合同编号" required>
          <el-input v-model="contractForm.contractNumber" placeholder="请输入合同编号" />
        </el-form-item>
        <el-form-item label="首付款金额（元）" required>
          <el-input-number v-model="contractForm.paymentAmount" :min="0" :precision="2" :step="1000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="contractForm.note" type="textarea" :rows="3" placeholder="选填，如合同签订日期、付款方式等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showContractDialog = false">取消</el-button>
        <el-button type="success" @click="handleContractAdvance" :loading="contractLoading"
          :disabled="!contractForm.contractNumber || !contractForm.paymentAmount">
          确认并推进到制作阶段
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 管理员取消订单对话框（SMS验证） -->
    <el-dialog v-model="showCancelDialog" title="取消订单" width="480px" destroy-on-close>
      <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
        取消订单需要进行手机验证码确认，此操作不可撤回。
      </el-alert>
      <el-form :model="cancelForm" label-width="100px" label-position="top">
        <el-form-item label="手机号">
          <el-input v-model="cancelForm.phone" placeholder="管理员手机号">
            <template #append>
              <el-button 
                :disabled="smsCooldown > 0" 
                @click="sendCancelSms"
                :loading="smsLoading"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s 后重试` : '发送验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="验证码">
          <el-input v-model="cancelForm.smsCode" placeholder="请输入短信验证码" maxlength="6" />
        </el-form-item>
        <el-form-item label="取消原因">
          <el-input v-model="cancelForm.reason" type="textarea" :rows="3" placeholder="选填，取消原因将通知客户" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCancelDialog = false">返回</el-button>
        <el-button type="danger" @click="handleAdminCancel" :loading="cancelLoading"
          :disabled="!cancelForm.phone || !cancelForm.smsCode">
          确认取消订单
        </el-button>
      </template>
    </el-dialog>

    <!-- 派单给承包商对话框 -->
    <el-dialog v-model="showContractorAssignDialog" title="派单给承包商" width="480px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="选择承包商" required>
          <el-select v-model="contractorAssignForm.contractorId" placeholder="请选择" filterable style="width:100%">
            <el-option
              v-for="c in contractorOptions"
              :key="c.id"
              :label="`${c.username}${c.company ? ' (' + c.company + ')' : ''}`"
              :value="c.id"
              :disabled="!c.isActive"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showContractorAssignDialog = false">取消</el-button>
        <el-button type="primary" :loading="contractorAssigning" :disabled="!contractorAssignForm.contractorId" @click="handleContractorAssign">
          确认派单
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, User, Upload, ArrowDown, Picture, Document as DocumentIcon, VideoPlay, Download } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useOrderStore } from '@/stores/order'
import { orderApi, authApi, contractorAdminApi } from '@/utils/api'
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
const showContractDialog = ref(false)
const showCancelDialog = ref(false)
const contractLoading = ref(false)
const cancelLoading = ref(false)
const smsLoading = ref(false)
const smsCooldown = ref(0)

// 承包商相关状态
const showContractorAssignDialog = ref(false)
const contractorAssigning = ref(false)
const contractorOptions = ref<any[]>([])
const contractorAssignments = ref<any[]>([])
const contractorAssignForm = ref({ contractorId: '' })

const contractForm = ref({
  contractNumber: '',
  paymentAmount: 0,
  note: ''
})

const cancelForm = ref({
  phone: '',
  smsCode: '',
  reason: ''
})

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
    case 'pending_contract': return 1
    case 'in_production': return 2
    case 'pending_review': 
    case 'review_rejected':
    case 'preview_ready':
    case 'revision_needed':
      const isFinal = previewHistoryList.value.some(h => h.previewType === 'final')
      return isFinal ? 4 : 3
    case 'final_preview': return 4
    case 'completed': return 6
    case 'cancelled': return 0
    default: return 0
  }
})

onMounted(async () => {
  const orderId = route.params.id as string
  order.value = await orderStore.getOrderDetail(orderId)
  loading.value = false
  // 加载承包商列表和派单记录
  loadContractorData(orderId)
})

const loadContractorData = async (orderId: string) => {
  try {
    const [contractorsRes, assignmentsRes] = await Promise.all([
      contractorAdminApi.getContractors({ page: 1, pageSize: 100 }),
      contractorAdminApi.getAssignments({ order_id: orderId }),
    ])
    contractorOptions.value = contractorsRes?.data || []
    contractorAssignments.value = assignmentsRes?.data || []
  } catch {
    // 非阻断错误，承包商功能可能未启用
  }
}

const handleContractorAssign = async () => {
  if (!order.value || !contractorAssignForm.value.contractorId) return
  contractorAssigning.value = true
  try {
    await contractorAdminApi.assignOrder({
      order_id: order.value.id,
      contractor_id: contractorAssignForm.value.contractorId,
    })
    ElMessage.success('派单成功')
    showContractorAssignDialog.value = false
    contractorAssignForm.value.contractorId = ''
    loadContractorData(order.value.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '派单失败')
  } finally {
    contractorAssigning.value = false
  }
}

const handleAdvanceStage = async (assignmentId: string) => {
  try {
    await ElMessageBox.confirm('确认推进到下一工作流环节？', '确认推进', { type: 'warning' })
    const res = await contractorAdminApi.advanceStage(assignmentId)
    ElMessage.success(res?.message || '已推进')
    if (order.value) loadContractorData(order.value.id)
  } catch { /* cancelled */ }
}

const handleReviewDlv = async (deliverableId: string, approved: boolean) => {
  try {
    let note = ''
    if (!approved) {
      const result = await ElMessageBox.prompt('请输入驳回理由', '驳回交付物', { inputType: 'textarea' })
      note = result.value
    } else {
      await ElMessageBox.confirm('确认通过该交付物？', '审核确认')
    }
    await contractorAdminApi.reviewDeliverable(deliverableId, { approved, review_note: note })
    ElMessage.success(approved ? '已通过' : '已驳回')
    if (order.value) loadContractorData(order.value.id)
  } catch { /* cancelled */ }
}

const handlePublishDlv = async (deliverableId: string) => {
  try {
    await ElMessageBox.confirm('推送后用户将看到此交付物内容', '推送给用户')
    await contractorAdminApi.publishDeliverable(deliverableId)
    ElMessage.success('已推送给用户')
    if (order.value) loadContractorData(order.value.id)
  } catch { /* cancelled */ }
}

const caStatusLabel = (s: string) => ({
  pending: '待接单', accepted: '已接单', in_progress: '进行中',
  completed: '已完成', rejected: '已拒绝', cancelled: '已取消',
}[s] || s)

const caStatusType = (s: string) => ({
  pending: 'warning', in_progress: '', accepted: 'success',
  completed: 'success', rejected: 'danger', cancelled: 'info',
}[s] || 'info') as '' | 'success' | 'warning' | 'danger' | 'info'

const dlvStatusLabel = (s: string) => ({
  draft: '草稿', submitted: '待审核', admin_approved: '已通过', admin_rejected: '已驳回',
}[s] || s)

const dlvStatusType = (s: string) => ({
  draft: 'info', submitted: 'warning', admin_approved: 'success', admin_rejected: 'danger',
}[s] || 'info') as '' | 'success' | 'warning' | 'danger' | 'info'

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
    pending_contract: '合同与付款',
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

// 合同推进
const handleContractAdvance = async () => {
  if (!order.value) return
  contractLoading.value = true
  try {
    await orderApi.advanceContract(order.value.id, {
      contractNumber: contractForm.value.contractNumber,
      paymentAmount: contractForm.value.paymentAmount,
      note: contractForm.value.note
    })
    ElMessage.success('合同确认成功，订单已进入制作阶段')
    showContractDialog.value = false
    order.value = await orderStore.getOrderDetail(order.value.id)
  } catch (error: any) {
    ElMessage.error(error?.message || '操作失败')
  } finally {
    contractLoading.value = false
  }
}

// 发送取消验证码
const sendCancelSms = async () => {
  if (!cancelForm.value.phone) {
    ElMessage.warning('请先输入手机号')
    return
  }
  smsLoading.value = true
  try {
    await authApi.sendSms(cancelForm.value.phone)
    ElMessage.success('验证码已发送')
    smsCooldown.value = 60
    const timer = setInterval(() => {
      smsCooldown.value--
      if (smsCooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (error: any) {
    ElMessage.error(error?.message || '发送失败')
  } finally {
    smsLoading.value = false
  }
}

// 管理员取消订单
const handleAdminCancel = async () => {
  if (!order.value) return
  cancelLoading.value = true
  try {
    await orderApi.adminCancelOrder(order.value.id, {
      phone: cancelForm.value.phone,
      smsCode: cancelForm.value.smsCode,
      reason: cancelForm.value.reason
    })
    ElMessage.success('订单已取消')
    showCancelDialog.value = false
    order.value = await orderStore.getOrderDetail(order.value.id)
  } catch (error: any) {
    ElMessage.error(error?.message || '取消失败')
  } finally {
    cancelLoading.value = false
  }
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

/* 承包商派单区域 */
.contractor-section {
  margin-top: 32px;
  h3 { font-size: 18px; font-weight: 600; color: #1D1D1F; margin: 0 0 16px; }
}
.contractor-assignment-card {
  background: #F9FAFB; border-radius: 10px; padding: 16px; margin-bottom: 12px;
  border: 1px solid #E5E7EB;
}
.ca-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.ca-schedule { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.ca-stage {
  padding: 6px 12px; border-radius: 6px; background: #fff; border: 1px solid #E5E7EB;
  font-size: 13px; display: flex; align-items: center; gap: 6px;
  &.active { border-color: #409eff; background: #F0F9FF; }
  &.completed { border-color: #67C23A; background: #F6FFED; }
}
.ca-stage-name { font-weight: 500; }
.ca-stage-days { color: #86868B; }
.ca-deliverables { margin-top: 12px; h4 { font-size: 14px; font-weight: 500; margin: 0 0 8px; color: #515154; } }
.ca-deliverable-item {
  background: #fff; border-radius: 8px; padding: 12px; margin-bottom: 8px;
  border: 1px solid #E5E7EB;
}
.ca-dlv-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 500; }
.ca-dlv-files { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.ca-dlv-file { font-size: 13px; color: #409eff; text-decoration: none; &:hover { text-decoration: underline; } }
.ca-dlv-desc { font-size: 13px; color: #515154; margin: 0 0 8px; }
.ca-dlv-actions { display: flex; gap: 8px; }
.ca-dlv-note { font-size: 12px; color: #E6A23C; margin-top: 8px; }
</style>

