<template>
  <div class="staff-order-list-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的订单</h1>
        <p class="page-subtitle">查看和管理分配给您的订单</p>
      </div>
      <el-button :icon="Refresh" @click="refreshData">刷新数据</el-button>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #E3F2FD;">
            <el-icon :size="24" color="#2196F3"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ orderStore.orderStats.total }}</div>
            <div class="stat-label">总订单数</div>
          </div>
        </div>
      </el-card>
      
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #F3E5F5;">
            <el-icon :size="24" color="#9C27B0"><Loading /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ orderStore.orderStats.inProduction }}</div>
            <div class="stat-label">制作中</div>
          </div>
        </div>
      </el-card>
      
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #FFF3E0;">
            <el-icon :size="24" color="#FF9800"><View /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ orderStore.orderStats.pendingReview }}</div>
            <div class="stat-label">待审核</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #FFF8E1;">
            <el-icon :size="24" color="#FFB300"><View /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ orderStore.orderStats.preview }}</div>
            <div class="stat-label">待预览</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #FFEBEE;">
            <el-icon :size="24" color="#E53935"><CircleClose /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ orderStore.orderStats.reviewRejected }}</div>
            <div class="stat-label">审核拒绝</div>
          </div>
        </div>
      </el-card>
      
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #E8F5E9;">
            <el-icon :size="24" color="#4CAF50"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ orderStore.orderStats.completed }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 筛选器 -->
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="订单类型">
          <el-select v-model="filters.orderType" placeholder="全部类型" clearable style="width: 180px" @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="裸眼3D成片购买" value="video_purchase" />
            <el-option label="AI裸眼3D定制" value="ai_3d_custom" />
            <el-option label="数字艺术定制" value="digital_art" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="订单状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 180px" @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="制作中" value="in_production" />
            <el-option label="待审核" value="pending_review" />
            <el-option label="初稿预览" value="preview_ready" />
            <el-option label="审核拒绝" value="review_rejected" />
            <el-option label="需要修改" value="revision_needed" />
            <el-option label="终稿预览" value="final_preview" />
            <el-option label="已完成" value="completed" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 订单表格 -->
    <el-card class="table-card">
      <el-table
        :data="filteredOrders"
        :loading="orderStore.loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="orderNumber" label="项目编号" width="180" fixed />
        <el-table-column prop="orderType" label="项目分类" width="150">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ getOrderTypeText(row.orderType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="当前状态" width="120">
          <template #default="{ row }">
            <OrderStatusBadge :status="row.status" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="userName" label="客户" width="120" />
        <el-table-column prop="revisionCount" label="修改次数" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.revisionCount > 0" type="warning" size="small">
              {{ row.revisionCount }}次
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column prop="feedbacks" label="客户反馈" width="100" align="center">
          <template #default="{ row }">
            <el-badge :value="row.feedbacks.length" :hidden="row.feedbacks.length === 0">
              <el-icon :size="18"><ChatLineSquare /></el-icon>
            </el-badge>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                size="small" 
                type="primary"
                @click="handleUploadPreview(row)"
                :disabled="row.status === 'pending_assign' || row.status === 'completed' || row.status === 'cancelled' || row.status === 'pending_review'"
              >
                上传预览
              </el-button>
              <el-button size="small" @click="viewDetail(row)">
                详情
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 上传预览对话框 -->
    <UploadPreviewDialog
      v-model="uploadDialogVisible"
      :order="currentOrder"
      @confirm="handleUploadConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Document, Loading, View, CircleCheck, CircleClose, ChatLineSquare } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import UploadPreviewDialog from '@/components/UploadPreviewDialog.vue'
import type { Order, OrderType, OrderStatus, UploadedFile } from '@/types'

const router = useRouter()
const orderStore = useOrderStore()

const filters = ref({
  orderType: '' as OrderType | '',
  status: '' as OrderStatus | ''
})

const uploadDialogVisible = ref(false)
const currentOrder = ref<Order | null>(null)

const filteredOrders = computed(() => {
  let result = orderStore.orders
  
  if (filters.value.orderType) {
    result = result.filter(o => o.orderType === filters.value.orderType)
  }
  
  if (filters.value.status) {
    result = result.filter(o => o.status === filters.value.status)
  }
  
  return result
})

onMounted(() => {
  refreshData()
})

const refreshData = () => {
  orderStore.fetchOrders()
}

const handleFilter = () => {
  // 筛选已经通过computed自动完成
}

const orderTypeMap: Record<OrderType, string> = {
  video_purchase: '裸眼3D成片购买',
  ai_3d_custom: 'AI裸眼3D定制',
  digital_art: '数字艺术定制'
}

const getOrderTypeText = (type: OrderType) => {
  return orderTypeMap[type] || type
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

const handleUploadPreview = (order: Order) => {
  currentOrder.value = order
  uploadDialogVisible.value = true
}

const handleUploadConfirm = async (files: UploadedFile[], previewType: string, note: string) => {
  if (!currentOrder.value) return
  
  await orderStore.uploadPreview(currentOrder.value.id, files, previewType === 'final' ? 'final' : 'initial', note)
  await refreshData()
}

const viewDetail = (order: Order) => {
  router.push(`/staff/orders/${order.id}`)
}
</script>

<style lang="scss" scoped>
.staff-order-list-page {
  padding: 32px;
  background-color: #f8f9fc;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  background: linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%);
  padding: 24px 32px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.8);

  h1.page-title {
    font-size: 32px;
    font-weight: 700;
    background: linear-gradient(90deg, #1d1d1f, #434343);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
  }

  p.page-subtitle {
    font-size: 15px;
    color: #86868b;
    margin: 0;
    font-weight: 500;
  }
}

/* 统计卡片高级样式 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  border-radius: 16px;
  border: none;
  background: #ffffff;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.02);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  overflow: hidden;
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(to bottom, transparent, transparent);
    transition: all 0.3s ease;
  }
  
  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
  }

  /* Different hover borders for each card type if desired */
  &:nth-child(1):hover::before { background: #2196F3; }
  &:nth-child(2):hover::before { background: #9C27B0; }
  &:nth-child(3):hover::before { background: #FF9800; }
  &:nth-child(4):hover::before { background: #FFB300; }
  &:nth-child(5):hover::before { background: #E53935; }
  &:nth-child(6):hover::before { background: #4CAF50; }
  
  :deep(.el-card__body) {
    padding: 24px;
  }
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s ease;
}

.stat-card:hover .stat-icon {
  transform: scale(1.1);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
  margin-bottom: 4px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  letter-spacing: -0.5px;
}

.stat-label {
  font-size: 14px;
  color: #86868b;
  font-weight: 500;
}

.filter-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
  margin-bottom: 24px;
  background: white;

  :deep(.el-card__body) {
    padding: 24px;
    padding-bottom: 4px; /* Form items have bottom margin */
  }

  .el-form-item {
    margin-bottom: 20px;
  }
}

.table-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
  overflow: hidden;

  /* Customizing Element Plus Table */
  :deep(.el-table) {
    border-radius: 12px;
    overflow: hidden;
    --el-table-border-color: #f0f0f0;
    --el-table-header-bg-color: #fafafa;
    
    th.el-table__cell {
      background-color: #fcfcfd;
      font-weight: 600;
      color: #1d1d1f;
      height: 56px;
    }
    
    td.el-table__cell {
      padding: 16px 0;
    }
    
    .el-table__row {
      transition: background-color 0.2s ease;
      &:hover > td.el-table__cell {
        background-color: #f5f7fa;
      }
    }
  }
}

/* Premium Buttons */
:deep(.el-button) {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s;
  
  &:active {
    transform: scale(0.96);
  }
}

:deep(.filter-card .el-select .el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #e4e4e7 inset;
}

:deep(.el-tag) {
  border-radius: 6px;
  padding: 0 10px;
  font-weight: 600;
}
</style>


