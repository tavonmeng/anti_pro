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

    <!-- 全局公司资料 Ingest -->
    <div class="global-ingest-card">
      <div>
        <h3>公司资料库</h3>
        <p>统一管理客户资料资产：原始 PDF/PPTX、解析文本、结构化 memory 都会保存；客户注册或填写企业名称后，Agent 会自动使用匹配到的资料。</p>
      </div>
      <el-upload
        :http-request="uploadCompanyProfileDocument"
        :show-file-list="false"
        accept=".pdf,.pptx,.txt,.md"
      >
        <el-button type="primary" :loading="companyDocUploading">上传公司资料并解析</el-button>
      </el-upload>
    </div>

    <div v-if="companyProfiles.length" class="company-profile-strip">
      <button
        v-for="item in companyProfiles"
        :key="item.company_key"
        class="company-profile-chip"
        type="button"
        @click="openCompanyProfile(item)"
      >
        <strong>{{ item.company_name }}</strong>
        <span>{{ item.document_count }} 份资料</span>
        <span>{{ item.screen_count }} 块屏幕</span>
        <span>查看</span>
      </button>
    </div>

    <div v-if="companyIngestJobs.length" class="company-ingest-jobs">
      <div class="job-list-header">
        <span>最近上传</span>
        <el-button size="small" text @click="loadCompanyIngestJobs">刷新</el-button>
      </div>
      <div v-for="job in companyIngestJobs.slice(0, 5)" :key="job.id" class="job-item">
        <div class="job-main">
          <div class="job-title">
            <span>{{ job.filename }}</span>
            <small v-if="job.company_name">{{ job.company_name }}</small>
          </div>
          <div v-if="job.error" class="job-error">{{ job.error }}</div>
          <div v-else class="job-meta">
            <span v-if="jobStageText(job)">{{ jobStageText(job) }}</span>
            <span v-if="job.page_count">{{ job.page_count }} 页</span>
            <span v-if="job.text_chars">{{ job.text_chars }} 字</span>
            <span>{{ formatTime(job.updated_at || job.created_at) }}</span>
          </div>
        </div>
        <el-tag :type="docStatusType(job.status)" size="small">{{ docStatusText(job.status) }}</el-tag>
      </div>
    </div>

    <div class="company-library-panel">
      <div class="job-list-header">
        <span>资料资产</span>
        <el-button size="small" text @click="loadCompanyLibraryDocuments">刷新</el-button>
      </div>
      <el-table :data="companyLibraryDocuments" size="small" stripe>
        <el-table-column label="资料" min-width="220">
          <template #default="{ row }">
            <div class="doc-name">{{ row.filename }}</div>
            <div class="job-meta">
              <span v-if="row.company_name">{{ row.company_name }}</span>
              <span v-if="row.page_count">{{ row.page_count }} 页</span>
              <span v-if="row.text_chars">{{ row.text_chars }} 字</span>
            </div>
            <div v-if="row.error" class="job-error">{{ row.error }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="docStatusType(row.status)" size="small">{{ docStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="保存资产" min-width="230">
          <template #default="{ row }">
            <div class="asset-links">
              <a v-if="assetUrl(row.raw_file)" :href="assetUrl(row.raw_file)" target="_blank">原文件</a>
              <a v-if="assetUrl(row.extracted_text)" :href="assetUrl(row.extracted_text)" target="_blank">解析文本</a>
              <a v-if="assetUrl(row.structured_memory)" :href="assetUrl(row.structured_memory)" target="_blank">结构化 Memory</a>
              <span v-if="!assetUrl(row.raw_file) && !assetUrl(row.extracted_text) && !assetUrl(row.structured_memory)">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="150">
          <template #default="{ row }">{{ formatTime(row.updated_at || row.created_at) }}</template>
        </el-table-column>
      </el-table>
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
      size="650px"
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

        <!-- 客户资料上传 / Ingest -->
        <div class="profile-section">
          <h4>📄 客户资料</h4>
          <div class="doc-upload-row">
            <el-upload
              :http-request="uploadCustomerDocument"
              :show-file-list="false"
              accept=".pdf,.pptx,.txt,.md"
            >
              <el-button size="small" type="primary" :loading="customerDocUploading">
                上传并解析 PDF/PPTX
              </el-button>
            </el-upload>
            <span class="doc-upload-tip">资料会写入该客户画像，供 Agent 对话使用</span>
          </div>
          <div v-if="profileData.company_info?.customer_documents?.length" class="doc-list">
            <div v-for="doc in profileData.company_info.customer_documents" :key="doc.document_id" class="doc-item">
              <div class="doc-main">
                <div class="doc-name">{{ doc.filename }}</div>
                <div v-if="doc.ingest_result?.brief" class="doc-brief">{{ doc.ingest_result.brief }}</div>
                <div v-else-if="doc.ingest_error" class="doc-error">{{ doc.ingest_error }}</div>
              </div>
              <el-tag :type="docStatusType(doc.ingest_status)" size="small">{{ docStatusText(doc.ingest_status) }}</el-tag>
            </div>
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
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="size" label="尺寸" width="80" />
            <el-table-column prop="daily_media_contacts" label="日媒体接触人次" width="140" />
            <el-table-column prop="daily_traffic" label="客流/曝光" width="120" />
          </el-table>
        </div>

        <!-- 项目偏好 -->
        <div v-if="hasPreferences" class="profile-section">
          <h4>📊 项目偏好</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="常用城市">{{ profileData.project_preferences?.common_cities?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="偏好风格">{{ profileData.project_preferences?.preferred_styles?.join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="预算范围">{{ profileData.project_preferences?.budget_range || '-' }}</el-descriptions-item>
            <el-descriptions-item label="典型时长">{{ profileData.project_preferences?.typical_duration || '-' }}</el-descriptions-item>
            <el-descriptions-item v-if="profileData.project_preferences?.notes" label="备注" :span="2">
              {{ profileData.project_preferences.notes }}
            </el-descriptions-item>
          </el-descriptions>
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
        <div v-if="!profileData.company_info?.description && !profileData.screen_resources?.length && !profileData.past_projects?.length && !profileData.interaction_stats?.total_sessions" class="empty-profile">
          暂无画像数据。点击「分析官网」可自动爬取客户公司信息。
        </div>
      </div>
    </el-drawer>

    <!-- 公司资料详情抽屉 -->
    <el-drawer
      v-model="companyProfileDrawerVisible"
      :title="`公司资料 — ${activeCompanyProfile?.company_name || ''}`"
      size="720px"
      direction="rtl"
    >
      <div v-if="companyProfileLoading" class="loading-center">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-else-if="activeCompanyProfile" class="profile-detail">
        <div class="company-profile-actions">
          <el-button v-if="!companyProfileEditing" size="small" type="primary" @click="beginEditCompanyProfile">编辑资料</el-button>
          <template v-else>
            <el-button size="small" type="primary" :loading="companyProfileSaving" @click="saveCompanyProfile">保存</el-button>
            <el-button size="small" @click="cancelEditCompanyProfile">取消</el-button>
          </template>
        </div>

        <div v-if="companyProfileEditing" class="profile-section">
          <h4>编辑内容</h4>
          <el-form label-position="top">
            <el-form-item label="公司名称">
              <el-input v-model="companyProfileForm.company_name" />
            </el-form-item>
            <el-form-item label="管理员备注">
              <el-input v-model="companyProfileForm.notes" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="画像 JSON">
              <el-input v-model="companyProfileForm.profile_data_json" type="textarea" :rows="12" />
            </el-form-item>
            <el-form-item label="屏幕资源 JSON">
              <el-input v-model="companyProfileForm.screen_resources_json" type="textarea" :rows="10" />
            </el-form-item>
          </el-form>
        </div>

        <div class="profile-section">
          <h4>资料摘要</h4>
          <p class="profile-brief">{{ activeCompanyProfile.profile_data?.brief || '-' }}</p>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="公司名称">{{ activeCompanyProfile.profile_data?.company_info?.company_name || activeCompanyProfile.company_name }}</el-descriptions-item>
            <el-descriptions-item label="行业">{{ activeCompanyProfile.profile_data?.company_info?.industry || '-' }}</el-descriptions-item>
            <el-descriptions-item label="公司定位">{{ activeCompanyProfile.profile_data?.company_info?.company_positioning || '-' }}</el-descriptions-item>
            <el-descriptions-item label="主营业务">{{ formatList(activeCompanyProfile.profile_data?.company_info?.business_scope) }}</el-descriptions-item>
            <el-descriptions-item label="核心卖点">{{ formatList(activeCompanyProfile.profile_data?.company_info?.selling_points) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div v-if="activeCompanyProfile.screen_resources?.length" class="profile-section">
          <h4>屏幕资源（{{ activeCompanyProfile.screen_resources.length }} 块）</h4>
          <el-table :data="activeCompanyProfile.screen_resources" size="small" border stripe>
            <el-table-column prop="city" label="城市" width="90" />
            <el-table-column prop="location" label="位置" min-width="150" />
            <el-table-column prop="type" label="特点" min-width="160" />
            <el-table-column prop="size" label="尺寸" width="100" />
            <el-table-column prop="resolution" label="分辨率" width="110" />
            <el-table-column prop="daily_media_contacts" label="日媒体接触人次" width="140" />
          </el-table>
        </div>

        <div class="profile-section">
          <h4>项目信息</h4>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="需求">{{ formatList(activeCompanyProfile.profile_data?.project_requirements) }}</el-descriptions-item>
            <el-descriptions-item label="创意方向">{{ formatList(activeCompanyProfile.profile_data?.creative_direction) }}</el-descriptions-item>
            <el-descriptions-item label="交付物">{{ formatList(activeCompanyProfile.profile_data?.deliverables) }}</el-descriptions-item>
            <el-descriptions-item label="周期预算">{{ formatList(activeCompanyProfile.profile_data?.timeline_budget) }}</el-descriptions-item>
            <el-descriptions-item label="待确认问题">{{ formatList(activeCompanyProfile.profile_data?.questions) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="profile-section">
          <h4>管理员备注</h4>
          <p class="profile-brief">{{ activeCompanyProfile.notes || '-' }}</p>
        </div>

        <div class="profile-section">
          <h4>关联已注册用户</h4>
          <div class="associate-row">
            <el-select
              v-model="attachUserId"
              filterable
              clearable
              placeholder="选择已注册客户"
              style="flex: 1"
            >
              <el-option
                v-for="customer in associateCustomers"
                :key="customer.userId"
                :label="`${customer.username}${customer.company ? ' / ' + customer.company : ''}${customer.phone ? ' / ' + customer.phone : ''}`"
                :value="customer.userId"
              />
            </el-select>
            <el-button type="primary" :loading="attachingCompanyProfile" @click="attachCompanyProfile">
              关联并同步
            </el-button>
          </div>
          <div v-if="activeCompanyProfile.profile_data?.manual_links?.length" class="linked-users">
            <el-tag
              v-for="item in activeCompanyProfile.profile_data.manual_links"
              :key="item.user_id"
              size="small"
            >
              {{ item.username || item.phone || item.user_id }}
            </el-tag>
          </div>
        </div>

        <div v-if="activeCompanyProfile.documents?.length" class="profile-section">
          <h4>来源资料</h4>
          <div class="doc-list">
            <div v-for="doc in activeCompanyProfile.documents" :key="doc.document_id" class="doc-item">
              <div class="doc-main">
                <div class="doc-name">{{ doc.filename }}</div>
                <div class="doc-brief">{{ doc.brief || doc.title || '-' }}</div>
                <div class="asset-links">
                  <a v-if="assetUrl(doc.assets?.raw_file)" :href="assetUrl(doc.assets.raw_file)" target="_blank">原文件</a>
                  <a v-if="assetUrl(doc.assets?.extracted_text)" :href="assetUrl(doc.assets.extracted_text)" target="_blank">解析文本</a>
                  <a v-if="assetUrl(doc.assets?.structured_memory)" :href="assetUrl(doc.assets.structured_memory)" target="_blank">结构化 Memory</a>
                </div>
              </div>
              <span class="doc-time">{{ formatTime(doc.ingested_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Search, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const customers = ref<any[]>([])
const associateCustomers = ref<any[]>([])
const companyProfiles = ref<any[]>([])
const companyIngestJobs = ref<any[]>([])
const companyLibraryDocuments = ref<any[]>([])
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
const customerDocUploading = ref(false)
const companyDocUploading = ref(false)
const companyProfileDrawerVisible = ref(false)
const companyProfileLoading = ref(false)
const activeCompanyProfile = ref<any>(null)
const companyProfileEditing = ref(false)
const companyProfileSaving = ref(false)
const attachUserId = ref('')
const attachingCompanyProfile = ref(false)
const companyProfileForm = ref({
  company_name: '',
  notes: '',
  profile_data_json: '',
  screen_resources_json: '',
})
let companyJobPollTimer: number | undefined

const hasPreferences = computed(() => {
  const pp = profileData.value?.project_preferences
  return pp && (pp.common_cities?.length || pp.preferred_styles?.length || pp.budget_range || pp.typical_duration)
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

const loadCompanyProfiles = async () => {
  try {
    const res: any = await request.get('/admin/memory/company-profiles')
    companyProfiles.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('加载公司资料库失败:', e)
  }
}

const loadCompanyLibraryDocuments = async () => {
  try {
    const res: any = await request.get('/admin/memory/company-library/documents')
    companyLibraryDocuments.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('加载公司资料资产失败:', e)
  }
}

const loadAssociateCustomers = async () => {
  try {
    const res: any = await request.get('/admin/memory/customers', {
      params: { page: 1, pageSize: 100 },
    })
    associateCustomers.value = res?.data || []
  } catch (e) {
    console.error('加载可关联客户失败:', e)
  }
}

const hasRunningCompanyJobs = () => companyIngestJobs.value.some((job) => ['queued', 'processing'].includes(job.status))

const stopCompanyJobPolling = () => {
  if (companyJobPollTimer) {
    window.clearInterval(companyJobPollTimer)
    companyJobPollTimer = undefined
  }
}

const startCompanyJobPolling = () => {
  if (companyJobPollTimer) return
  companyJobPollTimer = window.setInterval(() => {
    loadCompanyIngestJobs()
  }, 5000)
}

const loadCompanyIngestJobs = async () => {
  try {
    const res: any = await request.get('/admin/memory/company-profiles/ingest-jobs')
    companyIngestJobs.value = Array.isArray(res) ? res : []
    if (hasRunningCompanyJobs()) {
      startCompanyJobPolling()
    } else {
      const wasPolling = !!companyJobPollTimer
      stopCompanyJobPolling()
      if (wasPolling) {
        await loadCompanyProfiles()
        await loadCompanyLibraryDocuments()
        await loadCustomers()
      }
    }
  } catch (e) {
    console.error('加载公司资料解析任务失败:', e)
  }
}

const openProfile = async (row: any) => {
  activeCustomer.value = row
  drawerVisible.value = true
  profileLoading.value = true
  profileData.value = null
  agentNotes.value = ''
  try {
    const res: any = await request.get(`/admin/memory/${row.userId}`)
    profileData.value = res
    agentNotes.value = res?.agent_notes || ''
  } catch (e) {
    console.error('加载画像失败:', e)
  } finally {
    profileLoading.value = false
  }
}

const openCompanyProfile = async (item: any) => {
  companyProfileDrawerVisible.value = true
  companyProfileLoading.value = true
  activeCompanyProfile.value = null
  try {
    const res: any = await request.get(`/admin/memory/company-profiles/${encodeURIComponent(item.company_key)}`)
    activeCompanyProfile.value = res
    resetCompanyProfileForm()
    if (!associateCustomers.value.length) {
      await loadAssociateCustomers()
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载公司资料失败')
  } finally {
    companyProfileLoading.value = false
  }
}

const resetCompanyProfileForm = () => {
  if (!activeCompanyProfile.value) return
  companyProfileForm.value = {
    company_name: activeCompanyProfile.value.company_name || '',
    notes: activeCompanyProfile.value.notes || '',
    profile_data_json: JSON.stringify(activeCompanyProfile.value.profile_data || {}, null, 2),
    screen_resources_json: JSON.stringify(activeCompanyProfile.value.screen_resources || [], null, 2),
  }
}

const beginEditCompanyProfile = () => {
  resetCompanyProfileForm()
  companyProfileEditing.value = true
}

const cancelEditCompanyProfile = () => {
  resetCompanyProfileForm()
  companyProfileEditing.value = false
}

const saveCompanyProfile = async () => {
  if (!activeCompanyProfile.value?.company_key) return
  companyProfileSaving.value = true
  try {
    const profileData = JSON.parse(companyProfileForm.value.profile_data_json || '{}')
    const screenResources = JSON.parse(companyProfileForm.value.screen_resources_json || '[]')
    if (!Array.isArray(screenResources)) {
      throw new Error('屏幕资源 JSON 必须是数组')
    }
    const res: any = await request.put(`/admin/memory/company-profiles/${encodeURIComponent(activeCompanyProfile.value.company_key)}`, {
      company_name: companyProfileForm.value.company_name,
      notes: companyProfileForm.value.notes,
      profile_data: profileData,
      screen_resources: screenResources,
    })
    activeCompanyProfile.value = res
    companyProfileEditing.value = false
    ElMessage.success('公司资料已保存')
    await loadCompanyProfiles()
  } catch (e: any) {
    ElMessage.error(e?.message || e?.response?.data?.detail || '保存失败')
  } finally {
    companyProfileSaving.value = false
  }
}

const attachCompanyProfile = async () => {
  if (!activeCompanyProfile.value?.company_key || !attachUserId.value) {
    ElMessage.warning('请选择要关联的客户')
    return
  }
  attachingCompanyProfile.value = true
  try {
    const res: any = await request.post(`/admin/memory/company-profiles/${encodeURIComponent(activeCompanyProfile.value.company_key)}/attach-user`, {
      user_id: attachUserId.value,
    })
    activeCompanyProfile.value = res
    attachUserId.value = ''
    ElMessage.success('已关联并同步到用户画像')
    await loadCustomers()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '关联失败')
  } finally {
    attachingCompanyProfile.value = false
  }
}

const docStatusText = (status?: string) => ({
  queued: '等待解析',
  processing: '解析中',
  text_extracted: '已提取文本',
  success: '已解析',
  failed: '解析失败',
}[status || ''] || '未解析')

const docStatusType = (status?: string) => ({
  queued: 'warning',
  processing: 'warning',
  text_extracted: 'warning',
  success: 'success',
  failed: 'danger',
}[status || ''] || 'info') as '' | 'success' | 'warning' | 'danger' | 'info'

const jobStageText = (job: any) => {
  const result = job?.result || {}
  const stage = result.stage
  if (job?.status === 'success') return ''
  if (stage === 'text_extracted') return '已提取文本'
  if (stage === 'qwen_direct') return 'Qwen 解析中'
  if (stage === 'qwen_chunking') {
    return `分块解析 ${result.chunk_index || '?'} / ${result.chunk_count || '?'}`
  }
  if (stage === 'qwen_merging') return '汇总画像中'
  return ''
}

const uploadCustomerDocument = async (options: any) => {
  if (!activeCustomer.value?.userId) return
  customerDocUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', options.file)
    const token = localStorage.getItem('token')
    const resp = await fetch(`/api/admin/memory/${activeCustomer.value.userId}/documents/ingest`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data?.detail || '上传解析失败')
    }
    ElMessage.success('已上传客户资料并触发解析')
    await openProfile(activeCustomer.value)
    setTimeout(() => {
      if (activeCustomer.value) openProfile(activeCustomer.value)
    }, 10000)
  } catch (e: any) {
    ElMessage.error(e?.message || '上传解析失败')
  } finally {
    customerDocUploading.value = false
  }
}

const uploadCompanyProfileDocument = async (options: any) => {
  companyDocUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', options.file)
    const token = localStorage.getItem('token')
    const resp = await fetch('/api/admin/memory/company-profiles/ingest', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) {
      throw new Error(data?.detail || '公司资料解析失败')
    }
    ElMessage.success(data?.message || '已上传公司资料，后台解析中')
    await loadCompanyIngestJobs()
    await loadCompanyLibraryDocuments()
    startCompanyJobPolling()
  } catch (e: any) {
    ElMessage.error(e?.message || '公司资料解析失败')
  } finally {
    companyDocUploading.value = false
  }
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

const formatList = (value: any) => {
  if (!value) return '-'
  if (Array.isArray(value)) return value.filter(Boolean).join('、') || '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const assetUrl = (asset: any) => asset?.url || ''

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
  loadCompanyProfiles()
  loadCompanyLibraryDocuments()
  loadCompanyIngestJobs()
  loadAssociateCustomers()
})

onUnmounted(() => {
  stopCompanyJobPolling()
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

.global-ingest-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  padding: 16px;
  border: 1px solid #DCDFE6;
  border-radius: 8px;
  background: #fff;
}

.global-ingest-card h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #303133;
}

.global-ingest-card p {
  margin: 0;
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.company-profile-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.company-profile-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid #EBEEF5;
  border-radius: 6px;
  background: #FAFAFA;
  color: #606266;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
}

.company-profile-chip:hover {
  border-color: #409EFF;
  color: #409EFF;
}

.company-profile-chip strong {
  color: #303133;
  font-size: 13px;
}

.company-ingest-jobs {
  margin-top: 12px;
  border: 1px solid #EBEEF5;
  border-radius: 8px;
  background: #fff;
}

.company-library-panel {
  margin-top: 12px;
  border: 1px solid #EBEEF5;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.asset-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
}

.asset-links a {
  color: #409EFF;
  text-decoration: none;
}

.asset-links a:hover {
  text-decoration: underline;
}

.job-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #EBEEF5;
  color: #606266;
  font-size: 13px;
  font-weight: 500;
}

.job-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #F2F3F5;
}

.job-item:last-child {
  border-bottom: none;
}

.job-main {
  flex: 1;
  min-width: 0;
}

.job-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: #303133;
  font-size: 13px;
  font-weight: 500;
}

.job-title span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-title small {
  flex-shrink: 0;
  color: #409EFF;
  font-size: 12px;
  font-weight: 400;
}

.job-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
}

.job-error {
  margin-top: 4px;
  color: #F56C6C;
  font-size: 12px;
  line-height: 1.5;
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

.profile-section h4 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #303133;
  border-bottom: 1px solid #EBEEF5;
  padding-bottom: 8px;
}

.doc-upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.doc-upload-tip {
  color: #909399;
  font-size: 12px;
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #EBEEF5;
  border-radius: 6px;
  background: #FAFAFA;
}

.doc-main {
  flex: 1;
  min-width: 0;
}

.doc-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-brief {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #606266;
}

.doc-error {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #F56C6C;
}

.profile-brief {
  margin: 0 0 12px;
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
}

.doc-time {
  flex-shrink: 0;
  color: #909399;
  font-size: 12px;
  white-space: nowrap;
}

.company-profile-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 12px;
}

.associate-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.linked-users {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.empty-profile {
  text-align: center;
  padding: 40px 0;
  color: #C0C4CC;
  font-size: 14px;
}
</style>
