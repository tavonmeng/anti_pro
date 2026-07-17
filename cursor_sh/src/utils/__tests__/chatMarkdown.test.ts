import { describe, expect, it } from 'vitest'
import { renderChatMarkdown } from '../chatMarkdown'

describe('renderChatMarkdown', () => {
  it('renders common chat markdown structures', () => {
    const html = renderChatMarkdown([
      '## 阶段性结论',
      '',
      '**成立点**',
      '',
      '- 主体明确',
      '- 适合大屏传播',
      '',
      '`brief_agent` 继续处理。',
    ].join('\n'))

    expect(html).toContain('<h2>阶段性结论</h2>')
    expect(html).toContain('<strong>成立点</strong>')
    expect(html).toContain('<ul>')
    expect(html).toContain('<li>主体明确</li>')
    expect(html).toContain('<code>brief_agent</code>')
  })

  it('renders tables and opens safe links in a new tab', () => {
    const html = renderChatMarkdown([
      '| 字段 | 状态 |',
      '| --- | --- |',
      '| 屏幕规格 | 待补充 |',
      '',
      '[查看资料](https://example.com/spec)',
    ].join('\n'))

    expect(html).toContain('<table>')
    expect(html).toContain('<td>屏幕规格</td>')
    expect(html).toContain('href="https://example.com/spec"')
    expect(html).toContain('target="_blank"')
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('does not execute raw HTML or unsafe link protocols', () => {
    const html = renderChatMarkdown([
      '<img src=x onerror="alert(1)">',
      '',
      '[危险链接](javascript:alert(1))',
    ].join('\n'))

    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img src=x onerror="alert(1)"&gt;')
    expect(html).not.toContain('href="javascript:')
  })
})
