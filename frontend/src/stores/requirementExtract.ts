import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { requirementApi } from '@/api'
import type { Schemas } from '@/api/types'
import type { SSEEvent } from '@/api/request'

type ExtractedRequirement = Schemas['ExtractedRequirement']

export interface ExtractedRow extends ExtractedRequirement {
  _key: number
}

const PAGE_LEAVE_TIMEOUT_SEC = 60
const LEAVE_CANCEL_MESSAGE = '离开超过 60 秒，已停止需求解析'

let abortController: AbortController | null = null
let leaveTimer: number | null = null
let leaveWarningShown = false
let tempKey = 0

export const useRequirementExtractStore = defineStore('requirementExtract', {
  state: () => ({
    extracting: false,
    extracted: [] as ExtractedRow[],
    lastMode: '',
    extractMessage: '',
    progressMessage: '',
    progressCurrent: 0,
    progressChunk: 0,
    progressChunkTotal: 0,
    errorMessage: '',
    leftPageAt: null as number | null,
    leaveCountdown: 0,
    taskProjectId: null as number | null,
  }),
  getters: {
    shouldShowLeaveWarning(state): boolean {
      return state.extracting && state.leftPageAt !== null
    },
    progressPercent(state): number {
      if (state.progressChunkTotal) {
        const chunkProgress = state.progressChunk / state.progressChunkTotal
        return Math.min(99, Math.round(chunkProgress * 100))
      }
      if (state.extracting) return Math.min(95, 10 + state.progressCurrent * 5)
      return 100
    },
  },
  actions: {
    resetSession(): void {
      this.extracted = []
      this.lastMode = ''
      this.extractMessage = ''
      this.errorMessage = ''
      this.progressMessage = '准备分析...'
      this.progressCurrent = 0
      this.progressChunk = 0
      this.progressChunkTotal = 0
      tempKey = 0
    },

    handleStreamEvent(event: SSEEvent): void {
      if (event.type === 'status') {
        this.progressMessage = event.message || ''
        this.progressCurrent = event.current ?? this.progressCurrent
        this.progressChunk = event.chunk ?? this.progressChunk
        this.progressChunkTotal = event.chunk_total ?? this.progressChunkTotal
      } else if (event.type === 'requirement' && event.data) {
        const row: ExtractedRow = { ...event.data, _key: ++tempKey }
        this.extracted.push(row)
        this.progressCurrent = event.current ?? this.progressCurrent
        this.progressChunk = event.chunk ?? this.progressChunk
        this.progressChunkTotal = event.chunk_total ?? this.progressChunkTotal
        this.progressMessage = `已提取 ${event.current} 条需求点...`
      } else if (event.type === 'done') {
        this.lastMode = event.mode || ''
        this.progressCurrent = event.total ?? this.progressCurrent
        this.progressChunk = this.progressChunkTotal || this.progressChunk
        this.progressMessage = event.message || ''
        this.extractMessage = event.message || ''
        ElMessage.success(event.message || '解析完成')
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    },

    async startExtract(projectId: number, file: File, providerId?: number): Promise<boolean> {
      if (this.extracting) {
        ElMessage.warning('已有进行中的需求解析任务')
        return false
      }

      this.resetSession()
      this.extracting = true
      this.taskProjectId = projectId
      abortController = new AbortController()
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
      leaveWarningShown = false

      try {
        await requirementApi.extractFromDocumentStream(
          projectId,
          file,
          providerId,
          (event) => this.handleStreamEvent(event),
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
      } finally {
        this.extracting = false
        abortController = null
        this.clearLeaveTimer()
        this.leftPageAt = null
        this.leaveCountdown = 0
        leaveWarningShown = false
        this.taskProjectId = null
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
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
      leaveWarningShown = false
      this.taskProjectId = null
    },

    removeRow(key: number): void {
      this.extracted = this.extracted.filter((item) => item._key !== key)
    },

    stopForLogout(): void {
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      this.extracting = false
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
      leaveWarningShown = false
      this.taskProjectId = null
    },

    onLeavePage(): void {
      if (this.extracting) {
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
            this.cancelExtract(LEAVE_CANCEL_MESSAGE)
            ElMessage.warning(this.errorMessage)
            leaveWarningShown = false
          }
        }, 1000)
        return
      }
      this.resetSession()
    },

    onEnterPage(): void {
      this.clearLeaveTimer()
      this.leftPageAt = null
      this.leaveCountdown = 0
      leaveWarningShown = false
    },

    clearLeaveTimer(): void {
      if (leaveTimer) {
        clearInterval(leaveTimer)
        leaveTimer = null
      }
    },
  },
})
