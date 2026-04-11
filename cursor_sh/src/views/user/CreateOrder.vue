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
        @cancel="goBack"
      />
      <AI3DCustomForm
        v-else-if="orderType === 'ai_3d_custom'"
        :order="isEditMode ? (order || undefined) : undefined"
        @submit="handleSubmit"
        @cancel="goBack"
      />
      <DigitalArtForm
        v-else-if="orderType === 'digital_art'"
        :order="isEditMode ? (order || undefined) : undefined"
        @submit="handleSubmit"
        @cancel="goBack"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useOrderStore } from '@/stores/order'
import VideoPurchaseForm from '@/components/VideoPurchaseForm.vue'
import AI3DCustomForm from '@/components/AI3DCustomForm.vue'
import DigitalArtForm from '@/components/DigitalArtForm.vue'
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
      } else if (order.value.status !== 'pending_assign') {
        ElMessage.warning('只有待分配状态的订单可以修改')
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

const handleSubmit = async (formData: any) => {
  try {
    if (isEditMode.value && orderId.value) {
      // 修改订单
      await orderStore.updateOrder(orderId.value, {
        orderType: orderType.value,
        ...formData
      })
      // 刷新订单列表
      await orderStore.fetchOrders()
      router.push('/user/orders')
    } else {
      // 创建订单
      await orderStore.createOrder({
        orderType: orderType.value,
        ...formData
      })
      // 刷新订单列表，确保新创建的订单显示在列表中
      await orderStore.fetchOrders()
      router.push('/user/orders')
    }
  } catch (error) {
    console.error(isEditMode.value ? '修改订单失败:' : '创建订单失败:', error)
    // 错误已经在 store 中处理并显示，这里不需要再次显示
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
</style>
