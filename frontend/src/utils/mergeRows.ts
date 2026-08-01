/**
 * 轮询刷新场景下的列表就地合并。
 *
 * id 序列未变时只覆盖字段、保留原有对象引用，让表格按单元格粒度更新，
 * 避免每次刷新都整表重建造成视觉抖动；结构变化（增删 / 翻页 / 排序）时整体替换。
 */
export function mergeRowsInPlace<T extends { id: number }>(current: T[], next: T[]): T[] {
  const sameRows =
    current.length === next.length && current.every((row, i) => row.id === next[i].id)
  if (!sameRows) return next
  next.forEach((row, i) => Object.assign(current[i], row))
  return current
}
