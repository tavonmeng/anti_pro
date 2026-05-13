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

export const saveAiChatSessions = (userId: string | undefined, sessions: AiChatSavedSession[]) => {
  const normalized = sessions
    .filter(session => session?.id && Array.isArray(session.messages))
    .map(session => ({
      ...session,
      title: session.title || makeAiChatSessionTitle(session.messages),
      updatedAt: session.updatedAt || getSessionSortValue(session),
    }))
    .sort((a, b) => getSessionSortValue(b) - getSessionSortValue(a))

  localStorage.setItem(getAiChatHistoryKey(userId), JSON.stringify(normalized))
  window.dispatchEvent(new CustomEvent(AI_CHAT_HISTORY_EVENT))
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
