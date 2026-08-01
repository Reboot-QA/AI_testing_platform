import { get, post, type Id } from './request'

export type HubAiTaskType = 'requirement' | 'functional'

/** 列表/详情「类别」仅展示提供商名，去掉「 · model」后缀（历史任务兼容） */
export function formatHubTaskCategoryLabel(label: string | undefined | null): string {
  if (!label?.trim()) return '—'
  const sep = ' · '
  const idx = label.indexOf(sep)
  return idx >= 0 ? label.slice(0, idx) : label
}

export interface HubAiTaskBrief {
  id: number
  project_id: number
  task_type: HubAiTaskType
  status: string
  target: string
  category_label: string
  model_label?: string
  total_items: number
  done_items: number
  generated_total: number
  applied_total: number
  error?: string | null
  creator_name: string
  created_at: string
  finished_at?: string | null
}

export interface HubAiTaskPageOut {
  total: number
  items: HubAiTaskBrief[]
}

export interface HubAiTaskOut extends HubAiTaskBrief {
  meta?: Record<string, unknown> | null
  requirements?: HubAiTaskRequirementItem[] | null
}

export interface HubAiTaskRequirementItem {
  id: number
  title: string
  description?: string | null
  req_type: string
  priority: string
  requirement_id?: number | null
  imported_at?: string | null
}

export interface HubAiTaskCaseBrief {
  id: number
  link_id?: number
  title: string
  case_type: string
  priority: string
  preconditions?: string | null
  steps?: string | null
  expected_results?: string | null
  tags?: string | null
  requirement_title: string
  review_status: string
}

export type ListHubAiTasksParams = {
  task_type: HubAiTaskType
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  date_from?: string
  date_to?: string
  task_id?: number
}

export type HubAiTaskItemsPageParams = {
  page?: number
  page_size?: number
}

const HUB_TASK_ITEMS_PAGE_SIZE = 100

export const hubAiTasksApi = {
  listTasks: (projectId: Id, params: ListHubAiTasksParams) =>
    get<HubAiTaskPageOut>(`/projects/${projectId}/hub-ai-tasks`, { params }),

  getTask: (projectId: Id, taskId: number) =>
    get<HubAiTaskOut>(`/projects/${projectId}/hub-ai-tasks/${taskId}`),

  listRequirements: (projectId: Id, taskId: number, params?: HubAiTaskItemsPageParams) =>
    get<{ items: HubAiTaskRequirementItem[]; total: number }>(
      `/projects/${projectId}/hub-ai-tasks/${taskId}/requirements`,
      { params },
    ),

  listCases: (projectId: Id, taskId: number, params?: HubAiTaskItemsPageParams) =>
    get<{ items: HubAiTaskCaseBrief[]; total: number }>(
      `/projects/${projectId}/hub-ai-tasks/${taskId}/cases`,
      { params },
    ),

  discardRequirements: (projectId: Id, taskId: number, itemIds: number[]) =>
    post<{ discarded: number; message: string }>(
      `/projects/${projectId}/hub-ai-tasks/${taskId}/requirements/discard`,
      { item_ids: itemIds },
    ),

  cancelTask: (projectId: Id, taskId: number) =>
    post<HubAiTaskBrief>(`/projects/${projectId}/hub-ai-tasks/${taskId}/cancel`),
}

/** 拉取任务下全部需求明细（恢复进行中解析等场景） */
export async function fetchAllHubTaskRequirements(projectId: Id, taskId: number) {
  const items: HubAiTaskRequirementItem[] = []
  let page = 1
  let total = 0
  do {
    const res = await hubAiTasksApi.listRequirements(projectId, taskId, {
      page,
      page_size: HUB_TASK_ITEMS_PAGE_SIZE,
    })
    total = res.total
    items.push(...res.items)
    page += 1
  } while (items.length < total)
  return { items, total }
}

/** 拉取任务下全部用例明细（恢复进行中 AI 用例生成） */
export async function fetchAllHubTaskCases(projectId: Id, taskId: number) {
  const items: HubAiTaskCaseBrief[] = []
  let page = 1
  let total = 0
  do {
    const res = await hubAiTasksApi.listCases(projectId, taskId, {
      page,
      page_size: HUB_TASK_ITEMS_PAGE_SIZE,
    })
    total = res.total
    items.push(...res.items)
    page += 1
  } while (items.length < total)
  return { items, total }
}
