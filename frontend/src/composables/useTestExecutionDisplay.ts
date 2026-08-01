import type { Schemas } from '@/api/types'
import { formatBeijingTime, formatBeijingWallClock } from '@/utils/datetime'
import type { DateInput } from '@/types/common'

type TestRun = Schemas['ManualTestRunSummaryOut'] | Schemas['ManualTestRunDetailOut']

export const runStatusLabel: Record<string, string> = {
  waiting: '待开始',
  running: '执行中',
  finished: '已完成',
}

export const runStatusType: Record<string, string> = {
  waiting: 'info',
  running: 'warning',
  finished: 'success',
}

export const resultLabel: Record<string, string> = {
  pending: '待测',
  pass: '通过',
  fail: '失败',
  blocked: '阻塞',
  skip: '跳过',
}

export const resultType: Record<string, string> = {
  pending: 'info',
  pass: 'success',
  fail: 'danger',
  blocked: 'warning',
  skip: '',
}

export function formatTime(value: DateInput): string {
  return formatBeijingTime(value)
}

export function formatWallTime(value: DateInput): string {
  return formatBeijingWallClock(value)
}

export function runProgress(run: TestRun | null): number {
  if (!run?.total_count) return 0
  return Math.round(((run.total_count - run.pending_count) / run.total_count) * 100)
}
