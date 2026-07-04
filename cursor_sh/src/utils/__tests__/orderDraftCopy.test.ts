import { describe, expect, it } from 'vitest'
import { orderDraftCopy } from '../orderDraftCopy'

describe('orderDraftCopy', () => {
  it('uses order draft wording instead of draft box wording', () => {
    expect(orderDraftCopy.navLabel).toBe('订单草稿')
    expect(orderDraftCopy.pageTitle).toBe('订单草稿')
    expect(orderDraftCopy.emptyDescription).toBe('暂无订单草稿')
    expect(orderDraftCopy.keepAfterAuth).toContain('订单草稿')
    expect(orderDraftCopy.keepAfterAuth).not.toContain('草稿箱')
  })
})
