import { describe, expect, it } from 'vitest'
import { isOrderPendingReview, isOrderReviewRejected } from '../orderReviewStatus'

describe('admin order review queue status', () => {
  it('includes creator deliverables awaiting review while the order remains in production', () => {
    expect(isOrderPendingReview({
      status: 'in_production',
      creatorReviewStatus: 'pending_review',
    })).toBe(true)
  })

  it('keeps legacy order-level review statuses visible', () => {
    expect(isOrderPendingReview({ status: 'pending_review' })).toBe(true)
    expect(isOrderReviewRejected({ status: 'review_rejected' })).toBe(true)
  })

  it('does not treat unrelated production orders as review work', () => {
    expect(isOrderPendingReview({ status: 'in_production', creatorReviewStatus: null })).toBe(false)
    expect(isOrderReviewRejected({ status: 'in_production', creatorReviewStatus: null })).toBe(false)
  })
})
