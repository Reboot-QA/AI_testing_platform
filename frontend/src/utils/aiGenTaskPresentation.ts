import type { Schemas } from '@/api/types'

type Item = Schemas['AiGenTaskItemOut']
type View = 'all' | 'pending' | 'done' | 'discarded'

export const AI_GEN_TASK_STATUS_LABELS: Record<string, string> = {
  pending: '排队中',
  running: '生成中',
  succeeded: '全部完成',
  partial: '部分完成',
  failed: '生成失败',
  canceled: '已取消',
}

export function getAiGenItemCases(item: Item, view: View): Schemas['CaseCreate'][] {
  if (view === 'done') return item.applied_cases ?? []
  if (view === 'discarded') return item.discarded_cases ?? []
  return item.cases
}

export function isAiGenItemCasesVisible(item: Item, view: View): boolean {
  if (item.status !== 'succeeded' && item.status !== 'running') return false
  if (view === 'done') return item.applied_count > 0 || (item.applied_cases?.length ?? 0) > 0
  if (view === 'discarded') return (item.discarded_cases?.length ?? 0) > 0
  if (view === 'pending') return item.cases.length > 0 || item.status === 'running'
  return (
    item.cases.length > 0 ||
    item.status === 'running' ||
    item.applied_count > 0 ||
    (item.discarded_cases?.length ?? 0) > 0
  )
}

export function formatAiGenTaskDuration(
  createdAt?: string | null,
  finishedAt?: string | null,
): string {
  if (!finishedAt || !createdAt) return ''
  const elapsed = new Date(finishedAt).getTime() - new Date(createdAt).getTime()
  if (elapsed <= 0) return ''
  const seconds = Math.round(elapsed / 1000)
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

export function getAiGenItemStatusText(item: Item): string {
  if (item.status === 'succeeded') {
    if (item.cases.length) return `${item.cases.length} 条待入库`
    if (item.applied_count) return `已入库 ${item.applied_count} 条`
    if (item.discarded_cases?.length) return `已废弃 ${item.discarded_cases.length} 条`
    return '完成'
  }
  if (item.status === 'running') return item.cases.length ? `${item.cases.length} 条…` : '生成中'
  return AI_GEN_TASK_STATUS_LABELS[item.status] ?? item.status
}

export function getAiGenItemStatusType(status: string): string {
  return (
    { succeeded: 'success', failed: 'danger', running: 'primary', canceled: 'info' }[status] ?? ''
  )
}

export function getAiGenCategoryTagType(category: string): string {
  return (
    { positive: 'success', negative: 'warning', boundary: '', security: 'danger' }[category] ??
    'info'
  )
}
