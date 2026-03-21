<template>
  <el-dialog
    v-model="visible"
    title="上传预览文件"
    width="600px"
    @close="handleClose"
  >
    <div class="upload-preview-content">
      <el-form :model="form" label-width="100px">
        <el-form-item label="预览类型">
          <el-radio-group v-model="form.previewType">
            <el-radio-button label="initial">初稿预览</el-radio-button>
            <el-radio-button label="final">终稿预览</el-radio-button>
          </el-radio-group>
          <p class="help-text">预览提交后将进入管理员审核，通过后客户才能看到内容。</p>
        </el-form-item>
        
        <el-form-item label="上传文件">
          <FileUpload 
            v-model="form.files"
            accept="image/*,video/*,.pdf"
            :limit="10"
            tip-text="支持上传图片、视频或PDF文件，最多10个"
          />
        </el-form-item>
        
        <el-form-item label="备注说明">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="4"
            placeholder="请输入备注说明（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
    </div>
    
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button 
        type="primary" 
        @click="handleConfirm" 
        :disabled="form.files.length === 0"
        :loading="uploading"
      >
        {{ uploading ? '上传中...' : '确认上传' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileUpload from './FileUpload.vue'
import type { UploadedFile, Order } from '@/types'

interface Props {
  modelValue: boolean
  order?: Order | null  // 订单信息，用于显示之前的备注
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [files: UploadedFile[], previewType: string, note: string]
}>()

const visible = ref(props.modelValue)
const uploading = ref(false)

const form = ref({
  previewType: 'initial',
  files: [] as UploadedFile[],
  note: ''
})

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    // 重置表单，但保留之前的备注
    form.value = {
      previewType: 'initial',
      files: [],
      note: props.order?.previewNote || ''  // 显示之前的备注
    }
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const handleClose = () => {
  visible.value = false
}

const handleConfirm = async () => {
  if (form.value.files.length === 0) return
  
  uploading.value = true
  try {
    // 模拟上传延迟
    await new Promise(resolve => setTimeout(resolve, 800))
    emit('confirm', form.value.files, form.value.previewType, form.value.note)
    handleClose()
  } finally {
    uploading.value = false
  }
}
</script>

<style lang="scss" scoped>
.upload-preview-content {
  max-height: 70vh;
  overflow-y: auto;
}

.help-text {
  font-size: 12px;
  color: #86868B;
  margin-top: 8px;
}
</style>

