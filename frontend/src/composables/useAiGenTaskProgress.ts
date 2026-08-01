import { computed, reactive, ref, watch, type ComputedRef, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { categoryLabel } from '@/utils/caseCategory'
import { aiTaskModelDisplay } from '@/utils/aiTaskModelLabel'
import {
  AI_GEN_TASK_STATUS_LABELS,
  formatAiGenTaskDuration,
  getAiGenItemCases,
  getAiGenItemStatusText,
  getAiGenItemStatusType,
  isAiGenItemCasesVisible,
} from '@/utils/aiGenTaskPresentation'

type Item = Schemas['AiGenTaskItemOut']
type RecordView = 'pending' | 'done' | 'discarded'
type View = 'all' | RecordView

export interface AiGenTaskProgressProps {
  taskId: string | number
  projectId?: Id
  endpointId?: number
  view: View
  hideMultiEndpointBatch: boolean
}

export interface AiGenTaskProgressController {
  task: ComputedRef<Schemas['AiGenTaskOut'] | undefined>
  projectId: ComputedRef<Id>
  compact: ComputedRef<boolean>
  items: ComputedRef<Item[]>
  pagedItems: ComputedRef<Item[]>
  effectiveView: ComputedRef<View>
  recordView: Ref<RecordView>
  showRecordTabs: ComputedRef<boolean>
  pendingTabCount: ComputedRef<number>
  doneTabCount: ComputedRef<number>
  discardedTabCount: ComputedRef<number>
  recordEmptyText: ComputedRef<string>
  percent: ComputedRef<number>
  barStatus: ComputedRef<'' | 'success' | 'warning' | 'exception'>
  running: ComputedRef<boolean>
  overallText: ComputedRef<string>
  targetText: ComputedRef<string>
  categoryConfig: ComputedRef<string>
  modeText: ComputedRef<string>
  durationText: ComputedRef<string>
  genLogs: ComputedRef<string[]>
  expanded: Ref<number[]>
  selected: Record<number, boolean[]>
  epChecked: Record<number, boolean>
  applying: Record<number, boolean>
  discarding: Record<number, boolean>
  retrying: Record<number, boolean>
  batchApplying: Ref<boolean>
  applicableItems: ComputedRef<Item[]>
  epCheckedCount: ComputedRef<number>
  allEpSel: ComputedRef<boolean>
  someEpSel: ComputedRef<boolean>
  caseActionsEnabled: ComputedRef<boolean>
  showEndpointPager: ComputedRef<boolean>
  endpointPage: Ref<number>
  endpointPageSize: Ref<number>
  endpointPageSizes: readonly number[]
  itemCaseList: (item: Item) => Schemas['CaseCreate'][]
  casesBlockVisible: (item: Item) => boolean
  canSelectEp: (item: Item) => boolean
  isItemExpanded: (itemId: number) => boolean
  isCaseOpen: (itemId: number, index: number) => boolean
  toggleCase: (itemId: number, index: number) => void
  statusText: (item: Item) => string
  statusType: (status: string) => string
  selCount: (item: Item) => number
  allSel: (item: Item) => boolean
  someSel: (item: Item) => boolean
  toggleAll: (item: Item, selected: boolean) => void
  toggleAllEp: (selected: boolean) => void
  onEndpointPageChange: (page: number) => void
  onEndpointPageSizeChange: (size: number) => void
  batchApply: () => Promise<void>
  apply: (item: Item) => Promise<void>
  discard: (item: Item) => Promise<void>
  applyOne: (item: Item, index: number) => Promise<void>
  discardOne: (item: Item, index: number) => Promise<void>
  retry: (item: Item) => Promise<void>
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

export function useAiGenTaskProgress(
  props: AiGenTaskProgressProps,
  onApplied: (endpointId: number) => void,
): AiGenTaskProgressController {
  const store = useApifoxAiGenerateStore()
  const recordView = ref<RecordView>('pending')
  const showRecordTabs = computed(() => props.hideMultiEndpointBatch && props.endpointId == null)
  const effectiveView = computed<View>(() => (showRecordTabs.value ? recordView.value : props.view))
  const task = computed(() => store.taskById(Number(props.taskId)))
  const projectId = computed<Id>(() => props.projectId ?? task.value?.project_id ?? 0)
  const allItems = computed<Item[]>(() => task.value?.items ?? [])
  const compact = computed(() => props.endpointId != null)
  const items = computed<Item[]>(() => {
    let list = allItems.value
    if (props.endpointId != null)
      list = list.filter((item) => item.endpoint_id === props.endpointId)
    if (effectiveView.value === 'pending') {
      return list.filter((item) => item.status !== 'succeeded' || item.cases.length > 0)
    }
    if (effectiveView.value === 'done') {
      return list.filter((item) => item.applied_count > 0 || (item.applied_cases?.length ?? 0) > 0)
    }
    if (effectiveView.value === 'discarded') {
      return list.filter((item) => (item.discarded_cases?.length ?? 0) > 0)
    }
    return list
  })
  const pendingTabCount = computed(() =>
    allItems.value.reduce(
      (count, item) => count + (item.status === 'succeeded' ? item.cases.length : 0),
      0,
    ),
  )
  const doneTabCount = computed(() =>
    allItems.value.reduce((count, item) => count + item.applied_count, 0),
  )
  const discardedTabCount = computed(() =>
    allItems.value.reduce((count, item) => count + (item.discarded_cases?.length ?? 0), 0),
  )
  const recordEmptyText = computed(() => {
    if (recordView.value === 'done') {
      return doneTabCount.value
        ? '该任务有入库记录，但无快照（升级前入库）；请到接口用例列表查看'
        : '暂无已入库记录'
    }
    return recordView.value === 'discarded' ? '暂无废弃记录' : '暂无待入库用例'
  })
  const itemCaseList = (item: Item): Schemas['CaseCreate'][] =>
    getAiGenItemCases(item, effectiveView.value)
  const casesBlockVisible = (item: Item): boolean =>
    isAiGenItemCasesVisible(item, effectiveView.value)

  const endpointPageSizes = [10, 20, 50] as const
  const endpointPage = ref(1)
  const endpointPageSize = ref(20)
  const showEndpointPager = computed(
    () => !compact.value && items.value.length > endpointPageSizes[0],
  )
  const pagedItems = computed<Item[]>(() => {
    if (compact.value || items.value.length <= endpointPageSize.value) return items.value
    const start = (endpointPage.value - 1) * endpointPageSize.value
    return items.value.slice(start, start + endpointPageSize.value)
  })
  const onEndpointPageChange = (page: number): void => {
    endpointPage.value = page
  }
  const onEndpointPageSizeChange = (size: number): void => {
    endpointPageSize.value = size
    endpointPage.value = 1
  }
  watch(
    () => props.taskId,
    () => {
      endpointPage.value = 1
    },
  )
  watch(
    () => items.value.length,
    (length) => {
      const maxPage = Math.max(1, Math.ceil(length / endpointPageSize.value))
      if (endpointPage.value > maxPage) endpointPage.value = maxPage
    },
  )

  const caseActionsEnabled = computed(
    () =>
      effectiveView.value === 'pending' ||
      (props.hideMultiEndpointBatch && effectiveView.value === 'all'),
  )
  const running = computed(
    () =>
      !!task.value && !['succeeded', 'partial', 'failed', 'canceled'].includes(task.value.status),
  )
  const targetText = computed(() => {
    const currentTask = task.value
    if (!currentTask) return ''
    if (currentTask.total_items === 1 && currentTask.items[0]) {
      const item = currentTask.items[0]
      return `${item.endpoint_method} ${item.endpoint_name}`
    }
    return `批量 · ${currentTask.total_items} 接口`
  })
  const categoryConfig = computed(() => {
    const text = task.value?.categories
      .map(
        (category) =>
          `${categoryLabel(category.category)}（${category.count ? `限量 ${category.count}` : '自动'}）`,
      )
      .join(' · ')
    return text || '-'
  })
  const modeText = computed(() => {
    const currentTask = task.value
    if (!currentTask) return '-'
    return aiTaskModelDisplay(currentTask.model_label, {
      mode: currentTask.mode ?? undefined,
      mock_mode: currentTask.mode === 'mock',
    })
  })
  const durationText = computed(() => {
    const currentTask = task.value
    return currentTask?.finished_at && currentTask.created_at
      ? formatAiGenTaskDuration(currentTask.created_at, currentTask.finished_at)
      : ''
  })
  const percent = computed(() => {
    const currentTask = task.value
    if (!currentTask || !currentTask.total_items) return 0
    if (currentTask.total_items === 1 && items.value.length === 1) {
      const item = items.value[0]
      if (item.status === 'succeeded') return 100
      if (item.status === 'running') {
        if (item.cases.length)
          return Math.min(
            92,
            Math.round((item.cases.length / Math.max(currentTask.categories.length, 1) / 3) * 100),
          )
        return 8
      }
      if (item.status === 'pending') return 0
    }
    return Math.round((currentTask.done_items / currentTask.total_items) * 100)
  })
  const barStatus = computed<'' | 'success' | 'warning' | 'exception'>(() => {
    if (task.value?.status === 'succeeded') return 'success'
    if (task.value?.status === 'failed') return 'exception'
    return task.value?.status === 'partial' ? 'warning' : ''
  })
  const overallText = computed(() => {
    const currentTask = task.value
    if (!currentTask) return ''
    const base = `${AI_GEN_TASK_STATUS_LABELS[currentTask.status] || currentTask.status} · ${currentTask.done_items}/${currentTask.total_items} 个接口`
    if (currentTask.total_items === 1 && items.value[0]?.status === 'running') {
      return items.value[0].cases.length
        ? `${base} · 已生成 ${items.value[0].cases.length} 条用例`
        : `${base} · 等待模型响应…`
    }
    return base
  })
  const genLogs = computed(() => {
    const currentTask = task.value
    if (!currentTask) return []
    const lines = [
      `任务 #${currentTask.id} · ${AI_GEN_TASK_STATUS_LABELS[currentTask.status] || currentTask.status}`,
    ]
    if (currentTask.error) lines.push(`任务错误：${currentTask.error}`)
    items.value.forEach((item) => {
      const endpoint = `${item.endpoint_method} ${item.endpoint_name}`
      if (item.status === 'pending') lines.push(`${endpoint}：排队中`)
      else if (item.status === 'running')
        lines.push(
          `${endpoint}：生成中${item.cases.length ? `，已产出 ${item.cases.length} 条` : '…'}`,
        )
      else if (item.status === 'succeeded')
        lines.push(
          `${endpoint}：完成，共 ${item.cases.length + item.applied_count + (item.discarded_cases?.length ?? 0)} 条用例`,
        )
      else if (item.status === 'failed')
        lines.push(`${endpoint}：失败 · ${item.error || '未知错误'}`)
      else if (item.status === 'canceled') lines.push(`${endpoint}：已取消`)
      if (item.applied_count > 0) lines.push(`${endpoint}：已入库 ${item.applied_count} 条`)
    })
    return lines
  })

  const expanded = ref<number[]>([])
  const selected = reactive<Record<number, boolean[]>>({})
  const epChecked = reactive<Record<number, boolean>>({})
  const applying = reactive<Record<number, boolean>>({})
  const discarding = reactive<Record<number, boolean>>({})
  const retrying = reactive<Record<number, boolean>>({})
  const batchApplying = ref(false)
  const openCaseKeys = ref(new Set<string>())
  const caseKey = (itemId: number, index: number): string => `${itemId}:${index}`
  const isCaseOpen = (itemId: number, index: number): boolean =>
    openCaseKeys.value.has(caseKey(itemId, index))
  const isItemExpanded = (itemId: number): boolean => expanded.value.includes(itemId)
  const toggleCase = (itemId: number, index: number): void => {
    const next = new Set(openCaseKeys.value)
    const key = caseKey(itemId, index)
    next.has(key) ? next.delete(key) : next.add(key)
    openCaseKeys.value = next
  }
  const statusText = (item: Item): string => getAiGenItemStatusText(item)
  const statusType = (status: string): string => getAiGenItemStatusType(status)
  watch(
    () => items.value.map((item) => [item.id, item.status, item.cases.length, item.applied_count]),
    () => {
      items.value.forEach((item) => {
        if (
          (item.status === 'succeeded' || item.status === 'running') &&
          item.cases.length &&
          !selected[item.id]
        ) {
          selected[item.id] = item.cases.map(() => true)
          if (item.applied_count === 0 && item.status === 'succeeded') epChecked[item.id] = true
        } else if (item.cases.length && selected[item.id]) {
          selected[item.id] = item.cases.map((_, index) => selected[item.id][index] ?? true)
        } else if (!item.cases.length) delete selected[item.id]
      })
      if (compact.value && items.value.length && !expanded.value.length)
        expanded.value = items.value.map((item) => item.id)
    },
    { immediate: true },
  )
  const canSelectEp = (item: Item): boolean => item.status === 'succeeded' && item.cases.length > 0
  const applicableItems = computed(() => items.value.filter(canSelectEp))
  const epCheckedCount = computed(
    () => applicableItems.value.filter((item) => epChecked[item.id]).length,
  )
  const allEpSel = computed(
    () => applicableItems.value.length > 0 && epCheckedCount.value === applicableItems.value.length,
  )
  const someEpSel = computed(() => epCheckedCount.value > 0 && !allEpSel.value)
  const toggleAllEp = (checked: boolean): void => {
    applicableItems.value.forEach((item) => (epChecked[item.id] = checked))
  }
  const selCount = (item: Item): number => (selected[item.id] ?? []).filter(Boolean).length
  const allSel = (item: Item): boolean =>
    item.cases.length > 0 && selCount(item) === item.cases.length
  const someSel = (item: Item): boolean => selCount(item) > 0 && !allSel(item)
  const toggleAll = (item: Item, checked: boolean): void => {
    selected[item.id] = item.cases.map(() => checked)
  }
  const syncAfterCasesRemoved = (item: Item, removedIndexes: number[]): void => {
    const removed = new Set(removedIndexes)
    if (selected[item.id])
      selected[item.id] = selected[item.id].filter((_, index) => !removed.has(index))
    const prefix = `${item.id}:`
    const next = new Set<string>()
    openCaseKeys.value.forEach((key) => {
      if (!key.startsWith(prefix)) return next.add(key)
      const index = Number(key.slice(prefix.length))
      if (!removed.has(index))
        next.add(
          `${item.id}:${index - removedIndexes.filter((removedIndex) => removedIndex < index).length}`,
        )
    })
    openCaseKeys.value = next
  }
  const indexesRemovedByApply = (
    snapshots: { index: number; name: string }[],
    failed: string[],
  ): number[] => {
    const failedSet = new Set(failed)
    return snapshots
      .filter((snapshot) => snapshot.name && !failedSet.has(snapshot.name))
      .map((snapshot) => snapshot.index)
  }
  const batchApply = async (): Promise<void> => {
    const targets = applicableItems.value.filter((item) => epChecked[item.id] && selCount(item) > 0)
    if (!targets.length) return
    batchApplying.value = true
    try {
      const result = await store.applyItemsBatch(
        Number(props.taskId),
        targets.map((item) => ({
          item_id: item.id,
          indexes: item.cases
            .map((_, index) => index)
            .filter((index) => selected[item.id]?.[index]),
        })),
      )
      targets.forEach((item) => onApplied(item.endpoint_id))
      const suffix = result.skipped ? `，跳过 ${result.skipped} 条已存在` : ''
      const message = `批量入库${result.failed?.length ? '：部分完成' : '完成'}：${result.applied_items} 个接口共创建 ${result.created} 条用例${suffix}`
      result.failed?.length ? ElMessage.warning(message) : ElMessage.success(message)
    } catch {
      ElMessage.error('批量入库失败，请重试')
    } finally {
      batchApplying.value = false
    }
  }
  const apply = async (item: Item): Promise<void> => {
    const indexes = item.cases
      .map((_, index) => index)
      .filter((index) => selected[item.id]?.[index])
    const snapshots = indexes.map((index) => ({ index, name: item.cases[index]?.name ?? '' }))
    applying[item.id] = true
    try {
      const result = await store.applyItem(Number(props.taskId), item.id, indexes)
      syncAfterCasesRemoved(item, indexesRemovedByApply(snapshots, result.failed))
      const suffix = result.skipped ? `，跳过 ${result.skipped} 条已存在` : ''
      result.failed.length
        ? ElMessage.warning(
            `${item.endpoint_name}：已创建 ${result.created} 条，${result.failed.length} 条失败${suffix}`,
          )
        : ElMessage.success(`${item.endpoint_name}：已创建 ${result.created} 条用例${suffix}`)
      onApplied(item.endpoint_id)
    } catch (error) {
      ElMessage.error(errorMessage(error, '入库失败'))
    } finally {
      applying[item.id] = false
    }
  }
  const discardIndexes = async (item: Item, indexes: number[]): Promise<void> => {
    if (!indexes.length) return
    discarding[item.id] = true
    try {
      const result = await store.discardItem(Number(props.taskId), item.id, indexes)
      syncAfterCasesRemoved(item, indexes)
      ElMessage.success(`已废弃 ${result.discarded} 条预览用例`)
    } catch (error) {
      ElMessage.error(errorMessage(error, '废弃失败'))
    } finally {
      discarding[item.id] = false
    }
  }
  const discard = (item: Item): Promise<void> =>
    discardIndexes(
      item,
      item.cases.map((_, index) => index).filter((index) => selected[item.id]?.[index]),
    )
  const applyOne = async (item: Item, index: number): Promise<void> => {
    const snapshots = [{ index, name: item.cases[index]?.name ?? '' }]
    applying[item.id] = true
    try {
      const result = await store.applyItem(Number(props.taskId), item.id, [index])
      syncAfterCasesRemoved(item, indexesRemovedByApply(snapshots, result.failed))
      const suffix = result.skipped ? `，跳过 ${result.skipped} 条已存在` : ''
      if (result.failed.length) ElMessage.warning(`入库失败：${result.failed.join('、')}${suffix}`)
      else if (result.created) {
        ElMessage.success(`已入库 1 条用例${suffix}`)
        onApplied(item.endpoint_id)
      } else ElMessage.info(`未新建用例${suffix}`)
    } catch (error) {
      ElMessage.error(errorMessage(error, '入库失败'))
    } finally {
      applying[item.id] = false
    }
  }
  const discardOne = (item: Item, index: number): Promise<void> => discardIndexes(item, [index])
  const retry = async (item: Item): Promise<void> => {
    retrying[item.id] = true
    try {
      await store.retryItem(Number(props.taskId), item.id)
      ElMessage.info(`${item.endpoint_name}：已重新排队生成`)
    } catch (error) {
      ElMessage.error(errorMessage(error, '重试失败'))
    } finally {
      retrying[item.id] = false
    }
  }
  return {
    task,
    projectId,
    compact,
    items,
    pagedItems,
    effectiveView,
    recordView,
    showRecordTabs,
    pendingTabCount,
    doneTabCount,
    discardedTabCount,
    recordEmptyText,
    percent,
    barStatus,
    running,
    overallText,
    targetText,
    categoryConfig,
    modeText,
    durationText,
    genLogs,
    expanded,
    selected,
    epChecked,
    applying,
    discarding,
    retrying,
    batchApplying,
    applicableItems,
    epCheckedCount,
    allEpSel,
    someEpSel,
    caseActionsEnabled,
    showEndpointPager,
    endpointPage,
    endpointPageSize,
    endpointPageSizes,
    itemCaseList,
    casesBlockVisible,
    canSelectEp,
    isItemExpanded,
    isCaseOpen,
    toggleCase,
    statusText,
    statusType,
    selCount,
    allSel,
    someSel,
    toggleAll,
    toggleAllEp,
    onEndpointPageChange,
    onEndpointPageSizeChange,
    batchApply,
    apply,
    discard,
    applyOne,
    discardOne,
    retry,
  }
}
