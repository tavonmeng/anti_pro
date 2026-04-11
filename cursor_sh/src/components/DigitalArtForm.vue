<template>
  <div class="digital-art-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="120px"
      label-position="top"
    >
      <el-form-item label="艺术方向" prop="artDirection">
        <el-radio-group v-model="formData.artDirection" size="large">
          <el-radio-button value="abstract">抽象</el-radio-button>
          <el-radio-button value="realistic">写实</el-radio-button>
          <el-radio-button value="installation">装置</el-radio-button>
          <el-radio-button value="dynamic">动态艺术</el-radio-button>
          <el-radio-button value="custom">自定义</el-radio-button>
        </el-radio-group>
      </el-form-item>
      
      <el-form-item 
        v-if="formData.artDirection === 'custom'" 
        label="自定义艺术方向" 
        prop="customDirection"
      >
        <el-input
          v-model="formData.customDirection"
          placeholder="请输入自定义艺术方向"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="说明文字" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="8"
          placeholder="请详细描述您的艺术需求，包括风格、主题、色彩、构图等要求"
          maxlength="3000"
          show-word-limit
        />
      </el-form-item>
      
      <el-form-item label="相关材料" prop="materials">
        <FileUpload 
          v-model="formData.materials"
          :limit="20"
          tip-text="支持上传参考图片、设计稿、压缩包等，最多20个文件"
        />
      </el-form-item>
    </el-form>
    
    <div class="production-notice">
      <el-alert
        title="制作周期说明"
        type="info"
        :closable="false"
      >
        <template #default>
          <p>数字艺术内容定制服务将在 <strong>3个工作日内</strong> 提供初稿预览。</p>
          <p>初稿确认后，根据您的反馈意见进行调整和完善。</p>
          <p>我们致力于为您打造独特的数字艺术作品。</p>
        </template>
      </el-alert>
    </div>
    
    <div class="form-actions">
      <button class="btn-secondary" @click="handleCancel">取消</button>
      <button class="btn-primary" @click="handleSubmit">确认提交</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import FileUpload from './FileUpload.vue'
import type { ArtDirection, UploadedFile, Order } from '@/types'

const props = defineProps<{
  order?: Order
}>()

const emit = defineEmits<{
  submit: [data: any]
  cancel: []
}>()

const formRef = ref<FormInstance>()
const formData = reactive({
  artDirection: 'abstract' as ArtDirection,
  customDirection: '',
  description: '',
  materials: [] as UploadedFile[]
})

// 编辑模式：填充表单数据
onMounted(() => {
  if (props.order && props.order.orderType === 'digital_art') {
    const order = props.order as any
    formData.artDirection = order.artDirection || 'abstract'
    formData.customDirection = order.customDirection || ''
    formData.description = order.description || ''
    formData.materials = order.materials || []
  }
})

const formRules: FormRules = {
  artDirection: [
    { required: true, message: '请选择艺术方向', trigger: 'change' }
  ],
  customDirection: [
    { required: true, message: '请输入自定义艺术方向', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请填写说明文字', trigger: 'blur' },
    { min: 30, message: '说明文字至少30个字符', trigger: 'blur' }
  ],
  materials: [
    { 
      type: 'array',
      required: true,
      message: '请至少上传1个相关材料',
      trigger: 'change'
    }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const isEdit = !!props.order
        await ElMessageBox.confirm(
          `
            <div style="text-align: left;">
              <p>${isEdit ? '请确认您已核对所有修改信息：' : '请确认您已核对所有信息：'}</p>
              <ul style="margin: 12px 0; padding-left: 20px;">
                <li>艺术方向：${getArtDirectionText()}</li>
                <li>已上传 ${formData.materials.length} 个相关材料</li>
                <li>已填写完整的说明文字</li>
                <li>预计初稿时间：3个工作日内</li>
              </ul>
              <p>${isEdit ? '提交后，订单将被更新。' : '提交后，我们将立即开始创作。'}</p>
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
        
        emit('submit', {
          artDirection: formData.artDirection,
          customDirection: formData.artDirection === 'custom' ? formData.customDirection : undefined,
          description: formData.description,
          materials: formData.materials
        })
      } catch {
        // 用户取消
      }
    }
  })
}

const handleCancel = () => {
  emit('cancel')
}

const getArtDirectionText = (): string => {
  const map: Record<string, string> = {
    abstract: '抽象',
    realistic: '写实',
    installation: '装置',
    dynamic: '动态艺术',
    custom: formData.customDirection || '自定义'
  }
  return map[formData.artDirection] || formData.artDirection
}
</script>

<style lang="scss" scoped>
.digital-art-form {
  padding: 0;
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
  background: #000000;
  color: #ffffff;
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
  opacity: 0.85;
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

:deep(.el-radio-button__inner) {
  border-radius: 9999px;
  margin-right: 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: none;
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #000000;
  border-color: #000000;
  box-shadow: none;
}
</style>

