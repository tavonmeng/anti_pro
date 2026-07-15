import type { OrderStatus, PreviewHistory } from '@/types'

export const ORDER_WORKFLOW_STATES = [
  { value: 'draft', label: '需求确认', description: '收到订单' },
  { value: 'pending_contract', label: '合同与付款', description: '签订合同、收取首付款' },
  { value: 'in_production', label: '内容制作', description: '开发与设计环节' },
  { value: 'preview_ready', label: '初稿交付', description: '内部审核与客户反馈' },
  { value: 'final_preview', label: '终稿交付', description: '内部审核与定稿' },
  { value: 'completed', label: '项目完成', description: '订单已结束' },
] as const

export type WorkflowOrderStatus = typeof ORDER_WORKFLOW_STATES[number]['value']

const statusLabels: Record<OrderStatus, string> = {
  draft: '需求确认',
  pending_assign: '需求确认',
  pending_contract: '合同与付款',
  in_production: '内容制作',
  pending_review: '初稿交付',
  preview_ready: '初稿交付',
  review_rejected: '初稿交付',
  revision_needed: '初稿交付',
  final_preview: '终稿交付',
  completed: '项目完成',
  cancelled: '已取消',
}

const canonicalNextStatus: Partial<Record<WorkflowOrderStatus, WorkflowOrderStatus>> = {
  draft: 'pending_contract',
  pending_contract: 'in_production',
  in_production: 'preview_ready',
  preview_ready: 'final_preview',
  final_preview: 'completed',
}

const hasFinalPreview = (previewHistory: PreviewHistory[] = []) =>
  previewHistory.some(item => item.previewType === 'final')

export const getOrderStatusLabel = (status: OrderStatus) => statusLabels[status] || status

export const canonicalOrderStatus = (
  status: OrderStatus,
  previewHistory: PreviewHistory[] = [],
): WorkflowOrderStatus | 'cancelled' => {
  if (status === 'cancelled') return 'cancelled'
  if (status === 'pending_assign') return 'draft'
  if (status === 'pending_review' || status === 'review_rejected' || status === 'revision_needed') {
    return hasFinalPreview(previewHistory) ? 'final_preview' : 'preview_ready'
  }
  return status
}

export const getOrderWorkflowStep = (
  status: OrderStatus,
  previewHistory: PreviewHistory[] = [],
) => {
  const canonical = canonicalOrderStatus(status, previewHistory)
  if (canonical === 'cancelled') return 0
  if (canonical === 'completed') return ORDER_WORKFLOW_STATES.length
  return ORDER_WORKFLOW_STATES.findIndex(item => item.value === canonical)
}

export const getNextOrderStatus = (
  status: OrderStatus,
  previewHistory: PreviewHistory[] = [],
): WorkflowOrderStatus | null => {
  if (status === 'pending_assign') return 'pending_contract'
  if (status === 'pending_review' || status === 'review_rejected' || status === 'revision_needed') {
    return canonicalOrderStatus(status, previewHistory) as WorkflowOrderStatus
  }

  const canonical = canonicalOrderStatus(status, previewHistory)
  if (canonical === 'cancelled') return null
  return canonicalNextStatus[canonical] || null
}
