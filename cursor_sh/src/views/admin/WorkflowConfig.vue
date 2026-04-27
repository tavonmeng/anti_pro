<template>
  <div class="workflow-config">
    <div class="page-header">
      <h1 class="page-title">工作流配置</h1>
      <p class="page-desc">管理承包商项目的工作流环节、天数和审核项</p>
    </div>

    <div class="config-card">
      <div class="config-header">
        <h2 class="config-title">环节列表</h2>
        <el-button type="primary" size="small" @click="showAddDialog">新增环节</el-button>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>

      <div v-else class="stage-list">
        <div v-for="(stage, idx) in stages" :key="stage.id" class="stage-item">
          <div class="stage-order">
            <div class="order-controls">
              <el-button
                :disabled="idx === 0"
                circle
                size="small"
                @click="moveStage(idx, -1)"
              ><el-icon><ArrowUp /></el-icon></el-button>
              <span class="order-num">{{ idx + 1 }}</span>
              <el-button
                :disabled="idx === stages.length - 1"
                circle
                size="small"
                @click="moveStage(idx, 1)"
              ><el-icon><ArrowDown /></el-icon></el-button>
            </div>
          </div>

          <div class="stage-info">
            <div class="stage-name">{{ stage.name }}</div>
            <div class="stage-meta">
              <el-tag type="info" size="small">{{ stage.defaultDays }} 天</el-tag>
              <span class="review-count">{{ (stage.reviewItems || []).length }} 项审核</span>
            </div>
          </div>

          <div class="stage-review-items">
            <el-tag
              v-for="item in (stage.reviewItems || [])"
              :key="item"
              size="small"
              effect="plain"
              class="review-tag"
            >{{ item }}</el-tag>
          </div>

          <div class="stage-actions">
            <el-button link size="small" type="primary" @click="editStage(stage)">编辑</el-button>
            <el-button link size="small" type="danger" @click="deleteStage(stage)">删除</el-button>
          </div>
        </div>
      </div>

      <div class="total-days" v-if="stages.length > 0">
        总计：{{ stages.reduce((s, st) => s + st.defaultDays, 0) }} 工作日
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingStage ? '编辑环节' : '新增环节'" width="480px">
      <el-form label-position="top">
        <el-form-item label="环节名称" required>
          <el-input v-model="stageForm.name" placeholder="如：方案、原画、模型" />
        </el-form-item>
        <el-form-item label="默认工作日" required>
          <el-input-number v-model="stageForm.defaultDays" :min="1" :max="30" />
        </el-form-item>
        <el-form-item label="审核检查项">
          <div class="review-editor">
            <div v-for="(item, idx) in stageForm.reviewItems" :key="idx" class="review-edit-item">
              <el-input v-model="stageForm.reviewItems[idx]" size="small" />
              <el-button link type="danger" @click="stageForm.reviewItems.splice(idx, 1)">删除</el-button>
            </div>
            <el-button size="small" @click="stageForm.reviewItems.push('')">添加审核项</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveStage">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import request from '@/utils/request'

const stages = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingStage = ref<any>(null)
const saving = ref(false)

const stageForm = reactive({
  name: '',
  defaultDays: 3,
  reviewItems: ['内容安全合规性', '风格与品牌调性一致', '技术规格达标', '无版权/商标侵权风险'] as string[],
})

const fetchStages = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/workflow-config')
    stages.value = res.data || []
  } catch { /* ignore */ }
  finally { loading.value = false }
}

const showAddDialog = () => {
  editingStage.value = null
  stageForm.name = ''
  stageForm.defaultDays = 3
  stageForm.reviewItems = ['内容安全合规性', '风格与品牌调性一致', '技术规格达标', '无版权/商标侵权风险']
  dialogVisible.value = true
}

const editStage = (stage: any) => {
  editingStage.value = stage
  stageForm.name = stage.name
  stageForm.defaultDays = stage.defaultDays
  stageForm.reviewItems = [...(stage.reviewItems || [])]
  dialogVisible.value = true
}

const saveStage = async () => {
  if (!stageForm.name) {
    ElMessage.warning('请输入环节名称')
    return
  }
  saving.value = true
  try {
    const cleanItems = stageForm.reviewItems.filter(i => i.trim())
    if (editingStage.value) {
      await request.put(`/api/workflow-config/${editingStage.value.id}`, {
        name: stageForm.name,
        default_days: stageForm.defaultDays,
        review_items: cleanItems,
      })
      ElMessage.success('更新成功')
    } else {
      await request.post('/api/workflow-config', {
        name: stageForm.name,
        default_days: stageForm.defaultDays,
        review_items: cleanItems,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchStages()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const deleteStage = async (stage: any) => {
  try {
    await ElMessageBox.confirm(`确认删除环节"${stage.name}"？`, '确认操作', { type: 'warning' })
    await request.delete(`/api/workflow-config/${stage.id}`)
    ElMessage.success('已删除')
    fetchStages()
  } catch { /* cancelled */ }
}

const moveStage = async (idx: number, direction: number) => {
  const newIdx = idx + direction
  if (newIdx < 0 || newIdx >= stages.value.length) return
  const arr = [...stages.value]
  ;[arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]]
  stages.value = arr

  // 发送排序请求
  try {
    await request.post('/api/workflow-config/reorder', {
      stage_ids: arr.map(s => s.id),
    })
  } catch {
    fetchStages() // 回滚
  }
}

onMounted(fetchStages)
</script>

<style lang="scss" scoped>
.workflow-config { max-width: 800px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #1D1D1F; margin: 0 0 4px; }
.page-desc { font-size: 14px; color: #86868B; margin: 0; }
.config-card {
  background: #fff; border-radius: 12px; padding: 24px;
  border: 1px solid #E5E7EB;
}
.config-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.config-title { font-size: 16px; font-weight: 600; color: #1D1D1F; margin: 0; }
.loading-state { text-align: center; padding: 40px; color: #86868B; }

.stage-list { display: flex; flex-direction: column; gap: 12px; }
.stage-item {
  display: flex; align-items: center; gap: 16px; padding: 16px;
  background: #F9FAFB; border-radius: 10px; border: 1px solid #E5E7EB;
  transition: all 0.2s;
  &:hover { border-color: #409eff; }
}
.stage-order { flex-shrink: 0; }
.order-controls { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.order-num { font-size: 16px; font-weight: 700; color: #1D1D1F; margin: 2px 0; }
.stage-info { flex: 1; min-width: 0; }
.stage-name { font-size: 15px; font-weight: 600; color: #1D1D1F; }
.stage-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.review-count { font-size: 12px; color: #86868B; }
.stage-review-items { display: flex; flex-wrap: wrap; gap: 4px; max-width: 300px; }
.review-tag { font-size: 11px; }
.stage-actions { flex-shrink: 0; display: flex; gap: 4px; }
.total-days {
  margin-top: 16px; padding-top: 12px; border-top: 1px solid #E5E7EB;
  text-align: right; font-size: 14px; font-weight: 600; color: #409eff;
}
.review-editor { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.review-edit-item { display: flex; gap: 8px; align-items: center; }
</style>
