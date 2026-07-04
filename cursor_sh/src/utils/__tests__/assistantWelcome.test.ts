import { describe, expect, it } from 'vitest'
import { getAssistantWelcomeCopy, welcomeQuickStarts } from '../assistantWelcome'

describe('assistant welcome experience', () => {
  it('uses a consultative welcome copy for media customers', () => {
    const copy = getAssistantWelcomeCopy('media')

    expect(copy.title).toBe('您好，我是 Unique Vision AI 的创意提案总监。')
    expect(copy.description).toContain('您可以先从一句话')
    expect(copy.description).toContain('我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多媒体方客户提供过高品质的裸眼3D视觉内容解决方案。')
    expect(copy.description).toContain('一个还没完全成形的创意')
    expect(copy.description).toContain('帮您判断方向')
    expect(copy.description).toContain('逐步补齐')
    expect(copy.description).not.toContain('\n\n')
    expect(copy.description).toContain('可执行 Brief')
  })

  it('defines natural quick-start prompts instead of exposed feature modes', () => {
    expect(welcomeQuickStarts).toHaveLength(4)
    expect(welcomeQuickStarts.map(item => item.label)).toEqual([
      '我想做一个3D视频',
      '帮我评估一个创意',
      '基于图片给点方向',
      '查看我的订单进展',
    ])
    expect(welcomeQuickStarts.map(item => item.kind)).toEqual([
      'create',
      'evaluate',
      'image',
      'order',
    ])
    expect(welcomeQuickStarts.every(item => item.prompt.length > item.label.length)).toBe(true)
    expect(welcomeQuickStarts.every(item => !('mode' in item))).toBe(true)
  })

  it('uses the 3D video quick start to begin brief collection instead of creative generation', () => {
    const createPrompt = welcomeQuickStarts.find(item => item.kind === 'create')?.prompt || ''

    expect(createPrompt).toContain('3D视频')
    expect(createPrompt).toContain('需求')
    expect(createPrompt).not.toMatch(/大概方向|创意方向|创意方案|生成|出一版|来一版/)
  })
})
