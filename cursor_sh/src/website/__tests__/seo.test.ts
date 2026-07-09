import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(__dirname, '../../..')

const read = (path: string) => readFileSync(resolve(root, path), 'utf-8')

describe('homepage SEO files', () => {
  it('exposes crawl directives and sitemap location', () => {
    const robots = read('public/robots.txt')

    expect(robots).toContain('User-agent: *')
    expect(robots).toContain('Allow: /')
    expect(robots).toContain('Disallow: /admin/')
    expect(robots).toContain('Sitemap: https://uniquevisionx.com/sitemap.xml')
  })

  it('publishes a valid sitemap for the homepage', () => {
    const sitemap = read('public/sitemap.xml')

    expect(sitemap).toContain('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    expect(sitemap).toContain('<loc>https://uniquevisionx.com/</loc>')
    expect(sitemap).toContain('<priority>1.0</priority>')
  })

  it('includes homepage metadata for search and social previews', () => {
    const html = read('index.html')

    expect(html).toContain('<title>Unique Vision｜裸眼3D内容制作与AI驱动3D OOH内容平台</title>')
    expect(html).toContain('name="description"')
    expect(html).toContain('裸眼3D内容制作、AI驱动3D OOH创意定制')
    expect(html).toContain('rel="canonical" href="https://uniquevisionx.com/"')
    expect(html).toContain('property="og:title"')
    expect(html).toContain('name="twitter:card"')
    expect(html).toContain('"@type": "Organization"')
    expect(html).toContain('"@type": "Service"')
  })

  it('uses a descriptive Chinese homepage h1 without changing the hero slogan into h1', () => {
    const hero = read('src/website/sections/HeroSection.vue')
    const intro = read('src/website/sections/IntroSection.vue')

    expect(hero).not.toContain('<h1 class="hero-title')
    expect(intro).toContain('<h1 class="main-heading">')
    expect(intro).toContain('裸眼3D内容制作与3D OOH内容平台')
  })
})
