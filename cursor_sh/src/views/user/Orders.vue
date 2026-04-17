<template>
  <div class="orders-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的订单</h1>
        <p class="page-subtitle">查看和管理您的所有订单</p>
      </div>
    </div>
    
    <!-- 筛选器 -->
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="订单类型">
          <el-select v-model="filters.orderType" placeholder="全部类型" clearable style="width: 200px" @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="裸眼3D成片购买" value="video_purchase" />
            <el-option label="AI裸眼3D定制" value="ai_3d_custom" />
            <el-option label="数字艺术定制" value="digital_art" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="订单状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 200px" @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="草稿" value="draft" />
            <el-option label="待分配" value="pending_assign" />
            <el-option label="制作中" value="in_production" />
            <el-option label="初稿预览" value="preview_ready" />
            <el-option label="需要修改" value="revision_needed" />
            <el-option label="终稿预览" value="final_preview" />
            <el-option label="已完成" value="completed" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 订单列表 -->
    <div v-if="filteredOrders.length === 0" class="empty-state">
      <el-empty description="暂无订单" />
    </div>
    
    <div v-else class="orders-grid">
      <OrderCard
        v-for="order in filteredOrders"
        :key="order.id"
        :order="maskOrderForUser(order)"
        @view="viewOrder"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useOrderStore } from '@/stores/order'
import OrderCard from '@/components/OrderCard.vue'
import type { Order, OrderType, OrderStatus } from '@/types'

const router = useRouter()
const orderStore = useOrderStore()

const filters = ref({
  orderType: '' as OrderType | '',
  status: '' as OrderStatus | ''
})

// 将用户不应看到的状态映射为制作中
const mapUserVisibleStatus = (status: OrderStatus): OrderStatus => {
  if (status === 'pending_review' || status === 'review_rejected') return 'in_production'
  return status
}

const filteredOrders = computed(() => {
  // 先做状态映射，再做筛选
  let result = orderStore.orders.map(o => ({ ...o, status: mapUserVisibleStatus(o.status) as OrderStatus }))
  
  if (filters.value.orderType) {
    result = result.filter(o => o.orderType === filters.value.orderType)
  }
  
  if (filters.value.status) {
    result = result.filter(o => o.status === filters.value.status)
  }
  
  return result
})

// 页面挂载时获取订单列表
onMounted(() => {
  orderStore.fetchOrders()
})

// 页面激活时（从其他页面返回时）刷新订单列表
onActivated(() => {
  orderStore.fetchOrders()
})

const handleFilter = () => {
  // 筛选已经通过computed自动完成
}

const viewOrder = (order: Order) => {
  router.push(`/user/orders/${order.id}`)
}

// 传递给卡片的订单对象，做显示层面的状态掩蔽
const maskOrderForUser = (order: Order): Order => {
  return { ...order, status: mapUserVisibleStatus(order.status) as OrderStatus }
}
</script>

<style lang="scss" scoped>
.orders-page {
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

.filter-card {
  margin-bottom: 32px;
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
  background: white;
  
  :deep(.el-card__body) {
    padding: 24px 24px 4px 24px;
  }

  .el-form-item {
    margin-bottom: 20px;
  }
}

.empty-state {
  padding: 80px 0;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.02);
}

.orders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 24px;
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
</style>

