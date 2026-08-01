import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import {
  PRIORITY_OPTIONS,
  priorityMeta,
  useScenarioPriorityFilter,
} from '@/composables/useScenarioPriority'

describe('priorityMeta / PRIORITY_OPTIONS', () => {
  it('命中高中低；未知回退中', () => {
    expect(priorityMeta('high')).toEqual({ value: 'high', label: '高', type: 'danger' })
    expect(priorityMeta('low').label).toBe('低')
    expect(priorityMeta(null)).toBe(PRIORITY_OPTIONS[1])
    expect(priorityMeta('unknown')).toBe(PRIORITY_OPTIONS[1])
  })
})

describe('useScenarioPriorityFilter', () => {
  it('空过滤返回全部；有值时按 priority 等值筛', () => {
    const scenarios = ref([
      { id: 1, priority: 'high' as const },
      { id: 2, priority: 'medium' as const },
      { id: 3, priority: 'high' as const },
    ])
    const { priorityFilter, visibleScenarios } = useScenarioPriorityFilter(scenarios)
    expect(visibleScenarios.value).toHaveLength(3)
    priorityFilter.value = 'high'
    expect(visibleScenarios.value.map((s) => s.id)).toEqual([1, 3])
    priorityFilter.value = ''
    expect(visibleScenarios.value).toHaveLength(3)
  })
})
