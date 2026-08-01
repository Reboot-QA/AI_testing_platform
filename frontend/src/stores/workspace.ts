import { defineStore } from 'pinia'
import { apifoxApi, projectApi } from '@/api'
import type { Schemas } from '@/api/types'

type Project = Schemas['ProjectOut']
type Environment = Schemas['EnvironmentOut']

// 选当前环境：默认环境优先，否则首个；无环境为 null。
function pickCurrentEnv(list: Environment[]): number | null {
  return (list.find((e) => e.is_default) ?? list[0])?.id ?? null
}

// 接口自动化 v2 工作台/工作区的当前项目上下文（部门+项目模型，projectApi 已按可见性过滤）。
// 环境为工作区级：顶部选一次，调试/用例/场景等运行面板共享 currentEnvironmentId。
export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    currentProject: null as Project | null,
    environments: [] as Environment[],
    currentEnvironmentId: null as number | null,
  }),
  getters: {
    currentProjectName: (state): string => state.currentProject?.name || '',
    currentEnvironment(state): Environment | null {
      return state.environments.find((e) => e.id === state.currentEnvironmentId) ?? null
    },
    /** 当前环境的命名前置 URL（不含其它环境） */
    currentServerNames(state): string[] {
      const env = state.environments.find((e) => e.id === state.currentEnvironmentId)
      return (env?.servers ?? []).map((s) => s.name).filter(Boolean)
    },
  },
  actions: {
    // 首页快捷入口的默认项目：已有当前项目直接复用；否则取工作台概览首个
    // （后端 user_project_pref_service.order_cards 已按「置顶优先 → 自定义排序」返回）。
    // 一个项目都没有时返回 null，由调用方引导创建项目。
    async resolveDefaultProjectId(): Promise<number | null> {
      if (this.currentProject) return this.currentProject.id
      const overview = await apifoxApi.workbenchOverview()
      return overview.projects[0]?.id ?? null
    },
    // skipErrorToast：调用方自行提示（工作区校验项目可访问性时用，避免与自定义提示叠两条）
    async loadProject(id: number | string, skipErrorToast = false): Promise<Project> {
      this.currentProject = await projectApi.get(id, { skipErrorToast })
      return this.currentProject
    },
    async loadEnvironments(projectId: number | string): Promise<Environment[]> {
      this.environments = await apifoxApi.listEnvironments(projectId)
      this.currentEnvironmentId = pickCurrentEnv(this.environments)
      return this.environments
    },
    setEnvironments(list: Environment[]): void {
      this.environments = list
      // 当前选中已失效或未选时，回退默认/首个，保证顶部环境选择器有值（如新建环境后即时反映）
      const stillValid =
        this.currentEnvironmentId != null && list.some((e) => e.id === this.currentEnvironmentId)
      if (!stillValid) this.currentEnvironmentId = pickCurrentEnv(list)
    },
    setCurrentEnvironment(id: number | null): void {
      this.currentEnvironmentId = id
    },
    clearCurrent(): void {
      this.currentProject = null
      this.environments = []
      this.currentEnvironmentId = null
    },
  },
})
