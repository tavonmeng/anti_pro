import { ElMessageBox } from 'element-plus'
import { enterpriseApi } from '@/utils/api'

const normalizeStatus = (status: unknown) => String(status || 'none').toLowerCase()

export const getLatestEnterpriseStatus = async (authStore: any) => {
  let status = normalizeStatus(authStore.user?.enterprise_status)

  try {
    const data = await enterpriseApi.getStatus()
    status = normalizeStatus(data?.enterprise_status || status)

    if (authStore.user) {
      authStore.user.enterprise_status = status
      authStore.user.enterprise_name = data?.enterprise_name || authStore.user.enterprise_name
      authStore.user.enterprise_reject_reason = data?.enterprise_reject_reason || null
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
  } catch {
    // 如果状态接口暂时不可用，退回本地登录态判断。
  }

  return status
}

export const showEnterpriseAuthPrompt = async (
  router: any,
  message = '请先完成企业认证后再提交订单。'
) => {
  try {
    await ElMessageBox.alert(
      message,
      '需要企业认证',
      {
        confirmButtonText: '去认证',
        type: 'warning'
      }
    )
  } finally {
    router.push('/user/profile')
  }
}

export const ensureEnterpriseApproved = async (
  authStore: any,
  router: any,
  message = '请先完成企业认证后再提交订单。'
) => {
  const status = await getLatestEnterpriseStatus(authStore)
  if (status === 'approved') return true

  await showEnterpriseAuthPrompt(router, message)
  return false
}
