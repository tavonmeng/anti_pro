<template>
  <div class="handoff-page">
    <div class="page-header">
      <h2>转人工客户</h2>
      <p class="page-desc">集中查看用户主动转人工后的客户线索、订单草稿与聊天记录</p>
    </div>

    <div class="toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索客户、手机号、公司或聊天内容..."
        clearable
        style="width: 360px"
        @keyup.enter="loadHandoffs"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px" @change="loadHandoffs">
        <el-option label="待跟进" value="pending" />
        <el-option label="已跟进" value="followed" />
      </el-select>
      <el-button type="primary" @click="loadHandoffs">搜索</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <el-table
      :data="handoffs"
      v-loading="loading"
      stripe
      style="width: 100%; margin-top: 16px"
      @row-click="openDetail"
      row-class-name="clickable-row"
    >
      <el-table-column label="客户" min-width="180">
        <template #default="{ row }">
          <div class="user-cell">
            <el-avatar :size="32" style="background: #409eff; flex-shrink: 0">
              {{ (row.username || '?')[0] }}
            </el-avatar>
            <div class="user-meta">
              <span>{{ row.username || row.userId }}</span>
              <small v-if="row.phone">{{ row.phone }}</small>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="公司" min-width="160">
        <template #default="{ row }">{{ row.company || '-' }}</template>
      </el-table-column>

      <el-table-column label="触发消息" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">{{ row.triggerMessage }}</template>
      </el-table-column>

      <el-table-column label="业务类型" width="130">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ bizTypeLabel(row.businessType) }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'followed' ? 'success' : 'warning'" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="更新时间" width="160">
        <template #default="{ row }">{{ formatTime(row.updatedAt) }}</template>
      </el-table-column>

      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click.stop="openDetail(row)">查看</el-button>
          <el-button
            size="small"
            :type="row.status === 'followed' ? 'warning' : 'success'"
            link
            @click.stop="toggleStatus(row)"
          >
            {{ row.status === 'followed' ? '标为待跟进' : '标为已跟进' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="loadHandoffs"
      />
    </div>

    <el-drawer
      v-model="drawerVisible"
      :title="`转人工详情 — ${activeHandoff?.company || activeHandoff?.username || ''}`"
      size="720px"
      direction="rtl"
    >
      <div v-if="detailLoading" class="loading-center">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-else-if="activeHandoff" class="detail">
        <section class="detail-section">
          <div class="section-title">客户信息</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="用户名">{{ activeHandoff.username || '-' }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ activeHandoff.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ activeHandoff.email || '-' }}</el-descriptions-item>
            <el-descriptions-item label="公司">{{ activeHandoff.company || '-' }}</el-descriptions-item>
            <el-descriptions-item label="业务">{{ bizTypeLabel(activeHandoff.businessType) }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ statusLabel(activeHandoff.status) }}</el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-section">
          <div class="section-header">
            <div class="section-title">草稿与跟进</div>
            <div class="section-actions">
              <el-button v-if="activeHandoff.draftOrderId" size="small" @click="goToDraft(activeHandoff.draftOrderId)">
                查看订单草稿
              </el-button>
              <el-button
                size="small"
                :type="activeHandoff.status === 'followed' ? 'warning' : 'success'"
                @click="toggleStatus(activeHandoff)"
              >
                {{ activeHandoff.status === 'followed' ? '标为待跟进' : '标为已跟进' }}
              </el-button>
            </div>
          </div>
          <div class="summary-grid">
            <div v-for="item in extractedItems" :key="item.key" class="summary-item">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>

        <section class="detail-section">
          <div class="section-title">聊天记录</div>
          <div class="chat-list">
            <div
              v-for="(msg, idx) in activeHandoff.chatSnapshot || []"
              :key="idx"
              :class="['chat-bubble', msg.role === 'user' ? 'bubble-user' : 'bubble-assistant']"
            >
              <div class="bubble-header">
                <span>{{ msg.role === 'user' ? '客户' : 'AI 助手' }}</span>
                <span>{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="bubble-content">{{ msg.content }}</div>
            </div>
          </div>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Loading, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { humanHandoffApi } from '@/utils/api'
import { formatServerMonthDayTime } from '@/utils/time'

const router = useRouter()

const handoffs = ref<any[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const drawerVisible = ref(false)
const detailLoading = ref(false)
const activeHandoff = ref<any>(null)

const loadHandoffs = async () => {
  loading.value = true
  try {
    const res: any = await humanHandoffApi.list({
      page: currentPage.value,
      pageSize: pageSize.value,
      status: statusFilter.value || undefined,
      keyword: searchKeyword.value || undefined,
    })
    const d = res?.data || res
    handoffs.value = d?.data || []
    total.value = d?.total || handoffs.value.length
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  searchKeyword.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  loadHandoffs()
}

const openDetail = async (row: any) => {
  drawerVisible.value = true
  detailLoading.value = true
  try {
    const res: any = await humanHandoffApi.detail(row.id)
    activeHandoff.value = res?.data || res
  } finally {
    detailLoading.value = false
  }
}

const toggleStatus = async (row: any) => {
  const nextStatus = row.status === 'followed' ? 'pending' : 'followed'
  await humanHandoffApi.updateStatus(row.id, nextStatus)
  row.status = nextStatus
  if (activeHandoff.value?.id === row.id) activeHandoff.value.status = nextStatus
  ElMessage.success(nextStatus === 'followed' ? '已标为已跟进' : '已标为待跟进')
  await loadHandoffs()
}

const goToDraft = (orderId: string) => {
  router.push(`/admin/orders/${orderId}`)
}

const formatTime = (ts: string) => {
  return formatServerMonthDayTime(ts)
}

const statusLabel = (status: string) => {
  return status === 'followed' ? '已跟进' : '待跟进'
}

const bizTypeLabel = (t: string) => {
  const m: Record<string, string> = {
    ai_3d_custom: 'AI驱动3D OOH内容定制',
    video_purchase: '3D OOH数字内容资源库',
    digital_art: '数字艺术与沉浸式视觉设计',
    motion_content: '广告视觉与动态影像制作',
    media_post_production: '户外媒体后期制作服务',
    campaign_analytics: '广告投放分析与效果报告',
  }
  return m[t] || t || '未知'
}

const extractedItems = computed(() => {
  const data = activeHandoff.value?.extractedData || {}
  const labels: Record<string, string> = {
    brand: '品牌',
    project_name: '项目名称',
    city: '城市',
    city_location: '点位/城市',
    content: '内容需求',
    theme_concept: '主题概念',
    art_direction: '艺术方向',
    budget: '预算',
    online_time: '上线时间',
    remarks: '备注',
  }
  return Object.keys(labels)
    .map(key => ({ key, label: labels[key], value: data[key] }))
    .filter(item => item.value)
})

onMounted(() => {
  loadHandoffs()
})
</script>

<style scoped>
.handoff-page {
  padding: 24px;
  max-width: 1280px;
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

.toolbar {
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

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.loading-center {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 40px 0;
  color: #909399;
}

.detail-section {
  margin-bottom: 22px;
}

.section-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-actions {
  display: flex;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fafafa;
}

.summary-item span {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.summary-item strong {
  display: block;
  font-size: 13px;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-bubble {
  padding: 12px 14px;
  border-radius: 8px;
  max-width: 92%;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble-user {
  align-self: flex-end;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
}

.bubble-assistant {
  align-self: flex-start;
  background: #f7f7f8;
  border: 1px solid #ebeef5;
}

.bubble-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.bubble-content {
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
}
</style>
