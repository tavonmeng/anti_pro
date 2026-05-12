<template>
  <div class="customer-page">
    <div class="page-header">
      <h2>👤 客户画像管理</h2>
      <p class="page-desc">以客户为维度管理画像、查看订单、分析官网</p>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索用户名、手机号、公司名..."
        clearable
        style="width: 320px"
        @keyup.enter="loadCustomers"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="loadCustomers">搜索</el-button>
      <el-button @click="searchKeyword = ''; loadCustomers()">重置</el-button>
    </div>

    <!-- 客户列表 -->
    <el-table
      :data="customers"
      v-loading="loading"
      stripe
      style="width: 100%; margin-top: 16px"
    >
      <el-table-column label="客户" min-width="180">
        <template #default="{ row }">
          <div class="user-cell">
            <el-avatar :size="32" style="background: linear-gradient(135deg, #667eea, #764ba2); flex-shrink: 0">
              {{ (row.username || '?')[0] }}
            </el-avatar>
            <div>
              <div class="username">{{ row.username }}</div>
              <div class="user-phone" v-if="row.phone">{{ row.phone }}</div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="公司" min-width="160">
        <template #default="{ row }">
          <span>{{ row.company || '未填写' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="订单数" width="90" align="center">
        <template #default="{ row }">
          <el-tag type="info" size="small">{{ row.orderCount }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="画像状态" width="120" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.memory?.hasCrawl" type="success" size="small">已分析</el-tag>
          <el-tag v-else-if="row.memory?.crawlStatus === 'pending'" type="warning" size="small">分析中</el-tag>
          <el-tag v-else-if="row.memory?.crawlStatus === 'failed'" type="danger" size="small">分析失败</el-tag>
          <el-tag v-else type="info" size="small">未分析</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="注册时间" width="150">
        <template #default="{ row }">
          {{ formatTime(row.createdAt) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openProfile(row)">
            查看画像
          </el-button>
          <el-button
            size="small"
            type="warning"
            link
            :loading="row._crawling"
            @click="triggerCrawl(row)"
          >
            {{ row.memory?.hasCrawl ? '重新分析' : '分析官网' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="loadCustomers"
      />
    </div>

    <!-- 客户画像详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="`客户画像 — ${activeCustomer?.username || ''}`"
      size="780px"
      direction="rtl"
    >
      <div v-if="profileLoading" class="loading-center">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-else-if="profileData" class="profile-detail">
        <!-- 客户基本信息 -->
        <div class="profile-section">
          <h4>📋 基本信息</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="用户名">{{ activeCustomer?.username }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ activeCustomer?.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="公司">{{ profileData.user_company || activeCustomer?.company || '-' }}</el-descriptions-item>
            <el-descriptions-item label="订单数">{{ activeCustomer?.orderCount || 0 }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 客户资料导入 -->
        <div class="profile-section">
          <div class="section-header">
            <h4>📎 客户资料</h4>
            <div class="section-actions">
              <el-upload
                :show-file-list="false"
                :http-request="uploadCustomerDocument"
                :before-upload="beforeCustomerDocumentUpload"
                accept=".pdf,.docx,.pptx"
              >
                <el-button size="small" type="primary" :icon="Upload" :loading="docUploadLoading">
                  上传资料
                </el-button>
              </el-upload>
              <el-button size="small" :icon="Refresh" @click="loadDocuments" :loading="documentsLoading">
                刷新
              </el-button>
            </div>
          </div>
          <el-table
            v-if="customerDocuments.length"
            :data="customerDocuments"
            size="small"
            border
            stripe
            v-loading="documentsLoading"
          >
            <el-table-column prop="original_filename" label="文件" min-width="180" show-overflow-tooltip />
            <el-table-column label="状态" width="96">
              <template #default="{ row }">
                <el-tag :type="docStatusType(row.status)" size="small">{{ docStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="摘要" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.extraction?.summary || row.processing_error || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" link :icon="View" @click="openReviewDialog(row)">
                  审核
                </el-button>
                <el-button size="small" type="warning" link :icon="Refresh" @click="reprocessDocument(row)">
                  重跑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-else class="document-empty">
            上传客户 PDF / Word / PPT 后，系统会抽取公司介绍、屏幕资源、案例和重要备注。
          </div>
        </div>

        <!-- 公司分析结果 -->
        <div v-if="profileData.company_info?.description" class="profile-section">
          <h4>🏢 公司官网分析</h4>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="公司名称">{{ profileData.company_info.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="官网">
              <a v-if="profileData.company_info.website" :href="profileData.company_info.website" target="_blank" style="color: #409eff;">
                {{ profileData.company_info.website }}
              </a>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="简介">{{ profileData.company_info.description }}</el-descriptions-item>
            <el-descriptions-item label="核心优势" v-if="profileData.company_info.advantages?.length">
              <el-tag v-for="adv in profileData.company_info.advantages" :key="adv" size="small" style="margin-right: 4px;">{{ adv }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="分析时间">{{ profileData.company_info.crawled_at || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 屏幕资源 -->
        <div v-if="profileData.screen_resources?.length" class="profile-section">
          <h4>📺 屏幕资源（{{ profileData.screen_resources.length }} 块）</h4>
          <el-table :data="profileData.screen_resources" size="small" border stripe>
            <el-table-column prop="city" label="城市" width="80" />
            <el-table-column prop="location" label="位置" min-width="120" />
            <el-table-column prop="name" label="屏幕名" min-width="110" show-overflow-tooltip />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="size" label="尺寸" width="80" />
            <el-table-column prop="resolution" label="分辨率" width="110" />
            <el-table-column prop="daily_traffic" label="日均客流" width="90" />
          </el-table>
        </div>

        <!-- 项目偏好 -->
        <div v-if="hasPreferences" class="profile-section">
          <h4>📊 项目偏好</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="常用城市">{{ profileData.project_preferences?.common_cities?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="偏好风格">{{ profileData.project_preferences?.preferred_styles?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创意目标">{{ profileData.project_preferences?.creative_goals?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="历史主题">{{ profileData.project_preferences?.theme_concepts?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="内容禁忌">{{ profileData.project_preferences?.content_taboos?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="参考案例">{{ profileData.project_preferences?.reference_cases?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="预算范围">{{ profileData.project_preferences?.budget_range || '-' }}</el-descriptions-item>
            <el-descriptions-item label="典型时长">{{ profileData.project_preferences?.typical_duration || '-' }}</el-descriptions-item>
            <el-descriptions-item v-if="profileData.project_preferences?.notes" label="备注" :span="2">
              {{ profileData.project_preferences.notes }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 客户资料案例 -->
        <div v-if="profileData.company_info?.past_cases?.length" class="profile-section">
          <h4>🎬 资料案例（{{ profileData.company_info.past_cases.length }} 个）</h4>
          <el-table :data="profileData.company_info.past_cases" size="small" border stripe>
            <el-table-column prop="brand" label="品牌" width="110" />
            <el-table-column prop="title" label="案例" min-width="150" show-overflow-tooltip />
            <el-table-column prop="city" label="城市" width="80" />
            <el-table-column prop="content_type" label="类型" width="120" show-overflow-tooltip />
          </el-table>
        </div>

        <!-- 历史项目 -->
        <div v-if="profileData.past_projects?.length" class="profile-section">
          <h4>📁 历史项目（{{ profileData.past_projects.length }} 个）</h4>
          <el-table :data="profileData.past_projects" size="small" border stripe>
            <el-table-column prop="project_name" label="项目名" min-width="140" />
            <el-table-column prop="city" label="城市" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 交互统计 -->
        <div v-if="profileData.interaction_stats?.total_sessions" class="profile-section">
          <h4>💬 交互统计</h4>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="对话次数">{{ profileData.interaction_stats.total_sessions }}</el-descriptions-item>
            <el-descriptions-item label="首次接触">{{ formatTime(profileData.interaction_stats.first_contact) }}</el-descriptions-item>
            <el-descriptions-item label="最近接触">{{ formatTime(profileData.interaction_stats.last_contact) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- Agent 备忘录 -->
        <div class="profile-section">
          <h4>📝 Agent 备忘录</h4>
          <el-input
            v-model="agentNotes"
            type="textarea"
            :rows="3"
            placeholder="管理员对该客户的备忘（AI 对话时会参考）"
          />
          <el-button
            type="primary"
            size="small"
            style="margin-top: 8px"
            :loading="notesLoading"
            @click="saveNotes"
          >
            保存备忘
          </el-button>
        </div>

        <!-- 空状态 -->
        <div v-if="!profileData.company_info?.description && !profileData.company_info?.past_cases?.length && !profileData.screen_resources?.length && !profileData.past_projects?.length && !profileData.interaction_stats?.total_sessions" class="empty-profile">
          暂无画像数据。点击「分析官网」可自动爬取客户公司信息。
        </div>
      </div>
    </el-drawer>

    <el-dialog
      v-model="reviewDialogVisible"
      title="客户资料审核"
      width="920px"
      destroy-on-close
    >
      <div v-if="activeDocument" class="review-dialog">
        <div class="review-meta">
          <span>{{ activeDocument.original_filename }}</span>
          <el-tag :type="docStatusType(activeDocument.status)" size="small">
            {{ docStatusLabel(activeDocument.status) }}
          </el-tag>
          <span v-if="activeDocument.processing_error" class="review-error">
            {{ activeDocument.processing_error }}
          </span>
        </div>

        <el-form label-position="top">
          <el-form-item label="公司名称">
            <el-input v-model="reviewForm.company_info.name" />
          </el-form-item>
          <el-form-item label="公司简介">
            <el-input v-model="reviewForm.company_info.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="核心优势（每行一条）">
            <el-input v-model="reviewAdvantagesText" type="textarea" :rows="3" />
          </el-form-item>

          <div class="review-block">
            <div class="review-block-header">
              <h4>屏幕资源</h4>
              <el-button size="small" :icon="Plus" @click="addScreenResource">新增</el-button>
            </div>
            <el-table :data="reviewForm.screen_resources" size="small" border>
              <el-table-column label="城市" width="90">
                <template #default="{ row }"><el-input v-model="row.city" size="small" /></template>
              </el-table-column>
              <el-table-column label="点位" min-width="150">
                <template #default="{ row }"><el-input v-model="row.location" size="small" /></template>
              </el-table-column>
              <el-table-column label="屏幕名" min-width="130">
                <template #default="{ row }"><el-input v-model="row.name" size="small" /></template>
              </el-table-column>
              <el-table-column label="类型" width="110">
                <template #default="{ row }"><el-input v-model="row.type" size="small" /></template>
              </el-table-column>
              <el-table-column label="尺寸" width="100">
                <template #default="{ row }"><el-input v-model="row.size" size="small" /></template>
              </el-table-column>
              <el-table-column label="操作" width="70">
                <template #default="{ $index }">
                  <el-button size="small" type="danger" link :icon="Delete" @click="reviewForm.screen_resources.splice($index, 1)" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="review-block">
            <div class="review-block-header">
              <h4>案例信息</h4>
              <el-button size="small" :icon="Plus" @click="addPastCase">新增</el-button>
            </div>
            <el-table :data="reviewForm.past_cases" size="small" border>
              <el-table-column label="品牌" width="120">
                <template #default="{ row }"><el-input v-model="row.brand" size="small" /></template>
              </el-table-column>
              <el-table-column label="案例" min-width="170">
                <template #default="{ row }"><el-input v-model="row.title" size="small" /></template>
              </el-table-column>
              <el-table-column label="城市" width="90">
                <template #default="{ row }"><el-input v-model="row.city" size="small" /></template>
              </el-table-column>
              <el-table-column label="类型" width="130">
                <template #default="{ row }"><el-input v-model="row.content_type" size="small" /></template>
              </el-table-column>
              <el-table-column label="操作" width="70">
                <template #default="{ $index }">
                  <el-button size="small" type="danger" link :icon="Delete" @click="reviewForm.past_cases.splice($index, 1)" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-form-item label="重要备注（每行一条）">
            <el-input v-model="reviewNotesText" type="textarea" :rows="4" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="approveLoading" @click="approveDocument">
          确认写入 Memory
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Loading, Upload, Refresh, View, Plus, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const customers = ref<any[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const drawerVisible = ref(false)
const activeCustomer = ref<any>(null)
const profileData = ref<any>(null)
const profileLoading = ref(false)
const agentNotes = ref('')
const notesLoading = ref(false)
const customerDocuments = ref<any[]>([])
const documentsLoading = ref(false)
const docUploadLoading = ref(false)
const reviewDialogVisible = ref(false)
const activeDocument = ref<any>(null)
const approveLoading = ref(false)
const reviewAdvantagesText = ref('')
const reviewNotesText = ref('')
const reviewForm = ref<any>(emptyReviewData())

const hasPreferences = computed(() => {
  const pp = profileData.value?.project_preferences
  return pp && (
    pp.common_cities?.length || pp.preferred_styles?.length ||
    pp.creative_goals?.length || pp.theme_concepts?.length ||
    pp.content_taboos?.length || pp.reference_cases?.length ||
    pp.budget_range || pp.typical_duration || pp.notes
  )
})

const loadCustomers = async () => {
  loading.value = true
  try {
    const res: any = await request.get('/admin/memory/customers', {
      params: {
        page: currentPage.value,
        pageSize: pageSize.value,
        keyword: searchKeyword.value || undefined,
      },
    })
    // axios 拦截器已解包 response.data.data → res = {data: [...], total: N}
    customers.value = res?.data || []
    total.value = res?.total || 0
  } catch (e) {
    console.error('加载客户列表失败:', e)
  } finally {
    loading.value = false
  }
}

const openProfile = async (row: any) => {
  activeCustomer.value = row
  drawerVisible.value = true
  profileLoading.value = true
  profileData.value = null
  agentNotes.value = ''
  customerDocuments.value = []
  try {
    const res: any = await request.get(`/admin/memory/${row.userId}`)
    profileData.value = res
    agentNotes.value = res?.agent_notes || ''
    await loadDocuments()
  } catch (e) {
    console.error('加载画像失败:', e)
  } finally {
    profileLoading.value = false
  }
}

const loadDocuments = async () => {
  if (!activeCustomer.value?.userId) return
  documentsLoading.value = true
  try {
    const res: any = await request.get(`/admin/documents/user/${activeCustomer.value.userId}`)
    customerDocuments.value = res || []
  } catch (e) {
    console.error('加载客户资料失败:', e)
  } finally {
    documentsLoading.value = false
  }
}

const beforeCustomerDocumentUpload = (file: File) => {
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  if (!['.pdf', '.docx', '.pptx'].includes(ext)) {
    ElMessage.error('仅支持 PDF / Word(docx) / PPT(pptx)')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过50MB')
    return false
  }
  return true
}

const uploadCustomerDocument = async (options: any) => {
  if (!activeCustomer.value?.userId) return
  docUploadLoading.value = true
  const formData = new FormData()
  formData.append('file', options.file)
  try {
    await request.post(`/admin/documents/${activeCustomer.value.userId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
    options.onSuccess?.({}, options.file)
    ElMessage.success('资料已上传，正在抽取客户知识')
    await loadDocuments()
    setTimeout(loadDocuments, 4000)
  } catch (e: any) {
    options.onError?.(e)
    ElMessage.error(e?.response?.data?.detail || '上传资料失败')
  } finally {
    docUploadLoading.value = false
  }
}

const reprocessDocument = async (row: any) => {
  try {
    await request.post(`/admin/documents/${row.id}/reprocess`)
    ElMessage.success('已重新触发抽取')
    await loadDocuments()
    setTimeout(loadDocuments, 4000)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重跑失败')
  }
}

const openReviewDialog = (row: any) => {
  activeDocument.value = row
  const data = row.extraction?.reviewed_data || row.extraction?.extracted_data || emptyReviewData()
  reviewForm.value = normalizeReviewData(data)
  reviewAdvantagesText.value = (reviewForm.value.company_info.advantages || []).join('\n')
  reviewNotesText.value = (reviewForm.value.important_notes || []).map((n: any) => n.note || '').filter(Boolean).join('\n')
  reviewDialogVisible.value = true
}

const approveDocument = async () => {
  if (!activeDocument.value) return
  approveLoading.value = true
  try {
    const payload = buildReviewedPayload()
    await request.post(`/admin/documents/${activeDocument.value.id}/approve`, { reviewed_data: payload })
    ElMessage.success('已写入客户 Memory')
    reviewDialogVisible.value = false
    await loadDocuments()
    if (activeCustomer.value?.userId) {
      const res: any = await request.get(`/admin/memory/${activeCustomer.value.userId}`)
      profileData.value = res
      agentNotes.value = res?.agent_notes || ''
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '写入 Memory 失败')
  } finally {
    approveLoading.value = false
  }
}

const addScreenResource = () => {
  reviewForm.value.screen_resources.push({
    city: '', location: '', name: '', type: '', size: '', resolution: '', daily_traffic: '', highlights: ''
  })
}

const addPastCase = () => {
  reviewForm.value.past_cases.push({
    title: '', brand: '', city: '', location: '', year: '', content_type: '', highlights: ''
  })
}

function emptyReviewData() {
  return {
    company_info: { name: '', description: '', advantages: [] },
    screen_resources: [],
    past_cases: [],
    important_notes: [],
  }
}

function normalizeReviewData(data: any) {
  const base = emptyReviewData()
  const copy = JSON.parse(JSON.stringify(data || {}))
  return {
    company_info: {
      ...base.company_info,
      ...(copy.company_info || {}),
      advantages: Array.isArray(copy.company_info?.advantages) ? copy.company_info.advantages : [],
    },
    screen_resources: Array.isArray(copy.screen_resources) ? copy.screen_resources : [],
    past_cases: Array.isArray(copy.past_cases) ? copy.past_cases : [],
    important_notes: Array.isArray(copy.important_notes) ? copy.important_notes : [],
  }
}

function buildReviewedPayload() {
  const data = JSON.parse(JSON.stringify(reviewForm.value))
  data.company_info.advantages = reviewAdvantagesText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  data.important_notes = reviewNotesText.value
    .split('\n')
    .map((note) => note.trim())
    .filter(Boolean)
    .map((note) => ({ note }))
  data.screen_resources = (data.screen_resources || []).filter((s: any) => s.city || s.location || s.name || s.type)
  data.past_cases = (data.past_cases || []).filter((c: any) => c.title || c.brand)
  return data
}

const docStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    uploaded: '已上传',
    processing: '处理中',
    pending_review: '待审核',
    approved: '已写入',
    failed: '失败',
  }
  return map[status] || status || '-'
}

const docStatusType = (status: string) => {
  const map: Record<string, string> = {
    uploaded: 'info',
    processing: 'warning',
    pending_review: 'primary',
    approved: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const triggerCrawl = async (row: any) => {
  row._crawling = true
  try {
    await request.post(`/admin/memory/${row.userId}/crawl`, {
      company_name: row.company || '',
    })
    ElMessage.success('已触发官网分析，请稍后查看结果')
    // 8 秒后刷新
    setTimeout(() => {
      loadCustomers()
      row._crawling = false
    }, 8000)
  } catch (e: any) {
    const detail = e?.response?.data?.detail || '触发分析失败'
    ElMessage.error(detail)
    row._crawling = false
  }
}

const saveNotes = async () => {
  if (!activeCustomer.value) return
  notesLoading.value = true
  try {
    await request.put(`/admin/memory/${activeCustomer.value.userId}/notes`, {
      agent_notes: agentNotes.value,
    })
    ElMessage.success('备忘已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    notesLoading.value = false
  }
}

const formatTime = (ts: string) => {
  if (!ts) return '-'
  try {
    return new Date(ts).toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return ts }
}

const statusLabel = (s: string) => {
  const m: Record<string, string> = {
    completed: '已完成', in_production: '制作中',
    pending_assign: '待确认', cancelled: '已取消',
  }
  return m[s] || s || '-'
}

const statusTag = (s: string) => {
  const m: Record<string, string> = {
    completed: 'success', in_production: '', cancelled: 'danger',
  }
  return m[s] || 'info'
}

onMounted(() => {
  loadCustomers()
})
</script>

<style scoped>
.customer-page {
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

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.username {
  font-weight: 500;
  font-size: 14px;
}

.user-phone {
  font-size: 12px;
  color: #909399;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

/* Drawer Profile */
.loading-center {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 40px 0;
  color: #909399;
}

.profile-detail {
  padding: 0 8px;
}

.profile-section {
  margin-bottom: 24px;
}

.section-header,
.review-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-header h4,
.review-block-header h4 {
  margin: 0;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.profile-section h4 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #303133;
  border-bottom: 1px solid #EBEEF5;
  padding-bottom: 8px;
}

.profile-section .section-header h4,
.review-block-header h4 {
  margin: 0;
  padding-bottom: 0;
  border-bottom: 0;
}

.section-header + .el-table {
  margin-top: 0;
}

.document-empty {
  padding: 16px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.review-dialog {
  max-height: 68vh;
  overflow-y: auto;
  padding-right: 4px;
}

.review-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  color: #606266;
  font-size: 13px;
}

.review-error {
  color: #f56c6c;
}

.review-block {
  margin-bottom: 18px;
}

.empty-profile {
  text-align: center;
  padding: 40px 0;
  color: #C0C4CC;
  font-size: 14px;
}
</style>
