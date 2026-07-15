import type { UserRole } from '@/types'

export type RouteRole = UserRole | UserRole[] | string | string[] | undefined | null

export const creatorRoles = ['contractor', 'staff'] as const

export const isCreatorRole = (role?: string | null) =>
  role === 'contractor' || role === 'staff'

export const isRouteRoleAllowed = (
  requiredRole: RouteRole,
  currentRole?: string | null,
) => {
  if (!requiredRole) return true
  if (!currentRole) return false

  const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole]
  return roles.includes(currentRole)
}

export const authenticatedHomeForRole = (
  role?: string | null,
  fallback = '/user/workspace',
) => {
  if (role === 'admin') return '/admin'
  if (isCreatorRole(role)) return '/contractor'
  if (role === 'user') return '/user/workspace'
  return fallback
}

export const shouldCheckContractorProfile = (role?: string | null) =>
  role === 'contractor'

export const creatorSidebarTitle = (role?: string | null) =>
  role === 'staff' ? '制作者中心' : '承包商中心'

export const creatorWorkspaceSubtitle = (role?: string | null) =>
  role === 'staff' ? '内部交付工作台' : '交付工作台'

export const creatorMenuRoute = (index: string, role?: string | null) => {
  if (!isCreatorRole(role)) return ''
  if (index === 'assignments' || index === 'orders') return '/contractor/assignments'
  if (index === 'profile') return '/contractor/profile'
  return ''
}

export const adminLoginRoles = (): UserRole[] => ['admin']

export const assignmentCreatorName = (assignment: Record<string, any> = {}) =>
  assignment.creatorName || assignment.contractorName || assignment.staffName || assignment.creatorId || assignment.contractorId || '制作者'

export const assignmentCreatorLabel = (creatorType?: string | null) =>
  creatorType === 'staff' ? '内部制作者' : '外部承包商'

export const deliverableCommentPlaceholder = (creatorType?: string | null) =>
  `写评论给${assignmentCreatorLabel(creatorType)}...`

export const creatorAssignmentDisabledReason = (
  orderStatus?: string | null,
  isDesignPlanCompleted = false,
) => {
  if (orderStatus === 'completed' || orderStatus === 'cancelled') {
    return '订单已结束，无法分配制作者'
  }
  if (!orderStatus || ['draft', 'pending_assign', 'pending_contract'].includes(orderStatus)) {
    return '请先将订单推进到「内容制作」阶段'
  }
  if (!isDesignPlanCompleted) {
    return '请先完成AI方案设计'
  }
  return ''
}

type CreatorAssignmentLike = Record<string, any>

const creatorAssignmentSchedule = (assignment: CreatorAssignmentLike = {}) =>
  Array.isArray(assignment.schedule) ? assignment.schedule : []

const creatorAssignmentCurrentStageOrder = (assignment: CreatorAssignmentLike = {}) => {
  const parsed = Number.parseInt(String(assignment.currentStageOrder || '1'), 10)
  return Number.isFinite(parsed) ? parsed : 1
}

const creatorAssignmentNextStage = (assignment: CreatorAssignmentLike = {}) => {
  const nextOrder = creatorAssignmentCurrentStageOrder(assignment) + 1
  return creatorAssignmentSchedule(assignment).find(
    (stage: Record<string, any>) => Number(stage.display_order) === nextOrder,
  )
}

export const canAdvanceCreatorStage = (assignment: CreatorAssignmentLike = {}) => {
  if (!['accepted', 'in_progress'].includes(assignment.status)) return false

  const currentStageOrder = creatorAssignmentCurrentStageOrder(assignment)
  const deliverables = Array.isArray(assignment.deliverables) ? assignment.deliverables : []
  return deliverables.some(
    (deliverable: Record<string, any>) =>
      Number(deliverable.stageOrder) === currentStageOrder
      && deliverable.status === 'admin_approved',
  )
}

export const creatorStageAdvanceTooltip = (assignment: CreatorAssignmentLike = {}) => {
  if (assignment.creatorType === 'staff') {
    return '内部负责人任务无需使用此功能，点击查看说明'
  }
  if (assignment.creatorType !== 'contractor') {
    return '此功能仅用于多环节承包商任务'
  }
  if (creatorAssignmentSchedule(assignment).length < 2) {
    return '单环节承包商任务无需推进，点击查看说明'
  }
  if (!canAdvanceCreatorStage(assignment)) {
    return '需先审批通过当前制作环节的交付物'
  }
  return creatorAssignmentNextStage(assignment)
    ? '进入承包商的下一制作环节'
    : '完成承包商制作任务'
}

export const creatorStageAdvanceButtonLabel = (assignment: CreatorAssignmentLike = {}) => {
  if (
    assignment.creatorType === 'contractor'
    && creatorAssignmentSchedule(assignment).length > 1
    && !creatorAssignmentNextStage(assignment)
  ) {
    return '完成承包商制作任务'
  }
  return '推进到下一环节'
}

export type CreatorStageAdvanceDialog = {
  action: 'info' | 'advance' | 'complete'
  title: string
  message: string
  confirmButtonText: string
}

export const creatorStageAdvanceDialog = (
  assignment: CreatorAssignmentLike = {},
): CreatorStageAdvanceDialog => {
  if (assignment.creatorType === 'staff') {
    return {
      action: 'info',
      title: '内部负责人任务无需操作',
      message: '此功能仅用于多环节承包商任务。内部负责人任务不需要手动推进制作环节；请在审核后直接推送交付物，并通过订单状态菜单推进订单主流程。',
      confirmButtonText: '我知道了',
    }
  }

  const schedule = creatorAssignmentSchedule(assignment)
  if (assignment.creatorType !== 'contractor' || schedule.length < 2) {
    return {
      action: 'info',
      title: '当前任务无需推进',
      message: '此功能仅用于多环节承包商任务。当前任务没有需要手动进入的下一制作环节，请在审核后直接推送交付物。',
      confirmButtonText: '我知道了',
    }
  }

  const currentOrder = creatorAssignmentCurrentStageOrder(assignment)
  const currentStage = schedule.find(
    (stage: Record<string, any>) => Number(stage.display_order) === currentOrder,
  )
  const nextStage = creatorAssignmentNextStage(assignment)

  if (nextStage) {
    const stageDescription = currentStage?.name && nextStage?.name
      ? `，将从「${currentStage.name}」进入「${nextStage.name}」`
      : ''
    return {
      action: 'advance',
      title: '推进承包商制作环节',
      message: `此功能仅用于多环节承包商任务${stageDescription}。推进后，承包商才能提交下一制作环节的交付物；内部负责人任务无需使用。确认继续？`,
      confirmButtonText: '确认推进',
    }
  }

  return {
    action: 'complete',
    title: '完成承包商制作任务',
    message: '当前已经是最后一个制作环节。继续后将把该承包商制作任务标记为完成，确认继续？',
    confirmButtonText: '确认完成',
  }
}
