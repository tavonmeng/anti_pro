import { describe, expect, it } from 'vitest'
import {
  adminLoginRoles,
  assignmentCreatorLabel,
  assignmentCreatorName,
  authenticatedHomeForRole,
  creatorAssignmentDisabledReason,
  creatorMenuRoute,
  creatorSidebarTitle,
  creatorWorkspaceSubtitle,
  deliverableCommentPlaceholder,
  isCreatorRole,
  isRouteRoleAllowed,
  shouldCheckContractorProfile,
} from '../creatorAccess'

describe('creator access helpers', () => {
  it('treats both staff and contractor as creator roles', () => {
    expect(isCreatorRole('staff')).toBe(true)
    expect(isCreatorRole('contractor')).toBe(true)
    expect(isCreatorRole('admin')).toBe(false)
    expect(isCreatorRole('user')).toBe(false)
  })

  it('allows staff into routes shared by creator roles', () => {
    expect(isRouteRoleAllowed(['contractor', 'staff'], 'staff')).toBe(true)
    expect(isRouteRoleAllowed(['contractor', 'staff'], 'contractor')).toBe(true)
    expect(isRouteRoleAllowed(['contractor', 'staff'], 'admin')).toBe(false)
  })

  it('sends staff from login to the shared creator workspace', () => {
    expect(authenticatedHomeForRole('staff')).toBe('/contractor')
    expect(authenticatedHomeForRole('contractor')).toBe('/contractor')
    expect(authenticatedHomeForRole('admin')).toBe('/admin')
    expect(authenticatedHomeForRole('user')).toBe('/user/workspace')
  })

  it('keeps contractor profile completion prompts contractor-only', () => {
    expect(shouldCheckContractorProfile('contractor')).toBe(true)
    expect(shouldCheckContractorProfile('staff')).toBe(false)
  })

  it('uses the shared creator sidebar routes for staff and contractors', () => {
    expect(creatorSidebarTitle('staff')).toBe('制作者中心')
    expect(creatorWorkspaceSubtitle('staff')).toBe('内部交付工作台')
    expect(creatorMenuRoute('assignments', 'staff')).toBe('/contractor/assignments')
    expect(creatorMenuRoute('orders', 'staff')).toBe('/contractor/assignments')
    expect(creatorMenuRoute('profile', 'staff')).toBe('/contractor/profile')
    expect(creatorMenuRoute('profile', 'contractor')).toBe('/contractor/profile')
    expect(creatorMenuRoute('profile', 'user')).toBe('')
  })

  it('keeps the admin login entry admin-only', () => {
    expect(adminLoginRoles()).toEqual(['admin'])
  })

  it('labels admin assignment creators by internal or external type', () => {
    expect(assignmentCreatorName({ creatorName: '内部制作 A', contractorName: '旧字段' })).toBe('内部制作 A')
    expect(assignmentCreatorName({ contractorName: '外部承包商 B' })).toBe('外部承包商 B')
    expect(assignmentCreatorLabel('staff')).toBe('内部制作者')
    expect(assignmentCreatorLabel('contractor')).toBe('外部承包商')
  })

  it('uses role-aware admin comment placeholders', () => {
    expect(deliverableCommentPlaceholder('staff')).toBe('写评论给内部制作者...')
    expect(deliverableCommentPlaceholder('contractor')).toBe('写评论给外部承包商...')
  })

  it('requires a completed design plan before assigning any creator', () => {
    expect(creatorAssignmentDisabledReason('in_production', false)).toBe('请先完成AI方案设计')
    expect(creatorAssignmentDisabledReason('completed', true)).toBe('订单已结束，无法分配制作者')
    expect(creatorAssignmentDisabledReason('cancelled', true)).toBe('订单已结束，无法分配制作者')
    expect(creatorAssignmentDisabledReason('in_production', true)).toBe('')
  })
})
