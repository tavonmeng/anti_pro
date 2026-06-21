import { formatServerMonthDayTime, formatServerShortTime } from './time'

export type AiAgentSessionMeta = {
  agentKey: string
  agentLabel?: string
  sessionType: string
  businessType?: string
  agentMode?: string
  routeFullPath?: string
}

export type AiChatSavedSession = {
  id: string
  title?: string
  messages: any[]
  mode?: string | null
  agentKey?: string
  agentLabel?: string
  sessionType?: string
  businessType?: string
  agentMode?: string
  routeFullPath?: string
  stateSnapshot?: Record<string, any> | null
  savedAt: string
  updatedAt?: number
}

export type AiChatRemoteSession = {
  id: string
  title?: string
  sessionType?: string
  businessType?: string
  messageCount?: number
  createdAt?: string
  updatedAt?: string
}

export const AI_CHAT_HISTORY_EVENT = 'ai-chat-history-updated'

export const getAiChatHistoryKey = (userId?: string) => {
  return `ai_chat_session_${userId || 'anonymous'}`
}

export const getSessionSortValue = (session: Pick<AiChatSavedSession, 'id' | 'updatedAt'>) => {
  return session.updatedAt || Number(String(session.id).split('_')[0]) || 0
}

export const makeAiChatSessionTitle = (messages: any[] = [], fallback = '新的对话') => {
  const firstUser = messages.find(m => m?.role === 'user' && !m?.isContextCarryOver)
  const raw = String(firstUser?.content || fallback)
    .replace(/\[已上传[^\]]+\]\s*/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  if (!raw) return fallback
  return raw.length > 24 ? `${raw.slice(0, 24)}...` : raw
}

const formatRemoteMessageTime = (value?: string) => {
  return formatServerShortTime(value, '')
}

export const getAiChatAgentMeta = (sessionType?: string, businessType?: string) => {
  if (sessionType === 'order_query') {
    return { agentKey: 'order_query', agentLabel: '订单查询', mode: 'order_query' }
  }
  if (sessionType === 'business_intro') {
    return { agentKey: 'business_intro', agentLabel: '业务介绍', mode: 'business_intro' }
  }
  if (sessionType === 'case_intro') {
    return { agentKey: 'business_intro', agentLabel: '咨询顾问', mode: 'business_intro' }
  }
  if (sessionType === 'requirement') {
    const type = businessType || 'ai_3d_custom'
    const labels: Record<string, string> = {
      ai_3d_custom: 'AI驱动3D OOH内容定制',
      video_purchase: '3D OOH数字内容资源库',
      digital_art: '数字艺术与沉浸式视觉设计',
    }
    return {
      agentKey: `requirement_${type}`,
      agentLabel: labels[type] || '需求收集',
      mode: 'order_create',
    }
  }
  return { agentKey: 'general', agentLabel: '通用问答', mode: null }
}

export const createAiChatSessionFromRemote = (
  remote: AiChatRemoteSession,
  messages: any[] = [],
): AiChatSavedSession => {
  const normalizedMessages = messages
    .filter(message => message?.role === 'user' || message?.role === 'assistant')
    .map(message => ({
      client_message_id: message.client_message_id || message.clientMessageId,
      role: message.role,
      content: message.content || '',
      timestamp: formatRemoteMessageTime(message.timestamp),
      attachments: message.metadata?.attachments || undefined,
    }))

  const updatedAt = remote.updatedAt ? Date.parse(remote.updatedAt) : Date.now()
  const meta = getAiChatAgentMeta(remote.sessionType, remote.businessType)

  return {
    id: remote.id,
    title: remote.title || makeAiChatSessionTitle(normalizedMessages),
    messages: normalizedMessages,
    mode: meta.mode,
    agentKey: meta.agentKey,
    agentLabel: meta.agentLabel,
    sessionType: remote.sessionType || 'general',
    businessType: remote.businessType || 'ai_3d_custom',
    stateSnapshot: null,
    updatedAt: Number.isFinite(updatedAt) ? updatedAt : Date.now(),
    savedAt: formatServerMonthDayTime(new Date(Number.isFinite(updatedAt) ? updatedAt : Date.now()).toISOString()),
  }
}

export const loadAiChatSessions = (userId?: string): AiChatSavedSession[] => {
  try {
    const raw = localStorage.getItem(getAiChatHistoryKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    const sessions = Array.isArray(parsed) ? parsed : [parsed]
    return sessions
      .filter(session => session?.id && Array.isArray(session.messages))
      .map(session => ({
        ...session,
        title: session.title || makeAiChatSessionTitle(session.messages),
        updatedAt: session.updatedAt || getSessionSortValue(session),
      }))
      .sort((a, b) => getSessionSortValue(b) - getSessionSortValue(a))
  } catch {
    return []
  }
}

export const saveAiChatSessions = (
  userId: string | undefined,
  sessions: AiChatSavedSession[],
  notify = true,
) => {
  const normalized = sessions
    .filter(session => session?.id && Array.isArray(session.messages))
    .map(session => ({
      ...session,
      title: session.title || makeAiChatSessionTitle(session.messages),
      updatedAt: session.updatedAt || getSessionSortValue(session),
    }))
    .sort((a, b) => getSessionSortValue(b) - getSessionSortValue(a))

  localStorage.setItem(getAiChatHistoryKey(userId), JSON.stringify(normalized))
  if (notify) {
    window.dispatchEvent(new CustomEvent(AI_CHAT_HISTORY_EVENT))
  }
  return normalized
}

export const upsertAiChatSession = (
  userId: string | undefined,
  session: AiChatSavedSession,
  limit = 30,
) => {
  const sessions = loadAiChatSessions(userId)
  const nextSession = {
    ...session,
    title: session.title || makeAiChatSessionTitle(session.messages),
    updatedAt: session.updatedAt || Date.now(),
  }
  const existingIndex = sessions.findIndex(item => item.id === nextSession.id)
  if (existingIndex >= 0) {
    sessions[existingIndex] = nextSession
  } else {
    sessions.push(nextSession)
  }
  const sorted = sessions.sort((a, b) => getSessionSortValue(b) - getSessionSortValue(a))
  return saveAiChatSessions(userId, sorted.slice(0, limit))
}

export const deleteAiChatSession = (userId: string | undefined, sessionId: string) => {
  const sessions = loadAiChatSessions(userId).filter(session => session.id !== sessionId)
  return saveAiChatSessions(userId, sessions)
}
