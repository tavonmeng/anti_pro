<template>
  <div class="assignment-list">
    <section class="overview-board">
      <div class="overview-hero">
        <div class="overview-switcher">
          <span class="switcher-label">当前展示</span>
          <strong>{{ privacyText(currentOverviewTitle) }}</strong>
          <small>{{ privacyText(currentOverviewMeta) }}</small>
          <button
            v-if="overviewAssignments.length > 1"
            type="button"
            class="next-assignment-button"
            @click="showNextOverviewAssignment"
          >
            下一单
          </button>
        </div>
        <button
          class="share-action privacy-action"
          :class="{ 'is-locked': privacyLocked }"
          type="button"
          :aria-label="privacyLocked ? '显示关键信息' : '隐藏关键信息'"
          @click="privacyLocked = !privacyLocked"
        >
          <el-icon :size="21"><Lock /></el-icon>
        </button>
      </div>

      <!-- 资料未完善提示 -->
      <div v-if="profileIncomplete" class="profile-alert" @click="router.push('/contractor/profile')">
        <span class="alert-icon"><el-icon><InfoFilled /></el-icon></span>
        <span class="alert-text">您的资料尚未完善，请前往<strong>个人设置</strong>补充公司信息和专业方向，以便接收派单</span>
        <span class="alert-arrow">→</span>
      </div>

      <div class="dashboard-grid">
        <article class="metric-card main-order-card">
          <div class="card-topline">
            <span class="icon-bubble"><el-icon><Document /></el-icon></span>
            <span class="soft-select">当前派单</span>
          </div>
          <template v-if="featuredAssignment">
            <h2>{{ privacyText(assignmentProjectName(featuredAssignment)) }}</h2>
            <p class="order-code">{{ privacyText(assignmentSubtitle(featuredAssignment)) }}</p>
            <div class="main-order-actions">
              <button type="button" class="dark-button" @click="goToDetail(featuredAssignment.id)">打开</button>
              <button
                v-if="featuredAssignment.status === 'pending'"
                type="button"
                class="light-button"
                @click.stop="handleAccept(featuredAssignment.id)"
              >
                接单
              </button>
              <button v-else type="button" class="light-button" @click="goToDetail(featuredAssignment.id)">查看</button>
            </div>
            <div class="order-mini-meta">
              <span>城市 <strong>{{ privacyText(featuredAssignment.order?.city || '—') }}</strong></span>
              <span>总排期 <strong>{{ privacyText(`${assignmentTotalDays(featuredAssignment)} 天`) }}</strong></span>
            </div>
          </template>
          <template v-else>
            <h2>暂无活跃派单</h2>
            <p class="order-code">新的派单会显示在这里</p>
          </template>
        </article>

        <article class="metric-card dot-card">
          <div class="card-topline">
            <span class="icon-bubble"><el-icon><Calendar /></el-icon></span>
            <span class="soft-select">排期日历</span>
          </div>
          <template v-if="scheduleAssignment">
            <div class="month-calendar">
              <div class="month-title">{{ privacyText(scheduleMonthTitle(scheduleAssignment)) }}</div>
              <div class="weekday-grid">
                <span v-for="day in weekdays" :key="day">{{ day }}</span>
              </div>
              <div class="month-grid">
                <span
                  v-for="(day, index) in monthCalendarDays(scheduleAssignment)"
                  :key="`${day.dateKey || 'blank'}-${index}`"
                  :class="privacyCalendarClasses(day)"
                >
                  {{ privacyLocked && day.label ? '*' : day.label }}
                </span>
              </div>
            </div>
            <p class="metric-label">项目排期</p>
            <div class="schedule-summary">
              <strong class="metric-value">{{ privacyText(`${assignmentTotalDays(scheduleAssignment)} 天`) }}</strong>
              <span>{{ privacyLocked ? '还剩 ****' : `还剩 ${remainingDays(scheduleAssignment)} 天` }}</span>
            </div>
          </template>
          <template v-else>
            <div class="calendar-empty">当前订单暂无排期</div>
            <p class="metric-label">项目排期</p>
            <strong class="metric-value">0 天</strong>
          </template>
        </article>

        <article class="metric-card compact-stat feedback-card">
          <div class="card-topline">
            <span class="icon-bubble"><el-icon><ChatLineSquare /></el-icon></span>
          </div>
          <strong>{{ privacyText(feedbackSummary.count) }}</strong>
          <span>用户反馈</span>
          <p class="feedback-copy">{{ privacyText(feedbackSummary.text) }}</p>
          <div class="feedback-lines">
            <i
              v-for="n in 4"
              :key="n"
              :class="{ active: n <= feedbackSummary.activeLines }"
            ></i>
          </div>
        </article>

        <article class="metric-card compact-stat stage-summary-card">
          <div class="card-topline">
            <span class="icon-bubble"><el-icon><SetUp /></el-icon></span>
          </div>
          <strong class="stage-value">{{ privacyText(stageSummary.current) }}</strong>
          <span>项目阶段</span>
          <div class="stage-mini-map">
            <i
              v-for="stage in stageSummary.steps"
              :key="stage.order"
              :class="{ done: stage.done, active: stage.active }"
            ></i>
          </div>
          <p class="stage-caption">{{ privacyText(stageSummary.caption) }}</p>
        </article>
      </div>
    </section>

    <section class="activity-panel">
      <div class="activity-header">
        <div>
          <h2>订单信息</h2>
          <p>项目位置、媒体规格、制作参数与创意方向</p>
        </div>
        <div class="activity-tools">
          <el-tabs v-model="activeTab" class="status-tabs" @tab-change="fetchAssignments">
            <el-tab-pane label="全部" name="all" />
            <el-tab-pane label="待处理" name="pending" />
            <el-tab-pane label="进行中" name="in_progress" />
            <el-tab-pane label="已完成" name="completed" />
            <el-tab-pane label="已拒绝" name="rejected" />
          </el-tabs>
        </div>
      </div>

    <!-- 列表 -->
    <div v-if="loading" class="loading-state">
      <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <div v-else-if="assignments.length === 0" class="empty-state">
      <el-empty description="暂无派单记录" />
    </div>

    <div v-else class="assignment-cards">
      <div
        v-for="item in assignments"
        :key="item.id"
        class="assignment-card"
        :class="statusClass(item.status)"
        @click="goToDetail(item.id)"
      >
        <div class="card-header">
          <div>
            <div class="order-number">{{ privacyText(assignmentProjectName(item)) }}</div>
            <div class="order-subtitle">{{ privacyText(orderHeroLine(item)) }}</div>
          </div>
          <span class="status-pill">{{ statusLabel(item.status) }}</span>
        </div>

        <div class="brief-tags">
          <span v-for="(tag, index) in orderTags(item)" :key="`${tag}-${index}`">{{ privacyText(tag) }}</span>
        </div>

        <div class="brief-spec-grid">
          <div v-for="spec in orderBriefSpecs(item)" :key="spec.label" class="brief-spec" :class="spec.tone">
            <span class="spec-label">{{ spec.label }}</span>
            <strong>{{ privacyText(spec.value) }}</strong>
            <span class="brief-mark">
              <el-icon><component :is="spec.icon" /></el-icon>
            </span>
          </div>
        </div>

        <div class="brief-story">
          <div class="story-main">
            <span>主题与核心表达</span>
            <p>{{ privacyText(orderTheme(item)) }}</p>
            <div v-if="privacyLocked && orderPreviewImages(item).length" class="story-preview-placeholder">****</div>
            <div v-else-if="orderPreviewImages(item).length" class="story-preview-strip">
              <img
                v-for="image in orderPreviewImages(item)"
                :key="image.url"
                :src="image.url"
                :alt="image.name || '项目参考图'"
              />
            </div>
            <span class="brief-mark">
              <el-icon><MagicStick /></el-icon>
            </span>
          </div>
          <div class="story-side">
            <div>
              <span>艺术方向/风格</span>
              <p>{{ privacyText(orderArtDirection(item)) }}</p>
              <span class="brief-mark">
                <el-icon><Brush /></el-icon>
              </span>
            </div>
            <div>
              <span>技术需求</span>
              <p>{{ privacyText(orderTech(item)) }}</p>
              <span class="brief-mark">
                <el-icon><Film /></el-icon>
              </span>
            </div>
          </div>
        </div>

        <div class="card-footer">
          <span class="time">订单号：{{ privacyText(item.order?.orderNumber || '—') }} · 当前：{{ privacyText(currentStageName(item)) }}</span>
          <div class="actions" v-if="item.status === 'pending'" @click.stop>
            <el-button size="small" type="primary" @click="handleAccept(item.id)">接单</el-button>
            <el-button size="small" @click="showRejectDialog(item.id)">拒绝</el-button>
          </div>
          <div class="actions" v-else @click.stop>
            <el-button size="small" type="primary" @click="goToDetail(item.id)">查看详情</el-button>
          </div>
        </div>
      </div>
    </div>
    </section>

    <!-- 拒绝对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="拒绝派单" width="400px" :append-to-body="true">
      <el-form>
        <el-form-item label="拒绝理由">
          <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写拒绝理由（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejecting" @click="handleReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Brush, Calendar, ChatLineSquare, Clock, Document, Film, InfoFilled, Loading,
  Location, Lock, MagicStick, Monitor, SetUp
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import { formatServerMonthDayTime } from '@/utils/time'

const router = useRouter()
const activeTab = ref('all')
const loading = ref(false)
const assignments = ref<any[]>([])
const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const rejectingId = ref('')
const rejecting = ref(false)
const profileIncomplete = ref(false)
const privacyLocked = ref(false)
const overviewIndex = ref(0)
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const DAY_MS = 24 * 60 * 60 * 1000

const privacyText = (value: unknown, fallback = '—') => {
  if (privacyLocked.value) return '****'
  const text = String(value ?? '').trim()
  return text || fallback
}

const overviewAssignments = computed(() => {
  const activeItems = assignments.value.filter(item => ['pending', 'accepted', 'in_progress'].includes(item.status))
  return activeItems.length > 0 ? activeItems : assignments.value
})

const featuredAssignment = computed(() => {
  const items = overviewAssignments.value
  if (items.length === 0) return null
  const index = Math.min(overviewIndex.value, items.length - 1)
  return items[index] || items[0]
})

const scheduleAssignment = computed(() => {
  const item = featuredAssignment.value
  if (!item || !Array.isArray(item.schedule) || item.schedule.length === 0) return null
  return item
})

const currentOverviewTitle = computed(() =>
  featuredAssignment.value ? assignmentProjectName(featuredAssignment.value) : '暂无活跃派单'
)

const currentOverviewMeta = computed(() => {
  const items = overviewAssignments.value
  if (!featuredAssignment.value || items.length === 0) return '新的派单会显示在这里'
  const index = Math.min(overviewIndex.value, items.length - 1) + 1
  return `${index}/${items.length} · ${statusLabel(featuredAssignment.value.status)}`
})

const showNextOverviewAssignment = () => {
  const total = overviewAssignments.value.length
  if (total <= 1) return
  overviewIndex.value = (overviewIndex.value + 1) % total
}

const statusSummary = computed(() => ({
  pending: assignments.value.filter(item => item.status === 'pending').length,
  inProgress: assignments.value.filter(item => ['accepted', 'in_progress'].includes(item.status)).length,
  completed: assignments.value.filter(item => item.status === 'completed').length,
}))

const feedbackText = (item: any) =>
  item?.feedback?.content ||
  item?.order?.remarks ||
  item?.order?.special_requirements ||
  item?.order?.content_review ||
  ''

const feedbackSummary = computed(() => {
  const item = featuredAssignment.value
  const text = feedbackText(item)
  return {
    count: text ? 1 : 0,
    text: text ? `${item?.feedback?.label || '用户反馈'}：${text}` : '当前订单暂无新的用户或管理员反馈',
    activeLines: text ? 3 : 1,
  }
})

const stageSummary = computed(() => {
  const item = featuredAssignment.value
  const schedule = item?.schedule || []
  const currentOrder = Number(item?.currentStageOrder || 1)
  const current = item ? currentStageName(item) : '待开始'
  const steps = schedule.length > 0
    ? schedule.slice(0, 5).map((stage: any) => {
      const order = Number(stage.display_order || 0)
      return {
        order,
        done: stage.status === 'completed' || order < currentOrder,
        active: order === currentOrder,
      }
    })
    : [{ order: 1, done: false, active: true }, { order: 2, done: false, active: false }, { order: 3, done: false, active: false }]

  return {
    current,
    steps,
    caption: schedule.length > 0
      ? `第 ${currentOrder} 阶段 · 共 ${schedule.length} 阶段`
      : '暂无项目阶段',
  }
})

const checkProfile = async () => {
  try {
    const d: any = await request.get('/contractor/profile')
    const missing = !d?.realName && !d?.real_name || !d?.company || !d?.specialty || !d?.expertise
    profileIncomplete.value = !!missing
  } catch { /* ignore */ }
}

const statusLabel = (s: string) => ({
  pending: '待处理', accepted: '已接单', in_progress: '进行中',
  completed: '已完成', rejected: '已拒绝', cancelled: '已取消',
}[s] || s)

const totalDays = (schedule: any[]) => schedule?.reduce((sum: number, s: any) => sum + (s.days || 0), 0) || 0

const assignmentTotalDays = (item: any) => totalDays(item?.schedule || [])

const assignmentProjectName = (item: any) =>
  item?.order?.projectName ||
  item?.order?.project_name ||
  item?.order?.brand ||
  item?.order?.content ||
  '未命名项目'

const assignmentSubtitle = (item: any) => {
  const brand = item?.order?.brand
  const orderNumber = item?.order?.orderNumber || item?.orderId || item?.id || '—'
  if (brand && brand !== assignmentProjectName(item)) return `${brand} · ${orderNumber}`
  return orderNumber
}

const orderLocation = (item: any) => item?.order?.city_location || item?.order?.city || '待确认'

const orderMediaSpec = (item: any) => item?.order?.media_specs || item?.order?.media_size || '待确认'

const orderDuration = (item: any) => item?.order?.timing_number || item?.order?.time_number || '待确认'

const orderLaunchTime = (item: any) => item?.order?.online_time || '待确认'

const orderTech = (item: any) => item?.order?.tech_delivery || item?.order?.technology || '待确认'

const orderTheme = (item: any) =>
  item?.order?.theme_concept ||
  item?.order?.content ||
  item?.order?.remarks ||
  '暂无主题说明'

const orderArtDirection = (item: any) =>
  item?.order?.art_direction ||
  item?.order?.style ||
  '暂无风格说明'

const imageUrlKeys = ['signed_url', 'signedUrl', 'url', 'fileUrl', 'file_url', 'ossUrl', 'object_url', 'path']

const orderPreviewImages = (item: any) => {
  const photos = item?.order?.site_photos
  if (!Array.isArray(photos)) return []

  return photos
    .map((photo: any, index: number) => {
      if (typeof photo === 'string') {
        return { url: photo, name: `项目参考图 ${index + 1}` }
      }

      const url = imageUrlKeys
        .map(key => photo?.[key])
        .find(value => typeof value === 'string' && value)

      return url
        ? { url, name: photo?.name || photo?.filename || `项目参考图 ${index + 1}` }
        : null
    })
    .filter(Boolean)
    .slice(0, 2)
}

const orderHeroLine = (item: any) => {
  const location = orderLocation(item)
  const media = orderMediaSpec(item)
  const duration = orderDuration(item)
  return [location, media, duration].filter(value => value && value !== '待确认').join(' · ') || assignmentSubtitle(item)
}

const orderTags = (item: any) => {
  const tags = [
    orderLocation(item),
    orderDuration(item),
    orderTech(item),
    item?.order?.orderType,
  ].filter(value => value && value !== '待确认')
  return Array.from(new Set(tags)).slice(0, 4)
}

const orderBriefSpecs = (item: any) => [
  { label: '投放城市/位置', value: orderLocation(item), tone: 'location', icon: Location },
  { label: '媒体尺寸/物理规格', value: orderMediaSpec(item), tone: 'media', icon: Monitor },
  { label: '投放时长/数量', value: orderDuration(item), tone: 'duration', icon: Clock },
  { label: '预计上刊时间', value: orderLaunchTime(item), tone: 'launch', icon: Calendar },
]

const currentStageName = (item: any) => {
  const currentOrder = Number(item?.currentStageOrder || 1)
  const stage = (item?.schedule || []).find((s: any) => Number(s.display_order || 0) === currentOrder)
  return stage?.name || item?.schedule?.[0]?.name || '待开始'
}

const parseCalendarDate = (value: string | undefined | null) => {
  if (!value) return null
  const datePart = String(value).split('T')[0]?.split(' ')[0]
  const parts = datePart?.split('-').map(Number)
  if (!parts || parts.length !== 3 || parts.some(Number.isNaN)) return null
  return new Date(parts[0], parts[1] - 1, parts[2])
}

const todayStart = () => {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

const addDays = (date: Date, days: number) => {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

const dateKey = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

const scheduleStartDate = (item: any) =>
  parseCalendarDate(item?.respondedAt) || parseCalendarDate(item?.assignedAt) || todayStart()

const scheduleEndDate = (item: any) =>
  addDays(scheduleStartDate(item), Math.max(assignmentTotalDays(item), 1) - 1)

const calendarMonthBaseDate = (item: any) => {
  const start = scheduleStartDate(item)
  const end = scheduleEndDate(item)
  const today = todayStart()
  if (today >= start && today <= end) return today
  return start
}

const scheduleMonthTitle = (item: any) => {
  const base = calendarMonthBaseDate(item)
  return `${base.getFullYear()}年${base.getMonth() + 1}月`
}

const remainingDays = (item: any) => {
  const end = scheduleEndDate(item)
  const today = todayStart()
  if (today > end) return 0
  return Math.max(Math.ceil((end.getTime() - today.getTime()) / DAY_MS) + 1, 0)
}

const monthCalendarDays = (item: any) => {
  const base = calendarMonthBaseDate(item)
  const start = scheduleStartDate(item)
  const end = scheduleEndDate(item)
  const todayKey = dateKey(todayStart())
  const first = new Date(base.getFullYear(), base.getMonth(), 1)
  const daysInMonth = new Date(base.getFullYear(), base.getMonth() + 1, 0).getDate()
  const leading = (first.getDay() + 6) % 7
  const days: Array<{ label: string; dateKey?: string; classes: Record<string, boolean> }> = []

  for (let i = 0; i < leading; i += 1) {
    days.push({ label: '', classes: { blank: true } })
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = new Date(base.getFullYear(), base.getMonth(), day)
    const inSchedule = date >= start && date <= end
    const key = dateKey(date)
    days.push({
      label: String(day),
      dateKey: key,
      classes: {
        'calendar-day': true,
        'in-schedule': inSchedule,
        today: key === todayKey,
      },
    })
  }

  while (days.length % 7 !== 0) {
    days.push({ label: '', classes: { blank: true } })
  }

  return days
}

const privacyCalendarClasses = (day: { label: string; classes: Record<string, boolean> }) => {
  if (!privacyLocked.value) return day.classes
  return {
    blank: day.classes.blank,
    'calendar-day': !!day.label,
    today: day.classes.today,
  }
}

const statusClass = (status: string) => `is-${status || 'unknown'}`

const formatTime = (iso: string) => {
  return formatServerMonthDayTime(iso, '—')
}

const fetchAssignments = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (activeTab.value !== 'all') params.status = activeTab.value
    const res: any = await request.get('/contractor/assignments', { params })
    assignments.value = Array.isArray(res) ? res : (res?.data || res?.items || [])
    if (overviewIndex.value >= assignments.value.length) overviewIndex.value = 0
  } catch (e: any) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const goToDetail = (id: string) => {
  router.push(`/contractor/assignments/${id}`)
}

const handleAccept = async (id: string) => {
  try {
    await request.put(`/contractor/assignments/${id}/accept`)
    ElMessage.success('接单成功')
    fetchAssignments()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const showRejectDialog = (id: string) => {
  rejectingId.value = id
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

const handleReject = async () => {
  rejecting.value = true
  try {
    await request.put(`/contractor/assignments/${rejectingId.value}/reject`, {
      reject_reason: rejectReason.value,
    })
    ElMessage.success('已拒绝')
    rejectDialogVisible.value = false
    fetchAssignments()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    rejecting.value = false
  }
}

onMounted(() => {
  fetchAssignments()
  checkProfile()
})
</script>

<style lang="scss" scoped>
.assignment-list {
  min-height: calc(100vh - 126px);
  padding: 0 0 36px;
  background: #F8F7F5;
}

.overview-board {
  background: transparent;
}

.overview-hero {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px clamp(24px, 2.6vw, 40px) 4px clamp(36px, 3.4vw, 52px);
  background: transparent;
}

.overview-switcher {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;
  color: #4B4640;

  .switcher-label {
    min-height: 28px;
    display: inline-flex;
    align-items: center;
    padding: 0 12px;
    border-radius: 14px;
    background: #FFFFFF;
    color: #8B5E3C;
    font-size: 12px;
    font-weight: 850;
  }

  strong {
    max-width: min(42vw, 520px);
    overflow: hidden;
    color: #171412;
    font-size: 18px;
    font-weight: 850;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    color: #8F877F;
    font-size: 13px;
    font-weight: 750;
    white-space: nowrap;
  }
}

.next-assignment-button {
  min-height: 30px;
  padding: 0 13px;
  border: 0;
  border-radius: 15px;
  background: #8B5E3C;
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
}

.share-action {
  width: 58px;
  height: 58px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 50%;
  background: #FFFFFF;
  color: #151515;
  cursor: pointer;
  box-shadow: 0 20px 34px rgba(49, 42, 35, 0.08);
}

.privacy-action {
  transition: all 0.2s ease;

  &.is-locked {
    background: #8B5E3C;
    color: #FFFFFF;
    box-shadow: 0 18px 32px rgba(139, 94, 60, 0.22);
  }
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(0, 0.92fr) minmax(0, 0.74fr) minmax(0, 0.66fr);
  align-items: stretch;
  gap: 18px;
  padding: 4px clamp(18px, 2.2vw, 32px) 26px clamp(36px, 3.4vw, 52px);
  background: transparent;
}

.metric-card {
  min-width: 0;
  min-height: 232px;
  height: 100%;
  box-sizing: border-box;
  padding: clamp(20px, 1.65vw, 28px);
  border-radius: 30px;
  background: #FFFFFF;
  box-shadow: 0 1px 0 rgba(42, 37, 31, 0.04);
}

.main-order-card {
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(135deg, rgba(139, 94, 60, 0.08), transparent 48%),
    #FFFFFF;

  h2 {
    max-width: 360px;
    margin: 24px 0 4px;
    color: #151515;
    font-size: 30px;
    font-weight: 850;
    line-height: 1.05;
  }
}

.card-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.icon-bubble {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #F4F2EF;
  color: #121212;
  border: 1px solid rgba(18, 18, 18, 0.08);
}

.soft-select {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  padding: 0 16px;
  border-radius: 17px;
  background: #F7F6F4;
  color: #4B4640;
  font-size: 12px;
  font-weight: 750;
}

.order-code {
  margin: 0;
  color: #928B84;
  font-size: 13px;
  font-weight: 700;
}

.main-order-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 22px 0;
  max-width: 370px;
}

.dark-button,
.light-button {
  height: 42px;
  border: 0;
  border-radius: 21px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.dark-button {
  background: #080808;
  color: #FFFFFF;
}

.light-button {
  background: #F7F6F4;
  color: #2E2A26;
}

.order-mini-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-top: auto;
  color: #A29B94;
  font-size: 12px;
  font-weight: 650;

  strong {
    display: block;
    margin-top: 4px;
    color: #8B5E3C;
    font-size: 15px;
  }
}

.dot-card {
  display: flex;
  flex-direction: column;
}

.month-calendar {
  margin-top: 22px;
}

.month-title {
  margin-bottom: 10px;
  color: #161412;
  font-size: 18px;
  font-weight: 850;
}

.weekday-grid,
.month-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 5px;
}

.weekday-grid {
  margin-bottom: 6px;

  span {
    color: #A29B94;
    font-size: 11px;
    font-weight: 800;
    text-align: center;
  }
}

.month-grid {
  span {
    height: 26px;
    min-width: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: #FFFFFF;
    color: #6D6760;
    font-size: 12px;
    font-weight: 750;
  }

  .blank {
    background: transparent;
  }

  .in-schedule {
    background: #D8D4CF;
    color: #241F1B;
  }

  .today {
    background: #8B5E3C;
    color: #FFFFFF;
    box-shadow: none;
  }
}

.metric-label {
  margin: 24px 0 6px;
  color: #A29B94;
  font-size: 14px;
  font-weight: 700;
}

.metric-value {
  color: #151515;
  font-size: 30px;
  font-weight: 850;
}

.schedule-summary {
  display: flex;
  align-items: baseline;
  gap: 10px;

  span {
    color: #8B5E3C;
    font-size: 13px;
    font-weight: 800;
  }
}

.calendar-empty {
  min-height: 168px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 22px;
  border-radius: 22px;
  background: #F7F6F4;
  color: #9B948C;
  font-size: 13px;
  font-weight: 750;
}

.compact-stat {
  display: flex;
  flex-direction: column;

  strong {
    margin-top: 26px;
    color: #151515;
    font-size: 34px;
    font-weight: 850;
    line-height: 1;
  }

  > span:not(.icon-bubble) {
    margin-top: 8px;
    color: #89827A;
    font-size: 14px;
    font-weight: 750;
  }
}

.feedback-card,
.stage-summary-card {
  overflow: hidden;
}

.feedback-copy,
.stage-caption {
  display: -webkit-box;
  margin: 12px 0 0;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  color: #5E5954;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.45;
}

.feedback-lines {
  display: grid;
  grid-template-columns: 1fr;
  gap: 7px;
  margin-top: auto;

  i {
    height: 7px;
    border-radius: 999px;
    background: #E8E3DD;

    &:nth-child(1) { width: 82%; }
    &:nth-child(2) { width: 100%; }
    &:nth-child(3) { width: 68%; }
    &:nth-child(4) { width: 46%; }

    &.active {
      background: #8B5E3C;
    }
  }
}

.stage-value {
  max-width: 100%;
  overflow: hidden;
  font-size: 28px !important;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-mini-map {
  min-height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;

  i {
    position: relative;
    width: 17px;
    height: 17px;
    flex: 0 0 17px;
    border-radius: 50%;
    background: #E5E0DA;
    box-shadow: inset 0 0 0 4px #FFFFFF;

    &::after {
      content: '';
      position: absolute;
      left: 19px;
      top: 8px;
      width: 16px;
      height: 2px;
      border-radius: 2px;
      background: #E5E0DA;
    }

    &:last-child::after {
      display: none;
    }

    &.done {
      background: #BA957C;
    }

    &.active {
      background: #8B5E3C;
      box-shadow: inset 0 0 0 4px #FFFFFF, 0 0 0 2px rgba(139, 94, 60, 0.24);
    }
  }
}

.activity-panel {
  margin-top: 4px;
  padding: 30px clamp(18px, 2.2vw, 32px) 0 clamp(36px, 3.4vw, 52px);
  background: transparent;
}

.activity-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;

  h2 {
    margin: 0 0 6px;
    color: #161412;
    font-size: 21px;
    font-weight: 850;
  }

  p {
    margin: 0;
    color: #9B948C;
    font-size: 13px;
    font-weight: 650;
  }
}

.activity-tools {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-tabs {
  :deep(.el-tabs__header) {
    margin: 0;
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }

  :deep(.el-tabs__active-bar) {
    display: none;
  }

  :deep(.el-tabs__nav) {
    gap: 8px;
  }

  :deep(.el-tabs__item) {
    height: 36px;
    padding: 0 14px !important;
    border-radius: 18px;
    background: #FFFFFF;
    color: #6D6760;
    font-size: 12px;
    font-weight: 750;

    &.is-active {
      background: #111111;
      color: #FFFFFF;
    }
  }
}

.loading-state {
  text-align: center; padding: 60px 0; color: #86868B;
  .loading-icon { animation: spin 1s linear infinite; }
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { padding: 60px 0; }
.assignment-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 18px;
}
.profile-alert {
  display: flex; align-items: center; gap: 10px;
  background: #F4EAE2; border: 1px solid #D8C4B4;
  border-radius: 22px; padding: 14px 18px; margin: 0 52px 8px;
  cursor: pointer; transition: all 0.2s;
  &:hover { background: #EFE0D6; transform: translateY(-1px); }
}
.alert-icon { font-size: 18px; flex-shrink: 0; color: #8B5E3C; }
.alert-text { flex: 1; font-size: 13px; color: #1D1D1F; line-height: 1.5;
  strong { color: #8B5E3C; }
}
.alert-arrow { font-size: 16px; color: #8B5E3C; font-weight: 600; }
.assignment-card {
  background:
    linear-gradient(135deg, rgba(139, 94, 60, 0.08), transparent 36%),
    #fff;
  border-radius: 28px;
  padding: 24px;
  border: 1px solid #EFEDE9;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #D7C5B7; box-shadow: 0 20px 42px rgba(42,37,31,0.09); transform: translateY(-2px); }
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 14px;
}
.order-number {
  max-width: 520px;
  font-size: clamp(20px, 2.2vw, 28px);
  font-weight: 850;
  color: #151515;
  line-height: 1.08;
}
.order-subtitle { margin-top: 8px; color: #8B5E3C; font-size: 13px; font-weight: 800; }
.status-pill {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  padding: 0 12px;
  border-radius: 16px;
  background: #F4F2EF;
  color: #5E5954;
  font-size: 12px;
  font-weight: 800;
}
.assignment-card.is-pending .status-pill,
.assignment-card.is-in_progress .status-pill,
.assignment-card.is-accepted .status-pill {
  background: #8B5E3C;
  color: #FFFFFF;
}

.brief-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;

  span {
    min-height: 30px;
    display: inline-flex;
    align-items: center;
    padding: 0 12px;
    border-radius: 15px;
    background: rgba(255, 255, 255, 0.76);
    color: #4B4640;
    border: 1px solid rgba(139, 94, 60, 0.12);
    font-size: 12px;
    font-weight: 800;
  }
}

.brief-spec-grid {
  display: grid;
  grid-template-columns: 1.05fr 1.5fr 0.88fr 1.12fr;
  gap: 10px;
  margin-bottom: 18px;
  padding: 10px;
  border-radius: 22px;
  background: rgba(244, 242, 239, 0.72);
}

.brief-spec {
  min-height: 92px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 14px 14px 12px;
  border-radius: 17px;
  background: rgba(255, 255, 255, 0.68);
  border-top: 4px solid #D8D0C7;

  &.location {
    border-top-color: #8B5E3C;
  }

  &.media {
    border-top-color: #6D6760;
  }

  &.duration {
    border-top-color: #BA957C;
  }

  &.launch {
    border-top-color: #B8ADA3;
  }

  .spec-label {
    color: #9B948C;
    font-size: 12px;
    font-weight: 800;
  }

  strong {
    display: block;
    color: #151515;
    font-size: 18px;
    font-weight: 850;
    line-height: 1.15;
    word-break: break-word;
  }

  .brief-mark {
    align-self: flex-start;
    margin-top: 12px;
    width: 30px;
    height: 30px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: rgba(139, 94, 60, 0.08);
    color: #9B948C;
    font-size: 16px;
  }
}

.brief-story {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(180px, 0.86fr);
  gap: 12px;
  margin-bottom: 18px;
}

.story-main,
.story-side {
  min-width: 0;
  border-radius: 22px;
}

.story-main {
  position: relative;
  overflow: hidden;
  padding: 22px 22px 20px;
  background:
    linear-gradient(135deg, rgba(139, 94, 60, 0.12), transparent 44%),
    #F7F4F1;
  color: #151515;
  border-left: 5px solid #8B5E3C;

  &::after {
    content: '';
    position: absolute;
    right: 18px;
    bottom: 16px;
    width: 110px;
    height: 36px;
    border-radius: 999px;
    background: repeating-linear-gradient(
      90deg,
      rgba(139, 94, 60, 0.14) 0,
      rgba(139, 94, 60, 0.14) 5px,
      transparent 5px,
      transparent 12px
    );
    opacity: 0.7;
  }

  span {
    display: block;
    margin-bottom: 10px;
    color: #8B5E3C;
    font-size: 12px;
    font-weight: 850;
  }

  p {
    position: relative;
    z-index: 1;
    margin: 0;
    color: #1F1A16;
    font-size: 16px;
    font-weight: 760;
    line-height: 1.58;
  }

  .brief-mark {
    position: relative;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-top: 16px;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: rgba(139, 94, 60, 0.1);
    color: #8B5E3C;
    font-size: 18px;
  }
}

.story-preview-strip {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;

  img {
    width: 100%;
    aspect-ratio: 16 / 9;
    display: block;
    border-radius: 15px;
    object-fit: cover;
    background: #FFFFFF;
    box-shadow: 0 10px 22px rgba(42, 37, 31, 0.08);
  }
}

.story-preview-placeholder {
  position: relative;
  z-index: 1;
  min-height: 88px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.72);
  color: #8B5E3C;
  font-size: 22px;
  font-weight: 850;
  letter-spacing: 0;
}

.story-side {
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 10px;

  div {
    min-width: 0;
    padding: 16px;
    border-radius: 20px;
    background: #F7F4F1;
    border-left: 5px solid #BA957C;
  }

  div + div {
    border-left-color: #8B5E3C;
  }

  span {
    display: block;
    margin-bottom: 7px;
    color: #9B948C;
    font-size: 12px;
    font-weight: 850;
  }

  p {
    display: -webkit-box;
    margin: 0;
    overflow: hidden;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    color: #151515;
    font-size: 14px;
    font-weight: 780;
    line-height: 1.45;
  }

  .brief-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-top: 12px;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: rgba(139, 94, 60, 0.08);
    color: #9B948C;
    font-size: 16px;
  }
}

.card-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 14px; border-top: 1px solid #F1EFEC;
}
.card-footer .time { font-size: 12px; color: #86868B; }
.actions { display: flex; gap: 8px; }

:deep(.el-button--primary) {
  --el-button-bg-color: #8B5E3C;
  --el-button-border-color: #8B5E3C;
  --el-button-hover-bg-color: #8B5E3C;
  --el-button-hover-border-color: #8B5E3C;
}

@media (max-width: 1360px) {
  .dashboard-grid {
    grid-template-columns: minmax(0, 1.22fr) minmax(0, 0.9fr) minmax(0, 0.72fr) minmax(0, 0.64fr);
    gap: 14px;
  }
}

@media (max-width: 1180px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .brief-spec-grid,
  .brief-story {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .assignment-list {
    padding: 0 0 28px;
  }

  .overview-hero,
  .dashboard-grid,
  .activity-panel {
    padding-left: 20px;
    padding-right: 20px;
  }

  .dashboard-grid,
  .assignment-cards,
  .brief-spec-grid,
  .brief-story {
    grid-template-columns: 1fr;
  }

  .assignment-cards {
    grid-template-columns: minmax(0, 1fr);
  }

  .card-header,
  .card-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .profile-alert {
    margin-left: 20px;
    margin-right: 20px;
  }

  .activity-header {
    flex-direction: column;
  }
}
</style>
