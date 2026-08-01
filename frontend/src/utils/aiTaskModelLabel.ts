/** 任务列表/详情「模型」列：优先 meta.model，否则 model_label，再解析 · / . 后缀 */

function peelModelFromCombined(text: string): string {
  const t = text.trim()
  if (!t) return ''
  for (const sep of [' · ', ' ·', '· ', '·', '.']) {
    if (t.includes(sep)) {
      return t.split(sep).pop()!.trim()
    }
  }
  return t
}

export function aiTaskModelDisplay(
  modelLabel?: string | null,
  meta?: Record<string, unknown> | null,
): string {
  if (meta?.mock_mode === true || meta?.mode === 'mock') return 'Mock'
  const fromMeta = typeof meta?.model === 'string' ? meta.model.trim() : ''
  if (fromMeta) return fromMeta
  const label = (modelLabel || '').trim()
  if (!label) return '—'
  if (label === 'Mock') return 'Mock'
  return peelModelFromCombined(label)
}
