import { SYSTEM_MENUS, SYSTEM_VIEW_PERMS } from '@/config/menus'

/** 进入 Hub 壳层所需任一权限（首页与项目独立） */
export const HUB_ENTRY_PERMISSIONS = [
  'dashboard',
  'projects',
  ...SYSTEM_MENUS.map((item) => item.key),
] as const

export const WORKSPACE_ENTRY_PERMISSIONS = [
  'projects',
  'requirement_docs',
  'requirements',
  'ai_generate',
  'testcases',
  'test_execution',
  'apifox_workbench',
] as const

const SYSTEM_LANDING_PATHS: { key: string; path: string }[] = [
  { key: 'system_settings', path: '/system/settings' },
  { key: 'system_users', path: '/system/users' },
  { key: 'system_departments', path: '/system/departments' },
  { key: 'system_permissions', path: '/system/permissions' },
]

export function canAccessHub(hasPermission: (key: string) => boolean): boolean {
  return (
    HUB_ENTRY_PERMISSIONS.some(hasPermission) ||
    WORKSPACE_ENTRY_PERMISSIONS.some(hasPermission)
  )
}

/** 登录成功或无权访问当前页时的默认落地路径 */
export function resolveLandingPath(hasPermission: (key: string) => boolean): string {
  if (hasPermission('dashboard')) return '/hub'
  if (hasPermission('projects')) return '/hub#view=projects'
  const systemPath = SYSTEM_LANDING_PATHS.find((item) => hasPermission(item.key))?.path
  if (systemPath) return systemPath
  if (WORKSPACE_ENTRY_PERMISSIONS.some(hasPermission)) return '/hub#view=projects'
  if (SYSTEM_VIEW_PERMS.some((key) => hasPermission(key))) return '/hub#view=system'
  return '/hub#view=projects'
}

/** Hub 内默认视图：无「首页」权限时不应落在 view=home */
export function resolveDefaultHubView(
  hasPermission: (key: string) => boolean,
  canSeeSystem: boolean,
): 'home' | 'projects' | 'activity' | 'system' {
  if (hasPermission('dashboard')) return 'home'
  if (hasPermission('projects')) return 'projects'
  if (canSeeSystem) return 'system'
  return 'activity'
}

export function isSameRouteTarget(currentFullPath: string, target: string): boolean {
  const normalize = (raw: string) => {
    const url = new URL(raw, 'http://local')
    const path = url.pathname
    const view = new URLSearchParams(url.hash.replace(/^#/, '')).get('view') || 'home'
    return `${path}#view=${view}`
  }
  try {
    return normalize(currentFullPath) === normalize(target)
  } catch {
    return currentFullPath === target
  }
}
