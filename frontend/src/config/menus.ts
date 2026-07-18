export interface MenuDefinition {
  key: string
  label: string
  path: string
  group: 'business' | 'system' | 'logs'
  parent?: string
  parentLabel?: string
}

export interface MenuGroup {
  key: string
  label: string
  items: MenuDefinition[]
}

export const MENU_DEFINITIONS: MenuDefinition[] = [
  { key: 'dashboard', label: '仪表盘', path: '/dashboard', group: 'business' },
  { key: 'projects', label: '项目管理', path: '/projects', group: 'business' },
  {
    key: 'requirement_docs',
    label: 'AI分析需求',
    path: '/requirement-docs',
    group: 'business',
    parent: 'requirement_mgmt',
    parentLabel: '需求管理',
  },
  {
    key: 'requirements',
    label: '需求点',
    path: '/requirements',
    group: 'business',
    parent: 'requirement_mgmt',
    parentLabel: '需求管理',
  },
  {
    key: 'ai_generate',
    label: 'AI生成用例',
    path: '/ai-generate',
    group: 'business',
    parent: 'testcase_mgmt',
    parentLabel: '用例管理',
  },
  {
    key: 'testcases',
    label: '用例库',
    path: '/testcases',
    group: 'business',
    parent: 'testcase_mgmt',
    parentLabel: '用例管理',
  },
  {
    key: 'test_execution',
    label: '用例执行',
    path: '/test-execution',
    group: 'business',
    parent: 'testcase_mgmt',
    parentLabel: '用例管理',
  },
  {
    key: 'apifox_workbench',
    label: '工作台',
    path: '/apifox',
    group: 'business',
    parent: 'api_automation_mgmt',
    parentLabel: '接口自动化',
  },
  {
    key: 'apifox2_workbench',
    label: 'apifox2工作台',
    path: '/apifox2',
    group: 'business',
    parent: 'api_automation_mgmt',
    parentLabel: '接口自动化',
  },
  { key: 'system_settings', label: '全局设置', path: '/system/settings', group: 'system' },
  { key: 'system_users', label: '用户管理', path: '/system/users', group: 'system' },
  { key: 'system_departments', label: '部门权限', path: '/system/departments', group: 'system' },
  { key: 'system_permissions', label: '权限管理', path: '/system/permissions', group: 'system' },
  {
    key: 'system_logs',
    label: '日志监控',
    path: '/system/logs',
    group: 'logs',
    parent: 'log_mgmt',
    parentLabel: '日志管理',
  },
  {
    key: 'system_error_logs',
    label: '错误日志',
    path: '/system/error-logs',
    group: 'logs',
    parent: 'log_mgmt',
    parentLabel: '日志管理',
  },
]

export const PAGE_TITLES: Record<string, string> = {
  '/dashboard': '仪表盘',
  '/projects': '项目管理',
  '/apifox': '工作台',
  '/apifox2': 'apifox2工作台',
  '/requirement-docs': 'AI分析需求',
  '/requirements': '需求点',
  '/testcases': '用例库',
  '/ai-generate': 'AI生成用例',
  '/test-execution': '用例执行',
  '/system/settings': '全局设置',
  '/system/users': '用户管理',
  '/system/departments': '部门权限',
  '/system/permissions': '权限管理',
  '/system/logs': '日志监控',
  '/system/error-logs': '错误日志',
}

export const BUSINESS_MENUS = MENU_DEFINITIONS.filter((item) => item.group === 'business')
export const SYSTEM_MENUS = MENU_DEFINITIONS.filter((item) => item.group === 'system')
export const LOG_MENUS = MENU_DEFINITIONS.filter((item) => item.group === 'logs')

export const STANDALONE_BUSINESS_MENUS = BUSINESS_MENUS.filter((item) => !item.parent)

export const BUSINESS_MENU_GROUPS: MenuGroup[] = [
  {
    key: 'requirement_mgmt',
    label: '需求管理',
    items: BUSINESS_MENUS.filter((item) => item.parent === 'requirement_mgmt'),
  },
  {
    key: 'testcase_mgmt',
    label: '用例管理',
    items: BUSINESS_MENUS.filter((item) => item.parent === 'testcase_mgmt'),
  },
  {
    key: 'api_automation_mgmt',
    label: '接口自动化',
    items: BUSINESS_MENUS.filter((item) => item.parent === 'api_automation_mgmt'),
  },
]

export const LOG_MENU_GROUPS: MenuGroup[] = [
  {
    key: 'log_mgmt',
    label: '日志管理',
    items: LOG_MENUS.filter((item) => item.parent === 'log_mgmt'),
  },
]

export const SUBMENU_INDEX_BY_PATH: Record<string, string> = {
  '/apifox': 'api_automation_mgmt',
  '/apifox2': 'api_automation_mgmt',
  '/requirement-docs': 'requirement_mgmt',
  '/requirements': 'requirement_mgmt',
  '/testcases': 'testcase_mgmt',
  '/ai-generate': 'testcase_mgmt',
  '/test-execution': 'testcase_mgmt',
  '/system/logs': 'log_mgmt',
  '/system/error-logs': 'log_mgmt',
}
