<template>
  <div class="drafts-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">草稿箱</h1>
        <p class="page-subtitle">未提交的订单草稿，随时可以继续编辑或提交</p>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-if="draftOrders.length === 0 && !orderStore.loading" class="empty-state">
      <el-empty description="暂无草稿">
        <el-button type="primary" @click="goToWorkspace">去创建订单</el-button>
      </el-empty>
    </div>
    
    <!-- 草稿列表 -->
    <div v-else class="drafts-grid">
      <div
        v-for="order in draftOrders"
        :key="order.id"
        class="draft-card"
        @click="viewDraft(order)"
      >
        <div class="draft-card-header">
          <div class="draft-type">
            <el-icon class="type-icon"><EditPen /></el-icon>
            <span class="type-text">{{ orderTypeMap[order.orderType] || order.orderType }}</span>
          </div>
          <el-tag type="info" size="small" effect="plain">草稿</el-tag>
        </div>
        
        <div class="draft-card-body">
          <p class="draft-number">{{ order.orderNumber }}</p>
          <p class="draft-time">最后编辑：{{ formatTime(order.updatedAt) }}</p>
        </div>
        
        <div class="draft-card-actions">
          <el-button size="small" @click.stop="handleEdit(order)">
            继续编辑
          </el-button>
          <el-button size="small" type="primary" @click.stop="handleSubmit(order)">
            提交订单
          </el-button>
          <el-button size="small" type="danger" text @click.stop="handleDelete(order)">
            删除
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 需求告知函确认弹窗 -->
    <OrderConfirmationDialog
      v-if="selectedOrder"
      v-model="showConfirmation"
      :order-number="selectedOrder.orderNumber"
      :order-type="selectedOrder.orderType"
      :form-data="selectedOrder"
      @confirm="handleConfirmOrder"
      @cancel="showConfirmation = false; selectedOrder = null"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onActivated, ref } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useOrderStore } from '@/stores/order'
import OrderConfirmationDialog from '@/components/OrderConfirmationDialog.vue'
import type { Order } from '@/types'

const router = useRouter()
const orderStore = useOrderStore()

const showConfirmation = ref(false)
const selectedOrder = ref<Order | null>(null)

const orderTypeMap: Record<string, string> = {
  video_purchase: '裸眼3D成片购买适配',
  ai_3d_custom: 'AI裸眼3D内容定制',
  digital_art: '数字艺术内容定制'
}

const draftOrders = computed(() => {
  return orderStore.orders.filter(o => o.status === 'draft')
})

onMounted(() => {
  orderStore.fetchOrders()
})

onActivated(() => {
  orderStore.fetchOrders()
})

const formatTime = (timeString: string) => {
  if (!timeString) return '-'
  const date = new Date(timeString)
  if (isNaN(date.getTime())) return timeString
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

const viewDraft = (order: Order) => {
  router.push(`/user/orders/${order.id}`)
}

const handleEdit = (order: Order) => {
  router.push(`/user/edit-order/${order.id}`)
}

const handleSubmit = async (order: Order) => {
  selectedOrder.value = order
  showConfirmation.value = true
}

const handleConfirmOrder = async (confirmData: { email: string; phone: string }) => {
  if (!selectedOrder.value) return
  
  try {
    const finalData = {
      ...selectedOrder.value,
      confirmEmail: confirmData.email,
      confirmPhone: confirmData.phone
    }
    
    // 更新订单数据并通过草稿状态提交
    await orderStore.updateOrder(selectedOrder.value.id, {
      orderType: selectedOrder.value.orderType,
      ...finalData
    })
    
    await orderStore.updateOrderStatus(selectedOrder.value.id, 'pending_assign')
    ElMessage.success('订单已提交')
    showConfirmation.value = false
    selectedOrder.value = null
    await orderStore.fetchOrders()
  } catch (error) {
    console.error('提交订单失败:', error)
  }
}

const handleDelete = async (order: Order) => {
  try {
    await ElMessageBox.confirm(
      '确认删除此草稿？删除后不可恢复。',
      '删除草稿',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
        center: true
      }
    )
    await orderStore.updateOrderStatus(order.id, 'cancelled')
    ElMessage.success('草稿已删除')
    await orderStore.fetchOrders()
  } catch {
    // 用户取消
  }
}

const goToWorkspace = () => {
  router.push('/user/workspace')
}
</script>

<style lang="scss" scoped>
.drafts-page {
  padding: 32px;
  background-color: #f8f9fc;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 32px;
  background: linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%);
  padding: 24px 32px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.8);

  h1.page-title {
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(90deg, #1d1d1f, #434343);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
  }

  p.page-subtitle {
    font-size: 14px;
    color: #86868b;
    margin: 0;
    font-weight: 500;
  }
}

.empty-state {
  padding: 80px 0;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.02);
}

.drafts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.draft-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 14px;

  &:hover {
    border-color: rgba(0, 113, 227, 0.3);
    box-shadow: 0 4px 16px rgba(0, 113, 227, 0.08);
    transform: translateY(-1px);
  }
}

.draft-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.draft-type {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-icon {
  font-size: 16px;
  color: #0071e3;
}

.type-text {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.draft-card-body {
  .draft-number {
    font-family: 'SF Mono', 'Menlo', monospace;
    font-size: 13px;
    color: #515154;
    margin: 0 0 6px 0;
  }
  
  .draft-time {
    font-size: 12px;
    color: #86868b;
    margin: 0;
  }
}

.draft-card-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}
</style>
