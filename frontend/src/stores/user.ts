import { defineStore } from 'pinia'
import { authApi } from '@/api'
import type { Schemas } from '@/api/types'
import { clearAssistantChat } from '@/utils/assistantChatStorage'
import { useAiGenerateStore } from '@/stores/aiGenerate'
import { useRequirementExtractStore } from '@/stores/requirementExtract'
import { useWorkspaceStore } from '@/stores/workspace'
import { useApiTabsStore } from '@/stores/apiTabs'
import { useScenarioTabsStore } from '@/stores/scenarioTabs'
import { useSuiteTabsStore } from '@/stores/suiteTabs'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'

type User = Schemas['UserOut']

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null as User | null,
    _fetchUserPromise: null as Promise<User> | null,
  }),
  getters: {
    isLoggedIn: (state): boolean => !!state.token,
    isAdmin: (state): boolean => state.user?.role === 'admin',
    mustChangePassword: (state): boolean => !!state.user?.must_change_password,
    menuPermissions: (state): string[] => state.user?.menu_permissions || [],
  },
  actions: {
    async login(username: string, password: string): Promise<void> {
      const res = await authApi.login(username, password)
      // 登录成功即清一遍上一会话残留（logout 已清，此处兜住「未走 logout 就回到登录页」的情形）
      this.clearSessionState()
      this.token = res.access_token
      localStorage.setItem('token', res.access_token)
      await this.fetchUser()
    },
    async fetchUser(): Promise<User | undefined> {
      if (!this.token) return
      if (this._fetchUserPromise) {
        return this._fetchUserPromise
      }
      this._fetchUserPromise = authApi
        .me()
        .then((user) => {
          this.user = user
          return user
        })
        .finally(() => {
          this._fetchUserPromise = null
        })
      return this._fetchUserPromise
    },
    async updateProfile(data: Schemas['UserProfileUpdate']): Promise<User> {
      const user = await authApi.updateProfile(data)
      this.user = user
      return user
    },
    hasPermission(permission: string): boolean {
      if (this.isAdmin) return true
      if (this.menuPermissions.includes(permission)) return true
      if (
        permission.startsWith('api_automation_') &&
        this.menuPermissions.includes('api_automation')
      ) {
        return true
      }
      return false
    },
    /**
     * 清掉所有「属于某个账号」的内存态。
     * 登录/登出都是 SPA 软跳转（不整页刷新），Pinia 状态会跨账号残留：上个用户的当前项目 /
     * 环境 / 各类 tab 若不清，切号后会带着别人的项目 id 去请求 → 404「项目不存在」。
     */
    clearSessionState(): void {
      useAiGenerateStore().stopForLogout()
      useRequirementExtractStore().stopForLogout()
      useWorkspaceStore().clearCurrent()
      useApiTabsStore().resetAll()
      useScenarioTabsStore().resetAll()
      useSuiteTabsStore().resetAll()
      useApifoxAiGenerateStore().reset()
      clearAssistantChat()
    },
    /** notifyServer=false 用于「别的标签页已登出」这类被动同步：本地清干净但不再重复通知后端 */
    logout(notifyServer = true): void {
      const token = this.token
      this.clearSessionState()
      this.token = ''
      this.user = null
      this._fetchUserPromise = null
      localStorage.removeItem('token')
      // 通知后端退出（JWT 无状态，作审计/会话钩子）；本地已清，带旧 token 触发，失败不阻断登出
      if (token && notifyServer) authApi.logout(token).catch(() => {})
    },
  },
})
