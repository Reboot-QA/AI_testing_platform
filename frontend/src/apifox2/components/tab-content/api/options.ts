import { API_STATUS_CONFIG, HTTP_CODE_CONFIG, HTTP_METHOD_CONFIG } from '@/apifox2/configs/static'
import { ContentType } from '@/apifox2/enums'

export const methodOptions = Object.entries(HTTP_METHOD_CONFIG).map(([method, { color }]) => ({
  value: method,
  color,
}))

export const statusOptions = Object.entries(API_STATUS_CONFIG).map(([value, { text, color }]) => ({
  value,
  text,
  color,
}))

export const httpCodeOptions = Object.entries(HTTP_CODE_CONFIG).map(
  ([, { text, value, desc }]) => ({
    label: value,
    value,
    text,
    desc,
  }),
)

export const contentTypeOptions = [
  { label: 'JSON', value: ContentType.JSON },
  { label: 'XML', value: ContentType.XML },
  { label: 'HTML', value: ContentType.HTML },
  { label: 'Raw', value: ContentType.Raw },
  { label: 'Binary', value: ContentType.Binary },
]

/** 简易日期格式化：YYYY年M月D日（替代 dayjs）。 */
export function formatCnDate(value?: string): string {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}
