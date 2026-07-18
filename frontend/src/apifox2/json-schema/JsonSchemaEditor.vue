<template>
  <JsonSchemaNode :value="value" @change="onChange" />
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import JsonSchemaNode from './JsonSchemaNode.vue'
import { defaultFieldData, KEY_ITEMS, KEY_PROPERTIES, SchemaType } from './constants'
import type { ArraySchema, ColumnType, FieldPath, JsonSchema, ObjectSchema } from './types'
import { getAllExpandedKeys, getByPath, setByPath } from './utils'
import { provideJsonSchema } from './context'
import { deepClone } from '@/apifox2/utils'

const props = defineProps<{
  value?: JsonSchema
  defaultExpandAll?: boolean
  readOnly?: boolean
  expandedKeys?: string[]
  extraColumns?: ColumnType[]
}>()
const emit = defineEmits<{ change: [JsonSchema | undefined] }>()

const expandedKeysState = ref<string[] | undefined>()
let hasSetDefaultExpanded = false

onMounted(() => {
  if (!hasSetDefaultExpanded && props.defaultExpandAll && props.value) {
    expandedKeysState.value = getAllExpandedKeys(props.value)
    hasSetDefaultExpanded = true
  }
})

watch(
  () => props.expandedKeys,
  (keys) => {
    if (keys) expandedKeysState.value = keys
  },
)

function onChange(v: JsonSchema | undefined) {
  emit('change', v)
}

function newField(): JsonSchema {
  return { ...defaultFieldData }
}

function handleAddField(targetPath: FieldPath[]) {
  if (!props.value) return
  const draft = deepClone(props.value)
  const path = [...targetPath]

  const shouldAddToProperties = path[path.length - 2] === KEY_PROPERTIES
  const shouldAddToItems = path[path.length - 1] === KEY_ITEMS

  if (shouldAddToProperties) {
    const targetSchema = getByPath(draft, path)
    if (targetSchema) {
      const propertyIdx = Number(path.pop())
      if (propertyIdx >= 0) {
        const properties = getByPath(draft, path)
        if (Array.isArray(properties)) {
          properties.splice(propertyIdx + 1, 0, newField())
        }
      }
    } else {
      setByPath(draft, path, newField())
    }
  } else if (shouldAddToItems) {
    const targetItems = getByPath(draft, path) as ArraySchema['items'] | undefined
    if (targetItems && targetItems.type === SchemaType.Object) {
      const objItems = targetItems as ObjectSchema
      if (objItems.properties) {
        objItems.properties.push(newField())
      } else {
        objItems.properties = [newField()]
      }
    }
  }

  emit('change', draft)
}

function handleRemoveField(targetPath: FieldPath[]) {
  if (!props.value) return
  const draft = deepClone(props.value)
  const path = [...targetPath]

  if (path[path.length - 2] === KEY_PROPERTIES) {
    const propertyIdx = Number(path.pop())
    if (propertyIdx >= 0) {
      const properties = getByPath(draft, path)
      if (Array.isArray(properties)) {
        properties.splice(propertyIdx, 1)
      }
    }
  }

  emit('change', draft)
}

provideJsonSchema({
  readOnly: props.readOnly,
  expandedKeys: expandedKeysState,
  onExpand: (keys) => {
    expandedKeysState.value = keys
  },
  extraColumns: props.extraColumns,
  onAddField: handleAddField,
  onRemoveField: handleRemoveField,
})
</script>
