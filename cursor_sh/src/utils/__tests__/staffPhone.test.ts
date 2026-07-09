import { describe, expect, it } from 'vitest'
import {
  normalizeStaffPhone,
  isValidStaffPhone,
  staffPhoneWarning,
} from '../staffPhone'

describe('staffPhone utilities', () => {
  it('normalizes spaces and dashes from staff phone numbers', () => {
    expect(normalizeStaffPhone(' 138 0000-0001 ')).toBe('13800000001')
  })

  it('accepts valid 11-digit China mobile numbers', () => {
    expect(isValidStaffPhone('13800000001')).toBe(true)
  })

  it('rejects invalid phone numbers', () => {
    expect(isValidStaffPhone('12345')).toBe(false)
  })

  it('warns when an active staff member has no phone', () => {
    expect(staffPhoneWarning({ phone: '', isActive: true })).toBe('未填写手机号，无法登录制作端')
  })

  it('does not warn for inactive staff without phone', () => {
    expect(staffPhoneWarning({ phone: '', isActive: false })).toBe('')
  })
})
