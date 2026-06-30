import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { testcaseApi } from '@/api'

const PAGE_LEAVE_TIMEOUT_SEC = 60

let abortController = null
let leaveTimer = null

export const useAiGenerateStore = defineStore('aiGenerate', {
  state: () => ({
    generating: false,
    results: [],
    progressMessage: '',
    progressCurrent: 0,
    progressTotal: 0,
    lastMode: '',
    lastProviderName: '',
    errorMessage: '',
    activeNames: [],
    leftPageAt: null,
    leaveCountdown: 0,
  }),
  getters: {
    shouldShowLeaveWarning(state) {
      return state.generating && state.leftPageAt !== null
    },
  },
  actions: {
    resetSession() {
      this.results = []
      this.errorMessage = ''
      this.activeNames = []
      this.lastMode = ''
      this.lastProviderName = ''
      this.progressCurrent = 0
      this.progressTotal = 0
      this.progressMessage = '准备生成...'
    },

    handleStreamEvent(event) {
      if (event.type === 'status') {
        this.progressMessage = event.message
        this.progressCurrent = event.current || this.progressCurrent
        this.progressTotal = event.total || this.progressTotal
      } else if (event.type === 'case') {
        this.results.push(event.data)
        this.progressCurrent = event.current
        this.progressTotal = event.total
        this.progressMessage = `已生成 ${event.current}/${event.total} 条用例`
        this.activeNames = [event.data.id, ...this.activeNames]
      } else if (event.type === 'done') {
        this.lastMode = event.mode
        this.lastProviderName = event.provider_name
          ? `${event.provider_name} (${event.model})`
          : ''
        this.progressCurrent = event.generated_count
        this.progressMessage = '生成完成'
        const successMessage =
          event.message ||
          `成功生成 ${event.generated_count} 条用例（${event.mode === 'llm' ? 'LLM 模式' : 'Mock 模式'}）`
        if (event.failed_count > 0 || event.partial) {
          ElMessage.warning(successMessage)
        } else {
          ElMessage.success(successMessage)
        }
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    },

    async startGeneration(payload) {
      if (this.generating) {
        ElMessage.warning('已有进行中的 AI 生成任务')
        return false
      }

      this.resetSession()
      this.generating = true
      this.progressTotal = payload.count
      abortController = new AbortController()
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0

      try {
        await testcaseApi.aiGenerateStream(
          payload,
          (event) => this.handleStreamEvent(event),
          { signal: abortController.signal }
        )
      } catch (error) {
        if (error.name === 'AbortError') {
          if (!this.errorMessage) {
            this.errorMessage = '生成已取消'
          }
        } else {
          this.errorMessage = error.message || '生成失败'
          ElMessage.error(this.errorMessage)
        }
      } finally {
        this.generating = false
        abortController = null
        this.clearLeaveTimer()
        this.leftPageAt = null
        this.leaveCountdown = 0
      }
      return true
    },

    cancelGeneration(message) {
      if (message) {
        this.errorMessage = message
      }
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      this.generating = false
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
    },

    onLeaveAiGeneratePage() {
      if (!this.generating) return
      this.leftPageAt = Date.now()
      this.leaveCountdown = PAGE_LEAVE_TIMEOUT_SEC
      this.clearLeaveTimer()
      leaveTimer = window.setInterval(() => {
        if (!this.leftPageAt) {
          this.clearLeaveTimer()
          return
        }
        const elapsed = Math.floor((Date.now() - this.leftPageAt) / 1000)
        this.leaveCountdown = Math.max(0, PAGE_LEAVE_TIMEOUT_SEC - elapsed)
        if (elapsed >= PAGE_LEAVE_TIMEOUT_SEC) {
          this.cancelGeneration('离开 AI 生成页面超过 60 秒，已自动停止生成')
          ElMessage.warning(this.errorMessage)
        }
      }, 1000)
    },

    onEnterAiGeneratePage() {
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
    },

    clearLeaveTimer() {
      if (leaveTimer) {
        clearInterval(leaveTimer)
        leaveTimer = null
      }
    },
  },
})
