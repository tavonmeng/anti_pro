import { describe, expect, it } from 'vitest'
import {
  ORDER_WORKFLOW_STATES,
  canonicalOrderStatus,
  getNextOrderStatus,
  getOrderStatusLabel,
  getOrderWorkflowStep,
} from '../orderWorkflow'

describe('ordered order workflow', () => {
  it('exposes exactly the six ordered business states', () => {
    expect(ORDER_WORKFLOW_STATES.map(item => item.label)).toEqual([
      '需求确认',
      '合同与付款',
      '内容制作',
      '初稿交付',
      '终稿交付',
      '项目完成',
    ])
  })

  it('only offers the immediate next state', () => {
    expect(getNextOrderStatus('draft')).toBe('pending_contract')
    expect(getNextOrderStatus('pending_contract')).toBe('in_production')
    expect(getNextOrderStatus('in_production')).toBe('preview_ready')
    expect(getNextOrderStatus('preview_ready')).toBe('final_preview')
    expect(getNextOrderStatus('final_preview')).toBe('completed')
    expect(getNextOrderStatus('completed')).toBeNull()
    expect(getNextOrderStatus('cancelled')).toBeNull()
  })

  it('normalizes legacy review states without moving backward', () => {
    expect(canonicalOrderStatus('pending_assign')).toBe('draft')
    expect(getNextOrderStatus('pending_assign')).toBe('pending_contract')
    expect(getNextOrderStatus('revision_needed')).toBe('preview_ready')
    expect(getNextOrderStatus('revision_needed', [{ previewType: 'final' } as any])).toBe('final_preview')
  })

  it('uses the same labels and progress positions everywhere', () => {
    expect(getOrderStatusLabel('in_production')).toBe('内容制作')
    expect(getOrderStatusLabel('review_rejected')).toBe('初稿交付')
    expect(getOrderWorkflowStep('preview_ready')).toBe(3)
    expect(getOrderWorkflowStep('completed')).toBe(6)
  })
})
