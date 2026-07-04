export type AssistantMode = 'order_create' | 'order_query' | 'business_intro' | 'general' | string | null

export type RouterAgent =
  | 'brief_agent'
  | 'business_intro_agent'
  | 'creative_direction_agent'
  | 'creative_diagnosis_agent'
  | 'budget_agent'
  | 'order_agent'
  | 'general_agent'

export type RouterState = {
  current_agent: RouterAgent
  stage: string
}

export const getRouterStateForMode = (mode: AssistantMode): RouterState => {
  if (mode === 'order_query') {
    return { current_agent: 'order_agent', stage: 'order_query' }
  }
  if (mode === 'business_intro') {
    return { current_agent: 'business_intro_agent', stage: 'business_intro' }
  }
  if (mode === 'general') {
    return { current_agent: 'general_agent', stage: 'idle' }
  }
  return { current_agent: 'brief_agent', stage: 'brief_building' }
}

export const getModeForTargetAgent = (
  targetAgent?: string | null,
  intent?: string | null,
): 'order_create' | 'order_query' | 'business_intro' | 'general' => {
  if (targetAgent === 'order_agent' || intent === 'order_query') return 'order_query'
  if (targetAgent === 'business_intro_agent' || intent === 'business_intro') return 'business_intro'
  if (targetAgent === 'general_agent' || intent === 'general') return 'general'
  return 'order_create'
}
