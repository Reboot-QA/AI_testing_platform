import { describe, expect, it } from 'vitest'
import type { Requirement } from '@/types/common'
import {
  displayRequirementSortOrder,
  formatRequirementTime,
  requirementSourceLabel,
  requirementStatusLabel,
  requirementStatusType,
  requirementTypeLabel,
  reviewStatusLabel,
  reviewStatusType,
} from '@/composables/useRequirementDisplay'

describe('label maps', () => {
  it('类型 / 来源 / 状态标签齐全', () => {
    expect(requirementTypeLabel.functional).toBe('功能')
    expect(requirementSourceLabel.ai_document).toBe('文档解析')
    expect(requirementStatusLabel.draft).toBe('草稿')
    expect(requirementStatusType.approved).toBe('success')
    expect(reviewStatusLabel.rejected).toBe('已驳回')
    expect(reviewStatusType.pending).toBe('warning')
  })
})

describe('formatRequirementTime', () => {
  it('委托北京时间格式化', () => {
    expect(formatRequirementTime(null)).toBe('-')
    expect(formatRequirementTime('2024-01-01T00:00:00Z')).toMatch(/08:00:00/)
  })
})

describe('displayRequirementSortOrder', () => {
  it('有正数 sort_order 时直接用', () => {
    const row = { sort_order: 7 } as Requirement
    expect(displayRequirementSortOrder(row, 0, 2, 20)).toBe(7)
  })

  it('缺省或 <=0 时按分页推算', () => {
    expect(displayRequirementSortOrder({} as Requirement, 0, 1, 20)).toBe(1)
    expect(displayRequirementSortOrder({ sort_order: 0 } as Requirement, 3, 2, 20)).toBe(24)
  })
})
