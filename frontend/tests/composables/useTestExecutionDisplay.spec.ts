import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/types'
import {
  formatTime,
  formatWallTime,
  resultLabel,
  resultType,
  runProgress,
  runStatusLabel,
  runStatusType,
} from '@/composables/useTestExecutionDisplay'

describe('label maps', () => {
  it('运行状态与结果标签齐全', () => {
    expect(runStatusLabel.running).toBe('执行中')
    expect(runStatusType.finished).toBe('success')
    expect(resultLabel.fail).toBe('失败')
    expect(resultType.blocked).toBe('warning')
    expect(resultType.skip).toBe('')
  })
})

describe('formatTime / formatWallTime', () => {
  it('空值返回 -', () => {
    expect(formatTime(null)).toBe('-')
    expect(formatWallTime(undefined)).toBe('-')
  })

  it('UTC 与 wall clock 各自格式化', () => {
    expect(formatTime('2024-01-01T00:00:00Z')).toMatch(/08:00:00/)
    expect(formatWallTime('2024-06-01 12:30:00')).toMatch(/12:30:00/)
  })
})

describe('runProgress', () => {
  it('空 run 或 total_count=0 返回 0', () => {
    expect(runProgress(null)).toBe(0)
    expect(
      runProgress({ total_count: 0, pending_count: 0 } as Schemas['ManualTestRunSummaryOut']),
    ).toBe(0)
  })

  it('按已完成数算百分比并四舍五入', () => {
    const run = {
      total_count: 3,
      pending_count: 1,
    } as Schemas['ManualTestRunSummaryOut']
    expect(runProgress(run)).toBe(67)
  })
})
