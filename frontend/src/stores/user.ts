import { defineStore } from 'pinia'
import { authApi } from '@/api'
import type { Schemas } from '@/api/types'
import { clearAssistantChat } from '@/utils/assistantChatStorage'
import { useAiGenerateStore } from '@/stores/aiGenerate'

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
    logout(): void {
      useAiGenerateStore().stopForLogout()
      this.token = ''
      this.user = null
      this._fetchUserPromise = null
      localStorage.removeItem('token')
      clearAssistantChat()
    },
  },
})
