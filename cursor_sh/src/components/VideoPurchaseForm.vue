<template>
  <div class="video-purchase-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="120px"
      label-position="top"
    >
      <el-form-item label="行业类型" prop="industryType">
        <el-radio-group v-model="formData.industryType" size="large">
          <el-radio-button value="movie">电影</el-radio-button>
          <el-radio-button value="outdoor">户外</el-radio-button>
          <el-radio-button value="custom">自定义</el-radio-button>
        </el-radio-group>
      </el-form-item>
      
      <el-form-item 
        v-if="formData.industryType === 'custom'" 
        label="自定义行业" 
        prop="customIndustry"
      >
        <el-input
          v-model="formData.customIndustry"
          placeholder="请输入自定义行业类型"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="视觉风格" prop="visualStyle">
        <el-radio-group v-model="formData.visualStyle" size="large">
          <el-radio-button value="scifi">科幻</el-radio-button>
          <el-radio-button value="realistic">写真</el-radio-button>
          <el-radio-button value="custom">自定义</el-radio-button>
        </el-radio-group>
      </el-form-item>
      
      <el-form-item 
        v-if="formData.visualStyle === 'custom'" 
        label="自定义风格" 
        prop="customStyle"
      >
        <el-input
          v-model="formData.customStyle"
          placeholder="请输入自定义视觉风格"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="时长（秒）" prop="duration">
        <el-input-number
          v-model="formData.duration"
          :min="1"
          :max="3600"
          :step="1"
          placeholder="请输入视频时长"
          style="width: 100%"
        />
      </el-form-item>
      
      <el-form-item label="价格区间（元）" prop="priceRange">
        <div class="price-range-input">
          <el-input-number
            v-model="formData.priceMin"
            :min="0"
            :step="100"
            placeholder="最低价格"
            style="width: 100%"
          />
          <span class="separator">至</span>
          <el-input-number
            v-model="formData.priceMax"
            :min="formData.priceMin || 0"
            :step="100"
            placeholder="最高价格"
            style="width: 100%"
          />
        </div>
      </el-form-item>
      
      <el-form-item label="分辨率" prop="resolution">
        <el-select v-model="formData.resolution" placeholder="请选择分辨率" style="width: 100%">
          <el-option label="1920x1080 (Full HD)" value="1920x1080" />
          <el-option label="2560x1440 (2K)" value="2560x1440" />
          <el-option label="3840x2160 (4K)" value="3840x2160" />
          <el-option label="7680x4320 (8K)" value="7680x4320" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>
      
      <el-form-item 
        v-if="formData.resolution === 'custom'" 
        label="自定义分辨率" 
        prop="customResolution"
      >
        <el-input
          v-model="formData.customResolution"
          placeholder="例如：1024x768"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="屏幕尺寸" prop="size">
        <el-input
          v-model="formData.size"
          placeholder="例如：55英寸、100x200cm"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="曲率（可选）" prop="curvature">
        <el-input
          v-model="formData.curvature"
          placeholder="例如：1800R、2000R"
          clearable
        />
      </el-form-item>
    </el-form>
    
    <div class="form-actions">
      <el-button @click="handleCancel">取消</el-button>
      <el-button @click="handleSaveDraft">保存草稿</el-button>
      <el-button type="primary" @click="handleSubmit">确认提交</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import type { IndustryType, VisualStyle, Order } from '@/types'

const props = defineProps<{
  order?: Order
}>()

const emit = defineEmits<{
  submit: [data: any]
  'save-draft': [data: any]
  cancel: []
}>()

const formRef = ref<FormInstance>()
const formData = reactive({
  industryType: 'movie' as IndustryType,
  customIndustry: '',
  visualStyle: 'scifi' as VisualStyle,
  customStyle: '',
  duration: 60 as number | undefined,
  priceMin: undefined as number | undefined,
  priceMax: undefined as number | undefined,
  resolution: '3840x2160',
  customResolution: '',
  size: '',
  curvature: ''
})

// 编辑模式：填充表单数据
onMounted(() => {
  if (props.order && props.order.orderType === 'video_purchase') {
    const order = props.order as any
    formData.industryType = order.industryType || 'movie'
    formData.customIndustry = order.customIndustry || ''
    formData.visualStyle = order.visualStyle || 'scifi'
    formData.customStyle = order.customStyle || ''
    formData.duration = order.duration || 60
    formData.priceMin = order.priceRange?.min
    formData.priceMax = order.priceRange?.max
    // 处理分辨率：如果是自定义的，需要判断
    if (order.resolution && !['3840x2160', '1920x1080', '2560x1440'].includes(order.resolution)) {
      formData.resolution = 'custom'
      formData.customResolution = order.resolution
    } else {
      formData.resolution = order.resolution || '3840x2160'
    }
    formData.size = order.size || ''
    formData.curvature = order.curvature || ''
  }
})

const validatePriceRange = (rule: any, value: any, callback: Function) => {
  if (!formData.priceMin || !formData.priceMax) {
    callback(new Error('请输入完整的价格区间'))
  } else if (formData.priceMin >= formData.priceMax) {
    callback(new Error('最高价格必须大于最低价格'))
  } else {
    callback()
  }
}

const formRules: FormRules = {
  industryType: [
    { required: true, message: '请选择行业类型', trigger: 'change' }
  ],
  customIndustry: [
    { required: true, message: '请输入自定义行业类型', trigger: 'blur' }
  ],
  visualStyle: [
    { required: true, message: '请选择视觉风格', trigger: 'change' }
  ],
  customStyle: [
    { required: true, message: '请输入自定义视觉风格', trigger: 'blur' }
  ],
  duration: [
    { required: true, message: '请输入时长', trigger: 'blur' }
  ],
  priceRange: [
    { validator: validatePriceRange, trigger: 'blur' }
  ],
  resolution: [
    { required: true, message: '请选择分辨率', trigger: 'change' }
  ],
  customResolution: [
    { required: true, message: '请输入自定义分辨率', trigger: 'blur' }
  ],
  size: [
    { required: true, message: '请输入屏幕尺寸', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const isEdit = !!props.order
        await ElMessageBox.confirm(
          isEdit 
            ? '请确认您已核对所有修改信息，提交后订单将被更新。'
            : '请确认您已核对所有参数信息，提交后我们将为您适配专属的裸眼3D成片。',
          isEdit ? '确认修改' : '确认提交',
          {
            confirmButtonText: isEdit ? '确认修改' : '确认',
            cancelButtonText: '再检查一下',
            type: 'info'
          }
        )
        
        const submitData = {
          industryType: formData.industryType,
          customIndustry: formData.industryType === 'custom' ? formData.customIndustry : undefined,
          visualStyle: formData.visualStyle,
          customStyle: formData.visualStyle === 'custom' ? formData.customStyle : undefined,
          duration: formData.duration,
          priceRange: {
            min: formData.priceMin!,
            max: formData.priceMax!
          },
          resolution: formData.resolution === 'custom' ? formData.customResolution : formData.resolution,
          size: formData.size,
          curvature: formData.curvature || undefined
        }
        
        emit('submit', submitData)
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
  const submitData = {
    industryType: formData.industryType,
    customIndustry: formData.industryType === 'custom' ? formData.customIndustry : undefined,
    visualStyle: formData.visualStyle,
    customStyle: formData.visualStyle === 'custom' ? formData.customStyle : undefined,
    duration: formData.duration,
    priceRange: (formData.priceMin && formData.priceMax) ? {
      min: formData.priceMin,
      max: formData.priceMax
    } : undefined,
    resolution: formData.resolution === 'custom' ? formData.customResolution : formData.resolution,
    size: formData.size || undefined,
    curvature: formData.curvature || undefined
  }
  emit('save-draft', submitData)
}
</script>

<style lang="scss" scoped>
.video-purchase-form {
  padding: 24px;
}

.price-range-input {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  
  .separator {
    color: #86868B;
    white-space: nowrap;
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #E8E8ED;
}

:deep(.el-form-item__label) {
  font-weight: 600;
  color: #1D1D1F;
}

:deep(.el-radio-button__inner) {
  border-radius: 8px;
  margin-right: 8px;
}
</style>

