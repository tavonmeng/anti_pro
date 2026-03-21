<template>
  <div class="create-order-page">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="goBack">返回工作台</el-button>
      <h1 class="page-title">{{ pageTitle }}</h1>
      <p class="page-subtitle">{{ pageSubtitle }}</p>
    </div>
    
    <el-card class="form-card" v-loading="loading">
      <VideoPurchaseForm
        v-if="orderType === 'video_purchase'"
        :order="isEditMode ? order : undefined"
        @submit="handleSubmit"
        @cancel="goBack"
      />
      <AI3DCustomForm
        v-else-if="orderType === 'ai_3d_custom'"
        :order="isEditMode ? order : undefined"
        @submit="handleSubmit"
        @cancel="goBack"
      />
      <DigitalArtForm
        v-else-if="orderType === 'digital_art'"
        :order="isEditMode ? order : undefined"
        @submit="handleSubmit"
        @cancel="goBack"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
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
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  
  .el-button {
    margin-bottom: 16px;
  }
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #86868B;
  margin: 0;
}

.form-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
</style>

