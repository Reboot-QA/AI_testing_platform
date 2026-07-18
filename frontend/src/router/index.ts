import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAiGenerateStore } from '@/stores/aiGenerate'

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
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { permission: 'dashboard' },
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/Projects.vue'),
        meta: { permission: 'projects' },
      },
      {
        path: 'requirement-docs',
        name: 'RequirementDocs',
        component: () => import('@/views/RequirementDocs.vue'),
        meta: { permission: 'requirement_docs' },
      },
      {
        path: 'requirements',
        name: 'Requirements',
        component: () => import('@/views/Requirements.vue'),
        meta: { permission: 'requirements' },
      },
      {
        path: 'testcases',
        name: 'TestCases',
        component: () => import('@/views/TestCases.vue'),
        meta: { permission: 'testcases' },
      },
      {
        path: 'ai-generate',
        name: 'AIGenerate',
        component: () => import('@/views/AIGenerate.vue'),
        meta: { permission: 'ai_generate' },
      },
      {
        path: 'test-execution',
        name: 'TestExecution',
        component: () => import('@/views/TestExecution.vue'),
        meta: { permission: 'test_execution' },
      },
      {
        path: 'apifox',
        name: 'ApifoxWorkbench',
        component: () => import('@/views/apifox/Workbench.vue'),
        meta: { permission: 'apifox_workbench' },
      },
      {
        path: 'apifox/project/:projectId',
        component: () => import('@/views/apifox/ProjectWorkspace.vue'),
        redirect: (to) => `/apifox/project/${to.params.projectId}/apis`,
        meta: { permission: 'apifox_workbench' },
        children: [
          {
            path: 'apis',
            name: 'ApifoxApis',
            component: () => import('@/views/apifox/sections/ApiManage.vue'),
            meta: { permission: 'apifox_workbench', sectionTitle: '接口管理' },
          },
          {
            path: 'datamodels',
            name: 'ApifoxDataModels',
            component: () => import('@/views/apifox/sections/SchemaManage.vue'),
            meta: { permission: 'apifox_workbench', sectionTitle: '数据模型' },
          },
          {
            path: 'tests',
            name: 'ApifoxTests',
            component: () => import('@/views/apifox/sections/AutoTests.vue'),
            meta: { permission: 'apifox_workbench', sectionTitle: '自动化测试' },
          },
          {
            path: 'reports',
            name: 'ApifoxReports',
            component: () => import('@/views/apifox/sections/RunReports.vue'),
            meta: { permission: 'apifox_workbench', sectionTitle: '测试报告' },
          },
          {
            path: 'ai-jobs',
            name: 'ApifoxAiJobs',
            component: () => import('@/views/apifox/sections/AiGenJobsPanel.vue'),
            meta: { permission: 'apifox_workbench', sectionTitle: 'AI 生成' },
          },
          {
            path: 'environments',
            name: 'ApifoxEnvironments',
            component: () => import('@/views/apifox/sections/EnvManage.vue'),
            meta: { permission: 'apifox_workbench', sectionTitle: '环境' },
          },
          {
            path: 'settings',
            name: 'ApifoxProjectSettings',
            component: () => import('@/views/apifox/sections/ProjectSettings.vue'),
            meta: { permission: 'apifox_workbench', sectionTitle: '项目设置' },
          },
        ],
      },
      {
        path: 'apifox2',
        name: 'Apifox2Workbench',
        component: () => import('@/views/apifox/Workbench.vue'),
        props: { basePath: '/apifox2' },
        meta: { permission: 'apifox_workbench' },
      },
      {
        path: 'apifox2/project/:projectId',
        name: 'Apifox2Project',
        component: () => import('@/apifox2/views/ProjectWorkspace.vue'),
        meta: { permission: 'apifox_workbench' },
      },
      {
        path: 'system',
        redirect: '/system/settings',
      },
      {
        path: 'system/settings',
        name: 'SystemSettings',
        component: () => import('@/views/SystemSettings.vue'),
        meta: { permission: 'system_settings' },
      },
      {
        path: 'system/users',
        name: 'UserManagement',
        component: () => import('@/views/UserManagement.vue'),
        meta: { permission: 'system_users' },
      },
      {
        path: 'system/departments',
        name: 'DepartmentManagement',
        component: () => import('@/views/DepartmentManagement.vue'),
        meta: { permission: 'system_departments' },
      },
      {
        path: 'system/permissions',
        name: 'PermissionManagement',
        component: () => import('@/views/PermissionManagement.vue'),
        meta: { permission: 'system_permissions' },
      },
      {
        path: 'system/logs',
        name: 'LogMonitor',
        component: () => import('@/views/LogMonitor.vue'),
        meta: { permission: 'system_logs' },
      },
      {
        path: 'system/error-logs',
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
    } catch {
      userStore.logout()
      if (to.path !== '/login') {
        return next('/login')
      }
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
      return next('/dashboard')
    }
    return next()
  }
  if (to.meta.permission && !userStore.hasPermission(to.meta.permission as string)) {
    return next('/dashboard')
  }
  next()
})

router.afterEach((to, from) => {
  const aiStore = useAiGenerateStore()
  if (from.path === '/ai-generate' && to.path !== '/ai-generate') {
    aiStore.onLeaveAiGeneratePage()
  }
  if (to.path === '/ai-generate') {
    aiStore.onEnterAiGeneratePage()
  }
})

export default router
