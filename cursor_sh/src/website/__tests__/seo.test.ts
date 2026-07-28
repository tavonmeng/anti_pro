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
    expect(robots).toContain('Disallow: /api/')
    expect(robots).not.toContain('Disallow: /user/')
    expect(robots).toContain('Sitemap: https://www.uniquevisionx.com/sitemap.xml')
  })

  it('publishes a valid sitemap for the homepage', () => {
    const sitemap = read('public/sitemap.xml')

    expect(sitemap).toContain('<urlset')
    expect(sitemap).toContain('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"')
    expect(sitemap).toContain('xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"')
    expect(sitemap).toContain('<loc>https://www.uniquevisionx.com/</loc>')
    expect(sitemap).toContain('<lastmod>2026-07-16</lastmod>')
    expect(sitemap).toContain('<image:loc>https://www.uniquevisionx.com/video-library-images/2.jpg</image:loc>')
    expect(sitemap).toContain('<priority>1.0</priority>')
  })

  it('includes homepage metadata for search and social previews', () => {
    const html = read('index.html')

    expect(html).toContain('<title>裸眼3D内容制作与AI 3D OOH创意平台｜Unique Vision</title>')
    expect(html).toContain('name="description"')
    expect(html).toContain('裸眼3D视频制作、AI驱动3D OOH内容定制')
    expect(html).toContain('rel="canonical" href="https://www.uniquevisionx.com/"')
    expect(html).toContain('rel="preload" as="image" href="/video-library-images/2.jpg"')
    expect(html).toContain('property="og:title"')
    expect(html).toContain('property="og:image:width" content="1691"')
    expect(html).toContain('name="twitter:card"')
    expect(html).toContain('"@type": "Organization"')
    expect(html).toContain('"@type": "WebPage"')
    expect(html).toContain('"@type": "Service"')
  })

  it('provides meaningful homepage content before JavaScript mounts', () => {
    const html = read('index.html')

    expect(html).toContain('<main class="seo-fallback">')
    expect(html).toContain('<h1>裸眼3D内容制作与AI驱动3D OOH创意平台</h1>')
    expect(html).toContain('<h2 id="fallback-services-title">核心内容制作服务</h2>')
    expect(html).toContain('support@uniquevisionx.com')
  })

  it('publishes the website ICP record in the rendered and fallback footers', () => {
    const html = read('index.html')
    const footer = read('src/website/sections/TheFooter.vue')

    expect(html).toContain('京ICP备2026029893号-1')
    expect(html).toContain('href="https://beian.miit.gov.cn/"')
    expect(footer).toContain('京ICP备2026029893号-1')
    expect(footer).toContain('href="https://beian.miit.gov.cn/"')
  })

  it('uses a single descriptive Chinese homepage h1 and ordered section headings', () => {
    const hero = read('src/website/sections/HeroSection.vue')
    const intro = read('src/website/sections/IntroSection.vue')
    const brands = read('src/website/sections/BrandsSection.vue')
    const contact = read('src/website/sections/ContactSection.vue')

    expect(hero).toContain('<h1 class="visually-hidden">裸眼3D内容制作与AI驱动3D OOH创意平台</h1>')
    expect(hero).not.toContain('<h1 class="hero-title')
    expect(intro).toContain('<h2 id="services-heading"')
    expect(intro).not.toContain('<h1 class="main-heading">')
    expect(brands).toContain('<h2 id="brands-heading"')
    expect(contact).toContain('<h2 id="contact-heading"')
  })

  it('marks private SPA routes as noindex and returns 404 for unknown public paths', () => {
    const externalNginx = read('nginx.external.conf')
    const internalNginx = read('nginx.internal.conf')

    expect(externalNginx).toContain('if ($host = uniquevisionx.com)')
    expect(externalNginx).toContain('return 308 https://www.uniquevisionx.com$request_uri;')
    expect(externalNginx).toContain('add_header X-Robots-Tag "noindex, nofollow" always;')
    expect(externalNginx).toContain('try_files $uri $uri/ =404;')
    expect(internalNginx).toContain('add_header X-Robots-Tag "noindex, nofollow" always;')
  })
})
