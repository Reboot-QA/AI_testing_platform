import { computed, inject, provide, type ComputedRef, type InjectionKey, type Ref } from 'vue'
import type { EditorVariable, KvRow } from '@/types/apifox'
import type { Schemas } from '@/api/types'
import { collectProcessorExtractVariables, VARIABLE_SCOPE_LABELS } from '@/utils/apiCaseConfig'
import { useResolvableVars, type VarMap } from '@/composables/useResolvableVars'

export interface EditorVariableContext {
  postProcessors?: Schemas['ProcessorRow'][]
  variableRows?: KvRow[]
  extractedVariables?: Record<string, string>
}

const KEY: InjectionKey<ComputedRef<EditorVariable[]>> = Symbol('editorVariables')
const PROJECT_PROCESSORS_KEY: InjectionKey<Ref<Schemas['ProcessorRow'][]>> =
  Symbol('projectPostProcessors')

function fromResolvable(map: VarMap): EditorVariable[] {
  return Object.entries(map).map(([name, v]) => ({
    name,
    value: v.value,
    scope: 'resolved',
    scopeLabel: v.source,
  }))
}

function mergeProcessors(
  projectProcessors: Schemas['ProcessorRow'][],
  localProcessors: Schemas['ProcessorRow'][] = [],
): Schemas['ProcessorRow'][] {
  return [...projectProcessors, ...localProcessors]
}

function mergeEditorVariables(resolvable: VarMap, ctx: EditorVariableContext): EditorVariable[] {
  const merged = new Map<string, EditorVariable>()
  fromResolvable(resolvable).forEach((v) => merged.set(v.name, v))

  collectProcessorExtractVariables(ctx.postProcessors, ctx.extractedVariables).forEach((v) => {
    merged.set(v.name, v)
  })

  ;(ctx.variableRows || []).forEach((row) => {
    if (row?.enabled === false) return
    const name = (row.key || '').trim()
    if (!name) return
    merged.set(name, {
      name,
      value: row.value ?? '',
      scope: 'case',
      scopeLabel: VARIABLE_SCOPE_LABELS.case,
    })
  })

  return Array.from(merged.values())
}

/** 接口管理页：注入项目内所有接口的后置处理器，供跨接口 {{ 联想 */
export function provideProjectPostProcessors(getProcessors: () => Schemas['ProcessorRow'][]) {
  const processors = computed(getProcessors)
  provide(PROJECT_PROCESSORS_KEY, processors)
  return processors
}

export function provideEditorVariables(getCtx: () => EditorVariableContext) {
  const resolvable = useResolvableVars()
  const projectProcessors = inject(
    PROJECT_PROCESSORS_KEY,
    computed(() => [] as Schemas['ProcessorRow'][]),
  )
  const variables = computed(() => {
    const ctx = getCtx()
    return mergeEditorVariables(resolvable.value, {
      ...ctx,
      postProcessors: mergeProcessors(projectProcessors.value, ctx.postProcessors),
    })
  })
  provide(KEY, variables)
  return variables
}

export function useEditorVariables(): ComputedRef<EditorVariable[]> {
  const injected = inject(KEY, null)
  const resolvable = useResolvableVars()
  if (injected) return injected
  return computed(() => fromResolvable(resolvable.value))
}
