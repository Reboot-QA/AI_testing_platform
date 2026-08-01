import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { testcaseApi } from '@/api'
import {
  fetchAllHubTaskCases,
  hubAiTasksApi,
  type HubAiTaskCaseBrief,
  type HubAiTaskOut,
} from '@/api/hubAiTasks'
import type { Schemas } from '@/api/types'
import type { SSEEvent } from '@/api/request'

type GeneratedCase = Schemas['TestCaseOut']
type GeneratePayload = Schemas['AIGenerateRequest']
type AiGenerateStreamEvent =
  | (SSEEvent & {
      type: 'status'
      message?: string
      current?: number
      total?: number
      hub_task_id?: number
    })
  | (SSEEvent & { type: 'case'; data: GeneratedCase; current: number; total: number })
  | (SSEEvent & {
      type: 'task_failed'
      requirement_id?: number | null
      title?: string
      reason?: string
    })
  | (SSEEvent & {
      type: 'done'
      message?: string
      mode: string
      provider_name?: string
      model?: string
      generated_count: number
      failed_count: number
      partial?: boolean
      failed_tasks?: FailedRequirement[]
    })
  | (SSEEvent & { type: 'error'; message: string })

export interface FailedRequirement {
  requirement_id: number | null
  title: string
  reason: string
}

const TERMINAL_TASK = new Set(['succeeded', 'partial', 'failed', 'canceled'])
const RESTORE_POLL_MS = 4000

let abortController: AbortController | null = null
let restorePollTimer: ReturnType<typeof setInterval> | null = null

function stopRestorePoll(): void {
  if (restorePollTimer) {
    clearInterval(restorePollTimer)
    restorePollTimer = null
  }
}

function caseBriefToResult(row: HubAiTaskCaseBrief, projectId: number): GeneratedCase {
  return {
    id: row.id,
    project_id: projectId,
    title: row.title,
    case_type: row.case_type,
    priority: row.priority,
    preconditions: row.preconditions ?? '',
    steps: row.steps ?? '',
    expected_results: row.expected_results ?? '',
    tags: row.tags ?? '',
    requirement_title: row.requirement_title ?? '',
    review_status: row.review_status,
    source: 'ai_generated',
    project_name: '',
  } as GeneratedCase
}

export const useAiGenerateStore = defineStore('aiGenerate', {
  state: () => ({
    generating: false,
    restoringRunning: false,
    results: [] as GeneratedCase[],
    progressMessage: '',
    progressCurrent: 0,
    progressTotal: 0,
    lastMode: '',
    lastProviderName: '',
    errorMessage: '',
    activeNames: [] as Array<number | string>,
    failedRequirements: [] as FailedRequirement[],
    hubTaskId: null as number | null,
    activeProjectId: null as number | null,
  }),
  getters: {
    taskActive(state): boolean {
      return state.generating || state.restoringRunning
    },
    hasResultsPanel(state): boolean {
      return state.generating || state.restoringRunning || state.results.length > 0
    },
  },
  actions: {
    resetSession(): void {
      stopRestorePoll()
      this.restoringRunning = false
      this.results = []
      this.errorMessage = ''
      this.activeNames = []
      this.lastMode = ''
      this.lastProviderName = ''
      this.progressCurrent = 0
      this.progressTotal = 0
      this.progressMessage = '准备生成...'
      this.failedRequirements = []
      this.hubTaskId = null
      this.activeProjectId = null
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

    applyHubTaskToState(task: HubAiTaskOut, cases: HubAiTaskCaseBrief[], projectId: number): void {
      this.activeProjectId = projectId
      this.results = cases.map((c) => caseBriefToResult(c, projectId))
      this.progressCurrent = task.generated_total
      this.progressTotal = task.total_items || task.generated_total || 0
      const meta = task.meta as Record<string, unknown> | null | undefined
      if (typeof meta?.mode === 'string') {
        this.lastMode = meta.mode
      }
      if (this.results.length && !this.activeNames.length) {
        this.activeNames = [this.results[0].id]
      }
      if (TERMINAL_TASK.has(task.status)) {
        this.restoringRunning = false
        this.progressMessage =
          (typeof meta?.message === 'string' && meta.message) ||
          `共 ${this.results.length} 条用例，已写入用例库`
        if (task.status === 'failed' && task.error) {
          this.errorMessage = task.error
        }
      } else {
        this.restoringRunning = true
        this.progressMessage = `任务进行中，已生成 ${task.generated_total} 条用例...`
      }
    },

    async loadFromHubTask(projectId: number, taskId: number): Promise<boolean> {
      try {
        const [task, casePage] = await Promise.all([
          hubAiTasksApi.getTask(projectId, taskId),
          fetchAllHubTaskCases(projectId, taskId),
        ])
        this.hubTaskId = taskId
        this.activeProjectId = projectId
        this.applyHubTaskToState(task, casePage.items, projectId)
        return true
      } catch {
        return false
      }
    },

    startRestorePoll(projectId: number, taskId: number): void {
      stopRestorePoll()
      restorePollTimer = setInterval(() => {
        void (async () => {
          if (this.generating) return
          try {
            const task = await hubAiTasksApi.getTask(projectId, taskId)
            const casePage = await fetchAllHubTaskCases(projectId, taskId)
            this.applyHubTaskToState(task, casePage.items, projectId)
            if (TERMINAL_TASK.has(task.status)) {
              stopRestorePoll()
              const meta = task.meta as Record<string, unknown> | null | undefined
              const msg = (typeof meta?.message === 'string' && meta.message) || ''
              if (task.status === 'succeeded' || task.status === 'partial') {
                ElMessage.success(msg || '生成完成，用例已写入用例库')
              } else if (task.status === 'failed') {
                ElMessage.error(task.error || msg || '生成失败')
              }
            }
          } catch {
            stopRestorePoll()
          }
        })()
      }, RESTORE_POLL_MS)
    },

    async restoreRunningFunctionalTask(projectId: number): Promise<void> {
      if (this.generating) return
      stopRestorePoll()

      const running = await hubAiTasksApi.listTasks(projectId, {
        task_type: 'functional',
        status: 'running',
        page: 1,
        page_size: 1,
      })
      const taskId = running.items[0]?.id ?? null
      if (!taskId) return

      const ok = await this.loadFromHubTask(projectId, taskId)
      if (ok && this.restoringRunning) {
        this.startRestorePoll(projectId, taskId)
      }
    },

    handleStreamEvent(event: AiGenerateStreamEvent, projectId: number): void {
      if (this.activeProjectId != null && this.activeProjectId !== projectId) {
        return
      }
      if (event.type === 'status') {
        this.progressMessage = event.message ?? this.progressMessage
        this.progressCurrent = event.current || this.progressCurrent
        this.progressTotal = event.total || this.progressTotal
        if (typeof event.hub_task_id === 'number') {
          this.hubTaskId = event.hub_task_id
          this.activeProjectId = projectId
        }
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
        stopRestorePoll()
        this.restoringRunning = false
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
        stopRestorePoll()
        this.restoringRunning = false
        throw new Error(event.message)
      }
    },

    async startGeneration(
      payload: GeneratePayload,
      options: { append?: boolean } = {},
    ): Promise<boolean> {
      if (this.generating) {
        if (this.activeProjectId === payload.project_id) {
          ElMessage.warning('已有进行中的 AI 任务')
          return false
        }
        this.cancelGeneration('已切换项目，生成已取消')
      }

      if (!options.append) {
        stopRestorePoll()
        this.resetSession()
      } else {
        this.errorMessage = ''
        const retryIds = new Set(payload.requirement_ids || [])
        this.failedRequirements = this.failedRequirements.filter(
          (f) => f.requirement_id == null || !retryIds.has(f.requirement_id),
        )
      }
      this.activeProjectId = payload.project_id
      this.generating = true
      this.progressTotal = payload.count
      abortController = new AbortController()

      try {
        await testcaseApi.aiGenerateStream<AiGenerateStreamEvent>(
          payload,
          (event) => this.handleStreamEvent(event, payload.project_id),
          { signal: abortController.signal },
        )
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
    },

    stopForLogout(): void {
      stopRestorePoll()
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      this.generating = false
      this.restoringRunning = false
      this.resetSession()
    },

    onLeaveAiGeneratePage(): void {
      stopRestorePoll()
      if (!this.generating && !this.restoringRunning) {
        this.resetSession()
      }
    },

    onEnterAiGeneratePage(projectId: number): void {
      if (this.generating) {
        if (this.activeProjectId === projectId) return
        this.cancelGeneration('已切换项目，生成已取消')
      }
      if (this.restoringRunning && this.hubTaskId != null && this.activeProjectId === projectId) {
        this.startRestorePoll(projectId, this.hubTaskId)
        return
      }
      if (this.activeProjectId != null && this.activeProjectId !== projectId) {
        stopRestorePoll()
        this.restoringRunning = false
      }
      this.resetSession()
      void this.restoreRunningFunctionalTask(projectId)
    },
  },
})
