import { defineStore } from 'pinia'
import { authApi } from '@/api'
import { clearAssistantChat } from '@/utils/assistantChatStorage'
import { useAiGenerateStore } from '@/stores/aiGenerate'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin',
    mustChangePassword: (state) => !!state.user?.must_change_password,
    menuPermissions: (state) => state.user?.menu_permissions || [],
  },
  actions: {
    async login(username, password) {
      const res = await authApi.login(username, password)
      this.token = res.access_token
      localStorage.setItem('token', res.access_token)
      await this.fetchUser()
    },
    async fetchUser() {
      if (!this.token) return
      this.user = await authApi.me()
    },
    hasPermission(permission) {
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
    logout() {
      useAiGenerateStore().stopForLogout()
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      clearAssistantChat()
    },
  },
})
