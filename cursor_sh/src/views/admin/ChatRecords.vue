<template>
  <div class="chat-records-page">
    <div class="page-header">
      <h2>📋 客户 AI 聊天记录</h2>
      <p class="page-desc">查看所有客户与 AI 助手的对话历史</p>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        class="search-input"
        v-model="searchKeyword"
        placeholder="搜索用户名、公司、手机号或对话内容..."
        clearable
        style="width: 360px"
        @keyup.enter="loadSessions"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="loadSessions">搜索</el-button>
      <el-button @click="searchKeyword = ''; loadSessions()">重置</el-button>
    </div>

    <!-- 会话列表 -->
    <el-table
      class="desktop-session-table"
      :data="sessions"
      v-loading="loading"
      stripe
      style="width: 100%; margin-top: 16px"
      @row-click="openSession"
      row-class-name="clickable-row"
    >
      <el-table-column label="用户" width="140">
        <template #default="{ row }">
          <div class="user-cell">
            <el-avatar :size="28" style="background: #409EFF; flex-shrink: 0">
              {{ (row.username || '?')[0] }}
            </el-avatar>
            <div class="user-meta">
              <span>{{ row.username || row.userId }}</span>
              <small v-if="row.phone">{{ row.phone }}</small>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="客户公司" width="180">
        <template #default="{ row }">
          <span>{{ row.company || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="对话主题" min-width="300">
        <template #default="{ row }">
          <span class="session-title">{{ row.title || '（无标题）' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="消息数" width="90" align="center">
        <template #default="{ row }">
          <el-tag type="info" size="small">{{ row.messageCount }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="业务类型" width="120">
        <template #default="{ row }">
          <el-tag :type="bizTypeTag(row.businessType)" size="small">
            {{ bizTypeLabel(row.businessType) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最后更新" width="170">
        <template #default="{ row }">
          {{ formatTime(row.updatedAt) }}
        </template>
      </el-table-column>
    </el-table>

    <div class="mobile-session-list" v-loading="loading">
      <button
        v-for="row in sessions"
        :key="row.id"
        class="mobile-session-item"
        type="button"
        @click="openSession(row)"
      >
        <span class="mobile-session-top">
          <span class="mobile-user">
            <el-avatar :size="30" style="background: #409EFF; flex-shrink: 0">
              {{ (row.username || '?')[0] }}
            </el-avatar>
            <span>
              <strong>{{ row.username || row.userId }}</strong>
              <small>{{ row.company || row.phone || '未填写客户信息' }}</small>
            </span>
          </span>
          <el-tag type="info" size="small">{{ row.messageCount }} 条</el-tag>
        </span>
        <span class="mobile-session-title">{{ row.title || '（无标题）' }}</span>
        <span class="mobile-session-bottom">
          <el-tag :type="bizTypeTag(row.businessType)" size="small">
            {{ bizTypeLabel(row.businessType) }}
          </el-tag>
          <span>{{ formatTime(row.updatedAt) }}</span>
        </span>
      </button>
      <el-empty v-if="!loading && sessions.length === 0" description="暂无聊天记录" :image-size="90" />
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="loadSessions"
      />
    </div>

    <!-- 对话详情弹窗 -->
    <el-drawer
      class="chat-record-drawer"
      v-model="drawerVisible"
      :title="`对话详情 — ${activeSession?.company || activeSession?.username || ''}`"
      size="600px"
      direction="rtl"
    >
      <div v-if="messagesLoading" class="loading-center">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-else class="chat-messages">
        <div
          v-for="(msg, idx) in activeMessages"
          :key="idx"
          :class="['chat-bubble', msg.role === 'user' ? 'bubble-user' : 'bubble-assistant']"
        >
          <div class="bubble-header">
            <span class="bubble-role">{{ msg.role === 'user' ? '👤 客户' : '🤖 AI 助手' }}</span>
            <span class="bubble-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="bubble-content" v-html="renderMarkdown(msg.content)"></div>
        </div>

        <div v-if="activeMessages.length === 0" class="empty-msg">
          暂无消息记录
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search, Loading } from '@element-plus/icons-vue'
import { chatHistoryApi } from '@/utils/api'
import { formatServerMonthDayTime } from '@/utils/time'

const sessions = ref<any[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const drawerVisible = ref(false)
const activeSession = ref<any>(null)
const activeMessages = ref<any[]>([])
const messagesLoading = ref(false)

const loadSessions = async () => {
  loading.value = true
  try {
    const res: any = await chatHistoryApi.adminGetSessions({
      page: currentPage.value,
      pageSize: pageSize.value,
      keyword: searchKeyword.value || undefined,
    })
    const d = Array.isArray(res?.data) ? res : (res?.data || res)
    sessions.value = d?.data || []
    total.value = d?.total || sessions.value.length
  } catch (e) {
    console.error('加载聊天记录失败:', e)
  } finally {
    loading.value = false
  }
}

const openSession = async (row: any) => {
  activeSession.value = row
  drawerVisible.value = true
  messagesLoading.value = true
  activeMessages.value = []
  try {
    const res: any = await chatHistoryApi.adminGetSessionMessages(row.id)
    activeMessages.value = Array.isArray(res) ? res : (res?.data || [])
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    messagesLoading.value = false
  }
}

const formatTime = (ts: string) => {
  return formatServerMonthDayTime(ts)
}

const bizTypeLabel = (t: string) => {
  const m: Record<string, string> = {
    ai_3d_custom: '裸眼3D定制',
    video_purchase: '成片购买',
    digital_art: '数字艺术',
  }
  return m[t] || t || '未知'
}

const bizTypeTag = (t: string) => {
  const m: Record<string, string> = {
    ai_3d_custom: '',
    video_purchase: 'success',
    digital_art: 'warning',
  }
  return m[t] || 'info'
}

const renderMarkdown = (text: string) => {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
.chat-records-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header h2 {
  margin: 0 0 4px;
  font-size: 20px;
}

.page-desc {
  color: #909399;
  font-size: 13px;
  margin: 0 0 16px;
}

.search-bar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.clickable-row {
  cursor: pointer;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  min-width: 0;
}

.user-meta small {
  color: #909399;
  font-size: 11px;
}

.session-title {
  font-size: 13px;
  color: #303133;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.mobile-session-list {
  display: none;
}

/* Drawer chat */
.loading-center {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 40px 0;
  color: #909399;
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px;
}

.chat-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  max-width: 90%;
}

.bubble-user {
  align-self: flex-end;
  background: #ECF5FF;
  border: 1px solid #D9ECFF;
}

.bubble-assistant {
  align-self: flex-start;
  background: #F4F4F5;
  border: 1px solid #E4E7ED;
}

.bubble-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.bubble-role {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.bubble-time {
  font-size: 11px;
  color: #C0C4CC;
}

.bubble-content {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  word-break: break-word;
}

.empty-msg {
  text-align: center;
  padding: 40px 0;
  color: #C0C4CC;
}

@media (max-width: 768px) {
  .chat-records-page {
    padding: 12px;
    max-width: none;
  }

  .page-header h2 {
    font-size: 18px;
    line-height: 1.35;
  }

  .page-desc {
    margin-bottom: 12px;
  }

  .search-bar {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }

  .search-input {
    width: 100% !important;
  }

  .search-bar .el-button {
    width: 100%;
    margin-left: 0;
  }

  .desktop-session-table {
    display: none;
  }

  .mobile-session-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 120px;
    margin-top: 14px;
  }

  .mobile-session-item {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
    padding: 12px;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    background: #fff;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }

  .mobile-session-top,
  .mobile-session-bottom,
  .mobile-user {
    display: flex;
    align-items: center;
  }

  .mobile-session-top,
  .mobile-session-bottom {
    justify-content: space-between;
    gap: 10px;
  }

  .mobile-user {
    min-width: 0;
    gap: 8px;
  }

  .mobile-user span {
    display: flex;
    flex-direction: column;
    min-width: 0;
    line-height: 1.35;
  }

  .mobile-user strong,
  .mobile-session-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-user strong {
    font-size: 14px;
    color: #303133;
  }

  .mobile-user small,
  .mobile-session-bottom span {
    color: #909399;
    font-size: 12px;
  }

  .mobile-session-title {
    display: block;
    color: #303133;
    font-size: 14px;
    font-weight: 500;
  }

  .pagination-wrapper {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .pagination-wrapper :deep(.el-pagination) {
    white-space: nowrap;
  }

  .chat-record-drawer :deep(.el-drawer.rtl) {
    width: 100% !important;
  }

  .chat-record-drawer :deep(.el-drawer__header) {
    margin-bottom: 8px;
    padding: 14px 14px 8px;
  }

  .chat-record-drawer :deep(.el-drawer__body) {
    padding: 0 10px 12px;
  }

  .chat-messages {
    gap: 12px;
    padding: 4px;
  }

  .chat-bubble {
    max-width: 96%;
    padding: 10px 12px;
    border-radius: 8px;
  }

  .bubble-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }

  .bubble-content {
    font-size: 13px;
    line-height: 1.65;
  }
}
</style>
