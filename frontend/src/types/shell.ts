// v2 新壳的信息架构类型：域 / 自动化二级业务 / 设置子页 / 首页视图。
// 深链语义严格对齐原型 hash（#project&domain&section&biz&open / #view）。

export type WorkspaceDomain = 'requirements' | 'functional' | 'automation' | 'ai_tasks' | 'settings'

export type AutomationBiz = 'apis' | 'autotest' | 'reports'

export type SettingsSection =
  | 'basic'
  | 'scripts'
  | 'sql-scripts'
  | 'datasets'
  | 'databases'
  | 'notify'
  | 'envs'
  | 'members'
  | 'import'
  | 'export'

export type HomeView = 'home' | 'projects' | 'activity' | 'system'

// projectId、域和子页均走工作区具名路由；列表筛选和报告来源使用 query。
export interface WorkspaceHashState {
  domain: WorkspaceDomain
  section: string
  biz: AutomationBiz
  open: SettingsSection
  filter?: string
  /** 深链打开某条运行报告（全页详情，非抽屉） */
  run?: number
}

// 域概览卡片：动作按钮与统计项（原定义在 shell/DomainOverview.vue）。
export interface OverviewAction {
  label: string
  section: string
  icon: string
  desc?: string
  primary?: boolean
}
export interface OverviewStat {
  label: string
  value: number | string
  icon?: string
  caption?: string
  tone?: 'brand' | 'warning' | 'success'
  section?: string
  filter?: string
}

export interface OverviewStep {
  label: string
  section?: string
}
