export type BriefFieldState = {
  value?: unknown
  confidence?: string
  source_message_ids?: string[]
  updated_at?: string
}

export type BriefState = {
  fields?: Record<string, BriefFieldState | unknown>
  filled_fields?: string[]
  missing_fields?: string[]
  readiness?: {
    level?: string
    missing_for_provisional?: string[]
    missing_for_formal?: string[]
  }
}

export type AgentStateWithBrief = {
  brief_state?: BriefState | null
}

export type BriefProgressField = {
  key: string
  label: string
  value: string
  confidence: string
}

export type BriefProgressView = {
  visible: boolean
  percent: number
  filledCount: number
  totalCount: number
  status: 'partial' | 'ready' | 'complete'
  statusLabel: string
  fields: BriefProgressField[]
  missingFields: string[]
}

const FIELD_LABELS: Record<string, string> = {
  project_name: '项目名称',
  resource_background: '项目背景与媒体简介',
  audience_scene: '目标受众与场景特点',
  media_positioning: '媒体定位与品牌调性',
  city_location: '投放城市与媒体位置',
  viewing_path: '观看动线说明',
  art_direction: '艺术方向与风格偏好',
  theme_concept: '内容主题与核心表达',
  media_specs: '媒体尺寸与物理规格',
  timing_number: '投放时长与数量',
  tech_delivery: '技术需求',
  content_review: '素材审核规范与周期',
  budget: '项目制作预算',
  online_time: '预计上刊时间',
  special_requirements: '其他特殊合作要求',
  site_photos: '现场实拍图',
  remarks: '备注',
}

const displayValue = (raw: unknown) => {
  if (Array.isArray(raw)) return raw.filter(Boolean).join('、').trim()
  if (raw && typeof raw === 'object') return String((raw as BriefFieldState).value || '').trim()
  return String(raw || '').trim()
}

const displayLabel = (key: string) => {
  if (key === 'resource_background_or_media_positioning') return '项目背景或媒体定位'
  return FIELD_LABELS[key] || key
}

export const getBriefProgress = (agentState?: AgentStateWithBrief | null): BriefProgressView => {
  const briefState = agentState?.brief_state
  const fields = briefState?.fields || {}
  const collectedFields = Object.entries(fields)
    .map(([key, raw]) => {
      const value = displayValue(raw)
      const confidence = raw && typeof raw === 'object'
        ? String((raw as BriefFieldState).confidence || 'unknown')
        : 'unknown'
      return { key, label: displayLabel(key), value, confidence }
    })
    .filter(field => field.value)

  const totalCount = Object.keys(fields).length
  const filledKeys = new Set(
    (briefState?.filled_fields || []).filter(Boolean).concat(collectedFields.map(field => field.key)),
  )
  const filledCount = Math.max(collectedFields.length, filledKeys.size)
  const percent = totalCount > 0 ? Math.round((filledCount / totalCount) * 100) : 0
  const readinessLevel = briefState?.readiness?.level
  const status = readinessLevel === 'formal' ? 'complete' : readinessLevel === 'provisional' ? 'ready' : 'partial'
  const statusLabel = status === 'complete' ? '正式条件已满足' : status === 'ready' ? '已达到执行条件' : '持续收集中'
  const missingFields = (briefState?.readiness?.missing_for_formal || briefState?.missing_fields || [])
    .filter(key => key && !filledKeys.has(key))
    .map(displayLabel)

  return {
    visible: Boolean(briefState && totalCount > 0 && filledCount > 0),
    percent,
    filledCount,
    totalCount,
    status,
    statusLabel,
    fields: collectedFields,
    missingFields,
  }
}
