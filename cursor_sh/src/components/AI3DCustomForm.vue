<template>
  <div class="ai-3d-custom-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="120px"
      label-position="top"
    >
      <el-form-item label="配置信息" prop="configuration">
        <el-input
          v-model="formData.configuration"
          type="textarea"
          :rows="4"
          placeholder="请详细描述您的配置需求，包括屏幕参数、显示要求等"
          maxlength="1000"
          show-word-limit
        />
      </el-form-item>
      
      <el-form-item label="创意说明" prop="creativeIdea">
        <el-input
          v-model="formData.creativeIdea"
          type="textarea"
          :rows="6"
          placeholder="请详细描述您的创意想法、设计风格、期望效果等"
          maxlength="2000"
          show-word-limit
        />
      </el-form-item>
      
      <el-form-item label="现场实拍图" prop="scenePhotos">
        <FileUpload 
          v-model="formData.scenePhotos"
          accept="image/*"
          :limit="10"
          tip-text="支持上传现场照片，最多10张，支持 JPG、PNG 格式"
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
          <p>AI裸眼3D内容定制服务预计制作周期为 <strong>5-7个工作日</strong>。</p>
          <p>制作完成后，我们将上传初版预览供您确认。您可以提出修改意见，我们将根据反馈进行调整。</p>
        </template>
      </el-alert>
    </div>
    
    <div class="form-actions">
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确认提交</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import FileUpload from './FileUpload.vue'
import type { UploadedFile, Order } from '@/types'

const props = defineProps<{
  order?: Order
}>()

const emit = defineEmits<{
  submit: [data: any]
  cancel: []
}>()

const formRef = ref<FormInstance>()
const formData = reactive({
  configuration: '',
  creativeIdea: '',
  scenePhotos: [] as UploadedFile[]
})

// 编辑模式：填充表单数据
onMounted(() => {
  if (props.order && props.order.orderType === 'ai_3d_custom') {
    const order = props.order as any
    formData.configuration = order.configuration || ''
    formData.creativeIdea = order.creativeIdea || ''
    formData.scenePhotos = order.scenePhotos || []
  }
})

const formRules: FormRules = {
  configuration: [
    { required: true, message: '请填写配置信息', trigger: 'blur' },
    { min: 10, message: '配置信息至少10个字符', trigger: 'blur' }
  ],
  creativeIdea: [
    { required: true, message: '请填写创意说明', trigger: 'blur' },
    { min: 20, message: '创意说明至少20个字符', trigger: 'blur' }
  ],
  scenePhotos: [
    { 
      type: 'array',
      required: true,
      message: '请至少上传1张现场实拍图',
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
                <li>已上传 ${formData.scenePhotos.length} 张现场实拍图</li>
                <li>已填写完整的配置信息和创意说明</li>
                <li>预计制作周期：5-7个工作日</li>
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
        
        emit('submit', {
          configuration: formData.configuration,
          creativeIdea: formData.creativeIdea,
          scenePhotos: formData.scenePhotos
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
</script>

<style lang="scss" scoped>
.ai-3d-custom-form {
  padding: 24px;
}

.production-notice {
  margin: 24px 0;
  
  :deep(.el-alert) {
    border-radius: 12px;
    padding: 16px;
    
    p {
      margin: 8px 0;
      font-size: 14px;
      line-height: 1.6;
      
      &:first-child {
        margin-top: 0;
      }
      
      &:last-child {
        margin-bottom: 0;
      }
      
      strong {
        color: #667eea;
        font-weight: 600;
      }
    }
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
</style>

