// 运行记录展示的纯格式化函数（测试报告 / 接口报告 tab 共用）
import { formatBeijingTime } from '@/utils/datetime'

export type RunStatus = 'running' | 'passed' | 'failed'

const STATUS_LABELS: Record<RunStatus, string> = {
  running: '执行中',
  passed: '通过',
  failed: '失败',
}

const STATUS_TAGS: Record<RunStatus, string> = {
  running: 'warning',
  passed: 'success',
  failed: 'danger',
}

export const statusLabel = (s: string): string => STATUS_LABELS[s as RunStatus] || s
export const statusTag = (s: string): string => STATUS_TAGS[s as RunStatus] || 'info'
export const formatTime = (v: string | number | Date | null | undefined): string =>
  formatBeijingTime(v)
