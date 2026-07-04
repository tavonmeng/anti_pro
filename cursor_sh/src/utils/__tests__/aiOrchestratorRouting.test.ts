import { describe, expect, it } from 'vitest'
import { getModeForTargetAgent, getRouterStateForMode } from '../aiOrchestratorRouting'

describe('aiOrchestratorRouting', () => {
  it('starts a blank conversation in the main brief flow', () => {
    expect(getRouterStateForMode(null)).toEqual({
      current_agent: 'brief_agent',
      stage: 'brief_building',
    })
  })

  it('still routes existing order-query sessions through the order agent context', () => {
    expect(getRouterStateForMode('order_query')).toEqual({
      current_agent: 'order_agent',
      stage: 'order_query',
    })
  })

  it('maps creative subagents back to the main brief mode in the UI', () => {
    expect(getModeForTargetAgent('creative_direction_agent')).toBe('order_create')
    expect(getModeForTargetAgent('creative_diagnosis_agent')).toBe('order_create')
    expect(getModeForTargetAgent('brief_agent')).toBe('order_create')
  })
})
