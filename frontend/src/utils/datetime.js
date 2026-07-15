const BEIJING_TZ = 'Asia/Shanghai'

function parseApiDateTime(value) {
  if (!value) return null
  const text = String(value).trim()
  if (!text) return null
  const iso = text.includes('T') ? text : text.replace(' ', 'T')
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/i.test(iso) ? iso : `${iso}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatBeijingTime(value, fallback = '-') {
  const date = parseApiDateTime(value)
  if (!date) return fallback
  return date.toLocaleString('zh-CN', {
    timeZone: BEIJING_TZ,
    hour12: false,
  })
}
