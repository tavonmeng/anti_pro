import { describe, expect, it } from 'vitest'
import {
  adminLoginRoles,
  assignmentCreatorLabel,
  assignmentCreatorName,
  authenticatedHomeForRole,
  canAdvanceCreatorStage,
  creatorAssignmentDisabledReason,
  creatorMenuRoute,
  creatorSidebarTitle,
  creatorStageAdvanceButtonLabel,
  creatorStageAdvanceDialog,
  creatorStageAdvanceTooltip,
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
    expect(creatorAssignmentDisabledReason('pending_contract', true)).toBe('请先将订单推进到「内容制作」阶段')
    expect(creatorAssignmentDisabledReason('preview_ready', true)).toBe('')
    expect(creatorAssignmentDisabledReason('completed', true)).toBe('订单已结束，无法分配制作者')
    expect(creatorAssignmentDisabledReason('cancelled', true)).toBe('订单已结束，无法分配制作者')
    expect(creatorAssignmentDisabledReason('in_production', true)).toBe('')
  })

  it('explains that internal creator tasks do not use manual stage advancement', () => {
    const assignment = {
      creatorType: 'staff',
      status: 'in_progress',
      currentStageOrder: '1',
      schedule: [{ display_order: 1, name: '制作交付' }],
      deliverables: [{ stageOrder: 1, status: 'admin_approved' }],
    }

    expect(canAdvanceCreatorStage(assignment)).toBe(true)
    expect(creatorStageAdvanceTooltip(assignment)).toContain('内部负责人任务无需使用')
    expect(creatorStageAdvanceDialog(assignment)).toMatchObject({
      action: 'info',
      title: '内部负责人任务无需操作',
    })
  })

  it('does not advance single-stage contractor tasks', () => {
    const dialog = creatorStageAdvanceDialog({
      creatorType: 'contractor',
      schedule: [{ display_order: 1, name: '制作交付' }],
      currentStageOrder: '1',
    })

    expect(dialog.action).toBe('info')
    expect(dialog.message).toContain('仅用于多环节承包商任务')
  })

  it('confirms the exact transition for multi-stage contractor tasks', () => {
    const assignment = {
      creatorType: 'contractor',
      status: 'in_progress',
      currentStageOrder: '1',
      schedule: [
        { display_order: 1, name: 'Demo上传' },
        { display_order: 2, name: '最终稿交付' },
      ],
      deliverables: [{ stageOrder: 1, status: 'admin_approved' }],
    }

    expect(canAdvanceCreatorStage(assignment)).toBe(true)
    expect(creatorStageAdvanceDialog(assignment)).toMatchObject({
      action: 'advance',
      title: '推进承包商制作环节',
      confirmButtonText: '确认推进',
    })
    expect(creatorStageAdvanceDialog(assignment).message).toContain('从「Demo上传」进入「最终稿交付」')
    expect(creatorStageAdvanceButtonLabel(assignment)).toBe('推进到下一环节')
  })

  it('labels the last contractor stage as completing the production task', () => {
    const assignment = {
      creatorType: 'contractor',
      currentStageOrder: '2',
      schedule: [
        { display_order: 1, name: 'Demo上传' },
        { display_order: 2, name: '最终稿交付' },
      ],
    }

    expect(creatorStageAdvanceDialog(assignment).action).toBe('complete')
    expect(creatorStageAdvanceButtonLabel(assignment)).toBe('完成承包商制作任务')
  })
})
