const DISPLAY_TIME_ZONE = 'Asia/Shanghai'

const hasTimezone = (value: string) => {
  return /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value.trim())
}

const normalizeServerTime = (value: string) => {
  const trimmed = value.trim()
  if (!trimmed) return trimmed
  if (hasTimezone(trimmed)) return trimmed
  if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(trimmed)) {
    return `${trimmed.replace(' ', 'T')}+08:00`
  }
  return trimmed
}

export const parseServerTime = (value?: string | null) => {
  if (!value) return null
  const date = new Date(normalizeServerTime(value))
  return Number.isNaN(date.getTime()) ? null : date
}

export const formatServerTime = (value?: string | null, fallback = '-') => {
  const date = parseServerTime(value)
  if (!date) return value || fallback
  return date.toLocaleString('zh-CN', {
    timeZone: DISPLAY_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

export const formatServerShortTime = (value?: string | null, fallback = '') => {
  const date = parseServerTime(value)
  if (!date) return value || fallback
  return date.toLocaleTimeString('zh-CN', {
    timeZone: DISPLAY_TIME_ZONE,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

export const formatServerMonthDayTime = (value?: string | null, fallback = '-') => {
  const date = parseServerTime(value)
  if (!date) return value || fallback
  return date.toLocaleString('zh-CN', {
    timeZone: DISPLAY_TIME_ZONE,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

export const formatServerRelativeTime = (value?: string | null, fallback = '-') => {
  const date = parseServerTime(value)
  if (!date) return value || fallback

  const diff = Date.now() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return formatServerTime(value, fallback)
}
