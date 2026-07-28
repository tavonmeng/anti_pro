export const HOMEPAGE_TITLE = '裸眼3D内容制作与AI 3D OOH创意平台｜Unique Vision'
export const HOMEPAGE_DESCRIPTION = 'Unique Vision 为品牌方、媒体方和商业空间提供裸眼3D视频制作、AI驱动3D OOH内容定制、户外LED大屏适配、FOOH传播与沉浸式数字艺术设计服务。'
export const HOMEPAGE_URL = 'https://www.uniquevisionx.com/'
export const HOMEPAGE_IMAGE = 'https://www.uniquevisionx.com/video-library-images/2.jpg'
export const HOMEPAGE_ROBOTS = 'index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1'

type SeoRoute = {
  path: string
  name?: string | symbol | null
}

const routeTitles: Record<string, string> = {
  Login: '用户登录｜Unique Vision',
  Register: '受邀注册｜Unique Vision',
  AdminLogin: '管理后台登录｜Unique Vision',
  ContractorLogin: '创作者登录｜Unique Vision',
  ContractorRegister: '创作者注册｜Unique Vision'
}

const upsertMeta = (attribute: 'name' | 'property', key: string, content: string) => {
  let element = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`)
  if (!element) {
    element = document.createElement('meta')
    element.setAttribute(attribute, key)
    document.head.appendChild(element)
  }
  element.setAttribute('content', content)
}

const setCanonical = (href?: string) => {
  const canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]')
  if (!href) {
    canonical?.remove()
    return
  }

  const element = canonical || document.createElement('link')
  element.setAttribute('rel', 'canonical')
  element.setAttribute('href', href)
  if (!canonical) document.head.appendChild(element)
}

const routeUrl = (path: string) => {
  if (typeof window === 'undefined') return path
  return new URL(path, window.location.origin).href
}

export const applySeoForRoute = ({ path, name }: SeoRoute) => {
  const isHomepage = path === '/'

  if (isHomepage) {
    document.title = HOMEPAGE_TITLE
    upsertMeta('name', 'description', HOMEPAGE_DESCRIPTION)
    upsertMeta('name', 'robots', HOMEPAGE_ROBOTS)
    upsertMeta('property', 'og:title', HOMEPAGE_TITLE)
    upsertMeta('property', 'og:description', HOMEPAGE_DESCRIPTION)
    upsertMeta('property', 'og:url', HOMEPAGE_URL)
    upsertMeta('property', 'og:image', HOMEPAGE_IMAGE)
    upsertMeta('name', 'twitter:title', HOMEPAGE_TITLE)
    upsertMeta('name', 'twitter:description', HOMEPAGE_DESCRIPTION)
    upsertMeta('name', 'twitter:image', HOMEPAGE_IMAGE)
    setCanonical(HOMEPAGE_URL)
    return
  }

  const routeName = name == null ? '' : String(name)
  const title = routeTitles[routeName] || 'Unique Vision 创作协作平台'
  const description = '登录或进入 Unique Vision 创作协作平台。'

  document.title = title
  upsertMeta('name', 'description', description)
  upsertMeta('name', 'robots', 'noindex,nofollow')
  upsertMeta('property', 'og:title', title)
  upsertMeta('property', 'og:description', description)
  upsertMeta('property', 'og:url', routeUrl(path))
  upsertMeta('name', 'twitter:title', title)
  upsertMeta('name', 'twitter:description', description)
  setCanonical()
}
