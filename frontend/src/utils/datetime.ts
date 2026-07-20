const BEIJING_TZ = 'Asia/Shanghai'

function parseApiDateTime(value: string | Date | number | null | undefined): Date | null {
  if (value == null) return null
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  if (typeof value === 'number') return Number.isNaN(value) ? null : new Date(value)
  const text = String(value).trim()
  if (!text) return null
  const iso = text.includes('T') ? text : text.replace(' ', 'T')
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/i.test(iso) ? iso : `${iso}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatBeijingTime(
  value: string | Date | number | null | undefined,
  fallback = '-',
): string {
  const date = parseApiDateTime(value)
  if (!date) return fallback
  return date.toLocaleString('zh-CN', {
    timeZone: BEIJING_TZ,
    hour12: false,
  })
}

/** 工作台活动流等场景：近期显示相对时间，较远显示北京时间 */
export function formatRelativeTime(
  value: string | Date | number | null | undefined,
  fallback = '-',
): string {
  const date = parseApiDateTime(value)
  if (!date) return fallback

  const diffSec = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diffSec < 60) return '刚刚'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay} 天前`
  return formatBeijingTime(date)
}
