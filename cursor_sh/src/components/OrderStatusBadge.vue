<template>
  <el-tag :type="tagType" :effect="effect" :size="size">
    {{ statusText }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { OrderStatus } from '@/types'

interface Props {
  status: OrderStatus
  size?: 'small' | 'default' | 'large'
  effect?: 'dark' | 'light' | 'plain'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default',
  effect: 'light'
})

const statusConfig: Record<OrderStatus, { text: string; type: 'success' | 'info' | 'warning' | 'danger' | '' }> = {
  draft: { text: '草稿', type: 'info' },
  pending_assign: { text: '待分配', type: 'info' },
  pending_contract: { text: '合同与付款', type: 'warning' },
  in_production: { text: '制作中', type: '' },
  pending_review: { text: '待审核', type: 'warning' },
  preview_ready: { text: '初稿预览', type: 'warning' },
  review_rejected: { text: '审核拒绝', type: 'danger' },
  revision_needed: { text: '需要修改', type: 'danger' },
  final_preview: { text: '终稿预览', type: 'warning' },
  completed: { text: '已完成', type: 'success' },
  cancelled: { text: '已取消', type: 'info' }
}

const statusText = computed(() => statusConfig[props.status]?.text || props.status)
const tagType = computed(() => statusConfig[props.status]?.type || '')
</script>

