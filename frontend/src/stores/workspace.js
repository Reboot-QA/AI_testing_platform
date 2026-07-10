import { defineStore } from 'pinia'
import { apifoxApi, projectApi } from '@/api'

// 接口自动化 v2 工作台/工作区的当前项目上下文（部门+项目模型，projectApi 已按可见性过滤）。
// 环境为工作区级：顶部选一次，调试/用例/场景等运行面板共享 currentEnvironmentId。
export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    currentProject: null,
    environments: [],
    currentEnvironmentId: null,
  }),
  getters: {
    currentProjectName: (state) => state.currentProject?.name || '',
  },
  actions: {
    async loadProject(id) {
      this.currentProject = await projectApi.get(id)
      return this.currentProject
    },
    // 切项目时环境集变化，重载并把当前环境重置为默认环境
    async loadEnvironments(projectId) {
      this.environments = await apifoxApi.listEnvironments(projectId)
      const def = this.environments.find((e) => e.is_default)
      // 无默认环境则保持未选（与原各面板一致，避免误跑非预期环境）
      this.currentEnvironmentId = def ? def.id : null
      return this.environments
    },
    setCurrentEnvironment(id) {
      this.currentEnvironmentId = id
    },
    clearCurrent() {
      this.currentProject = null
      this.environments = []
      this.currentEnvironmentId = null
    },
  },
})
