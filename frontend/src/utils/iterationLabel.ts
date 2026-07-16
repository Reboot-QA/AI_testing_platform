// 数据驱动/循环运行的分组标题：有注入数据→「第 N 组数据 · k=v, ...」；无数据(循环)→「第 N 轮」
export function iterationLabel(
  index: number,
  data: Record<string, unknown> | null | undefined,
): string {
  const n = index + 1
  const entries = Object.entries(data || {})
  if (entries.length === 0) return `第 ${n} 轮`
  const preview = entries.map(([k, v]) => `${k}=${v}`).join(', ')
  return `第 ${n} 组数据 · ${preview}`
}
