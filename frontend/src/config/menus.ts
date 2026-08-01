export interface MenuDefinition {
  key: string
  label: string
  path: string
  group: 'business' | 'system'
  parent?: string
  parentLabel?: string
  hint?: string
}

export interface MenuGroup {
  key: string
  label: string
  items: MenuDefinition[]
}

/** 与 backend/app/constants/menus.py 对齐；key 勿改，仅更新 label / 分组以匹配 Hub */
export const MENU_DEFINITIONS: MenuDefinition[] = [
  {
    key: 'dashboard',
    label: '首页',
    path: '/hub',
    group: 'business',
    parent: 'hub',
    parentLabel: 'Hub',
    hint: 'Hub 落地页；取消授权后仍可通过「项目」等入口登录',
  },
  {
    key: 'projects',
    label: '项目',
    path: '/hub',
    group: 'business',
    parent: 'hub',
    parentLabel: 'Hub',
    hint: '项目列表、新建项目、进入项目工作区',
  },
  {
    key: 'requirement_docs',
    label: 'AI 分析需求',
    path: '/hub/workspace',
    group: 'business',
    parent: 'requirements',
    parentLabel: '需求',
    hint: '上传文档、AI 解析需求点、导入需求点',
  },
  {
    key: 'requirements',
    label: '需求点',
    path: '/hub/workspace',
    group: 'business',
    parent: 'requirements',
    parentLabel: '需求',
    hint: '手工维护需求点、导入导出、关联用例',
  },
  {
    key: 'ai_generate',
    label: 'AI 生成功能用例',
    path: '/hub/workspace',
    group: 'business',
    parent: 'functional',
    parentLabel: '功能',
    hint: '基于已评审需求 AI 生成功能用例',
  },
  {
    key: 'testcases',
    label: '功能用例库',
    path: '/hub/workspace',
    group: 'business',
    parent: 'functional',
    parentLabel: '功能',
    hint: '维护功能用例、关联需求点',
  },
  {
    key: 'test_execution',
    label: '手工执行',
    path: '/hub/workspace',
    group: 'business',
    parent: 'functional',
    parentLabel: '功能',
    hint: '新建测试单、标记执行结果、功能测试报告',
  },
  {
    key: 'apifox_workbench',
    label: '接口自动化',
    path: '/hub/workspace',
    group: 'business',
    parent: 'automation',
    parentLabel: '自动化',
    hint: '接口目录、数据模型、接口用例、测试场景、测试套件、定时任务、测试报告、回收站',
  },
  { key: 'system_settings', label: '全局设置', path: '/system/settings', group: 'system' },
  { key: 'system_users', label: '用户管理', path: '/system/users', group: 'system' },
  { key: 'system_departments', label: '部门权限', path: '/system/departments', group: 'system' },
  { key: 'system_permissions', label: '权限管理', path: '/system/permissions', group: 'system' },
]

export const PAGE_TITLES: Record<string, string> = {
  '/hub': 'Hub',
  '/dashboard': 'Hub',
  '/projects': '项目',
  '/apifox': '接口自动化',
  '/requirement-docs': 'AI 分析需求',
  '/requirements': '需求点',
  '/testcases': '功能用例库',
  '/ai-generate': 'AI 生成功能用例',
  '/test-execution': '手工执行',
  '/system/settings': '全局设置',
  '/system/users': '用户管理',
  '/system/departments': '部门权限',
  '/system/permissions': '权限管理',
}

export const BUSINESS_MENUS = MENU_DEFINITIONS.filter((item) => item.group === 'business')
export const SYSTEM_MENUS = MENU_DEFINITIONS.filter((item) => item.group === 'system')

export const SYSTEM_VIEW_PERMS = [
  'system_settings',
  'system_users',
  'system_departments',
  'system_permissions',
] as const

export const HUB_MENU_GROUP: MenuGroup = {
  key: 'hub',
  label: 'Hub',
  items: BUSINESS_MENUS.filter((item) => item.parent === 'hub'),
}

export const WORKSPACE_PERMISSION_GROUPS: MenuGroup[] = [
  {
    key: 'requirements',
    label: '需求（项目工作区）',
    items: BUSINESS_MENUS.filter((item) => item.parent === 'requirements'),
  },
  {
    key: 'functional',
    label: '功能（项目工作区）',
    items: BUSINESS_MENUS.filter((item) => item.parent === 'functional'),
  },
  {
    key: 'automation',
    label: '自动化（项目工作区）',
    items: BUSINESS_MENUS.filter((item) => item.parent === 'automation'),
  },
]

/** @deprecated 使用 HUB_MENU_GROUP + WORKSPACE_PERMISSION_GROUPS */
export const STANDALONE_BUSINESS_MENUS = HUB_MENU_GROUP.items

/** @deprecated 使用 WORKSPACE_PERMISSION_GROUPS */
export const BUSINESS_MENU_GROUPS: MenuGroup[] = WORKSPACE_PERMISSION_GROUPS

export const SUBMENU_INDEX_BY_PATH: Record<string, string> = {
  '/hub': 'hub',
  '/apifox': 'automation',
  '/requirement-docs': 'requirements',
  '/requirements': 'requirements',
  '/testcases': 'functional',
  '/ai-generate': 'functional',
  '/test-execution': 'functional',
}

/** AI 任务域权限说明（无独立 menu key） */
export const AI_TASK_PERMISSION_NOTES = [
  { label: 'AI 需求任务', requires: 'AI 分析需求（requirement_docs）' },
  { label: 'AI 用例任务', requires: 'AI 生成功能用例（ai_generate）' },
  { label: 'AI 接口任务', requires: '接口自动化（apifox_workbench）' },
] as const

export const DEFAULT_BUSINESS_MENU_KEYS = BUSINESS_MENUS.map((item) => item.key)
