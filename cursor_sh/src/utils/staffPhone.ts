export function normalizeStaffPhone(phone?: string | null): string {
  return (phone || '').replace(/[\s-]+/g, '').trim()
}

export function isValidStaffPhone(phone?: string | null): boolean {
  const normalized = normalizeStaffPhone(phone)
  return /^1\d{10}$/.test(normalized)
}

export function staffPhoneWarning(staff: { phone?: string | null; isActive?: boolean }): string {
  if (staff.isActive && !normalizeStaffPhone(staff.phone)) {
    return '未填写手机号，无法登录制作端'
  }
  return ''
}
