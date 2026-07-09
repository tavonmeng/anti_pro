<template>
  <div class="business-data-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">业务数据看板</h1>
        <p class="page-subtitle">官网访问统计</p>
      </div>
      <div class="header-actions">
        <el-select v-model="days" class="range-select" @change="loadWebsiteVisits">
          <el-option label="最近 7 天" :value="7" />
          <el-option label="最近 30 天" :value="30" />
          <el-option label="最近 90 天" :value="90" />
        </el-select>
        <el-button :icon="Refresh" @click="loadWebsiteVisits" :loading="loading">
          刷新
        </el-button>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric-card">
        <span>今日 PV</span>
        <strong>{{ formatNumber(summary.totals.today_pv) }}</strong>
      </div>
      <div class="metric-card">
        <span>今日 UV</span>
        <strong>{{ formatNumber(summary.totals.today_uv) }}</strong>
      </div>
      <div class="metric-card">
        <span>昨日 PV</span>
        <strong>{{ formatNumber(summary.totals.yesterday_pv) }}</strong>
      </div>
      <div class="metric-card">
        <span>{{ summary.totals.days }} 天 PV</span>
        <strong>{{ formatNumber(summary.totals.range_pv) }}</strong>
      </div>
      <div class="metric-card">
        <span>{{ summary.totals.days }} 天 UV</span>
        <strong>{{ formatNumber(summary.totals.range_uv) }}</strong>
      </div>
    </div>

    <el-card class="data-section" v-loading="loading">
      <template #header>
        <div class="section-header">
          <h2>按天统计</h2>
        </div>
      </template>
      <el-table :data="summary.daily" stripe style="width: 100%">
        <el-table-column prop="date" label="日期" min-width="140" />
        <el-table-column prop="pv" label="PV" min-width="120" align="right">
          <template #default="{ row }">{{ formatNumber(row.pv) }}</template>
        </el-table-column>
        <el-table-column prop="uv" label="UV" min-width="120" align="right">
          <template #default="{ row }">{{ formatNumber(row.uv) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="data-section" v-loading="loading">
      <template #header>
        <div class="section-header">
          <h2>页面路径统计</h2>
        </div>
      </template>
      <el-table :data="summary.paths" stripe style="width: 100%">
        <el-table-column prop="path" label="路径" min-width="220" show-overflow-tooltip />
        <el-table-column prop="pv" label="PV" width="140" align="right">
          <template #default="{ row }">{{ formatNumber(row.pv) }}</template>
        </el-table-column>
        <el-table-column prop="uv" label="UV" width="140" align="right">
          <template #default="{ row }">{{ formatNumber(row.uv) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="data-section" v-loading="loading">
      <template #header>
        <div class="section-header">
          <h2>最近原始访问日志</h2>
        </div>
      </template>
      <el-table :data="summary.recent_events" stripe style="width: 100%">
        <el-table-column label="访问时间" width="170">
          <template #default="{ row }">{{ formatServerTime(row.visited_at) }}</template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="150" />
        <el-table-column prop="path" label="路径" min-width="180" show-overflow-tooltip />
        <el-table-column label="PV" width="92" align="center">
          <template #default="{ row }">
            <el-tag :type="row.counted_for_pv ? 'success' : 'info'" size="small">
              {{ row.counted_for_pv ? '已计入' : '去抖' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="属地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ visitGeoText(row) }}</template>
        </el-table-column>
        <el-table-column label="属地状态" width="110">
          <template #default="{ row }">
            <el-tag :type="geoStatusType(row.geo_status)" size="small">
              {{ geoStatusLabel(row.geo_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="referrer" label="来源" min-width="180" show-overflow-tooltip />
        <el-table-column prop="user_agent" label="User-Agent" min-width="220" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { businessDataApi, type WebsiteVisitSummary } from '@/utils/api'
import { formatServerTime } from '@/utils/time'

const loading = ref(false)
const days = ref(7)
const numberFormatter = new Intl.NumberFormat('zh-CN')

const emptySummary = (): WebsiteVisitSummary => ({
  totals: {
    today_pv: 0,
    today_uv: 0,
    yesterday_pv: 0,
    yesterday_uv: 0,
    range_pv: 0,
    range_uv: 0,
    days: days.value,
  },
  daily: [],
  paths: [],
  recent_events: [],
})

const summary = reactive<WebsiteVisitSummary>(emptySummary())

const formatNumber = (value: number) => numberFormatter.format(value || 0)

const visitGeoText = (row: WebsiteVisitSummary['recent_events'][number]) => {
  return [row.country, row.province, row.city].filter(Boolean).join(' / ') || '-'
}

const geoStatusLabel = (status: string) => {
  if (status === 'done') return '已解析'
  if (status === 'failed') return '失败'
  return '待解析'
}

const geoStatusType = (status: string) => {
  if (status === 'done') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
}

const loadWebsiteVisits = async () => {
  loading.value = true
  try {
    const data = await businessDataApi.getWebsiteVisits(days.value)
    Object.assign(summary, data || emptySummary())
  } catch (error: any) {
    ElMessage.error(error?.message || '获取官网访问统计失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadWebsiteVisits()
})
</script>

<style lang="scss" scoped>
.business-data-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  margin: 0;
  color: #1D1D1F;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0;
}

.page-subtitle {
  margin: 6px 0 0;
  color: #6B7280;
  font-size: 14px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.range-select {
  width: 132px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  min-height: 92px;
  padding: 18px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #FFFFFF;
  box-sizing: border-box;

  span {
    display: block;
    color: #6B7280;
    font-size: 13px;
  }

  strong {
    display: block;
    margin-top: 10px;
    color: #111827;
    font-size: 28px;
    font-weight: 760;
    line-height: 1;
  }
}

.data-section {
  border-radius: 8px;

  :deep(.el-card__header) {
    padding: 14px 18px;
  }

  :deep(.el-card__body) {
    padding: 0;
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    color: #1F2937;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0;
  }
}

@media (max-width: 960px) {
  .page-header,
  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .range-select {
    width: 100%;
  }
}

@media (max-width: 520px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
