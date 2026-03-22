<template>
  <div class="ai-3d-custom-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="140px"
      label-position="top"
    >
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
        <el-col :span="12">
          <el-form-item label="预计上刊时间" prop="online_time">
            <el-input v-model="formData.online_time" placeholder="例如：2024年10月1日" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="销售对接人联系方式" prop="sales_contact">
            <el-input v-model="formData.sales_contact" placeholder="填写电话、微信或邮箱" />
          </el-form-item>
        </el-col>
      </el-row>

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
  sales_contact: '',
  scenePhotos: [] as UploadedFile[]
})

// 编辑模式：填充表单数据
onMounted(() => {
  if (props.order && props.order.orderType === 'ai_3d_custom') {
    const order = props.order as any
    formData.brand = order.brand || ''
    formData.background = order.background || ''
    formData.target_group = order.target_group || ''
    formData.brand_tone = order.brand_tone || ''
    formData.content = order.content || ''
    formData.style = order.style || ''
    formData.prohibited_content = order.prohibited_content || ''
    formData.city = order.city || ''
    formData.media_size = order.media_size || ''
    formData.time_number = order.time_number || ''
    formData.technology = order.technology || ''
    formData.budget = order.budget || ''
    formData.online_time = order.online_time || ''
    formData.sales_contact = order.sales_contact || ''
    formData.scenePhotos = order.scenePhotos || []
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
})

const formRules: FormRules = {
  brand: [
    { required: true, message: '请填写品牌关键词', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请填写内容需求', trigger: 'blur' }
  ],
  sales_contact: [
    { required: true, message: '请填写销售联系方式', trigger: 'blur' }
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
                <li>品牌与内容要求已明确</li>
                <li>已上传 ${formData.scenePhotos.length} 张现场实拍图</li>
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
