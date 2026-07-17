import { defineStore } from 'pinia'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'

type TaskOut = Schemas['AiGenTaskOut']
type Category = Schemas['AiGenTaskCreate']['categories'][number]

const TERMINAL = ['succeeded', 'partial', 'failed', 'canceled']
const POLL_INTERVAL_MS = 2000

// 轮询定时器放模块级，避免进 Pinia state 被序列化/响应式追踪
let pollTimer: ReturnType<typeof setInterval> | null = null

function isTerminal(status: string): boolean {
  return TERMINAL.includes(status)
}

export const useApifoxAiGenerateStore = defineStore('apifoxAiGenerate', {
  state: () => ({
    // taskId -> 任务全量（含 items 与生成的用例预览）
    tasks: {} as Record<number, TaskOut>,
  }),
  getters: {
    taskById(state) {
      return (taskId: number): TaskOut | undefined => state.tasks[taskId]
    },
    // 单接口弹窗重开时恢复：该接口最近一个任务（进行中或本会话刚完成的）
    latestTaskForEndpoint(state) {
      return (endpointId: number): TaskOut | undefined =>
        Object.values(state.tasks)
          .filter((t) => t.items.some((i) => i.endpoint_id === endpointId))
          .sort((a, b) => b.id - a.id)[0]
    },
    hasActive(state): boolean {
      return Object.values(state.tasks).some((t) => !isTerminal(t.status))
    },
  },
  actions: {
    async start(
      projectId: number,
      endpointIds: number[],
      categories: Category[],
      providerId?: number | null,
    ): Promise<number> {
      const task = await apifoxApi.createAiGenTask(projectId, {
        endpoint_ids: endpointIds,
        categories,
        provider_id: providerId ?? undefined,
      })
      this.tasks[task.id] = task
      this.ensurePolling()
      return task.id
    },

    async refreshActive(): Promise<void> {
      const active = Object.values(this.tasks).filter((t) => !isTerminal(t.status))
      if (!active.length) {
        this.stopPolling()
        return
      }
      await Promise.all(
        active.map(async (t) => {
          try {
            this.tasks[t.id] = await apifoxApi.getAiGenTask(t.id)
          } catch {
            /* 单次轮询失败忽略，下次继续 */
          }
        }),
      )
      if (Object.values(this.tasks).every((t) => isTerminal(t.status))) this.stopPolling()
    },

    ensurePolling(): void {
      if (pollTimer) return
      pollTimer = setInterval(() => this.refreshActive(), POLL_INTERVAL_MS)
    },

    stopPolling(): void {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
    },

    async cancel(taskId: number): Promise<void> {
      this.tasks[taskId] = await apifoxApi.cancelAiGenTask(taskId)
    },

    async applyItem(
      taskId: number,
      itemId: number,
      indexes?: number[] | null,
    ): Promise<Schemas['AiGenApplyResult']> {
      const result = await apifoxApi.applyAiGenTaskItem(taskId, itemId, { indexes })
      try {
        this.tasks[taskId] = await apifoxApi.getAiGenTask(taskId) // 刷新 applied_count
      } catch {
        /* 忽略刷新失败，不影响入库结果 */
      }
      return result
    },

    // 进项目工作区时恢复进行中的任务（刷新/重登后不丢进度）
    async resumeActive(projectId: number): Promise<void> {
      const briefs = await apifoxApi.listActiveAiGenTasks(projectId)
      await Promise.all(
        briefs.map(async (b) => {
          this.tasks[b.id] = await apifoxApi.getAiGenTask(b.id)
        }),
      )
      if (briefs.length) this.ensurePolling()
    },

    removeTask(taskId: number): void {
      delete this.tasks[taskId]
      if (!this.hasActive) this.stopPolling()
    },

    reset(): void {
      this.stopPolling()
      this.tasks = {}
    },
  },
})
