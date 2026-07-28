import { beforeEach, describe, expect, it } from 'vitest'
import {
  applySeoForRoute,
  HOMEPAGE_DESCRIPTION,
  HOMEPAGE_ROBOTS,
  HOMEPAGE_TITLE,
  HOMEPAGE_URL
} from '../seo'

const metaContent = (selector: string) => (
  document.head.querySelector<HTMLMetaElement>(selector)?.content
)

describe('route SEO metadata', () => {
  beforeEach(() => {
    document.head.innerHTML = ''
    document.title = ''
  })

  it('restores indexable homepage metadata', () => {
    applySeoForRoute({ path: '/', name: 'Landing' })

    expect(document.title).toBe(HOMEPAGE_TITLE)
    expect(metaContent('meta[name="description"]')).toBe(HOMEPAGE_DESCRIPTION)
    expect(metaContent('meta[name="robots"]')).toBe(HOMEPAGE_ROBOTS)
    expect(document.head.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(HOMEPAGE_URL)
  })

  it('removes the homepage canonical and applies noindex outside the landing page', () => {
    applySeoForRoute({ path: '/', name: 'Landing' })
    applySeoForRoute({ path: '/login', name: 'Login' })

    expect(document.title).toBe('用户登录｜Unique Vision')
    expect(metaContent('meta[name="robots"]')).toBe('noindex,nofollow')
    expect(document.head.querySelector('link[rel="canonical"]')).toBeNull()
    expect(metaContent('meta[property="og:url"]')).toContain('/login')
  })
})
