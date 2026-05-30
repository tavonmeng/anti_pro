const normalizedMode = String(import.meta.env.VITE_DEPLOYMENT_MODE || 'all')
  .trim()
  .toLowerCase()

export const deploymentMode = normalizedMode || 'all'
export const isExternalDeployment = deploymentMode === 'external'
export const isInternalDeployment = deploymentMode === 'internal'

export function isInternalRoute(path: string): boolean {
  return path === '/admin'
    || path.startsWith('/admin/')
    || path === '/staff'
    || path.startsWith('/staff/')
    || path === '/contractor'
    || path.startsWith('/contractor/')
}
