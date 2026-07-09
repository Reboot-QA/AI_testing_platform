import { defineStore } from 'pinia'
import { projectApi } from '@/api'

// 接口自动化 v2 工作台/工作区的当前项目上下文（部门+项目模型，projectApi 已按可见性过滤）。
export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    projects: [],
    currentProject: null,
  }),
  getters: {
    currentProjectName: (state) => state.currentProject?.name || '',
  },
  actions: {
    async loadProjects() {
      this.projects = await projectApi.list()
      return this.projects
    },
    async loadProject(id) {
      this.currentProject = await projectApi.get(id)
      return this.currentProject
    },
    clearCurrent() {
      this.currentProject = null
    },
  },
})
