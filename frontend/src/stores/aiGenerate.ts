import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { testcaseApi } from '@/api'
import type { Schemas } from '@/api/types'
import type { SSEEvent } from '@/api/request'

type GeneratedCase = Schemas['TestCaseOut']
type GeneratePayload = Schemas['AIGenerateRequest']

export interface FailedRequirement {
  requirement_id: number | null
  title: string
  reason: string
}

const PAGE_LEAVE_TIMEOUT_SEC = 60
const LEAVE_CANCEL_MESSAGE = '离开超过 60 秒，已停止用例生成'

let abortController: AbortController | null = null
let leaveTimer: number | null = null
let leaveWarningShown = false

export const useAiGenerateStore = defineStore('aiGenerate', {
  state: () => ({
    generating: false,
    results: [] as GeneratedCase[],
    progressMessage: '',
    progressCurrent: 0,
    progressTotal: 0,
    lastMode: '',
    lastProviderName: '',
    errorMessage: '',
    activeNames: [] as Array<number | string>,
    leftPageAt: null as number | null,
    leaveCountdown: 0,
    failedRequirements: [] as FailedRequirement[],
    taskProjectId: null as number | null,
  }),
  getters: {
    shouldShowLeaveWarning(state): boolean {
      return state.generating && state.leftPageAt !== null
    },
  },
  actions: {
    resetSession(): void {
      this.results = []
      this.errorMessage = ''
      this.activeNames = []
      this.lastMode = ''
      this.lastProviderName = ''
      this.progressCurrent = 0
      this.progressTotal = 0
      this.progressMessage = '准备生成...'
      this.failedRequirements = []
    },

    upsertFailed(item: FailedRequirement): void {
      const key = item.requirement_id ?? item.title
      const idx = this.failedRequirements.findIndex((f) => (f.requirement_id ?? f.title) === key)
      if (idx >= 0) {
        this.failedRequirements[idx] = item
      } else {
        this.failedRequirements.push(item)
      }
    },

    handleStreamEvent(event: SSEEvent): void {
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
      } else if (event.type === 'task_failed') {
        this.upsertFailed({
          requirement_id: event.requirement_id ?? null,
          title: event.title || '未知需求',
          reason: event.reason || '生成失败',
        })
      } else if (event.type === 'done') {
        this.lastMode = event.mode
        this.lastProviderName = event.provider_name ? `${event.provider_name} (${event.model})` : ''
        this.progressCurrent = event.generated_count
        this.progressMessage = '生成完成'
        if (Array.isArray(event.failed_tasks)) {
          for (const item of event.failed_tasks) {
            this.upsertFailed({
              requirement_id: item.requirement_id ?? null,
              title: item.title || '未知需求',
              reason: item.reason || '生成失败',
            })
          }
        }
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

    async startGeneration(
      payload: GeneratePayload,
      options: { append?: boolean } = {},
    ): Promise<boolean> {
      if (this.generating) {
        ElMessage.warning('已有进行中的 AI 任务')
        return false
      }

      if (options.append) {
        this.errorMessage = ''
        const retryIds = new Set(payload.requirement_ids || [])
        this.failedRequirements = this.failedRequirements.filter(
          (f) => f.requirement_id == null || !retryIds.has(f.requirement_id),
        )
      } else {
        this.resetSession()
      }
      this.generating = true
      this.taskProjectId = payload.project_id
      this.progressTotal = payload.count
      abortController = new AbortController()
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
      leaveWarningShown = false

      try {
        await testcaseApi.aiGenerateStream(payload, (event) => this.handleStreamEvent(event), {
          signal: abortController.signal,
        })
      } catch (error) {
        const err = error as Error
        if (err.name === 'AbortError') {
          if (!this.errorMessage) {
            this.errorMessage = '生成已取消'
          }
        } else {
          this.errorMessage = err.message || '生成失败'
          ElMessage.error(this.errorMessage)
        }
      } finally {
        this.generating = false
        abortController = null
        this.clearLeaveTimer()
        this.leftPageAt = null
        this.leaveCountdown = 0
        leaveWarningShown = false
        this.taskProjectId = null
      }
      return true
    },

    cancelGeneration(message?: string): void {
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
      leaveWarningShown = false
      this.taskProjectId = null
    },

    stopForLogout(): void {
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      this.generating = false
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
      leaveWarningShown = false
      this.taskProjectId = null
    },

    onLeaveAiGeneratePage(): void {
      if (this.generating) {
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
            this.cancelGeneration(LEAVE_CANCEL_MESSAGE)
            ElMessage.warning(this.errorMessage)
            leaveWarningShown = false
          }
        }, 1000)
        return
      }
      this.resetSession()
    },

    onEnterAiGeneratePage(): void {
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
      leaveWarningShown = false
      if (!this.generating) {
        this.resetSession()
      }
    },

    clearLeaveTimer(): void {
      if (leaveTimer) {
        clearInterval(leaveTimer)
        leaveTimer = null
      }
    },
  },
})
