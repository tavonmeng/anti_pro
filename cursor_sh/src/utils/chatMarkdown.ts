import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { normalizeAssistantMarkdown } from './assistantMarkdown'

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const allowedTags = [
  'p',
  'br',
  'strong',
  'em',
  's',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'ul',
  'ol',
  'li',
  'a',
  'code',
  'pre',
  'blockquote',
  'hr',
  'table',
  'thead',
  'tbody',
  'tr',
  'th',
  'td',
]

export const renderChatMarkdown = (text: string) => {
  if (!text) return ''

  const sanitized = DOMPurify.sanitize(
    markdown.render(normalizeAssistantMarkdown(text)),
    {
      ALLOWED_TAGS: allowedTags,
      ALLOWED_ATTR: ['href', 'target', 'rel'],
    },
  )

  const template = document.createElement('template')
  template.innerHTML = sanitized
  template.content.querySelectorAll('a[href]').forEach((link) => {
    link.setAttribute('target', '_blank')
    link.setAttribute('rel', 'noopener noreferrer')
  })
  return template.innerHTML
}
