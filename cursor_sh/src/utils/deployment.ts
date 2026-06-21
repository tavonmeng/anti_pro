const normalizedMode = String(import.meta.env.VITE_DEPLOYMENT_MODE || 'all')
  .trim()
  .toLowerCase()

export const deploymentMode = normalizedMode || 'all'
export const isExternalDeployment = deploymentMode === 'external'
export const isInternalDeployment = deploymentMode === 'internal'

export const loginPath = isInternalDeployment ? '/admin/login' : '/login'

export function isUserRoute(path: string): boolean {
  return path === '/user'
    || path.startsWith('/user/')
}

export function isContractorRoute(path: string): boolean {
  return path === '/contractor'
    || path.startsWith('/contractor/')
}

export function loginPathForRoute(path: string): string {
  if (isContractorRoute(path)) return '/contractor/login'
  return loginPath
}

export function loginPathForRole(role?: string | null): string {
  if (role === 'contractor') return '/contractor/login'
  if (role === 'admin' || role === 'staff') return '/admin/login'
  return loginPath
}

export function isInternalRoute(path: string): boolean {
  return path === '/admin'
    || path.startsWith('/admin/')
    || path === '/staff'
    || path.startsWith('/staff/')
    || path === '/contractor'
    || path.startsWith('/contractor/')
}
