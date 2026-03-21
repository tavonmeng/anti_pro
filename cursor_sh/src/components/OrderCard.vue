<template>
  <el-card class="order-card" shadow="hover">
    <div class="order-header">
      <div class="order-info">
        <div class="order-number">{{ order.orderNumber }}</div>
        <OrderStatusBadge :status="order.status" />
      </div>
      <div class="order-type">
        <el-tag type="info" size="small">{{ orderTypeText }}</el-tag>
      </div>
    </div>
    
    <div class="order-content">
      <div class="order-detail" v-if="order.orderType === 'video_purchase'">
        <p><strong>行业：</strong>{{ getIndustryText(order) }}</p>
        <p><strong>风格：</strong>{{ getStyleText(order) }}</p>
        <p><strong>时长：</strong>{{ order.duration }}秒</p>
      </div>
      <div class="order-detail" v-else-if="order.orderType === 'ai_3d_custom'">
        <p class="truncate"><strong>配置：</strong>{{ order.configuration }}</p>
        <p class="truncate"><strong>创意：</strong>{{ order.creativeIdea }}</p>
      </div>
      <div class="order-detail" v-else-if="order.orderType === 'digital_art'">
        <p><strong>艺术方向：</strong>{{ getArtDirectionText(order) }}</p>
        <p class="truncate"><strong>说明：</strong>{{ order.description }}</p>
      </div>
    </div>
    
    <div class="order-footer">
      <div class="order-meta">
        <span class="meta-item">
          <el-icon><User /></el-icon>
          {{ order.userName || '未知用户' }}
        </span>
        <span v-if="order.assignees && order.assignees.length > 0" class="meta-item">
          <el-icon><Avatar /></el-icon>
          {{ order.assignees.map(a => a.name).join('、') }}
        </span>
        <span class="meta-item">
          <el-icon><Clock /></el-icon>
          {{ formatTime(order.createdAt) }}
        </span>
      </div>
      <el-button type="primary" text @click="$emit('view', order)">
        查看详情
        <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { User, Avatar, Clock, ArrowRight } from '@element-plus/icons-vue'
import OrderStatusBadge from './OrderStatusBadge.vue'
import type { Order, VideoPurchaseOrder, DigitalArtOrder } from '@/types'

interface Props {
  order: Order
}

const props = defineProps<Props>()

defineEmits<{
  view: [order: Order]
}>()

const orderTypeMap: Record<string, string> = {
  video_purchase: '裸眼3D成片购买',
  ai_3d_custom: 'AI裸眼3D定制',
  digital_art: '数字艺术定制'
}

const orderTypeText = computed(() => orderTypeMap[props.order.orderType] || props.order.orderType)

const getIndustryText = (order: Order) => {
  if (order.orderType === 'video_purchase') {
    const vOrder = order as VideoPurchaseOrder
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

const getStyleText = (order: Order) => {
  if (order.orderType === 'video_purchase') {
    const vOrder = order as VideoPurchaseOrder
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

const getArtDirectionText = (order: Order) => {
  if (order.orderType === 'digital_art') {
    const dOrder = order as DigitalArtOrder
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
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style lang="scss" scoped>
.order-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
  }
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #E8E8ED;
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-number {
  font-size: 16px;
  font-weight: 600;
  color: #1D1D1F;
}

.order-content {
  margin-bottom: 16px;
}

.order-detail {
  p {
    margin: 6px 0;
    font-size: 14px;
    color: #515154;
    
    strong {
      color: #1D1D1F;
      font-weight: 500;
    }
    
    &.truncate {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #E8E8ED;
}

.order-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #86868B;
  
  .el-icon {
    font-size: 14px;
  }
}
</style>

