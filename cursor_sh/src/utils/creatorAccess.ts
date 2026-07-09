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
  if (!isDesignPlanCompleted) {
    return '请先完成AI方案设计'
  }
  return ''
}
