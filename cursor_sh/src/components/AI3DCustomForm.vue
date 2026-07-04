<template>
  <div class="ai-3d-custom-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="140px"
      label-position="top"
    >
      <!-- ===== 媒体方表单 ===== -->
      <template v-if="isMediaMode">
        <!-- ■ 基础信息 -->
        <div class="form-stage-label">基础信息</div>

        <el-form-item label="项目名称" prop="project_name">
          <el-input v-model="formData.project_name" placeholder="例如：上海首位中心大屏矩阵裸眼3D OOH项目" />
        </el-form-item>

        <el-form-item label="项目背景 & 媒体简介" prop="resource_background">
          <el-input v-model="formData.resource_background" type="textarea" :rows="3" placeholder="媒体资源的背景介绍，位置特点、日均客流、目标客群等" />
        </el-form-item>

        <el-form-item label="目标受众 & 场景特点" prop="audience_scene">
          <el-input v-model="formData.audience_scene" type="textarea" :rows="2" placeholder="受众画像和场景特征" />
        </el-form-item>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="投放城市 & 媒体位置" prop="city_location">
              <div class="city-location-field">
                <el-cascader
                  v-model="citySelection"
                  :options="cityCascaderOptions"
                  :props="cityCascaderProps"
                  clearable
                  filterable
                  placeholder="省份 / 城市"
                  @change="syncCityLocation"
                />
                <el-input
                  v-model="mediaLocationInput"
                  clearable
                  placeholder="媒体位置，如锦江区春熙路步行街"
                  @blur="syncCityLocation"
                />
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="媒体定位 & 品牌调性" prop="media_positioning">
              <el-input v-model="formData.media_positioning" placeholder="选填，适配的品牌类型" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ■ 创意方向 -->
        <div class="form-stage-label">创意方向</div>

        <el-form-item label="观看动线说明" prop="viewing_path">
          <el-input v-model="formData.viewing_path" type="textarea" :rows="2" placeholder="观众主要视角、人流方向、最佳观看点" />
        </el-form-item>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="艺术方向 & 风格偏好" prop="art_direction">
              <el-input v-model="formData.art_direction" placeholder="未来科技/自然生态/城市文化/抽象艺术等" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="内容主题 & 核心表达" prop="theme_concept">
              <el-input v-model="formData.theme_concept" placeholder="核心概念、IP形象、品牌露出等" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ■ 技术与交付 -->
        <div class="form-stage-label">技术与交付</div>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="媒体尺寸 & 物理规格" prop="media_specs">
              <el-input v-model="formData.media_specs" placeholder="屏幕分辨率、物理尺寸" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="技术需求" prop="tech_delivery">
              <el-input v-model="formData.tech_delivery" placeholder="分辨率、格式、帧率、色彩空间等" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="素材审核规范 & 周期" prop="content_review">
          <el-input v-model="formData.content_review" type="textarea" :rows="2" placeholder="审核要求、周期、需规避的内容等" />
        </el-form-item>

        <el-row :gutter="24">
          <el-col :span="8">
            <el-form-item label="投放时长 & 数量" prop="timing_number">
              <el-input v-model="formData.timing_number" placeholder="选填，如15秒x3支" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目制作预算" prop="budget">
              <el-input v-model="formData.budget" placeholder="选填" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预计上刊时间" prop="online_time">
              <el-input v-model="formData.online_time" placeholder="最迟报审时间" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="其他特殊合作要求" prop="special_requirements">
          <el-input v-model="formData.special_requirements" type="textarea" :rows="2" placeholder="选填，特殊定制效果等" />
        </el-form-item>

        <el-form-item label="现场实拍图和其他文件上传" prop="scenePhotos">
          <FileUpload 
            v-model="formData.scenePhotos"
            :accept="supportingFileAccept"
            :limit="10"
            tip-text="支持现场图片、PDF、PPT/PPTX、Word、Excel、压缩包、视频等文件，最多10个，单个不超过50MB"
          />
        </el-form-item>
      </template>

      <!-- ===== 品牌方表单（原版） ===== -->
      <template v-else>
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="品牌与产品关键词" prop="brand">
              <el-input v-model="formData.brand" placeholder="例如：蒙牛；酸酸乳..." />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标受众" prop="target_group">
              <el-input v-model="formData.target_group" placeholder="例如：18-25岁年轻女性" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="项目背景" prop="background">
          <el-input v-model="formData.background" type="textarea" :rows="2" placeholder="填写项目启动背景、核心目的等" />
        </el-form-item>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="品牌调性" prop="brand_tone">
              <el-input v-model="formData.brand_tone" placeholder="例如：高端、简约、科技感" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风格偏好" prop="style">
              <el-input v-model="formData.style" placeholder="例如：赛博朋克、写实、水墨" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="内容需求 (方案必备要素)" prop="content">
          <el-input v-model="formData.content" type="textarea" :rows="3" placeholder="详细描述所需的创意场景、画面元素要求等" />
        </el-form-item>

        <el-form-item label="品牌禁忌内容" prop="prohibited_content">
          <el-input v-model="formData.prohibited_content" placeholder="填写不可出现的元素（如：避免红色、避免涉及某竞品）" />
        </el-form-item>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="投放城市或站点" prop="city">
              <el-input v-model="formData.city" placeholder="例如：上海、北京各大商圈" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="投放媒体及尺寸" prop="media_size">
              <el-input v-model="formData.media_size" placeholder="例如：转角LED屏 1920x1080" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="8">
            <el-form-item label="投放时长与数量" prop="time_number">
              <el-input v-model="formData.time_number" placeholder="例如：15秒x10个" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="技术需求" prop="technology">
              <el-input v-model="formData.technology" placeholder="例如：4K, MP4, H264" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="制作预算" prop="budget">
              <el-input v-model="formData.budget" placeholder="例如：5万元" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="24">
            <el-form-item label="预计上刊时间" prop="online_time">
              <el-input v-model="formData.online_time" placeholder="例如：2024年10月1日" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="现场实拍图和其他文件上传" prop="scenePhotos">
          <FileUpload 
            v-model="formData.scenePhotos"
            :accept="supportingFileAccept"
            :limit="10"
            tip-text="支持现场图片、PDF、PPT/PPTX、Word、Excel、压缩包、视频等文件，最多10个，单个不超过50MB"
          />
        </el-form-item>
      </template>
    </el-form>
    
    <div class="production-notice">
      <el-alert
        title="制作周期说明"
        type="info"
        :closable="false"
      >
        <template #default>
          <p>AI驱动3D OOH内容定制服务预计制作周期为 <strong>15个工作日</strong>。</p>
          <p>制作完成后，我们将上传初版预览供您确认。您可以提出修改意见，我们将根据反馈进行调整。</p>
        </template>
      </el-alert>
    </div>
    
    <div class="form-actions">
      <button class="btn-secondary" @click="handleCancel">取消</button>
      <button class="btn-draft" @click="handleSaveDraft">保存为订单草稿</button>
      <button class="btn-primary" @click="handleSubmit">确认提交</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import provinceCityData from '@/data/chinaProvinceCities.json'
import FileUpload from './FileUpload.vue'
import type { UploadedFile, Order } from '@/types'

const isMediaMode = (import.meta.env.VITE_AGENT_MODE || 'media') === 'media'

const props = defineProps<{
  order?: Order
}>()

const emit = defineEmits<{
  submit: [data: any]
  'save-draft': [data: any]
  cancel: []
}>()

const formRef = ref<FormInstance>()
const supportingFileAccept = [
  'image/*',
  '.pdf',
  '.ppt',
  '.pptx',
  '.key',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.zip',
  '.rar',
  '.7z',
  '.mp4',
  '.mov',
  '.avi',
].join(',')
type RegionNode = {
  code: string
  name: string
  children?: RegionNode[]
}

type CascaderOption = {
  value: string
  label: string
  children?: CascaderOption[]
}

type CityPathCandidate = {
  text: string
  selection: string[]
  requireNonAdministrativeNext?: boolean
}

const citySelection = ref<string[]>([])
const mediaLocationInput = ref('')

const directAdminProvinceNames = new Set(['北京市', '天津市', '上海市', '重庆市', '香港特别行政区', '澳门特别行政区'])

const supplementalProvinceCities: RegionNode[] = [
  {
    code: '71',
    name: '台湾省',
    children: [
      { code: '7101', name: '台北市' },
      { code: '7102', name: '新北市' },
      { code: '7103', name: '桃园市' },
      { code: '7104', name: '台中市' },
      { code: '7105', name: '台南市' },
      { code: '7106', name: '高雄市' },
      { code: '7107', name: '基隆市' },
      { code: '7108', name: '新竹市' },
      { code: '7109', name: '嘉义市' },
      { code: '7110', name: '新竹县' },
      { code: '7111', name: '苗栗县' },
      { code: '7112', name: '彰化县' },
      { code: '7113', name: '南投县' },
      { code: '7114', name: '云林县' },
      { code: '7115', name: '嘉义县' },
      { code: '7116', name: '屏东县' },
      { code: '7117', name: '宜兰县' },
      { code: '7118', name: '花莲县' },
      { code: '7119', name: '台东县' },
      { code: '7120', name: '澎湖县' },
      { code: '7121', name: '金门县' },
      { code: '7122', name: '连江县' },
    ],
  },
  {
    code: '81',
    name: '香港特别行政区',
    children: [{ code: '810000', name: '香港特别行政区' }],
  },
  {
    code: '82',
    name: '澳门特别行政区',
    children: [{ code: '820000', name: '澳门特别行政区' }],
  },
]

const provinceCitySource = [...(provinceCityData as RegionNode[]), ...supplementalProvinceCities]

const getCityChildren = (province: RegionNode) => {
  if (directAdminProvinceNames.has(province.name)) {
    return [{ code: `${province.code}0000`, name: province.name }]
  }
  return province.children || []
}

const cityCascaderOptions: CascaderOption[] = provinceCitySource.map(province => ({
  value: province.code,
  label: province.name,
  children: getCityChildren(province).map(city => ({
    value: city.code,
    label: city.name,
  })),
}))

const cityCascaderProps = {
  expandTrigger: 'hover' as const,
}

const normalizeLocationPart = (value = '') => value.trim().replace(/\s+/g, ' ')

const getSelectedCityLabels = () => {
  const [provinceCode, cityCode] = citySelection.value
  const province = cityCascaderOptions.find(option => option.value === provinceCode)
  const city = province?.children?.find(option => option.value === cityCode)

  return {
    province: province?.label || '',
    city: city?.label || '',
  }
}

const formatCitySelection = () => {
  const { province, city } = getSelectedCityLabels()
  if (!province) return ''
  if (!city || city === province) return province
  return `${province} ${city}`
}

const composeCityLocation = () => {
  return [formatCitySelection(), mediaLocationInput.value]
    .map(normalizeLocationPart)
    .filter(Boolean)
    .join(' ')
}

const getNameAliases = (name: string) => {
  const aliases = new Set([name])
  aliases.add(name.replace(/省$/, ''))
  aliases.add(name.replace(/市$/, ''))
  aliases.add(name.replace(/特别行政区$/, ''))
  aliases.add(name.replace(/自治区$/, '').replace(/(壮族|回族|维吾尔|藏族)$/, ''))
  return Array.from(aliases).filter(Boolean)
}

const cleanLocationRemainder = (value: string) => {
  return value.replace(/^[\s,，、/|｜&-]+/, '').trim()
}

const getCityPathCandidates = () => {
  return cityCascaderOptions.flatMap(province => {
    return (province.children || []).flatMap(city => {
      const provinceAliases = getNameAliases(province.label)
      const cityAliases = getNameAliases(city.label)
      const combinedCandidates: CityPathCandidate[] = city.label === province.label
        ? provinceAliases.map(text => ({ text, selection: [province.value, city.value] }))
        : provinceAliases.flatMap(provinceAlias => cityAliases.flatMap(cityAlias => [
            { text: `${provinceAlias} ${cityAlias}`, selection: [province.value, city.value] },
            { text: `${provinceAlias}${cityAlias}`, selection: [province.value, city.value] },
          ]))

      const cityOnlyCandidates: CityPathCandidate[] = city.label === province.label
        ? []
        : [
            { text: city.label, selection: [province.value, city.value] },
            ...cityAliases
              .filter(alias => alias !== city.label)
              .map(alias => ({
                text: alias,
                selection: [province.value, city.value],
                requireNonAdministrativeNext: true,
              })),
          ]

      return [...combinedCandidates, ...cityOnlyCandidates]
        .filter(Boolean)
    })
  })
    .filter((candidate, index, candidates) => {
      return candidates.findIndex(item => item.text === candidate.text && item.selection.join('/') === candidate.selection.join('/')) === index
    })
    .sort((a, b) => b.text.length - a.text.length)
}

const cityPathCandidates = getCityPathCandidates()
const administrativeNextChars = new Set(['区', '县', '市', '州', '盟'])

const splitCityLocation = (value = '') => {
  const location = normalizeLocationPart(value)
  if (!location) {
    return { selection: [] as string[], mediaLocation: '' }
  }

  for (const candidate of cityPathCandidates) {
    const nextChar = location.charAt(candidate.text.length)
    if (
      location.startsWith(candidate.text) &&
      (!candidate.requireNonAdministrativeNext || !administrativeNextChars.has(nextChar))
    ) {
      return {
        selection: candidate.selection,
        mediaLocation: cleanLocationRemainder(location.slice(candidate.text.length)),
      }
    }
  }

  return { selection: [] as string[], mediaLocation: location }
}

const syncCityLocation = () => {
  formData.city_location = composeCityLocation()
  if (citySelection.value.length >= 2) {
    formRef.value?.clearValidate('city_location')
  }
}

const formData = reactive({
  // 品牌方字段
  brand: '',
  background: '',
  target_group: '',
  brand_tone: '',
  content: '',
  style: '',
  prohibited_content: '',
  city: '',
  media_size: '',
  time_number: '',
  technology: '',
  budget: '',
  online_time: '',
  scenePhotos: [] as UploadedFile[],
  // 媒体方字段
  project_name: '',
  resource_background: '',
  audience_scene: '',
  media_positioning: '',
  city_location: '',
  viewing_path: '',
  art_direction: '',
  theme_concept: '',
  media_specs: '',
  timing_number: '',
  tech_delivery: '',
  content_review: '',
  special_requirements: '',
  remarks: '',
})

// 编辑模式：填充表单数据
onMounted(() => {
  if (props.order && props.order.orderType === 'ai_3d_custom') {
    const order = props.order as any
    // 通用填充：遍历 formData 的 key，从 order 中取值
    Object.keys(formData).forEach(key => {
      if (key in order && order[key] !== undefined && order[key] !== null) {
        (formData as any)[key] = order[key]
      }
    })
  } else {
    // 检查是否有 AI 助手传过来的草稿数据
    const draftStr = sessionStorage.getItem('ai_draft_order')
    if (draftStr) {
      try {
        const draft = JSON.parse(draftStr)
        Object.keys(draft).forEach(key => {
          if (key in formData && draft[key] !== undefined && draft[key] !== null) {
            (formData as any)[key] = draft[key]
          }
        })
      } catch (e) {
        console.error('解析AI草稿数据失败', e)
      }
      // 提取后清除草稿数据，以免影响后续新建单
      sessionStorage.removeItem('ai_draft_order')
    }
  }
  const parts = splitCityLocation(formData.city_location)
  citySelection.value = parts.selection
  mediaLocationInput.value = parts.mediaLocation
  syncCityLocation()
})

watch([citySelection, mediaLocationInput], syncCityLocation, { deep: true })

const formRules: FormRules = isMediaMode ? {
  project_name: [
    { required: true, message: '请填写项目名称', trigger: 'blur' }
  ],
  city_location: [
    {
      validator: (_rule, _value, callback) => {
        if (citySelection.value.length < 2) {
          callback(new Error('请选择投放省份和城市'))
          return
        }
        callback()
      },
      trigger: ['change', 'blur'],
    }
  ],
} : {
  brand: [
    { required: true, message: '请填写品牌关键词', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请填写内容需求', trigger: 'blur' }
  ],
  budget: [
    { max: 50, message: '不能超过50个字符', trigger: 'blur' }
  ],
  online_time: [
    { max: 50, message: '不能超过50个字符', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const isEdit = !!props.order
        const confirmItems = isMediaMode
          ? `<li>项目名称及媒体位置已明确</li>
             <li>已上传 ${formData.scenePhotos.length} 个现场/参考文件</li>
             <li>预计制作周期：15个工作日</li>`
          : `<li>品牌与内容要求已明确</li>
             <li>已上传 ${formData.scenePhotos.length} 个现场/参考文件</li>
             <li>预计制作周期：15个工作日</li>`
        await ElMessageBox.confirm(
          `
            <div style="text-align: left;">
              <p>${isEdit ? '请确认您已核对所有修改信息：' : '请确认您已核对所有信息：'}</p>
              <ul style="margin: 12px 0; padding-left: 20px;">
                ${confirmItems}
              </ul>
              <p>${isEdit ? '提交后，订单将被更新。' : '提交后，我们将立即开始制作。'}</p>
            </div>
          `,
          isEdit ? '确认修改' : '确认提交',
          {
            confirmButtonText: isEdit ? '确认修改' : '确认提交',
            cancelButtonText: '再检查一下',
            type: 'info',
            dangerouslyUseHTMLString: true
          }
        )
        
        emit('submit', { ...formData })
      } catch {
        // 用户取消
      }
    }
  })
}

const handleCancel = () => {
  emit('cancel')
}

const handleSaveDraft = () => {
  emit('save-draft', { ...formData })
}
</script>

<style lang="scss" scoped>
.ai-3d-custom-form {
  padding: 0; /* No internal card padding */
}

.form-stage-label {
  font-size: 16px;
  font-weight: 700;
  color: var(--uv-ws-action-button-bg, #A0522D);
  text-transform: uppercase;
  letter-spacing: 0.02em;
  margin: 32px 0 18px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(160, 82, 45, 0.22);

  &:first-child {
    margin-top: 0;
  }
}

.city-location-field {
  display: grid;
  grid-template-columns: minmax(118px, 0.38fr) minmax(180px, 0.62fr);
  gap: 10px;
  width: 100%;

  :deep(.el-cascader) {
    width: 100%;
  }
}

.production-notice {
  margin: 32px 0 24px 0;
  padding: 16px 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  
  :deep(.el-alert) {
    background: transparent;
    border: none;
    padding: 0;
    
    .el-alert__title {
      font-family: 'SF Mono', 'Menlo', monospace;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #747474;
    }
    
    .el-alert__icon {
      display: none;
    }
    
    p {
      margin: 8px 0;
      font-size: 13px;
      line-height: 1.6;
      color: #414754;
      
      &:first-child {
        margin-top: 8px;
      }
      
      &:last-child {
        margin-bottom: 0;
      }
      
      strong {
        color: #1a1c1c;
        font-weight: 600;
      }
    }
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.btn-primary {
  background: var(--uv-ws-action-button-bg, #A0522D);
  color: var(--uv-ws-action-button-text, #ffffff);
  border: none;
  padding: 10px 24px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
  font-family: inherit;
}

.btn-primary:hover {
  background: var(--uv-ws-action-button-hover, #8F4527);
}

.btn-secondary {
  background: transparent;
  color: #414754;
  border: 1px solid rgba(0, 0, 0, 0.12);
  padding: 10px 24px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-secondary:hover {
  border-color: rgba(0, 0, 0, 0.3);
  color: #1a1c1c;
}

.btn-draft {
  background: transparent;
  color: var(--uv-ws-action-button-bg, #A0522D);
  border: 1px solid var(--uv-ws-action-button-bg, #A0522D);
  padding: 10px 24px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-draft:hover {
  background: var(--uv-ws-module-active-bg, #F3E7E1);
}

:deep(.el-form-item__label) {
  font-weight: 500;
  font-size: 13px;
  color: #1a1c1c;
  letter-spacing: -0.01em;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08) !important;
  transition: box-shadow 0.2s;
}

:deep(.el-input__wrapper:focus-within),
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.15) !important;
}

@media (max-width: 720px) {
  .city-location-field {
    grid-template-columns: 1fr;
  }
}
</style>
