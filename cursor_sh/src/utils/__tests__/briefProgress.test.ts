import { describe, expect, it } from 'vitest'
import { getBriefProgress } from '../briefProgress'

const emptyFields = {
  project_name: { value: '' },
  theme_concept: { value: '' },
  city_location: { value: '' },
}

describe('briefProgress', () => {
  it('hides the summary until the agent has collected a field', () => {
    expect(getBriefProgress({ brief_state: { fields: emptyFields } }).visible).toBe(false)
  })

  it('derives the count and percentage from the shared main brief state', () => {
    const result = getBriefProgress({
      brief_state: {
        fields: {
          ...emptyFields,
          project_name: { value: '春季城市视觉项目', confidence: 'medium' },
        },
        readiness: { level: 'insufficient', missing_for_formal: ['theme_concept', 'city_location'] },
      },
    })

    expect(result).toMatchObject({
      visible: true,
      filledCount: 1,
      totalCount: 3,
      percent: 33,
      status: 'partial',
      missingFields: ['内容主题与核心表达', '投放城市与媒体位置'],
    })
    expect(result.fields[0]).toMatchObject({
      label: '项目名称',
      value: '春季城市视觉项目',
    })
  })

  it('keeps the main brief visible when a subagent marks it ready', () => {
    const result = getBriefProgress({
      brief_state: {
        fields: {
          ...emptyFields,
          project_name: { value: '已确认项目' },
        },
        readiness: { level: 'provisional' },
      },
    })

    expect(result.status).toBe('ready')
    expect(result.statusLabel).toBe('已达到执行条件')
  })
})
