import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { isUnauthorizedError } from '@/api/request'
import { useUserStore } from '@/stores/user'

const WORKSPACE_PERMISSIONS = [
  'projects',
  'requirement_docs',
  'requirements',
  'ai_generate',
  'testcases',
  'test_execution',
  'apifox_workbench',
]

function workspaceSectionPermissions(hash: string): string[] {
  const params = new URLSearchParams(hash.replace(/^#/, ''))
  const domain = params.get('domain') || 'automation'
  const section = params.get('section') || ''
  if (domain === 'requirements') {
    if (section === 'req-docs') return ['requirement_docs']
    if (section === 'req-points') return ['requirements']
    return ['requirement_docs', 'requirements']
  }
  if (domain === 'functional') {
    if (section === 'ai') return ['ai_generate']
    if (section === 'func-runs' || section === 'func-exec') return ['test_execution']
    if (section === 'func-cases') return ['testcases']
    return ['ai_generate', 'testcases', 'test_execution']
  }
  if (domain === 'settings') return ['projects']
  return ['apifox_workbench']
}

function firstAccessibleWorkspaceHash(userStore: ReturnType<typeof useUserStore>): string | null {
  if (userStore.hasPermission('requirements')) return '#domain=requirements&section=req-points'
  if (userStore.hasPermission('requirement_docs')) return '#domain=requirements&section=req-docs'
  if (userStore.hasPermission('testcases')) return '#domain=functional&section=func-cases'
  if (userStore.hasPermission('ai_generate')) return '#domain=functional&section=ai'
  if (userStore.hasPermission('test_execution')) return '#domain=functional&section=func-runs'
  if (userStore.hasPermission('apifox_workbench')) {
    return '#domain=automation&biz=autotest&section=overview'
  }
  if (userStore.hasPermission('projects')) return '#domain=settings&open=basic'
  return null
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/force-change-password',
    name: 'ForceChangePassword',
    component: () => import('@/views/ForceChangePassword.vue'),
  },
  {
    path: '/account',
    name: 'Account',
    component: () => import('@/layouts/AccountShell.vue'),
  },
  { path: '/', redirect: '/hub' },

  // v2 新壳（无顶栏，56px 窄 Rail 自带 frame）
  {
    path: '/hub',
    name: 'HubHome',
    component: () => import('@/layouts/HubHomeShell.vue'),
    meta: { permission: 'dashboard' },
  },
  {
    path: '/hub/workspace/:projectId',
    name: 'HubWorkspace',
    component: () => import('@/layouts/ProjectShell.vue'),
    meta: { anyPermissions: WORKSPACE_PERMISSIONS },
  },

  // 旧业务路径重定向到新壳（视图文件仍被新壳复用，故不删）
  { path: '/dashboard', redirect: '/hub' },
  { path: '/projects', redirect: '/hub' },
  { path: '/requirement-docs', redirect: '/hub' },
  { path: '/requirements', redirect: '/hub' },
  { path: '/testcases', redirect: '/hub' },
  { path: '/ai-generate', redirect: '/hub' },
  { path: '/test-execution', redirect: '/hub' },
  { path: '/apifox', redirect: '/hub' },
  { path: '/apifox/project/:projectId', redirect: (to) => `/hub/workspace/${to.params.projectId}` },

  // 系统管理（SystemShell 壳，独立于业务工作区）
  {
    path: '/system',
    component: () => import('@/layouts/SystemShell.vue'),
    redirect: '/system/settings',
    children: [
      {
        path: 'settings',
        name: 'SystemSettings',
        component: () => import('@/views/SystemSettings.vue'),
        meta: { permission: 'system_settings' },
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('@/views/UserManagement.vue'),
        meta: { permission: 'system_users' },
      },
      {
        path: 'departments',
        name: 'DepartmentManagement',
        component: () => import('@/views/DepartmentManagement.vue'),
        meta: { permission: 'system_departments' },
      },
      {
        path: 'permissions',
        name: 'PermissionManagement',
        component: () => import('@/views/PermissionManagement.vue'),
        meta: { permission: 'system_permissions' },
      },
      {
        path: 'logs',
        name: 'LogMonitor',
        component: () => import('@/views/LogMonitor.vue'),
        meta: { permission: 'system_logs' },
      },
      {
        path: 'error-logs',
        name: 'ErrorLogs',
        component: () => import('@/views/ErrorLogs.vue'),
        meta: { permission: 'system_error_logs' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const userStore = useUserStore()
  if (!to.meta.public && !userStore.token) {
    return next('/login')
  }
  if (!to.meta.public && userStore.token && !userStore.user) {
    try {
      await userStore.fetchUser()
    } catch (error) {
      // 仅真·鉴权失败才清会话；代理抖动/超时（如 commit 后 Vite 整页刷新）保留 token
      if (isUnauthorizedError(error)) {
        userStore.logout()
        if (to.path !== '/login') {
          return next('/login')
        }
        return next()
      }
      ElMessage.warning('网络异常，登录状态暂未同步，请稍后刷新')
      return next()
    }
  }
  if (userStore.mustChangePassword && to.path !== '/force-change-password') {
    return next('/force-change-password')
  }
  if (to.path === '/force-change-password') {
    if (!userStore.token) {
      return next('/login')
    }
    if (!userStore.mustChangePassword) {
      return next('/hub')
    }
    return next()
  }
  if (to.meta.permission && !userStore.hasPermission(to.meta.permission as string)) {
    return next('/hub')
  }
  if (
    to.meta.anyPermissions?.length &&
    !to.meta.anyPermissions.some((permission) => userStore.hasPermission(permission))
  ) {
    return next('/hub')
  }
  if (to.name === 'HubWorkspace') {
    const allowed = workspaceSectionPermissions(to.hash).some((permission) =>
      userStore.hasPermission(permission),
    )
    if (!allowed) {
      const fallbackHash = firstAccessibleWorkspaceHash(userStore)
      if (!fallbackHash) return next('/hub')
      ElMessage.warning('您无权访问该模块，已切换到可访问区域')
      return next({ path: to.path, hash: fallbackHash, replace: true })
    }
  }
  next()
})

export default router
