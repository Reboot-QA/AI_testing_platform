import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { isUnauthorizedError } from '@/api/request'
import { useUserStore } from '@/stores/user'
import {
  canAccessWorkspacePage,
  firstWorkspaceRoute,
  legacyWorkspaceRoute,
  workspaceMeta,
  workspaceRoutes,
} from './workspace'

import {
  canAccessHub,
  isSameRouteTarget,
  resolveLandingPath,
  HUB_ENTRY_PERMISSIONS,
  WORKSPACE_ENTRY_PERMISSIONS,
} from './landing'

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
    meta: { anyPermissions: [...HUB_ENTRY_PERMISSIONS, ...WORKSPACE_ENTRY_PERMISSIONS] },
  },
  {
    path: '/hub/workspace/:projectId',
    name: 'HubWorkspace',
    component: () => import('@/layouts/ProjectShell.vue'),
    meta: { anyPermissions: [...WORKSPACE_ENTRY_PERMISSIONS] },
    children: workspaceRoutes,
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
  { path: '/system/logs', redirect: '/system/settings' },
  { path: '/system/error-logs', redirect: '/system/settings' },

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
      return next(resolveLandingPath(userStore.hasPermission))
    }
    return next()
  }
  const legacy = legacyWorkspaceRoute(to.hash)
  if (legacy) {
    return next({ name: legacy.name, params: to.params, query: legacy.query, replace: true })
  }
  if (to.name === 'HubWorkspace') {
    const fallback = firstWorkspaceRoute(userStore.hasPermission)
    if (!fallback) return next(resolveLandingPath(userStore.hasPermission))
    return next({ name: fallback, params: to.params, replace: true })
  }
  if (to.name === 'WorkspaceSettings') {
    return next({ name: 'WorkspaceSettingsBasic', params: to.params, replace: true })
  }
  const workspacePage = workspaceMeta(to)
  if (workspacePage && !canAccessWorkspacePage(workspacePage, userStore.hasPermission)) {
    const fallback = firstWorkspaceRoute(userStore.hasPermission)
    return next(
      fallback
        ? { name: fallback, params: to.params, replace: true }
        : resolveLandingPath(userStore.hasPermission),
    )
  }

  const redirectIfForbidden = () => {
    if (!canAccessHub(userStore.hasPermission)) {
      ElMessage.warning('账号暂无任何菜单权限，请联系管理员')
      userStore.logout()
      return next('/login')
    }
    const landing = resolveLandingPath(userStore.hasPermission)
    if (isSameRouteTarget(to.fullPath, landing)) {
      ElMessage.warning('暂无访问该页面的权限')
      return next(false)
    }
    return next(landing)
  }

  if (to.meta.permission && !userStore.hasPermission(to.meta.permission as string)) {
    return redirectIfForbidden()
  }
  if (
    to.meta.anyPermissions?.length &&
    !to.meta.anyPermissions.some((permission) => userStore.hasPermission(permission))
  ) {
    return redirectIfForbidden()
  }
  next()
})

export default router
