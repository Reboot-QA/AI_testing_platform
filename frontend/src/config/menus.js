export const MENU_DEFINITIONS = [
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
    key: 'api_automation_env',
    label: '环境配置',
    path: '/api-automation/env',
    group: 'business',
    parent: 'api_automation_mgmt',
    parentLabel: '接口自动化',
  },
  {
    key: 'api_automation_suites',
    label: '套件与用例',
    path: '/api-automation/suites',
    group: 'business',
    parent: 'api_automation_mgmt',
    parentLabel: '接口自动化',
  },
  {
    key: 'api_automation_reports',
    label: '测试报告',
    path: '/api-automation/reports',
    group: 'business',
    parent: 'api_automation_mgmt',
    parentLabel: '接口自动化',
  },
  {
    key: 'api_automation_schedule',
    label: '定时任务',
    path: '/api-automation/schedule',
    group: 'business',
    parent: 'api_automation_mgmt',
    parentLabel: '接口自动化',
  },
  { key: 'system_settings', label: '全局设置', path: '/system/settings', group: 'system' },
  { key: 'system_users', label: '用户管理', path: '/system/users', group: 'system' },
  { key: 'system_departments', label: '部门权限', path: '/system/departments', group: 'system' },
  { key: 'system_permissions', label: '权限管理', path: '/system/permissions', group: 'system' },
  { key: 'system_logs', label: '日志监控', path: '/system/logs', group: 'system' },
]

export const PAGE_TITLES = {
  '/dashboard': '仪表盘',
  '/projects': '项目管理',
  '/requirement-docs': 'AI分析需求',
  '/requirements': '需求点',
  '/testcases': '用例库',
  '/ai-generate': 'AI生成用例',
  '/test-execution': '用例执行',
  '/api-automation/env': '环境配置',
  '/api-automation/suites': '套件与用例',
  '/api-automation/reports': '测试报告',
  '/api-automation/schedule': '定时任务',
  '/system/settings': '全局设置',
  '/system/users': '用户管理',
  '/system/departments': '部门权限',
  '/system/permissions': '权限管理',
  '/system/logs': '日志监控',
}

export const BUSINESS_MENUS = MENU_DEFINITIONS.filter((item) => item.group === 'business')
export const SYSTEM_MENUS = MENU_DEFINITIONS.filter((item) => item.group === 'system')

export const STANDALONE_BUSINESS_MENUS = BUSINESS_MENUS.filter((item) => !item.parent)

export const BUSINESS_MENU_GROUPS = [
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

export const SUBMENU_INDEX_BY_PATH = {
  '/requirement-docs': 'requirement_mgmt',
  '/requirements': 'requirement_mgmt',
  '/testcases': 'testcase_mgmt',
  '/ai-generate': 'testcase_mgmt',
  '/test-execution': 'testcase_mgmt',
  '/api-automation/env': 'api_automation_mgmt',
  '/api-automation/suites': 'api_automation_mgmt',
  '/api-automation/reports': 'api_automation_mgmt',
  '/api-automation/schedule': 'api_automation_mgmt',
}
