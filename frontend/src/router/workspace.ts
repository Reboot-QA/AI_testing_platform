import type { RouteLocationNormalizedLoaded, RouteRecordRaw } from 'vue-router'
import type { AutomationBiz, WorkspaceDomain } from '@/types/shell'

export interface WorkspacePageMeta {
  domain: WorkspaceDomain
  biz?: AutomationBiz
  label: string
  icon: string
  group?: string
  groupIcon?: string
  permission?: string
  anyPermissions?: string[]
  managerOnly?: boolean
  legacy?: string[]
}

export interface WorkspacePage extends WorkspacePageMeta {
  name: string
}

export interface WorkspaceMenuGroup {
  title?: string
  icon?: string
  items: WorkspacePage[]
}

declare module 'vue-router' {
  // 路由元数据扩展仅供 TypeScript 合并声明使用。
  // eslint-disable-next-line no-unused-vars
  interface RouteMeta {
    workspace?: WorkspacePageMeta
    managerOnly?: boolean
  }
}

const page = (meta: WorkspacePageMeta) => ({ workspace: meta, ...meta })
const projectIdProps = (route: RouteLocationNormalizedLoaded) => ({
  projectId: Number(route.params.projectId),
})
const scopedProjectProps = (route: RouteLocationNormalizedLoaded) => ({
  scopedProjectId: Number(route.params.projectId),
})

export const workspaceRoutes: RouteRecordRaw[] = [
  {
    path: 'requirements',
    name: 'WorkspaceRequirements',
    component: () => import('@/components/shell/RequirementsOverview.vue'),
    props: projectIdProps,
    meta: page({
      domain: 'requirements',
      label: '需求概览',
      icon: 'HomeFilled',
      anyPermissions: ['requirement_docs', 'requirements'],
      legacy: ['requirements/req-overview'],
    }),
  },
  {
    path: 'requirements/documents',
    name: 'WorkspaceRequirementDocuments',
    component: () => import('@/views/RequirementDocs.vue'),
    props: scopedProjectProps,
    meta: page({
      domain: 'requirements',
      label: 'AI 分析需求',
      icon: 'MagicStick',
      group: '需求资产',
      groupIcon: 'Folder',
      permission: 'requirement_docs',
      legacy: ['requirements/req-docs'],
    }),
  },
  {
    path: 'requirements/points',
    name: 'WorkspaceRequirementPoints',
    component: () => import('@/views/Requirements.vue'),
    props: scopedProjectProps,
    meta: page({
      domain: 'requirements',
      label: '需求点',
      icon: 'Document',
      group: '需求资产',
      groupIcon: 'Folder',
      permission: 'requirements',
      legacy: ['requirements/req-points'],
    }),
  },
  {
    path: 'functional',
    name: 'WorkspaceFunctional',
    component: () => import('@/components/shell/FunctionalOverview.vue'),
    props: projectIdProps,
    meta: page({
      domain: 'functional',
      label: '功能测试概览',
      icon: 'HomeFilled',
      anyPermissions: ['ai_generate', 'testcases', 'test_execution'],
      legacy: ['functional/func-overview'],
    }),
  },
  {
    path: 'functional/ai-generate',
    name: 'WorkspaceFunctionalAi',
    component: () => import('@/views/AIGenerate.vue'),
    props: scopedProjectProps,
    meta: page({
      domain: 'functional',
      label: 'AI 生成功能用例',
      icon: 'MagicStick',
      group: '功能用例资产',
      groupIcon: 'Briefcase',
      permission: 'ai_generate',
      legacy: ['functional/ai'],
    }),
  },
  {
    path: 'functional/cases',
    name: 'WorkspaceFunctionalCases',
    component: () => import('@/views/TestCases.vue'),
    props: scopedProjectProps,
    meta: page({
      domain: 'functional',
      label: '功能用例库',
      icon: 'Files',
      group: '功能用例资产',
      groupIcon: 'Briefcase',
      permission: 'testcases',
      legacy: ['functional/func-cases'],
    }),
  },
  {
    path: 'functional/runs',
    name: 'WorkspaceFunctionalRuns',
    component: () => import('@/views/TestExecution.vue'),
    props: scopedProjectProps,
    meta: page({
      domain: 'functional',
      label: '手工执行',
      icon: 'VideoPlay',
      group: '功能用例资产',
      groupIcon: 'Briefcase',
      permission: 'test_execution',
      legacy: ['functional/func-runs', 'functional/func-exec'],
    }),
  },
  {
    path: 'functional/reports',
    name: 'WorkspaceFunctionalReports',
    component: () => import('@/views/functional/FunctionalTestReports.vue'),
    props: projectIdProps,
    meta: page({
      domain: 'functional',
      label: '功能测试报告',
      icon: 'Document',
      group: '测试报告',
      groupIcon: 'DataAnalysis',
      permission: 'test_execution',
      legacy: ['functional/func-reports'],
    }),
  },
  {
    path: 'automation',
    name: 'WorkspaceAutomation',
    component: () => import('@/components/shell/AutomationOverview.vue'),
    props: projectIdProps,
    meta: page({
      domain: 'automation',
      biz: 'autotest',
      label: '自动化概览',
      icon: 'HomeFilled',
      permission: 'apifox_workbench',
      legacy: ['automation/overview'],
    }),
  },
  {
    path: 'automation/apis',
    name: 'WorkspaceAutomationApis',
    component: () => import('@/views/apifox/sections/ApiManage.vue'),
    meta: page({
      domain: 'automation',
      biz: 'apis',
      label: '接口目录',
      icon: 'Connection',
      group: '接口管理',
      groupIcon: 'FolderOpened',
      permission: 'apifox_workbench',
      legacy: ['automation/apis'],
    }),
  },
  {
    path: 'automation/data-models',
    name: 'WorkspaceAutomationModels',
    component: () => import('@/views/apifox/sections/SchemaManage.vue'),
    meta: page({
      domain: 'automation',
      biz: 'autotest',
      label: '数据模型',
      icon: 'Grid',
      group: '接口管理',
      groupIcon: 'FolderOpened',
      permission: 'apifox_workbench',
      legacy: ['automation/datamodels'],
    }),
  },
  {
    path: 'automation/cases',
    name: 'WorkspaceAutomationCases',
    component: () => import('@/views/apifox/sections/ApiCasesExplorer.vue'),
    props: projectIdProps,
    meta: page({
      domain: 'automation',
      biz: 'autotest',
      label: '接口用例',
      icon: 'Files',
      group: '自动化测试',
      groupIcon: 'Cpu',
      permission: 'apifox_workbench',
      legacy: ['automation/cases'],
    }),
  },
  {
    path: 'automation/scenarios',
    name: 'WorkspaceAutomationScenarios',
    component: () => import('@/views/apifox/sections/ScenarioPanel.vue'),
    meta: page({
      domain: 'automation',
      biz: 'autotest',
      label: '测试场景',
      icon: 'Share',
      group: '自动化测试',
      groupIcon: 'Cpu',
      permission: 'apifox_workbench',
      legacy: ['automation/scenarios'],
    }),
  },
  {
    path: 'automation/suites',
    name: 'WorkspaceAutomationSuites',
    component: () => import('@/views/apifox/sections/SuitePanel.vue'),
    meta: page({
      domain: 'automation',
      biz: 'autotest',
      label: '测试套件',
      icon: 'Collection',
      group: '自动化测试',
      groupIcon: 'Cpu',
      permission: 'apifox_workbench',
      legacy: ['automation/suites'],
    }),
  },
  {
    path: 'automation/schedules',
    name: 'WorkspaceAutomationSchedules',
    component: () => import('@/views/apifox/sections/SchedulePanel.vue'),
    meta: page({
      domain: 'automation',
      biz: 'autotest',
      label: '定时任务',
      icon: 'Clock',
      group: '自动化测试',
      groupIcon: 'Cpu',
      permission: 'apifox_workbench',
      legacy: ['automation/schedules'],
    }),
  },
  {
    path: 'automation/reports',
    name: 'WorkspaceAutomationReports',
    component: () => import('@/views/apifox/sections/RunReports.vue'),
    meta: page({
      domain: 'automation',
      biz: 'reports',
      label: '测试报告',
      icon: 'Histogram',
      group: '报告',
      groupIcon: 'DataAnalysis',
      permission: 'apifox_workbench',
      legacy: ['automation/reports'],
    }),
  },
  {
    path: 'automation/trash',
    name: 'WorkspaceAutomationTrash',
    component: () => import('@/views/apifox/sections/TrashPanel.vue'),
    meta: page({
      domain: 'automation',
      biz: 'autotest',
      label: '回收站',
      icon: 'Delete',
      permission: 'apifox_workbench',
      legacy: ['automation/trash'],
    }),
  },
  {
    path: 'ai-tasks',
    name: 'WorkspaceAiTasks',
    component: () => import('@/components/shell/AiTasksOverview.vue'),
    props: projectIdProps,
    meta: page({
      domain: 'ai_tasks',
      label: 'AI 任务概览',
      icon: 'HomeFilled',
      anyPermissions: ['requirement_docs', 'ai_generate', 'apifox_workbench'],
      legacy: ['ai_tasks/ai-overview'],
    }),
  },
  {
    path: 'ai-tasks/requirements',
    name: 'WorkspaceAiRequirements',
    component: () => import('@/views/ai-tasks/HubAiTasksPanel.vue'),
    props: {
      panelTitle: 'AI 需求任务',
      taskType: 'requirement',
      generatedColumnLabel: '提取需求点',
      createDialogTitle: '创建 AI 需求任务',
    },
    meta: page({
      domain: 'ai_tasks',
      label: 'AI 需求任务',
      icon: 'Document',
      group: '任务执行',
      groupIcon: 'MagicStick',
      permission: 'requirement_docs',
      legacy: ['ai_tasks/ai-req'],
    }),
  },
  {
    path: 'ai-tasks/functional',
    name: 'WorkspaceAiFunctional',
    component: () => import('@/views/ai-tasks/HubAiTasksPanel.vue'),
    props: {
      panelTitle: 'AI 用例任务',
      taskType: 'functional',
      generatedColumnLabel: '生成用例',
      createDialogTitle: '创建 AI 用例任务',
    },
    meta: page({
      domain: 'ai_tasks',
      label: 'AI 用例任务',
      icon: 'List',
      group: '任务执行',
      groupIcon: 'MagicStick',
      permission: 'ai_generate',
      legacy: ['ai_tasks/ai-case'],
    }),
  },
  {
    path: 'ai-tasks/apis',
    name: 'WorkspaceAiApis',
    component: () => import('@/views/apifox/sections/AiGenJobsPanel.vue'),
    props: { panelTitle: 'AI 接口任务' },
    meta: page({
      domain: 'ai_tasks',
      label: 'AI 接口任务',
      icon: 'Connection',
      group: '任务执行',
      groupIcon: 'MagicStick',
      permission: 'apifox_workbench',
      legacy: ['ai_tasks/ai-api'],
    }),
  },
  {
    path: 'settings',
    name: 'WorkspaceSettings',
    component: () => import('@/components/shell/SettingsDomain.vue'),
    meta: page({ domain: 'settings', label: '设置', icon: 'Setting', permission: 'projects' }),
    children: [
      {
        path: 'basic',
        name: 'WorkspaceSettingsBasic',
        component: () => import('@/views/apifox/sections/ProjectSettings.vue'),
        meta: page({
          domain: 'settings',
          label: '基本信息',
          icon: 'Setting',
          group: '系统设置',
          groupIcon: 'Setting',
          permission: 'projects',
          legacy: ['settings/basic'],
        }),
      },
      {
        path: 'notifications',
        name: 'WorkspaceSettingsNotifications',
        component: () => import('@/components/apifox/project/NotifyConfigPanel.vue'),
        props: projectIdProps,
        meta: page({
          domain: 'settings',
          label: '失败通知',
          icon: 'Bell',
          group: '系统设置',
          groupIcon: 'Setting',
          permission: 'projects',
          legacy: ['settings/notify'],
        }),
      },
      {
        path: 'members',
        name: 'WorkspaceSettingsMembers',
        component: () => import('@/components/apifox/project/ProjectMembersPanel.vue'),
        props: projectIdProps,
        meta: {
          ...page({
            domain: 'settings',
            label: '成员管理',
            icon: 'User',
            group: '系统设置',
            groupIcon: 'Setting',
            permission: 'projects',
            managerOnly: true,
            legacy: ['settings/members'],
          }),
          managerOnly: true,
        },
      },
      {
        path: 'environments',
        name: 'WorkspaceSettingsEnvironments',
        component: () => import('@/views/apifox/sections/EnvManage.vue'),
        meta: page({
          domain: 'settings',
          label: '环境管理',
          icon: 'Connection',
          group: '系统设置',
          groupIcon: 'Setting',
          permission: 'projects',
          legacy: ['settings/envs'],
        }),
      },
      {
        path: 'import',
        name: 'WorkspaceSettingsImport',
        component: () => import('@/components/apifox/import-export/ImportDataPanel.vue'),
        meta: page({
          domain: 'settings',
          label: '导入数据',
          icon: 'Upload',
          group: '数据管理',
          groupIcon: 'Coin',
          permission: 'projects',
          legacy: ['settings/import', 'settings/data'],
        }),
      },
      {
        path: 'export',
        name: 'WorkspaceSettingsExport',
        component: () => import('@/components/apifox/import-export/ExportDataPanel.vue'),
        meta: page({
          domain: 'settings',
          label: '导出数据',
          icon: 'Download',
          group: '数据管理',
          groupIcon: 'Coin',
          permission: 'projects',
          legacy: ['settings/export'],
        }),
      },
      {
        path: 'scripts',
        name: 'WorkspaceSettingsScripts',
        component: () => import('@/components/apifox/script/ProjectScriptsPanel.vue'),
        props: projectIdProps,
        meta: page({
          domain: 'settings',
          label: '脚本库',
          icon: 'Document',
          group: '项目资源',
          groupIcon: 'FolderOpened',
          permission: 'projects',
          legacy: ['settings/scripts'],
        }),
      },
      {
        path: 'sql-scripts',
        name: 'WorkspaceSettingsSqlScripts',
        component: () => import('@/components/apifox/script/ProjectSqlScriptsPanel.vue'),
        props: projectIdProps,
        meta: page({
          domain: 'settings',
          label: 'SQL 脚本',
          icon: 'Document',
          group: '项目资源',
          groupIcon: 'FolderOpened',
          permission: 'projects',
          legacy: ['settings/sql-scripts'],
        }),
      },
      {
        path: 'datasets',
        name: 'WorkspaceSettingsDatasets',
        component: () => import('@/views/apifox/sections/DatasetPanel.vue'),
        meta: page({
          domain: 'settings',
          label: '数据集',
          icon: 'Coin',
          group: '项目资源',
          groupIcon: 'FolderOpened',
          permission: 'projects',
          legacy: ['settings/datasets'],
        }),
      },
      {
        path: 'databases',
        name: 'WorkspaceSettingsDatabases',
        component: () => import('@/components/apifox/project/ProjectDatabasesPanel.vue'),
        meta: page({
          domain: 'settings',
          label: '数据库',
          icon: 'Coin',
          group: '项目资源',
          groupIcon: 'FolderOpened',
          permission: 'projects',
          legacy: ['settings/databases'],
        }),
      },
    ],
  },
]

function collectPages(records: RouteRecordRaw[]): WorkspacePage[] {
  return records.flatMap((record) => {
    if (record.children?.length) return collectPages(record.children)
    const meta = record.meta?.workspace as WorkspacePageMeta | undefined
    return meta && record.name ? [{ ...meta, name: String(record.name) }] : []
  })
}

export const workspacePages = collectPages(workspaceRoutes)

export function workspaceMeta(route: RouteLocationNormalizedLoaded): WorkspacePageMeta | undefined {
  return route.matched
    .slice()
    .reverse()
    .find((record) => record.meta.workspace)?.meta.workspace as WorkspacePageMeta | undefined
}

export function canAccessWorkspacePage(
  meta: WorkspacePageMeta,
  hasPermission: (key: string) => boolean,
  isManager = true,
): boolean {
  if (meta.managerOnly && !isManager) return false
  if (meta.permission) return hasPermission(meta.permission)
  return !meta.anyPermissions || meta.anyPermissions.some(hasPermission)
}

export function workspaceMenuGroups(
  domain: WorkspaceDomain,
  hasPermission: (key: string) => boolean,
  isManager = true,
): WorkspaceMenuGroup[] {
  const groups = new Map<string | undefined, WorkspaceMenuGroup>()
  for (const item of workspacePages) {
    if (item.domain !== domain || !canAccessWorkspacePage(item, hasPermission, isManager)) continue
    const group = groups.get(item.group) ?? { title: item.group, icon: item.groupIcon, items: [] }
    group.items.push(item)
    groups.set(item.group, group)
  }
  return [...groups.values()]
}

export function workspaceDomains(hasPermission: (key: string) => boolean): WorkspaceDomain[] {
  return [
    ...new Set(
      workspacePages
        .filter((item) => canAccessWorkspacePage(item, hasPermission))
        .map((item) => item.domain),
    ),
  ]
}

export function firstWorkspaceRoute(
  hasPermission: (key: string) => boolean,
  domain?: WorkspaceDomain,
): string | undefined {
  return workspacePages.find(
    (item) => (!domain || item.domain === domain) && canAccessWorkspacePage(item, hasPermission),
  )?.name
}

export function legacyWorkspaceRoute(
  hash: string,
): { name: string; query?: Record<string, string> } | null {
  const params = new URLSearchParams(hash.replace(/^#/, ''))
  const domain = params.get('domain')
  const section = domain === 'settings' ? (params.get('open') ?? 'basic') : params.get('section')
  return legacyWorkspaceRouteFromParts(
    domain,
    section,
    Object.fromEntries(
      ['filter', 'run', 'from'].flatMap((name) => {
        const value = params.get(name)
        return value ? [[name, value]] : []
      }),
    ),
  )
}

export function legacyWorkspaceRouteFromParts(
  domain: string | null | undefined,
  section: string | null | undefined,
  query: Record<string, string> = {},
): { name: string; query?: Record<string, string> } | null {
  if (!domain || !section) return null
  const target = workspacePages.find((item) => item.legacy?.includes(`${domain}/${section}`))
  if (!target) return null
  return { name: target.name, query: Object.keys(query).length ? query : undefined }
}
