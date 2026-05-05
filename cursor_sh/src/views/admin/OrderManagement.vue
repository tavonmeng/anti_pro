<template>
  <div class="order-management-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">订单管理</h1>
        <p class="page-subtitle">管理所有用户的订单和工作流程</p>
      </div>
      <el-button :icon="Refresh" @click="refreshData">刷新数据</el-button>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card" v-for="stat in statItems" :key="stat.label"
        :class="{ active: filters.status === stat.filterValue }"
        @click="toggleStatusFilter(stat.filterValue)"
      >
        <div class="stat-icon" :style="{ background: stat.iconBg }">
          <el-icon :size="22" :color="stat.iconColor"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
    </div>
    
    <!-- 筛选器 -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索订单编号、客户名称..."
        :prefix-icon="Search"
        clearable
        class="search-input"
      />
      <el-select v-model="filters.orderType" placeholder="全部类型" clearable class="filter-select">
        <el-option label="全部类型" value="" />
        <el-option label="裸眼3D成片购买" value="video_purchase" />
        <el-option label="AI裸眼3D定制" value="ai_3d_custom" />
        <el-option label="数字艺术定制" value="digital_art" />
      </el-select>
      <el-select v-model="filters.assigneeId" placeholder="全部负责人" clearable class="filter-select">
        <el-option label="全部负责人" value="" />
        <el-option label="未分配" value="unassigned" />
        <el-option
          v-for="staff in staffStore.staffList"
          :key="staff.id"
          :label="staff.realName || staff.username"
          :value="staff.id"
        />
      </el-select>
    </div>
    
    <!-- 订单列表 -->
    <div class="order-list" v-loading="orderStore.loading">
      <div v-if="filteredOrders.length === 0 && !orderStore.loading" class="empty-state">
        <el-icon :size="48" color="#C0C4CC"><Document /></el-icon>
        <p>暂无订单</p>
      </div>
      
      <div
        v-for="order in filteredOrders"
        :key="order.id"
        class="order-card"
        @click="viewDetail(order)"
      >
        <!-- 左侧状态条 -->
        <div class="order-status-bar" :class="getStatusColorClass(order.status)"></div>
        
        <div class="order-card-body">
          <!-- 第一行：编号 + 类型 + 状态 -->
          <div class="order-card-header">
            <div class="order-main-info">
              <span class="order-number">{{ order.orderNumber }}</span>
              <el-tag size="small" type="info" effect="plain" class="type-tag">{{ getOrderTypeText(order.orderType) }}</el-tag>
            </div>
            <div class="order-status-area">
              <OrderStatusBadge :status="order.status" size="default" />
              <el-icon class="chevron-icon"><ArrowRight /></el-icon>
            </div>
          </div>
          
          <!-- 第二行：核心信息 -->
          <div class="order-card-meta">
            <div class="meta-item">
              <el-icon :size="14"><User /></el-icon>
              <span>{{ order.userName || '未知客户' }}</span>
            </div>
            <div class="meta-item">
              <el-icon :size="14"><Calendar /></el-icon>
              <span>{{ formatTime(order.createdAt) }}</span>
            </div>
            <div class="meta-item" v-if="order.assignees && order.assignees.length > 0">
              <el-icon :size="14"><UserFilled /></el-icon>
              <span>{{ order.assignees.map((a: any) => a.name).join('、') }}</span>
            </div>
            <div class="meta-item unassigned" v-else>
              <el-icon :size="14"><UserFilled /></el-icon>
              <span>未分配负责人</span>
            </div>
            <div class="meta-item" v-if="order.revisionCount > 0">
              <el-icon :size="14"><EditPen /></el-icon>
              <span>修改 {{ order.revisionCount }} 次</span>
            </div>
            <div class="meta-item" v-if="order.feedbacks && order.feedbacks.length > 0">
              <el-icon :size="14"><ChatLineSquare /></el-icon>
              <span>{{ order.feedbacks.length }} 条反馈</span>
            </div>
          </div>

          <!-- 第三行：品牌/内容摘要 (如有) -->
          <div class="order-card-summary" v-if="getOrderSummary(order)">
            {{ getOrderSummary(order) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Refresh, Document, Clock, Loading, CircleCheck, CircleClose, View, 
  ChatLineSquare, Search, User, Calendar, UserFilled, ArrowRight, EditPen 
} from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { useStaffStore } from '@/stores/staff'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import type { Order, OrderType, OrderStatus } from '@/types'

const router = useRouter()
const orderStore = useOrderStore()
const staffStore = useStaffStore()

const searchKeyword = ref('')
const filters = ref({
  orderType: '' as OrderType | '',
  status: '' as OrderStatus | '',
  assigneeId: ''
})

// 统计卡片数据
const statItems = computed(() => [
  { label: '全部订单', value: orderStore.orderStats.total, icon: Document, iconBg: '#EEF2FF', iconColor: '#6366F1', filterValue: '' },
  { label: '合同与付款', value: orderStore.orderStats.pendingContract, icon: Clock, iconBg: '#FFF7ED', iconColor: '#F59E0B', filterValue: 'pending_contract' },
  { label: '制作中', value: orderStore.orderStats.inProduction, icon: Loading, iconBg: '#F3E8FF', iconColor: '#8B5CF6', filterValue: 'in_production' },
  { label: '待审核', value: orderStore.orderStats.pendingReview, icon: View, iconBg: '#FEF9C3', iconColor: '#CA8A04', filterValue: 'pending_review' },
  { label: '审核拒绝', value: orderStore.orderStats.reviewRejected, icon: CircleClose, iconBg: '#FEE2E2', iconColor: '#EF4444', filterValue: 'review_rejected' },
  { label: '已完成', value: orderStore.orderStats.completed, icon: CircleCheck, iconBg: '#DCFCE7', iconColor: '#22C55E', filterValue: 'completed' },
])

const toggleStatusFilter = (val: string) => {
  filters.value.status = (filters.value.status === val ? '' : val) as OrderStatus | ''
}

const filteredOrders = computed(() => {
  let result = orderStore.orders
  
  if (filters.value.orderType) {
    result = result.filter(o => o.orderType === filters.value.orderType)
  }
  if (filters.value.status) {
    result = result.filter(o => o.status === filters.value.status)
  }
  if (filters.value.assigneeId) {
    if (filters.value.assigneeId === 'unassigned') {
      result = result.filter(o => !o.assignees || o.assignees.length === 0)
    } else {
      result = result.filter(o => 
        o.assignees && o.assignees.some((a: { id: string }) => a.id === filters.value.assigneeId)
      )
    }
  }
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    result = result.filter(o => 
      (o.orderNumber && o.orderNumber.toLowerCase().includes(kw)) ||
      (o.userName && o.userName.toLowerCase().includes(kw))
    )
  }
  return result
})

onMounted(() => {
  refreshData()
})

const refreshData = () => {
  orderStore.fetchOrders()
  staffStore.fetchStaff()
}

const orderTypeMap: Record<OrderType, string> = {
  video_purchase: '裸眼3D成片购买',
  ai_3d_custom: 'AI裸眼3D定制',
  digital_art: '数字艺术定制'
}

const getOrderTypeText = (type: OrderType) => orderTypeMap[type] || type

const formatTime = (timeString: string) => {
  if (!timeString) return '-'
  const date = new Date(timeString)
  if (isNaN(date.getTime())) return timeString
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false
  })
}

const getStatusColorClass = (status: string) => {
  const map: Record<string, string> = {
    pending_review: 'status-warning',
    pending_contract: 'status-orange',
    pending_assign: 'status-info',
    in_production: 'status-purple',
    preview_ready: 'status-blue',
    review_rejected: 'status-danger',
    revision_needed: 'status-danger',
    final_preview: 'status-blue',
    completed: 'status-success',
    cancelled: 'status-muted',
  }
  return map[status] || 'status-info'
}

const getOrderSummary = (order: Order) => {
  const data = (order as any).orderData || {}
  const parts = [data.brand, data.content, data.city].filter(Boolean)
  if (parts.length === 0) return ''
  return parts.join(' · ')
}

const viewDetail = (order: Order) => {
  router.push(`/admin/orders/${order.id}`)
}
</script>

<style lang="scss" scoped>
.order-management-page {
  padding: 32px;
  background-color: #f5f6fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;

  h1.page-title {
    font-size: 28px;
    font-weight: 700;
    color: #1D1D1F;
    margin: 0 0 4px;
    letter-spacing: -0.5px;
  }

  p.page-subtitle {
    font-size: 14px;
    color: #86868b;
    margin: 0;
  }
}

/* ---- 统计卡片 ---- */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 14px;
  margin-bottom: 24px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(3, 1fr);
  }
}

.stat-card {
  background: #fff;
  border-radius: 14px;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.06);
  }

  &.active {
    border-color: #6366F1;
    background: #F5F3FF;
  }

  .stat-icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #1D1D1F;
    line-height: 1;
  }

  .stat-label {
    font-size: 12px;
    color: #86868b;
    font-weight: 500;
  }
}

/* ---- 筛选栏 ---- */
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  
  .search-input {
    flex: 1;
    max-width: 360px;
    :deep(.el-input__wrapper) {
      border-radius: 10px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
  }

  .filter-select {
    width: 180px;
    :deep(.el-input__wrapper) {
      border-radius: 10px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
  }
}

/* ---- 订单卡片列表 ---- */
.order-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-state {
  text-align: center;
  padding: 80px 0;
  color: #86868b;
  p { margin: 16px 0 0; font-size: 15px; }
}

.order-card {
  display: flex;
  background: #fff;
  border-radius: 14px;
  cursor: pointer;
  overflow: hidden;
  border: 1px solid #F0F0F5;
  transition: all 0.2s ease;

  &:hover {
    border-color: #D0D5DD;
    box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    transform: translateY(-1px);
  }
}

/* 左侧状态色条 */
.order-status-bar {
  width: 5px;
  flex-shrink: 0;
  &.status-warning  { background: #F59E0B; }
  &.status-orange   { background: #F97316; }
  &.status-info     { background: #6B7280; }
  &.status-purple   { background: #8B5CF6; }
  &.status-blue     { background: #3B82F6; }
  &.status-danger   { background: #EF4444; }
  &.status-success  { background: #22C55E; }
  &.status-muted    { background: #D1D5DB; }
}

.order-card-body {
  flex: 1;
  padding: 18px 24px;
  min-width: 0;
}

.order-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.order-main-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.order-number {
  font-size: 16px;
  font-weight: 600;
  color: #1D1D1F;
  letter-spacing: -0.3px;
}

.type-tag {
  font-size: 11px;
  border-radius: 6px;
}

.order-status-area {
  display: flex;
  align-items: center;
  gap: 8px;

  .chevron-icon {
    color: #C0C4CC;
    font-size: 16px;
    transition: transform 0.2s;
  }
}

.order-card:hover .chevron-icon {
  transform: translateX(3px);
  color: #6366F1;
}

/* 元数据行 */
.order-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #515154;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  
  .el-icon { color: #86868b; }

  &.unassigned {
    color: #E6A23C;
    .el-icon { color: #E6A23C; }
  }
}

/* 订单摘要 */
.order-card-summary {
  margin-top: 8px;
  font-size: 13px;
  color: #86868b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 按钮 */
:deep(.el-button) {
  border-radius: 8px;
  font-weight: 500;
}
</style>
