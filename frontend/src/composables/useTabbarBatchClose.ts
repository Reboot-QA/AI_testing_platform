import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { ElMessage } from 'element-plus'

export type BatchCloseCommand = 'left' | 'right' | 'others' | 'all'

const DIRTY_ABORT_MSG = '有未保存的标签，请先保存或单独关闭后再批量操作'

export interface BatchCloseTab {
  id: number
}

export function resolveBatchCloseTargets(
  tabs: BatchCloseTab[],
  activeId: number | null,
  command: BatchCloseCommand,
): number[] {
  if (!tabs.length) return []
  if (command === 'all') return tabs.map((t) => t.id)

  const idx = activeId == null ? -1 : tabs.findIndex((t) => t.id === activeId)
  if (idx < 0) return []

  switch (command) {
    case 'left':
      return tabs.slice(0, idx).map((t) => t.id)
    case 'right':
      return tabs.slice(idx + 1).map((t) => t.id)
    case 'others':
      return tabs.filter((t) => t.id !== activeId).map((t) => t.id)
  }
}

export function batchCloseDisabled(
  tabs: BatchCloseTab[],
  activeId: number | null,
): Record<BatchCloseCommand, boolean> {
  const idx = activeId == null ? -1 : tabs.findIndex((t) => t.id === activeId)
  return {
    left: idx <= 0,
    right: idx < 0 || idx >= tabs.length - 1,
    others: tabs.length <= 1,
    all: tabs.length === 0,
  }
}

/** 批量关闭：目标含 dirty 则整批中止；关全部时最后关激活 tab，避免中途切换激活态 */
export function tryBatchClose<T extends BatchCloseTab>(opts: {
  tabs: T[]
  activeId: number | null
  command: BatchCloseCommand
  isDirty: (tab: T) => boolean
  closeTab: (id: number) => void
}): 'ok' | 'dirty' | 'empty' {
  const { tabs, activeId, command, isDirty, closeTab } = opts
  const ids = resolveBatchCloseTargets(tabs, activeId, command)
  if (!ids.length) return 'empty'

  const idSet = new Set(ids)
  if (tabs.some((t) => idSet.has(t.id) && isDirty(t))) {
    ElMessage.warning(DIRTY_ABORT_MSG)
    return 'dirty'
  }

  for (const id of ids) {
    if (id !== activeId) closeTab(id)
  }
  if (activeId != null && idSet.has(activeId)) closeTab(activeId)
  return 'ok'
}

export function useTabbarBatchClose<T extends BatchCloseTab>(opts: {
  tabs: MaybeRefOrGetter<T[]>
  activeId: MaybeRefOrGetter<number | null>
  isDirty: (tab: T) => boolean
  closeTab: (id: number) => void
}) {
  const disabled = computed(() => batchCloseDisabled(toValue(opts.tabs), toValue(opts.activeId)))

  function onCommand(command: BatchCloseCommand): void {
    tryBatchClose({
      tabs: toValue(opts.tabs),
      activeId: toValue(opts.activeId),
      command,
      isDirty: opts.isDirty,
      closeTab: opts.closeTab,
    })
  }

  return { disabled, onCommand }
}
