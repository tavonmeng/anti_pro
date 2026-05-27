export const WORKSPACE_THEME_STORAGE_KEY = 'uv_workspace_theme_debug'

export const DEFAULT_WORKSPACE_THEME = {
  pageText: '#1B1B1C',
  mutedText: '#646A78',
  divider: '#E5E5E5',
  aiAgentBg: '#E9D5BD',
  aiAgentTitle: '#1B1B1C',
  aiAgentInputBg: '#FFFFFF',
  aiAgentInputText: '#1B1B1C',
  aiAgentPlaceholder: '#A0A4AE',
  sendButtonBg: '#666666',
  sendButtonHover: '#555555',
  sendButtonText: '#FFFFFF',
  sendDot: '#000000',
  businessTitle: '#1B1B1C',
  businessSubtitle: '#646A78',
  serviceImageBorder: '#DADADA',
  serviceImageHoverBorder: '#B0B0B0',
  serviceBadgeBg: '#000000',
  serviceBadgeText: '#FFFFFF',
  serviceTitle: '#1B1B1C',
  serviceSubtitle: '#414754',
  serviceIntro: '#646A78',
  serviceTagBorder: '#C1C6D6',
  serviceTagText: '#414754',
  serviceFooter: '#A0522D',
  serviceArrow: '#414754',
  sidebarActive: '#A0522D',
  sidebarActiveBg: '#FFFFFF',
  sidebarHoverBg: '#EAE7E7',
  actionButtonBg: '#A0522D',
  actionButtonHover: '#8F4527',
  actionButtonText: '#FFFFFF',
  notificationBadge: '#A0522D',
  unreadText: '#A0522D',
  moduleActiveBg: '#F3E7E1',
  moduleActiveMark: '#A0522D',
  moduleTitle: '#414754',
  moduleIntroTitle: '#1F2329',
  moduleIntroText: '#6C707D',
  aiChatAccent: '#A0522D',
  aiChatButtonBg: '#666666',
  aiChatButtonHover: '#555555'
} as const

export type WorkspaceThemeKey = keyof typeof DEFAULT_WORKSPACE_THEME
export type WorkspaceTheme = Record<WorkspaceThemeKey, string>

const THEME_VARIABLES: Record<WorkspaceThemeKey, string> = {
  pageText: '--uv-ws-page-text',
  mutedText: '--uv-ws-muted-text',
  divider: '--uv-ws-divider',
  aiAgentBg: '--uv-ws-ai-agent-bg',
  aiAgentTitle: '--uv-ws-ai-agent-title',
  aiAgentInputBg: '--uv-ws-ai-agent-input-bg',
  aiAgentInputText: '--uv-ws-ai-agent-input-text',
  aiAgentPlaceholder: '--uv-ws-ai-agent-placeholder',
  sendButtonBg: '--uv-ws-send-button-bg',
  sendButtonHover: '--uv-ws-send-button-hover',
  sendButtonText: '--uv-ws-send-button-text',
  sendDot: '--uv-ws-send-dot',
  businessTitle: '--uv-ws-business-title',
  businessSubtitle: '--uv-ws-business-subtitle',
  serviceImageBorder: '--uv-ws-service-image-border',
  serviceImageHoverBorder: '--uv-ws-service-image-hover-border',
  serviceBadgeBg: '--uv-ws-service-badge-bg',
  serviceBadgeText: '--uv-ws-service-badge-text',
  serviceTitle: '--uv-ws-service-title',
  serviceSubtitle: '--uv-ws-service-subtitle',
  serviceIntro: '--uv-ws-service-intro',
  serviceTagBorder: '--uv-ws-service-tag-border',
  serviceTagText: '--uv-ws-service-tag-text',
  serviceFooter: '--uv-ws-service-footer',
  serviceArrow: '--uv-ws-service-arrow',
  sidebarActive: '--uv-ws-sidebar-active',
  sidebarActiveBg: '--uv-ws-sidebar-active-bg',
  sidebarHoverBg: '--uv-ws-sidebar-hover-bg',
  actionButtonBg: '--uv-ws-action-button-bg',
  actionButtonHover: '--uv-ws-action-button-hover',
  actionButtonText: '--uv-ws-action-button-text',
  notificationBadge: '--uv-ws-notification-badge',
  unreadText: '--uv-ws-unread-text',
  moduleActiveBg: '--uv-ws-module-active-bg',
  moduleActiveMark: '--uv-ws-module-active-mark',
  moduleTitle: '--uv-ws-module-title',
  moduleIntroTitle: '--uv-ws-module-intro-title',
  moduleIntroText: '--uv-ws-module-intro-text',
  aiChatAccent: '--uv-ws-ai-chat-accent',
  aiChatButtonBg: '--uv-ws-ai-chat-button-bg',
  aiChatButtonHover: '--uv-ws-ai-chat-button-hover'
}

export const WORKSPACE_THEME_FIELDS: Array<{
  key: WorkspaceThemeKey
  label: string
  group: string
  description: string
}> = [
  { key: 'aiAgentBg', label: '智能体背景色', group: 'AI 智能体', description: '首页顶部 AI 智能体区域底色' },
  { key: 'aiAgentTitle', label: '智能体标题文字', group: 'AI 智能体', description: 'UniqueVision AI 智能体标题颜色' },
  { key: 'aiAgentInputBg', label: '输入框背景', group: 'AI 智能体', description: '智能体输入框底色' },
  { key: 'aiAgentInputText', label: '输入框文字', group: 'AI 智能体', description: '输入框内文字颜色' },
  { key: 'aiAgentPlaceholder', label: '输入提示文字', group: 'AI 智能体', description: '动态提示语颜色' },
  { key: 'sendButtonBg', label: '发送按钮', group: 'AI 智能体', description: '发送按钮默认底色' },
  { key: 'sendButtonHover', label: '发送按钮悬浮', group: 'AI 智能体', description: '发送按钮 hover 底色' },
  { key: 'sendButtonText', label: '发送按钮文字', group: 'AI 智能体', description: '发送按钮文字颜色' },
  { key: 'sendDot', label: '发送旁圆片', group: 'AI 智能体', description: '发送按钮旁小圆片颜色' },
  { key: 'businessTitle', label: '业务区标题', group: '业务模块', description: '业务菜单标题颜色' },
  { key: 'businessSubtitle', label: '业务区副标题', group: '业务模块', description: '平台服务体系文字颜色' },
  { key: 'serviceImageBorder', label: '业务图片边框', group: '业务模块', description: '6 个业务模块图片边框' },
  { key: 'serviceImageHoverBorder', label: '图片悬浮边框', group: '业务模块', description: '业务图片 hover 边框' },
  { key: 'serviceBadgeBg', label: '业务标题底色', group: '业务模块', description: '图片上的黑底标题底色' },
  { key: 'serviceBadgeText', label: '业务标题文字', group: '业务模块', description: '图片上标题文字颜色' },
  { key: 'serviceTitle', label: '业务名称', group: '业务模块', description: '服务名称文字颜色' },
  { key: 'serviceSubtitle', label: '业务副标题', group: '业务模块', description: '服务副标题文字颜色' },
  { key: 'serviceIntro', label: '业务模块介绍', group: '业务模块', description: '服务描述文字颜色' },
  { key: 'serviceTagBorder', label: '业务标签边框', group: '业务模块', description: '功能标签描边颜色' },
  { key: 'serviceTagText', label: '业务标签文字', group: '业务模块', description: '功能标签文字颜色' },
  { key: 'serviceFooter', label: '业务底部文字', group: '业务模块', description: '卡片底部引导文字颜色' },
  { key: 'serviceArrow', label: '业务箭头', group: '业务模块', description: '业务卡片右下角箭头颜色' },
  { key: 'sidebarActive', label: '菜单选中名称', group: '菜单与功能区', description: '工作台、订单、草稿箱选中态文字' },
  { key: 'sidebarActiveBg', label: '菜单选中背景', group: '菜单与功能区', description: '左侧菜单选中态底色' },
  { key: 'sidebarHoverBg', label: '菜单悬浮背景', group: '菜单与功能区', description: '左侧菜单 hover 底色' },
  { key: 'actionButtonBg', label: '功能区按钮', group: '菜单与功能区', description: '去认证、查看订单等按钮底色' },
  { key: 'actionButtonHover', label: '功能按钮悬浮', group: '菜单与功能区', description: '功能按钮 hover 底色' },
  { key: 'actionButtonText', label: '功能按钮文字', group: '菜单与功能区', description: '功能按钮文字颜色' },
  { key: 'notificationBadge', label: '通知数字点', group: '通知与状态', description: '通知、草稿箱数量徽标底色' },
  { key: 'unreadText', label: '未读提示文字', group: '通知与状态', description: '公告未读和通知未读强调色' },
  { key: 'moduleActiveBg', label: '二级模块选中背景', group: '二级菜单', description: '业务模块折叠菜单选中底色' },
  { key: 'moduleActiveMark', label: '二级模块选中标记', group: '二级菜单', description: '二级菜单选中竖线和箭头' },
  { key: 'moduleTitle', label: '二级模块名称', group: '二级菜单', description: '折叠菜单模块名称文字' },
  { key: 'moduleIntroTitle', label: '二级业务标题', group: '二级菜单', description: '展开后的业务介绍标题' },
  { key: 'moduleIntroText', label: '二级业务介绍', group: '二级菜单', description: '展开后的业务介绍正文' },
  { key: 'aiChatAccent', label: '对话强调色', group: 'AI 对话区', description: '对话内选中、上传、表单焦点等强调色' },
  { key: 'aiChatButtonBg', label: '对话按钮', group: 'AI 对话区', description: '对话区主按钮底色' },
  { key: 'aiChatButtonHover', label: '对话按钮悬浮', group: 'AI 对话区', description: '对话区主按钮 hover 底色' },
  { key: 'pageText', label: '页面主文字', group: '全局文字', description: 'workspace 主要文字颜色' },
  { key: 'mutedText', label: '页面辅助文字', group: '全局文字', description: 'workspace 辅助说明文字颜色' },
  { key: 'divider', label: '分割线', group: '全局文字', description: 'workspace 分割线颜色' }
]

const isHexColor = (value: unknown): value is string => {
  return typeof value === 'string' && /^#[0-9a-fA-F]{6}$/.test(value.trim())
}

export const normalizeWorkspaceTheme = (theme?: Partial<Record<WorkspaceThemeKey, string>>): WorkspaceTheme => {
  const normalized = { ...DEFAULT_WORKSPACE_THEME } as WorkspaceTheme
  if (!theme) return normalized

  for (const key of Object.keys(DEFAULT_WORKSPACE_THEME) as WorkspaceThemeKey[]) {
    const value = theme[key]
    if (isHexColor(value)) normalized[key] = value.trim().toUpperCase()
  }

  return normalized
}

export const loadWorkspaceTheme = (): WorkspaceTheme => {
  if (typeof window === 'undefined') return normalizeWorkspaceTheme()
  try {
    const raw = window.localStorage.getItem(WORKSPACE_THEME_STORAGE_KEY)
    return normalizeWorkspaceTheme(raw ? JSON.parse(raw) : undefined)
  } catch (error) {
    return normalizeWorkspaceTheme()
  }
}

export const applyWorkspaceTheme = (theme: WorkspaceTheme = loadWorkspaceTheme()) => {
  if (typeof document === 'undefined') return
  const normalized = normalizeWorkspaceTheme(theme)
  for (const key of Object.keys(THEME_VARIABLES) as WorkspaceThemeKey[]) {
    document.documentElement.style.setProperty(THEME_VARIABLES[key], normalized[key])
  }
}

export const saveWorkspaceTheme = (theme: WorkspaceTheme) => {
  const normalized = normalizeWorkspaceTheme(theme)
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(WORKSPACE_THEME_STORAGE_KEY, JSON.stringify(normalized))
  }
  applyWorkspaceTheme(normalized)
  return normalized
}

export const resetWorkspaceTheme = () => {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(WORKSPACE_THEME_STORAGE_KEY)
  }
  const defaults = normalizeWorkspaceTheme()
  applyWorkspaceTheme(defaults)
  return defaults
}
