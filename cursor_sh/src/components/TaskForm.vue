<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑任务' : '创建任务'"
    width="700px"
    :before-close="handleClose"
    class="task-form-dialog"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
      label-position="top"
    >
      <el-row :gutter="20">
        <el-col :span="24">
          <el-form-item label="任务标题" prop="title">
            <el-input
              v-model="formData.title"
              placeholder="请输入任务标题"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
        </el-col>
        
        <el-col :span="24">
          <el-form-item label="任务描述" prop="description">
            <el-input
              v-model="formData.description"
              type="textarea"
              :rows="4"
              placeholder="请输入任务描述"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </el-col>
        
        <el-col :span="12">
          <el-form-item label="设计形状" prop="designShape">
            <el-select
              v-model="formData.designShape"
              placeholder="请选择设计形状"
              style="width: 100%"
            >
              <el-option label="圆形" value="circle">
                <div class="shape-option">
                  <span class="shape-icon shape-circle"></span>
                  <span>圆形</span>
                </div>
              </el-option>
              <el-option label="正方形" value="square">
                <div class="shape-option">
                  <span class="shape-icon shape-square"></span>
                  <span>正方形</span>
                </div>
              </el-option>
              <el-option label="长方形" value="rectangle">
                <div class="shape-option">
                  <span class="shape-icon shape-rectangle"></span>
                  <span>长方形</span>
                </div>
              </el-option>
              <el-option label="三角形" value="triangle">
                <div class="shape-option">
                  <span class="shape-icon shape-triangle"></span>
                  <span>三角形</span>
                </div>
              </el-option>
              <el-option label="自定义" value="custom">
                <div class="shape-option">
                  <span class="shape-icon shape-custom"></span>
                  <span>自定义</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col v-if="formData.designShape === 'custom'" :span="12">
          <el-form-item label="自定义形状" prop="customShapeText">
            <el-input
              v-model="formData.customShapeText"
              placeholder="请输入自定义形状描述"
              maxlength="50"
              show-word-limit
            />
          </el-form-item>
        </el-col>
        
        <el-col :span="formData.designShape === 'custom' ? 12 : 12">
          <el-form-item label="设计大小" prop="designSize">
            <el-select
              v-model="formData.designSize"
              placeholder="请选择设计大小"
              style="width: 100%"
            >
              <el-option label="1024 × 768" value="1024*768" />
              <el-option label="800 × 600" value="800*600" />
              <el-option label="640 × 680" value="640*680" />
              <el-option label="1920 × 1080" value="1920*1080" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col v-if="formData.designSize === 'custom'" :span="12">
          <el-form-item label="自定义尺寸" prop="customSize">
            <div class="custom-size-inputs">
              <el-input-number
                v-model="formData.customWidth"
                :min="1"
                :max="9999"
                placeholder="宽度"
                style="width: 48%"
                controls-position="right"
              />
              <span class="size-separator">×</span>
              <el-input-number
                v-model="formData.customHeight"
                :min="1"
                :max="9999"
                placeholder="高度"
                style="width: 48%"
                controls-position="right"
              />
            </div>
          </el-form-item>
        </el-col>
        
        <el-col :span="12">
          <el-form-item label="是否3D">
            <el-switch
              v-model="formData.is3D"
              active-text="是"
              inactive-text="否"
              active-color="#667eea"
            />
          </el-form-item>
        </el-col>
        
        <el-col :span="12">
          <el-form-item label="是否曲面">
            <el-switch
              v-model="formData.isCurved"
              active-text="是"
              inactive-text="否"
              active-color="#667eea"
            />
          </el-form-item>
        </el-col>
        
        <el-col :span="24">
          <el-form-item label="上传图片">
            <el-upload
              v-model:file-list="fileList"
              action="#"
              list-type="picture-card"
              :auto-upload="false"
              :limit="5"
              :on-exceed="handleExceed"
              :on-preview="handlePreview"
              :on-remove="handleRemove"
              :before-upload="beforeUpload"
            >
              <el-icon><Plus /></el-icon>
            </el-upload>
            <div class="upload-tip">
              <el-text size="small" type="info">最多上传5张图片，支持JPG、PNG格式</el-text>
            </div>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        {{ isEdit ? '更新' : '创建' }}
      </el-button>
    </template>
    
    <el-dialog v-model="previewVisible" width="800px">
      <img :src="previewImage" style="width: 100%" alt="预览图片" />
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { Task, DesignShape, DesignSize } from '@/types'

interface Props {
  modelValue: boolean
  task?: Task
}

const props = withDefaults(defineProps<Props>(), {
  task: undefined
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [data: {
    title: string
    description: string
    images?: string[]
    designShape?: DesignShape
    customShapeText?: string
    designSize?: DesignSize | string
    customWidth?: number
    customHeight?: number
    is3D?: boolean
    isCurved?: boolean
  }]
}>()

const visible = ref(props.modelValue)
const formRef = ref<FormInstance>()
const loading = ref(false)
const fileList = ref<UploadFile[]>([])
const previewVisible = ref(false)
const previewImage = ref('')

const isEdit = computed(() => !!props.task)

const formData = reactive({
  title: '',
  description: '',
  images: [] as string[],
  designShape: undefined as DesignShape | undefined,
  customShapeText: '',
  designSize: undefined as DesignSize | string | undefined,
  customWidth: undefined as number | undefined,
  customHeight: undefined as number | undefined,
  is3D: false,
  isCurved: false
})

const formRules: FormRules = {
  title: [
    { required: true, message: '请输入任务标题', trigger: 'blur' },
    { min: 3, max: 100, message: '标题长度在3到100个字符', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入任务描述', trigger: 'blur' },
    { min: 10, max: 500, message: '描述长度在10到500个字符', trigger: 'blur' }
  ],
  designShape: [
    { required: true, message: '请选择设计形状', trigger: 'change' }
  ],
  customShapeText: [
    { 
      required: true, 
      message: '请输入自定义形状描述', 
      trigger: 'blur',
      validator: (rule: any, value: string, callback: Function) => {
        if (formData.designShape === 'custom' && !value) {
          callback(new Error('请输入自定义形状描述'))
        } else {
          callback()
        }
      }
    }
  ],
  designSize: [
    { required: true, message: '请选择设计大小', trigger: 'change' }
  ],
  customSize: [
    {
      validator: (rule: any, value: any, callback: Function) => {
        if (formData.designSize === 'custom') {
          if (!formData.customWidth || !formData.customHeight) {
            callback(new Error('请输入自定义尺寸的宽度和高度'))
          } else if (formData.customWidth < 1 || formData.customHeight < 1) {
            callback(new Error('尺寸必须大于0'))
          } else {
            callback()
          }
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    if (props.task) {
      formData.title = props.task.title
      formData.description = props.task.description
      formData.images = props.task.images || []
      formData.designShape = props.task.designShape
      formData.customShapeText = props.task.customShapeText || ''
      
      // 解析设计大小：如果是自定义格式 custom:width*height，需要解析
      if (props.task.designSize && typeof props.task.designSize === 'string' && props.task.designSize.startsWith('custom:')) {
        formData.designSize = 'custom'
        const dimensions = props.task.designSize.replace('custom:', '').split('*')
        if (dimensions.length === 2) {
          formData.customWidth = parseInt(dimensions[0])
          formData.customHeight = parseInt(dimensions[1])
        }
      } else {
        formData.designSize = props.task.designSize
        formData.customWidth = props.task.customWidth
        formData.customHeight = props.task.customHeight
      }
      
      formData.is3D = props.task.is3D ?? false
      formData.isCurved = props.task.isCurved ?? false
      // 转换图片URL为UploadFile格式
      fileList.value = (props.task.images || []).map((url, index) => ({
        uid: `existing-${index}`,
        name: `image-${index}.jpg`,
        url: url,
        status: 'success'
      }))
    } else {
      resetForm()
    }
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const resetForm = () => {
  formData.title = ''
  formData.description = ''
  formData.images = []
  formData.designShape = undefined
  formData.customShapeText = ''
  formData.designSize = undefined
  formData.customWidth = undefined
  formData.customHeight = undefined
  formData.is3D = false
  formData.isCurved = false
  fileList.value = []
  formRef.value?.resetFields()
}

const handleClose = () => {
  visible.value = false
  resetForm()
}

const handleExceed = () => {
  ElMessage.warning('最多只能上传5张图片')
}

const handlePreview = (file: UploadFile) => {
  previewImage.value = file.url || ''
  previewVisible.value = true
}

const handleRemove = (file: UploadFile) => {
  const index = fileList.value.findIndex(item => item.uid === file.uid)
  if (index !== -1) {
    fileList.value.splice(index, 1)
  }
}

const beforeUpload = (file: File) => {
  const isImage = file.type.startsWith('image/')
  const isLt5M = file.size / 1024 / 1024 < 5

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过5MB!')
    return false
  }

  // 创建预览URL
  const reader = new FileReader()
  reader.onload = (e) => {
    const uploadFile: UploadFile = {
      uid: Date.now().toString(),
      name: file.name,
      url: e.target?.result as string,
      status: 'ready',
      raw: file
    }
    fileList.value.push(uploadFile)
  }
  reader.readAsDataURL(file)
  
  return false // 阻止自动上传
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 提取图片URL
        const images = fileList.value
          .filter(file => file.status === 'success' || file.url)
          .map(file => file.url || '')
          .filter(url => url)
        
        // 处理设计大小：如果是自定义，使用 custom:width*height 格式
        let finalDesignSize: string | undefined = formData.designSize
        if (formData.designSize === 'custom') {
          if (formData.customWidth && formData.customHeight) {
            finalDesignSize = `custom:${formData.customWidth}*${formData.customHeight}`
          } else {
            ElMessage.error('请输入自定义尺寸的宽度和高度')
            return
          }
        }
        
        emit('submit', {
          title: formData.title,
          description: formData.description,
          images: images.length > 0 ? images : undefined,
          designShape: formData.designShape,
          customShapeText: formData.designShape === 'custom' ? formData.customShapeText : undefined,
          designSize: finalDesignSize,
          customWidth: formData.designSize === 'custom' ? formData.customWidth : undefined,
          customHeight: formData.designSize === 'custom' ? formData.customHeight : undefined,
          is3D: formData.is3D,
          isCurved: formData.isCurved
        })
        
        handleClose()
      } catch (error: any) {
        ElMessage.error(error.message || '提交失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>


<style lang="scss" scoped>
:deep(.task-form-dialog) {
  .el-dialog__body {
    padding: 30px;
    max-height: 70vh;
    overflow-y: auto;
  }
}

.upload-tip {
  margin-top: 8px;
}

.shape-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shape-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #667eea;
  background: rgba(102, 126, 234, 0.1);
  
  &.shape-circle {
    border-radius: 50%;
  }
  
  &.shape-square {
    border-radius: 2px;
  }
  
  &.shape-rectangle {
    width: 20px;
    border-radius: 2px;
  }
  
  &.shape-triangle {
    width: 0;
    height: 0;
    border: none;
    background: none;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-bottom: 14px solid #667eea;
    border-top: none;
  }
  
  &.shape-custom {
    border-radius: 4px;
    clip-path: polygon(50% 0%, 0% 100%, 100% 100%);
  }
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #1D1D1F;
}

:deep(.el-switch__label) {
  color: #86868B;
  font-weight: 500;
  
  &.is-active {
    color: #667eea;
  }
}

.custom-size-inputs {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.size-separator {
  font-size: 18px;
  font-weight: 500;
  color: #86868B;
  flex-shrink: 0;
}
</style>

