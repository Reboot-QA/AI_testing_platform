import { computed } from 'vue'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import { useRoute } from 'vue-router'

function positiveId(value: unknown): number | null {
  const id = Number(value)
  return Number.isInteger(id) && id > 0 ? id : null
}

/** 从路由 query 解析列表关键字（filter=kw:xxx 或 keyword=xxx）。 */
export function parseWorkspaceKeywordFromRoute(
  route: RouteLocationNormalizedLoaded,
): string | null {
  const filter = route.query.filter
  if (typeof filter === 'string' && filter.startsWith('kw:')) {
    const kw = filter.slice(3).trim()
    if (kw) return kw
  }
  const keyword = route.query.keyword
  if (typeof keyword === 'string' && keyword.trim()) return keyword.trim()
  return null
}

export function parseWorkspaceTaskIdFromRoute(route: RouteLocationNormalizedLoaded): number | null {
  return positiveId(route.query.task)
}

export function parseWorkspaceRunIdFromRoute(route: RouteLocationNormalizedLoaded): number | null {
  return positiveId(route.query.run)
}

/** 兼容工作区列表页的筛选条件；非法或空值统一忽略。 */
export function readWorkspaceListFilter(): string | null {
  const value = useRoute().query.filter
  return typeof value === 'string' && value.trim() ? value : null
}

/** 兼容报告深链中的运行记录 id。 */
export function readWorkspaceRunId(): number | null {
  return parseWorkspaceRunIdFromRoute(useRoute())
}

/** 兼容 AI 任务列表页的任务详情深链。 */
export function readWorkspaceTaskId(): number | null {
  return parseWorkspaceTaskIdFromRoute(useRoute())
}

/** 报告页返回来源，仅接受已声明的来源页。 */
export function useWorkspaceReturnRoute() {
  const route = useRoute()
  const from = computed(() => (route.query.from === 'schedules' ? 'schedules' : null))
  return { from }
}
