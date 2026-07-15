import type { Order } from '@/types'

type ReviewAwareOrder = Pick<Order, 'status' | 'creatorReviewStatus'>

/** 兼容旧预览流程和当前制作者交付物审核队列。 */
export const isOrderPendingReview = (order: ReviewAwareOrder) =>
  order.status === 'pending_review' || order.creatorReviewStatus === 'pending_review'

/** 兼容旧订单状态，并以制作者当前交付版本的驳回状态补充审核队列。 */
export const isOrderReviewRejected = (order: ReviewAwareOrder) =>
  order.status === 'review_rejected' || order.creatorReviewStatus === 'review_rejected'
