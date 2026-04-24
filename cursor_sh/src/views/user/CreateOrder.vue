<template>
  <div class="create-order-page">
    <!-- Stitch Mono Section Label -->
    <div class="section-label">ORDER BRIEF</div>

    <div class="page-header">
      <h1 class="page-title">{{ pageTitle }}</h1>
      <p class="page-subtitle">{{ pageSubtitle }}</p>
    </div>
    
    <!-- Flat divider instead of card wrapper -->
    <div class="header-divider"></div>

    <div class="form-surface" v-loading="loading">
      <VideoPurchaseForm
        v-if="orderType === 'video_purchase'"
        :order="isEditMode ? (order || undefined) : undefined"
        @submit="handleSubmit"
        @save-draft="handleSaveDraft"
        @cancel="goBack"
      />
      <AI3DCustomForm
        v-else-if="orderType === 'ai_3d_custom'"
        :order="isEditMode ? (order || undefined) : undefined"
        @submit="handleSubmit"
        @save-draft="handleSaveDraft"
        @cancel="goBack"
      />
      <DigitalArtForm
        v-else-if="orderType === 'digital_art'"
        :order="isEditMode ? (order || undefined) : undefined"
        @submit="handleSubmit"
        @save-draft="handleSaveDraft"
        @cancel="goBack"
      />
    </div>

    <!-- 需求告知函确认弹窗 -->
    <OrderConfirmationDialog
      v-model="showConfirmation"
      :order-number="pendingOrderNumber"
      :order-type="orderType"
      :form-data="pendingFormData"
      @confirm="handleConfirmOrder"
      @cancel="showConfirmation = false"
    />

    <!-- 提交成功弹窗 -->
    <el-dialog
      v-model="showSuccessDialog"
      width="480px"
      :close-on-click-modal="false"
      align-center
      class="success-dialog"
    >
      <div class="success-content">
        <div class="success-icon">
          <el-icon :size="48" color="#34c759"><CircleCheckFilled /></el-icon>
        </div>
        <h2 class="success-title">需求已确认提交</h2>
        <p class="success-desc">
          您的订单已成功提交，我们的团队将尽快为您安排制作。<br/>
          您可以下载本次需求告知函留档。
        </p>
        <div class="success-actions">
          <el-button
            type="primary"
            :icon="Download"
            :loading="downloadingPdf"
            @click="handleDownloadPdf"
          >
            下载需求告知函 PDF
          </el-button>
          <el-button @click="goToOrders">
            查看我的订单
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Download } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { orderApi } from '@/utils/api'
import VideoPurchaseForm from '@/components/VideoPurchaseForm.vue'
import AI3DCustomForm from '@/components/AI3DCustomForm.vue'
import DigitalArtForm from '@/components/DigitalArtForm.vue'
import OrderConfirmationDialog from '@/components/OrderConfirmationDialog.vue'
import type { OrderType, Order } from '@/types'

const router = useRouter()
const route = useRoute()
const orderStore = useOrderStore()

const isEditMode = computed(() => route.name === 'EditOrder')
const orderId = computed(() => isEditMode.value ? route.params.id as string : null)
const orderType = computed(() => {
  if (isEditMode.value && order.value) {
    return order.value.orderType
  }
  return route.params.type as OrderType
})

const order = ref<Order | null>(null)
const loading = ref(false)

// 需求告知函确认弹窗状态
const showConfirmation = ref(false)
const pendingFormData = ref<Record<string, any>>({})
const pendingOrderNumber = ref('')

// 成功弹窗状态
const showSuccessDialog = ref(false)
const submittedOrderId = ref('')
const downloadingPdf = ref(false)

// 生成临时订单号
const generateTempOrderNumber = () => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const r = String(Math.floor(Math.random() * 10000)).padStart(4, '0')
  return `UV${y}${m}${d}${r}`
}

const pageTitle = computed(() => {
  if (isEditMode.value) {
    return '修改订单'
  }
  const titles: Record<OrderType, string> = {
    video_purchase: '裸眼3D成片购买适配',
    ai_3d_custom: 'AI裸眼3D内容定制',
    digital_art: '数字艺术内容定制'
  }
  return titles[orderType.value] || '创建订单'
})

const pageSubtitle = computed(() => {
  const subtitles: Record<OrderType, string> = {
    video_purchase: '填写屏幕参数，获取适配的专业裸眼3D视频内容',
    ai_3d_custom: '基于AI技术的定制化3D内容创作，5-7天交付',
    digital_art: '专业数字艺术创作服务，3天内提供初稿'
  }
  return subtitles[orderType.value] || ''
})

onMounted(async () => {
  if (isEditMode.value && orderId.value) {
    loading.value = true
    try {
      order.value = await orderStore.getOrderDetail(orderId.value)
      if (!order.value) {
        ElMessage.error('订单不存在')
        router.push('/user/orders')
      } else if (order.value.status !== 'pending_contract' && order.value.status !== 'pending_assign' && order.value.status !== 'draft') {
        ElMessage.warning('只有待分配、合同与付款或草稿状态的订单可以修改')
        router.push(`/user/orders/${orderId.value}`)
      }
    } catch (error) {
      console.error('获取订单失败:', error)
      router.push('/user/orders')
    } finally {
      loading.value = false
    }
  }
})

// 用户点击"确认提交" → 弹出需求告知函
const handleSubmit = async (formData: any) => {
  pendingFormData.value = formData
  if (isEditMode.value && orderId.value) {
    pendingOrderNumber.value = order.value?.orderNumber || ''
  } else {
    pendingOrderNumber.value = generateTempOrderNumber()
  }
  showConfirmation.value = true
}

// 用户确认需求告知函后，正式创建或更新订单
const handleConfirmOrder = async (confirmData: { email: string; phone: string }) => {
  try {
    const finalData = {
      orderType: orderType.value,
      ...pendingFormData.value,
      confirmEmail: confirmData.email,
      confirmPhone: confirmData.phone
    }
    
    let resultOrder: Order
    if (isEditMode.value && orderId.value) {
      resultOrder = await orderStore.updateOrder(orderId.value, finalData)
      await orderStore.updateOrderStatus(orderId.value, 'pending_contract')
      submittedOrderId.value = orderId.value
    } else {
      resultOrder = await orderStore.createOrder(finalData)
      submittedOrderId.value = resultOrder.id
    }
    showConfirmation.value = false
    await orderStore.fetchOrders()
    
    // 显示成功弹窗（含 PDF 下载）
    showSuccessDialog.value = true
  } catch (error) {
    console.error('保存/修改订单失败:', error)
  }
}

// 下载告知函 PDF
const handleDownloadPdf = async () => {
  if (!submittedOrderId.value) return
  downloadingPdf.value = true
  try {
    await orderApi.downloadConfirmationPdf(submittedOrderId.value)
    ElMessage.success('PDF 下载成功')
  } catch (error) {
    console.error('下载 PDF 失败:', error)
    ElMessage.error('下载 PDF 失败，请稍后重试')
  } finally {
    downloadingPdf.value = false
  }
}

// 跳转到订单列表
const goToOrders = () => {
  showSuccessDialog.value = false
  router.push('/user/orders')
}

const handleSaveDraft = async (formData: any) => {
  try {
    if (isEditMode.value && orderId.value) {
      await orderStore.updateOrder(orderId.value, {
        orderType: orderType.value,
        ...formData
      })
    } else {
      await orderStore.createOrder({
        orderType: orderType.value,
        ...formData
      }, true)
    }
    await orderStore.fetchOrders()
    router.push('/user/drafts')
  } catch (error) {
    console.error('保存草稿失败:', error)
  }
}

const goBack = () => {
  router.push('/user/workspace')
}
</script>

<style lang="scss" scoped>
.create-order-page {
  padding: 32px 40px;
  max-width: 900px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
  box-sizing: border-box;
}

/* Stitch monospace section label */
.section-label {
  font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
  font-size: 11px;
  font-weight: 500;
  color: #747474;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}

.page-header {
  margin-bottom: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 500;
  color: #1a1c1c;
  margin: 0 0 8px 0;
  letter-spacing: -0.01em;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

.page-subtitle {
  font-size: 13px;
  color: #747474;
  margin: 0;
  line-height: 1.5;
}

.header-divider {
  width: 100%;
  height: 1px;
  background: rgba(0, 0, 0, 0.08);
  margin: 24px 0;
}

/* Flat surface — no card, no shadow, no border-radius */
.form-surface {
  background: transparent;
  border: none;
  box-shadow: none;
  border-radius: 0;
}

/* 成功弹窗样式 */
.success-dialog {
  :deep(.el-dialog) {
    border-radius: 16px;
    overflow: hidden;
  }
  :deep(.el-dialog__header) {
    display: none;
  }
  :deep(.el-dialog__body) {
    padding: 48px 40px;
  }
}

.success-content {
  text-align: center;
}

.success-icon {
  margin-bottom: 20px;
  animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes scaleIn {
  from { transform: scale(0); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.success-title {
  font-size: 22px;
  font-weight: 600;
  color: #1a1c1c;
  margin: 0 0 12px 0;
}

.success-desc {
  font-size: 14px;
  color: #86868b;
  line-height: 1.7;
  margin: 0 0 28px 0;
}

.success-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;

  .el-button {
    width: 260px;
    height: 42px;
    border-radius: 10px;
    font-weight: 500;
  }
}
</style>
