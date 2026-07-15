<template>
  <el-tag :type="tagType" :effect="effect" :size="size">
    {{ statusText }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { OrderStatus } from '@/types'
import { getOrderStatusLabel } from '@/utils/orderWorkflow'

interface Props {
  status: OrderStatus
  size?: 'small' | 'default' | 'large'
  effect?: 'dark' | 'light' | 'plain'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default',
  effect: 'light'
})

const statusConfig: Record<OrderStatus, { type: 'success' | 'info' | 'warning' | 'danger' | '' }> = {
  draft: { type: 'info' },
  pending_assign: { type: 'info' },
  pending_contract: { type: 'warning' },
  in_production: { type: '' },
  pending_review: { type: 'warning' },
  preview_ready: { type: 'warning' },
  review_rejected: { type: 'warning' },
  revision_needed: { type: 'warning' },
  final_preview: { type: 'warning' },
  completed: { type: 'success' },
  cancelled: { type: 'info' }
}

const statusText = computed(() => getOrderStatusLabel(props.status))
const tagType = computed(() => statusConfig[props.status]?.type || '')
</script>
