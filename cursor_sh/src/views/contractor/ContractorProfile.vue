<template>
  <div class="contractor-profile">
    <div class="page-header">
      <h1 class="page-title">个人设置</h1>
      <p class="page-desc">管理您的承包商账户信息</p>
    </div>

    <div class="profile-card">
      <el-form ref="formRef" :model="form" label-position="top" class="profile-form">
        <div class="form-grid">
          <el-form-item label="用户名">
            <el-input :model-value="form.username" disabled />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input :model-value="form.phone" disabled />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="联系邮箱" />
          </el-form-item>
          <el-form-item label="真实姓名">
            <el-input v-model="form.realName" placeholder="真实姓名" />
          </el-form-item>
          <el-form-item label="公司名称">
            <el-input v-model="form.company" placeholder="所在公司" />
          </el-form-item>
          <el-form-item label="地址">
            <el-input v-model="form.address" placeholder="联系地址" />
          </el-form-item>
          <el-form-item label="专业方向">
            <el-input v-model="form.specialty" placeholder="如：3D建模、视频后期" />
          </el-form-item>
          <el-form-item label="擅长领域">
            <el-input v-model="form.expertise" placeholder="如：裸眼3D广告、产品展示" />
          </el-form-item>
        </div>
        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const formRef = ref()
const saving = ref(false)

const form = reactive({
  username: '',
  phone: '',
  email: '',
  realName: '',
  company: '',
  address: '',
  specialty: '',
  expertise: '',
})

const fetchProfile = async () => {
  try {
    const res = await request.get('/api/contractor/profile')
    const d = res.data
    form.username = d.username || ''
    form.phone = d.phone || ''
    form.email = d.email || ''
    form.realName = d.realName || ''
    form.company = d.company || ''
    form.address = d.address || ''
    form.specialty = d.specialty || ''
    form.expertise = d.expertise || ''
  } catch {
    ElMessage.error('加载个人信息失败')
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    await request.put('/api/contractor/profile', {
      email: form.email,
      real_name: form.realName,
      company: form.company,
      address: form.address,
      specialty: form.specialty,
      expertise: form.expertise,
    })
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(fetchProfile)
</script>

<style lang="scss" scoped>
.contractor-profile { max-width: 800px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #1D1D1F; margin: 0 0 4px; }
.page-desc { font-size: 14px; color: #86868B; margin: 0; }
.profile-card { background: #fff; border-radius: 12px; padding: 32px; border: 1px solid #E5E7EB; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 24px; }
@media (max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }
.form-actions { margin-top: 24px; display: flex; justify-content: flex-end; }
</style>
