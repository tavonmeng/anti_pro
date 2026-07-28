import { describe, expect, it } from 'vitest'
import { getModeForTargetAgent, getRouterStateForMode } from '../aiOrchestratorRouting'

describe('aiOrchestratorRouting', () => {
  it('starts a blank conversation without preselecting a subagent', () => {
    expect(getRouterStateForMode(null)).toEqual({
      current_agent: null,
      stage: 'intent_routing',
    })
  })

  it('keeps an established requirement conversation in the brief flow', () => {
    expect(getRouterStateForMode('order_create')).toEqual({
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
