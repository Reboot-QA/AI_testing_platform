import { defineStore } from 'pinia'
import { apifoxApi, projectApi } from '@/api'
import type { Schemas } from '@/api/types'

type Project = Schemas['ProjectOut']
type Environment = Schemas['EnvironmentOut']

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
  },
  actions: {
    async loadProject(id: number | string): Promise<Project> {
      this.currentProject = await projectApi.get(id)
      return this.currentProject
    },
    async loadEnvironments(projectId: number | string): Promise<Environment[]> {
      this.environments = await apifoxApi.listEnvironments(projectId)
      const def = this.environments.find((e) => e.is_default)
      this.currentEnvironmentId = def ? def.id : null
      return this.environments
    },
    setEnvironments(list: Environment[]): void {
      this.environments = list
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
