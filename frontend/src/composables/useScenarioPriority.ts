// 场景优先级（高/中/低）：标签配色常量 + 列表按优先级筛选。ScenarioPanel 与后续文件夹切片共用。
import { computed, ref, type ComputedRef, type Ref } from 'vue'

export type ScenarioPriority = 'high' | 'medium' | 'low' | string

export interface PriorityOption {
  value: ScenarioPriority
  label: string
  type: 'danger' | 'warning' | 'info' | string
}

export interface ScenarioWithPriority {
  priority?: ScenarioPriority
  [key: string]: unknown
}

export const PRIORITY_OPTIONS: PriorityOption[] = [
  { value: 'high', label: '高', type: 'danger' },
  { value: 'medium', label: '中', type: 'warning' },
  { value: 'low', label: '低', type: 'info' },
]

export function priorityMeta(p: ScenarioPriority | null | undefined): PriorityOption {
  return PRIORITY_OPTIONS.find((o) => o.value === p) || PRIORITY_OPTIONS[1]
}

export function useScenarioPriorityFilter(scenariosRef: Ref<ScenarioWithPriority[]>): {
  priorityFilter: Ref<string>
  visibleScenarios: ComputedRef<ScenarioWithPriority[]>
} {
  const priorityFilter = ref('')
  const visibleScenarios = computed(() =>
    priorityFilter.value
      ? scenariosRef.value.filter((s) => s.priority === priorityFilter.value)
      : scenariosRef.value,
  )
  return { priorityFilter, visibleScenarios }
}
