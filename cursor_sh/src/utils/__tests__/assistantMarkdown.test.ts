import MarkdownIt from 'markdown-it'
import { describe, expect, it } from 'vitest'
import { normalizeAssistantMarkdown } from '../assistantMarkdown'

describe('normalizeAssistantMarkdown', () => {
  it('keeps Chinese quoted bold spans renderable by markdown-it', () => {
    const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })
    const text = '您确认一下，这次的观看动线和受众定位是否就按**“利用 L 型折角表现空间纵深，主要面向现场年轻游客及路人”**来规划？'

    const html = markdown.render(normalizeAssistantMarkdown(text))

    expect(html).toContain('按“<strong>利用 L 型折角表现空间纵深，主要面向现场年轻游客及路人</strong>”来规划')
    expect(html).not.toContain('**“')
  })

  it('does not rewrite ordinary bold spans', () => {
    expect(normalizeAssistantMarkdown('按**利用 L 型折角表现空间纵深**来规划？')).toBe(
      '按**利用 L 型折角表现空间纵深**来规划？',
    )
  })
})
