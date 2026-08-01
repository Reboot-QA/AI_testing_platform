import type { Requirement, RequirementStatus, ReviewStatus } from '@/types/common'
import { formatBeijingTime } from '@/utils/datetime'
import type { DateInput } from '@/types/common'

export const requirementTypeLabel: Record<string, string> = {
  functional: '功能',
  api: '接口',
  performance: '性能',
  security: '安全',
}

export const requirementSourceLabel: Record<string, string> = {
  manual: '手动',
  ai_document: '文档解析',
}

export const requirementStatusLabel: Record<RequirementStatus, string> = {
  draft: '草稿',
  approved: '已评审',
  closed: '已关闭',
}

export const requirementStatusType: Record<RequirementStatus, 'info' | 'success' | 'warning'> = {
  draft: 'info',
  approved: 'success',
  closed: 'warning',
}

export const reviewStatusLabel: Record<ReviewStatus, string> = {
  draft: '草稿',
  pending: '待评审',
  approved: '已通过',
  rejected: '已驳回',
}

export const reviewStatusType: Record<ReviewStatus, 'info' | 'warning' | 'success' | 'danger'> = {
  draft: 'info',
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
}

export function formatRequirementTime(value: DateInput): string {
  return formatBeijingTime(value)
}

export function displayRequirementSortOrder(
  row: Requirement,
  rowIndex: number,
  currentPage: number,
  pageSize: number,
): number {
  if (typeof row.sort_order === 'number' && row.sort_order > 0) return row.sort_order
  return (currentPage - 1) * pageSize + rowIndex + 1
}
