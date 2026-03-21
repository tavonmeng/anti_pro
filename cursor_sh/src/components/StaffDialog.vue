<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑负责人' : '添加负责人'"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="formData.username"
          placeholder="请输入用户名"
          :disabled="isEdit"
          maxlength="50"
        />
        <div class="form-tip" v-if="!isEdit">
          用户名用于登录，创建后不可修改
        </div>
      </el-form-item>

      <el-form-item label="密码" prop="password" v-if="!isEdit">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="请输入密码"
          show-password
          maxlength="100"
        />
      </el-form-item>

      <el-form-item label="确认密码" prop="confirmPassword" v-if="!isEdit">
        <el-input
          v-model="formData.confirmPassword"
          type="password"
          placeholder="请再次输入密码"
          show-password
          maxlength="100"
        />
      </el-form-item>

      <el-form-item label="真实姓名" prop="realName">
        <el-input
          v-model="formData.realName"
          placeholder="请输入真实姓名"
          maxlength="50"
        />
      </el-form-item>

      <el-form-item label="邮箱" prop="email">
        <el-input
          v-model="formData.email"
          placeholder="请输入邮箱地址"
          maxlength="100"
        />
        <div class="form-tip">
          用于接收订单通知和系统消息
        </div>
      </el-form-item>

      <el-form-item label="角色" prop="role">
        <el-select v-model="formData.role" placeholder="请选择角色" style="width: 100%">
          <el-option label="管理员" value="admin">
            <div class="role-option">
              <span>管理员</span>
              <span class="role-desc">拥有所有权限，可管理负责人和订单</span>
            </div>
          </el-option>
          <el-option label="负责人" value="staff">
            <div class="role-option">
              <span>负责人</span>
              <span class="role-desc">可处理分配给自己的订单</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="状态" prop="isActive">
        <el-switch
          v-model="formData.isActive"
          active-text="启用"
          inactive-text="禁用"
        />
        <div class="form-tip">
          禁用后该负责人将无法登录系统
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { staffApi } from '@/utils/api'
import type { User } from '@/types'

// Props
interface Props {
  modelValue: boolean
  staff?: User | null
  isEdit?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  staff: null,
  isEdit: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'success': []
}>()

// 数据
const formRef = ref<FormInstance>()
const submitting = ref(false)

const defaultFormData = {
  username: '',
  password: '',
  confirmPassword: '',
  realName: '',
  email: '',
  role: 'staff' as 'admin' | 'staff',
  isActive: true
}

const formData = ref({ ...defaultFormData })

// 计算属性
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 表单验证规则
const validatePassword = (rule: any, value: any, callback: any) => {
  if (!props.isEdit && !value) {
    callback(new Error('请输入密码'))
  } else if (value && value.length < 6) {
    callback(new Error('密码长度不能小于6位'))
  } else {
    callback()
  }
}

const validateConfirmPassword = (rule: any, value: any, callback: any) => {
  if (!props.isEdit && !value) {
    callback(new Error('请再次输入密码'))
  } else if (value !== formData.value.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const validateEmail = (rule: any, value: any, callback: any) => {
  if (!value) {
    callback()
  } else {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(value)) {
      callback(new Error('请输入正确的邮箱格式'))
    } else {
      callback()
    }
  }
}

const formRules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  password: [
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  realName: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  email: [
    { validator: validateEmail, trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}))

// 方法
async function handleSubmit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (props.isEdit && props.staff) {
      // 编辑模式
      await staffApi.updateStaff(props.staff.id, {
        realName: formData.value.realName,
        email: formData.value.email,
        role: formData.value.role,
        isActive: formData.value.isActive
      })
      ElMessage.success('更新成功')
    } else {
      // 新增模式
      await staffApi.addStaff({
        username: formData.value.username,
        password: formData.value.password,
        realName: formData.value.realName,
        email: formData.value.email,
        role: formData.value.role,
        isActive: formData.value.isActive
      })
      ElMessage.success('创建成功')
    }

    emit('success')
    handleClose()
  } catch (error: any) {
    if (error.response?.data?.message) {
      ElMessage.error(error.response.data.message)
    } else {
      ElMessage.error(props.isEdit ? '更新失败' : '创建失败')
    }
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  formRef.value?.resetFields()
  formData.value = { ...defaultFormData }
  emit('update:modelValue', false)
}

// 监听 staff 变化，填充表单
watch(() => props.staff, (newStaff) => {
  if (newStaff && props.isEdit) {
    formData.value = {
      username: newStaff.username || '',
      password: '',
      confirmPassword: '',
      realName: newStaff.realName || '',
      email: newStaff.email || '',
      role: newStaff.role as 'admin' | 'staff',
      isActive: newStaff.isActive ?? true
    }
  } else {
    formData.value = { ...defaultFormData }
  }
}, { immediate: true })
</script>

<style lang="scss" scoped>
.form-tip {
  font-size: 12px;
  color: #86868B;
  margin-top: 4px;
  line-height: 1.4;
}

.role-option {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .role-desc {
    font-size: 12px;
    color: #86868B;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.el-dialog__body) {
  padding-top: 20px;
}
</style>

