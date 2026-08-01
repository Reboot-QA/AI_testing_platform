import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { requirementApi } from '@/api'
import { hubAiTasksApi, fetchAllHubTaskRequirements, type HubAiTaskOut } from '@/api/hubAiTasks'
import type { Schemas } from '@/api/types'
import type { SSEEvent } from '@/api/request'
import { clearReqExtractCtx, writeReqExtractCtx } from '@/constants/requirementExtractSession'

type ExtractedRequirement = Schemas['ExtractedRequirement']
type RequirementExtractStreamEvent =
  | (SSEEvent & {
      type: 'status'
      message?: string
      current?: number
      chunk?: number
      chunk_total?: number
      hub_task_id?: number
    })
  | (SSEEvent & {
      type: 'requirement'
      data: ExtractedRequirement
      saved?: boolean
      current?: number
      chunk?: number
      chunk_total?: number
    })
  | (SSEEvent & { type: 'done'; mode?: string; message?: string })
  | (SSEEvent & { type: 'error'; message: string })

export interface ExtractedRow extends ExtractedRequirement {
  _key: number
  id?: number
  saved?: boolean
}

const TERMINAL_TASK = new Set(['succeeded', 'partial', 'failed', 'canceled'])
const RESTORE_POLL_MS = 4000

let abortController: AbortController | null = null
let tempKey = 0
let restorePollTimer: ReturnType<typeof setInterval> | null = null

function stopRestorePoll(): void {
  if (restorePollTimer) {
    clearInterval(restorePollTimer)
    restorePollTimer = null
  }
}

export const useRequirementExtractStore = defineStore('requirementExtract', {
  state: () => ({
    extracting: false,
    restoringRunning: false,
    extracted: [] as ExtractedRow[],
    lastMode: '',
    extractMessage: '',
    progressMessage: '',
    progressCurrent: 0,
    progressChunk: 0,
    progressChunkTotal: 0,
    errorMessage: '',
    hubTaskId: null as number | null,
    activeProjectId: null as number | null,
    activeTarget: '',
  }),
  getters: {
    progressPercent(state): number {
      if (state.progressChunkTotal) {
        const total = state.progressChunkTotal
        const done = state.progressChunk
        const slice = 1 / total
        // 段与段之间 LLM 可能较慢：有已提取条数时在本段内略推进，避免长期停在 33%/66%
        let ratio = done / total
        if (state.extracting && done < total) {
          if (state.progressCurrent > 0 && done > 0) {
            ratio += slice * 0.35
          } else if (state.progressCurrent > 0) {
            ratio += slice * 0.12
          } else {
            // 首段 LLM 调用期间 completed 仍为 0，略推进避免长期 0%
            ratio += slice * 0.18
          }
        }
        return Math.min(state.extracting ? 99 : 100, Math.round(ratio * 100))
      }
      if (state.extracting || state.restoringRunning) {
        return Math.min(95, 10 + state.progressCurrent * 5)
      }
      return 100
    },
    showStreamProgress(state): boolean {
      return state.extracting || state.restoringRunning
    },
    taskActive(state): boolean {
      return state.extracting || state.restoringRunning
    },
    /** 右侧是否展示解析结果区（进行中或已有明细） */
    hasResultsPanel(state): boolean {
      return state.extracting || state.restoringRunning || state.extracted.length > 0
    },
  },
  actions: {
    clearResultsPanel(projectId?: number): void {
      stopRestorePoll()
      this.restoringRunning = false
      this.extracted = []
      this.lastMode = ''
      this.extractMessage = ''
      this.progressMessage = '准备分析...'
      this.progressCurrent = 0
      this.progressChunk = 0
      this.progressChunkTotal = 0
      this.hubTaskId = null
      const pid = projectId ?? this.activeProjectId
      if (pid != null) {
        clearReqExtractCtx(pid)
      }
    },

    resetSession(): void {
      stopRestorePoll()
      this.restoringRunning = false
      this.extracted = []
      this.lastMode = ''
      this.extractMessage = ''
      this.errorMessage = ''
      this.progressMessage = '准备分析...'
      this.progressCurrent = 0
      this.progressChunk = 0
      this.progressChunkTotal = 0
      tempKey = 0
      this.hubTaskId = null
      if (this.activeProjectId != null) {
        clearReqExtractCtx(this.activeProjectId)
      }
      this.activeProjectId = null
      this.activeTarget = ''
    },

    persistTaskContext(projectId: number, hubTaskId: number, target: string): void {
      this.hubTaskId = hubTaskId
      this.activeProjectId = projectId
      this.activeTarget = target
      writeReqExtractCtx({ projectId, hubTaskId, target })
    },

    applyHubTaskToState(task: HubAiTaskOut, items: ExtractedRow[]): void {
      this.extracted = items
      this.progressCurrent = task.generated_total
      this.progressChunk = task.done_items
      this.progressChunkTotal = task.total_items
      const meta = task.meta as Record<string, unknown> | null | undefined
      if (typeof meta?.mode === 'string') {
        this.lastMode = meta.mode
      }
      if (TERMINAL_TASK.has(task.status)) {
        this.restoringRunning = false
        this.progressMessage =
          (typeof meta?.message === 'string' && meta.message) ||
          `共 ${items.length} 条需求点，已写入需求点库`
        this.extractMessage = this.progressMessage
        if (task.status === 'failed' && task.error) {
          this.errorMessage = task.error
          this.extractMessage = task.error
        }
      } else {
        this.restoringRunning = true
        this.progressMessage = `任务进行中，已提取 ${task.generated_total} 条需求点...`
      }
    },

    rowsFromHubItems(
      items: Awaited<ReturnType<typeof hubAiTasksApi.listRequirements>>['items'],
    ): ExtractedRow[] {
      return items.map((item) => ({
        _key: item.id,
        id: item.requirement_id ?? undefined,
        title: item.title,
        description: item.description ?? '',
        req_type: item.req_type,
        priority: item.priority,
        saved: Boolean(item.imported_at || item.requirement_id),
      }))
    },

    async restoreRunningTaskForProject(projectId: number): Promise<void> {
      if (this.extracting) return
      stopRestorePoll()

      const running = await hubAiTasksApi.listTasks(projectId, {
        task_type: 'requirement',
        status: 'running',
        page: 1,
        page_size: 1,
      })
      const taskId = running.items[0]?.id ?? null
      if (!taskId) return

      const ok = await this.loadFromHubTask(projectId, taskId)
      if (ok && this.restoringRunning && this.hubTaskId != null) {
        this.startRestorePoll(projectId, this.hubTaskId)
      }
    },

    /** 进入「AI 分析需求」页：与 AI 用例一致，非进行中则清空；仅恢复 Hub 进行中任务 */
    onEnterRequirementDocsPage(projectId: number): void {
      if (this.extracting) {
        if (this.activeProjectId === projectId) return
        this.cancelExtract('已切换项目，解析已取消')
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
      void this.restoreRunningTaskForProject(projectId)
    },

    /** 离开「AI 分析需求」页：非解析/恢复进行中则清空展示 */
    onLeaveRequirementDocsPage(): void {
      stopRestorePoll()
      if (!this.extracting && !this.restoringRunning) {
        this.resetSession()
      }
    },

    async loadFromHubTask(projectId: number, taskId: number): Promise<boolean> {
      try {
        const [task, reqPage] = await Promise.all([
          hubAiTasksApi.getTask(projectId, taskId),
          fetchAllHubTaskRequirements(projectId, taskId),
        ])
        this.hubTaskId = taskId
        this.activeProjectId = projectId
        this.activeTarget = task.target
        writeReqExtractCtx({ projectId, hubTaskId: taskId, target: task.target })
        this.applyHubTaskToState(task, this.rowsFromHubItems(reqPage.items))
        return true
      } catch {
        return false
      }
    },

    startRestorePoll(projectId: number, taskId: number): void {
      stopRestorePoll()
      restorePollTimer = setInterval(() => {
        void (async () => {
          if (this.extracting) return
          try {
            const task = await hubAiTasksApi.getTask(projectId, taskId)
            const reqPage = await fetchAllHubTaskRequirements(projectId, taskId)
            this.applyHubTaskToState(task, this.rowsFromHubItems(reqPage.items))
            if (TERMINAL_TASK.has(task.status)) {
              stopRestorePoll()
              const meta = task.meta as Record<string, unknown> | null | undefined
              const msg =
                (typeof meta?.message === 'string' && meta.message) ||
                (task.status === 'failed' && task.error) ||
                ''
              if (task.status === 'succeeded' || task.status === 'partial') {
                ElMessage.success(msg || '解析完成，需求点已写入需求点库')
              } else if (task.status === 'failed' && msg) {
                ElMessage.error(msg)
              }
            }
          } catch {
            stopRestorePoll()
          }
        })()
      }, RESTORE_POLL_MS)
    },

    handleStreamEvent(
      event: RequirementExtractStreamEvent,
      projectId: number,
      target: string,
    ): void {
      if (this.activeProjectId != null && this.activeProjectId !== projectId) {
        return
      }
      if (event.type === 'status') {
        this.progressMessage = event.message || ''
        this.progressCurrent = event.current ?? this.progressCurrent
        this.progressChunk = event.chunk ?? this.progressChunk
        this.progressChunkTotal = event.chunk_total ?? this.progressChunkTotal
        if (typeof event.hub_task_id === 'number') {
          this.persistTaskContext(projectId, event.hub_task_id, target)
        }
      } else if (event.type === 'requirement' && event.data) {
        const row: ExtractedRow = { ...event.data, _key: ++tempKey }
        if (typeof row.id !== 'number') {
          row.saved = Boolean(event.saved)
        } else {
          row.saved = true
        }
        this.extracted.push(row)
        this.progressCurrent = event.current ?? this.progressCurrent
        this.progressChunk = event.chunk ?? this.progressChunk
        this.progressChunkTotal = event.chunk_total ?? this.progressChunkTotal
        this.progressMessage = `已实时写入需求点 ${this.extracted.length} 条...`
      } else if (event.type === 'done') {
        stopRestorePoll()
        this.lastMode = event.mode || ''
        this.restoringRunning = false
        const msg = event.message || `共 ${this.extracted.length} 条需求点，已写入需求点库`
        this.progressMessage = msg
        this.extractMessage = msg
        ElMessage.success(msg)
      } else if (event.type === 'error') {
        stopRestorePoll()
        this.clearResultsPanel(projectId)
        throw new Error(event.message)
      }
    },

    async startExtract(projectId: number, file: File, providerId?: number): Promise<boolean> {
      if (this.extracting && this.activeProjectId === projectId) {
        ElMessage.warning('当前项目已有进行中的需求解析任务')
        return false
      }

      stopRestorePoll()
      if (this.activeProjectId === projectId || this.activeProjectId == null) {
        this.resetSession()
      }
      this.activeProjectId = projectId
      this.activeTarget = file.name
      this.extracting = true
      abortController = new AbortController()

      try {
        await requirementApi.extractFromDocumentStream<RequirementExtractStreamEvent>(
          projectId,
          file,
          providerId,
          (event) => this.handleStreamEvent(event, projectId, file.name),
          { signal: abortController.signal },
        )
      } catch (error) {
        const err = error as Error
        if (err.name === 'AbortError') {
          if (!this.errorMessage) {
            this.errorMessage = '解析已取消'
          }
        } else {
          this.errorMessage = err.message || '解析失败'
          ElMessage.error(this.errorMessage)
        }
        this.clearResultsPanel(projectId)
      } finally {
        this.extracting = false
        abortController = null
      }
      return true
    },

    cancelExtract(message?: string): void {
      if (message) {
        this.errorMessage = message
      }
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      this.extracting = false
    },

    removeRow(key: number): void {
      this.extracted = this.extracted.filter((item) => item._key !== key)
    },

    stopForLogout(): void {
      stopRestorePoll()
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      this.extracting = false
      this.restoringRunning = false
      clearReqExtractCtx()
    },
  },
})
