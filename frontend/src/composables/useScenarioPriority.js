// 场景优先级（高/中/低）：标签配色常量 + 列表按优先级筛选。ScenarioPanel 与后续文件夹切片共用。
import { computed, ref } from 'vue'

export const PRIORITY_OPTIONS = [
  { value: 'high', label: '高', type: 'danger' },
  { value: 'medium', label: '中', type: 'warning' },
  { value: 'low', label: '低', type: 'info' },
]

export function priorityMeta(p) {
  return PRIORITY_OPTIONS.find((o) => o.value === p) || PRIORITY_OPTIONS[1]
}

// scenariosRef: Ref<Array> → 返回筛选状态与筛选后列表（空筛选时原样返回，不影响子场景引用所需全量）
export function useScenarioPriorityFilter(scenariosRef) {
  const priorityFilter = ref('')
  const visibleScenarios = computed(() =>
    priorityFilter.value
      ? scenariosRef.value.filter((s) => s.priority === priorityFilter.value)
      : scenariosRef.value,
  )
  return { priorityFilter, visibleScenarios }
}
