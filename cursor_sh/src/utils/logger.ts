/**
 * 前端操作日志工具
 *
 * 职责：
 * - 提供 logAction() 方法记录用户交互行为
 * - 批量缓冲发送，减少网络请求频次
 * - 页面卸载时通过 sendBeacon 发送残余日志
 * - 自动携带用户信息和设备上下文
 */

import { useAuthStore } from '@/stores/auth'

// ============================================================
// 配置
// ============================================================
const API_BASE = '/api/logs'
const BATCH_SIZE = 5       // 积攒多少条批量发送
const FLUSH_INTERVAL = 5000 // 最大缓冲时间 (ms)

// ============================================================
// Trace ID 生成
// ============================================================
function generateTraceId(): string {
  return Math.random().toString(36).substring(2, 10)
}

// ============================================================
// 日志条目类型
// ============================================================
interface LogEntry {
  module: string
  action: string
  trace_id: string
  payload?: Record<string, any>
}

// ============================================================
// ActionLogger 单例
// ============================================================
class ActionLogger {
  private buffer: LogEntry[] = []
  private timer: ReturnType<typeof setInterval> | null = null

  constructor() {
    // 定时 flush
    this.timer = setInterval(() => this.flush(), FLUSH_INTERVAL)

    // 页面卸载前 flush
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => this.flushSync())
      // 路由切换也触发
      window.addEventListener('pagehide', () => this.flushSync())
    }
  }

  /**
   * 记录一条用户操作日志
   * @param module  业务模块 (如 Workspace, Order, Auth, AI)
   * @param action  操作标识 (如 click_create_order, page_enter)
   * @param payload 额外上下文数据
   */
  logAction(module: string, action: string, payload?: Record<string, any>) {
    const entry: LogEntry = {
      module,
      action,
      trace_id: generateTraceId(),
      payload: {
        ...payload,
        pageUrl: window.location.pathname,
        timestamp: new Date().toISOString(),
      },
    }

    this.buffer.push(entry)

    // 达到批量阈值立即发送
    if (this.buffer.length >= BATCH_SIZE) {
      this.flush()
    }
  }

  /**
   * 异步批量发送缓冲中的日志
   */
  async flush() {
    if (this.buffer.length === 0) return

    const batch = [...this.buffer]
    this.buffer = []

    try {
      const authStore = useAuthStore()
      const token = authStore.token

      if (!token) return // 未登录不发送

      const url = batch.length === 1 ? API_BASE : `${API_BASE}/batch`
      const body = batch.length === 1 ? batch[0] : { logs: batch }

      await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })
    } catch (err) {
      // 日志发送失败不应影响用户体验，静默处理
      console.debug('[Logger] 日志发送失败:', err)
    }
  }

  /**
   * 同步发送（页面卸载时使用 sendBeacon）
   */
  flushSync() {
    if (this.buffer.length === 0) return

    try {
      const authStore = useAuthStore()
      const token = authStore.token
      if (!token) return

      const batch = [...this.buffer]
      this.buffer = []

      const url = batch.length === 1 ? API_BASE : `${API_BASE}/batch`
      const body = batch.length === 1 ? batch[0] : { logs: batch }

      // sendBeacon 不支持自定义 headers，使用 Blob
      const blob = new Blob([JSON.stringify(body)], { type: 'application/json' })
      navigator.sendBeacon(url, blob)
    } catch {
      // 静默
    }
  }

  /**
   * 清理定时器
   */
  destroy() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  }
}

// 导出单例
export const logger = new ActionLogger()
