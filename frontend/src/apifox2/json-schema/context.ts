import { inject, provide, type InjectionKey, type Ref } from 'vue'

import type { ColumnType, FieldPath } from './types'

export interface JsonSchemaContextData {
  readOnly?: boolean
  expandedKeys: Ref<string[] | undefined>
  onExpand: (keys: string[] | undefined) => void
  extraColumns?: ColumnType[]
  onAddField: (fieldPath: FieldPath[]) => void
  onRemoveField: (fieldPath: FieldPath[]) => void
}

const KEY: InjectionKey<JsonSchemaContextData> = Symbol('apifox2-json-schema')

export function provideJsonSchema(data: JsonSchemaContextData) {
  provide(KEY, data)
}

export function useJsonSchemaContext(): JsonSchemaContextData {
  const ctx = inject(KEY)
  if (!ctx) {
    throw new Error('useJsonSchemaContext 必须在 provideJsonSchema 之下使用')
  }
  return ctx
}
