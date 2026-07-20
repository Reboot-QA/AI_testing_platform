import { computed, type ComputedRef } from 'vue'
import { useRoute } from 'vue-router'
import type { Id } from '@/api/request'

export function useRouteParamId(name = 'projectId'): ComputedRef<Id> {
  const route = useRoute()
  return computed(() => {
    const raw = route.params[name]
    return Array.isArray(raw) ? raw[0]! : raw
  })
}

export function useRouteParamIdOptional(name = 'projectId'): ComputedRef<Id | undefined> {
  const route = useRoute()
  return computed(() => {
    const raw = route.params[name]
    const value = Array.isArray(raw) ? raw[0] : raw
    return value || undefined
  })
}
