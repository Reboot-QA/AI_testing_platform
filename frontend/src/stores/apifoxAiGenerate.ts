import { defineStore } from 'pinia'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'

type TaskOut = Schemas['AiGenTaskOut']
type TaskItem = Schemas['AiGenTaskItemOut']
type Category = Schemas['AiGenTaskCreate']['categories'][number]

const TERMINAL = ['succeeded', 'partial', 'failed', 'canceled']
const POLL_INTERVAL_MS = 5000

// 轮询定时器放模块级，避免进 Pinia state 被序列化/响应式追踪
let pollTimer: ReturnType<typeof setInterval> | null = null

function isTerminal(status: string): boolean {
  return TERMINAL.includes(status)
}

function patchTaskItem(
  tasks: Record<number, TaskOut>,
  taskId: number,
  itemId: number,
  patch: (item: TaskItem) => TaskItem,
): void {
  const task = tasks[taskId]
  if (!task) return
  const idx = task.items.findIndex((i) => i.id === itemId)
  if (idx < 0) return
  const prev = task.items[idx]
  task.items[idx] = patch({
    ...prev,
    cases: [...prev.cases],
    applied_cases: [...(prev.applied_cases || [])],
    discarded_cases: [...(prev.discarded_cases || [])],
  })
}

function patchAfterApply(
  item: TaskItem,
  indexes: number[] | null | undefined,
  result: Schemas['AiGenApplyResult'],
): TaskItem {
  const failed = new Set(result.failed)
  const pick =
    indexes && indexes.length ? new Set(indexes) : new Set(item.cases.map((_, i) => i))
  const archived = [...(item.applied_cases || [])]
  for (let i = 0; i < item.cases.length; i++) {
    if (!pick.has(i) || failed.has(item.cases[i].name)) continue
    archived.push(item.cases[i])
  }
  item.applied_cases = archived
  item.applied_count += result.created
  item.cases = item.cases.filter((c, i) => !pick.has(i) || failed.has(c.name))
  item.generated_count = item.cases.length
  return item
}

function patchAfterDiscard(item: TaskItem, indexes: number[]): TaskItem {
  const sorted = [...indexes].filter((i) => i >= 0 && i < item.cases.length).sort((a, b) => b - a)
  const removed: Schemas['CaseCreate'][] = []
  for (const i of sorted) {
    removed.unshift(item.cases[i])
    item.cases.splice(i, 1)
  }
  item.discarded_cases = [...(item.discarded_cases || []), ...removed]
  item.generated_count = item.cases.length
  return item
}

function mergeTaskItems(tasks: Record<number, TaskOut>, taskId: number, fresh: TaskOut): void {
  const task = tasks[taskId]
  if (!task) {
    tasks[taskId] = fresh
    return
  }
  task.status = fresh.status
  task.done_items = fresh.done_items
  task.error = fresh.error
  task.finished_at = fresh.finished_at
  for (const updated of fresh.items) {
    const idx = task.items.findIndex((i) => i.id === updated.id)
    if (idx >= 0) task.items[idx] = updated
  }
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
    activeCountForUser(state) {
      return (userName: string | null | undefined): number => {
        if (!userName) return 0
        return Object.values(state.tasks).filter(
          (t) => !isTerminal(t.status) && t.creator_name === userName,
        ).length
      }
    },
    activeCountForUserInProject(state) {
      return (userName: string | null | undefined, projectId: number): number => {
        if (!userName || !projectId) return 0
        return Object.values(state.tasks).filter(
          (t) =>
            !isTerminal(t.status) &&
            t.creator_name === userName &&
            t.project_id === projectId,
        ).length
      }
    },
    hasActiveInProject(state) {
      return (projectId: number): boolean =>
        !!projectId &&
        Object.values(state.tasks).some(
          (t) => !isTerminal(t.status) && t.project_id === projectId,
        )
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
      patchTaskItem(this.tasks, taskId, itemId, (item) => patchAfterApply(item, indexes, result))
      try {
        const fresh = await apifoxApi.getAiGenTask(taskId)
        mergeTaskItems(this.tasks, taskId, fresh)
      } catch {
        /* 本地 patch 已更新；拉全量失败时仍可用 */
      }
      return result
    },

    // 批量入库：一次请求入库多个接口项，服务端聚合并回传最新任务（省去逐项串行往返）
    async applyItemsBatch(
      taskId: number,
      items: Schemas['AiGenBatchApplyItem'][],
    ): Promise<Schemas['AiGenBatchApplyResult']> {
      const result = await apifoxApi.applyAiGenTaskBatch(taskId, { items })
      mergeTaskItems(this.tasks, taskId, result.task)
      return result
    },

    // 打开某任务详情：拉全量存入 map（供 AiGenTaskProgress 读），未终态则轮询
    async loadTask(taskId: number): Promise<TaskOut> {
      const task = await apifoxApi.getAiGenTask(taskId)
      this.tasks[taskId] = task
      if (!isTerminal(task.status)) this.ensurePolling()
      return task
    },

    // 重试某失败接口：任务复位 pending，重新轮询
    async retryItem(taskId: number, itemId: number): Promise<void> {
      this.tasks[taskId] = await apifoxApi.retryAiGenTaskItem(taskId, itemId)
      this.ensurePolling()
    },

    async discardItem(
      taskId: number,
      itemId: number,
      indexes?: number[] | null,
    ): Promise<Schemas['AiGenDiscardResult']> {
      const item = this.tasks[taskId]?.items.find((i) => i.id === itemId)
      const idxs = indexes && indexes.length ? indexes : (item?.cases.map((_, i) => i) ?? [])
      const result = await apifoxApi.discardAiGenTaskItem(taskId, itemId, { indexes })
      patchTaskItem(this.tasks, taskId, itemId, (it) => patchAfterDiscard(it, idxs))
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
