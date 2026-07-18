<template>
  <template v-if="!value" />

  <!-- Object -->
  <template v-else-if="value.type === SchemaType.Object">
    <JsonSchemaNodeRow
      v-if="!fromRef"
      :value="value"
      :field-path="fieldPath"
      :from-ref="fromRef"
      :disabled="disabled"
      @change="emitChange"
    />

    <JsonSchemaNodeWrapper v-if="hasProps" :should-expand="!!fromRef || shouldExpand">
      <JsonSchemaNode
        v-for="(propSchema, i) in value.properties"
        :key="`${propSchema.type}_${i}_${pathKey}`"
        :value="propSchema"
        :field-path="[...fieldPath, KEY_PROPERTIES, String(i)]"
        :disabled="disabled"
        :from-ref="fromRef"
        @change="(v) => onPropChange(i, v)"
      />
    </JsonSchemaNodeWrapper>
    <div v-else-if="shouldExpand" class="a2-js-empty" :style="{ paddingLeft: `${emptyIndent}px` }">
      <span class="a2-js-empty-text">
        没有字段，<span
          class="a2-js-empty-add"
          @click="onAddField([...fieldPath, KEY_PROPERTIES, '0'])"
          >添加</span
        >
      </span>
    </div>
  </template>

  <!-- Array -->
  <template v-else-if="value.type === SchemaType.Array">
    <JsonSchemaNodeRow
      :value="value"
      :field-path="fieldPath"
      :from-ref="fromRef"
      :disabled="disabled"
      @change="emitChange"
    />
    <JsonSchemaNodeWrapper :should-expand="shouldExpand">
      <JsonSchemaNode
        :value="value.items"
        :field-path="[...fieldPath, KEY_ITEMS]"
        :disabled="disabled"
        :from-ref="fromRef"
        @change="onItemsChange"
      />
    </JsonSchemaNodeWrapper>
  </template>

  <!-- Refer -->
  <template v-else-if="value.type === SchemaType.Refer">
    <JsonSchemaNodeRow
      :value="value"
      :field-path="fieldPath"
      :from-ref="fromRef"
      :disabled="disabled"
      @change="emitChange"
    />
    <JsonSchemaNodeWrapper
      v-if="value.$ref !== fromRef"
      class="a2-js-ref-wrap"
      :should-expand="shouldExpand"
    >
      <div class="a2-js-ref">
        <div class="a2-js-unbind" @click="unbindRef">解除关联</div>
        <JsonSchemaNode
          v-if="refJsonSchema"
          disabled
          :value="refJsonSchema"
          :field-path="[value.$ref, ...fieldPath]"
          :from-ref="value.$ref"
        />
      </div>
    </JsonSchemaNodeWrapper>
  </template>

  <!-- 基础类型 -->
  <template v-else>
    <JsonSchemaNodeRow
      :value="value"
      :field-path="fieldPath"
      :from-ref="fromRef"
      :disabled="disabled"
      @change="emitChange"
    />
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import JsonSchemaNodeRow from './JsonSchemaNodeRow.vue'
import JsonSchemaNodeWrapper from './JsonSchemaNodeWrapper.vue'
import { INDENT, KEY_ITEMS, KEY_PROPERTIES, SchemaType, SEPARATOR } from './constants'
import type { ArraySchema, FieldPath, JsonSchema, ObjectSchema } from './types'
import { getNodeLevelInfo, getRefJsonSchema } from './utils'
import { useJsonSchemaContext } from './context'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const props = defineProps<{
  value?: JsonSchema
  fieldPath?: FieldPath[]
  fromRef?: string
  disabled?: boolean
}>()
const emit = defineEmits<{ change: [JsonSchema | undefined] }>()

const { expandedKeys, onAddField } = useJsonSchemaContext()
const menuStore = useApifox2MenuStore()

const fieldPath = computed(() => props.fieldPath ?? [])
const pathKey = computed(() => fieldPath.value.join(SEPARATOR))
const shouldExpand = computed(() => !!expandedKeys.value?.includes(pathKey.value))

const hasProps = computed(() => {
  const v = props.value
  return v?.type === SchemaType.Object && Array.isArray(v.properties) && v.properties.length > 0
})

const emptyIndent = computed(
  () => getNodeLevelInfo([...fieldPath.value, KEY_PROPERTIES, '0']).indentWidth + INDENT,
)

const refJsonSchema = computed(() => {
  const v = props.value
  if (v?.type === SchemaType.Refer && menuStore.menuRawList) {
    return getRefJsonSchema(menuStore.menuRawList, v.$ref)
  }
  return undefined
})

function emitChange(v: JsonSchema | undefined) {
  emit('change', v)
}

function onPropChange(i: number, changed: JsonSchema | undefined) {
  const v = props.value as ObjectSchema
  if (!v.properties) return
  const newProperties = v.properties.map((prop, idx) => (idx === i && changed ? changed : prop))
  emit('change', { ...v, properties: newProperties })
}

function onItemsChange(changed: JsonSchema | undefined) {
  const v = props.value as ArraySchema
  if (changed) {
    emit('change', { ...v, items: changed as ArraySchema['items'] })
  }
}

function unbindRef() {
  const v = props.value
  if (v?.type === SchemaType.Refer && refJsonSchema.value) {
    // 解除引用：去掉 $ref，合并被引用模型的结构。
    const restValue = { ...v } as Record<string, unknown>
    delete restValue.$ref
    emit('change', { ...restValue, ...refJsonSchema.value } as JsonSchema)
  }
}
</script>

<style scoped>
.a2-js-empty {
  height: 32px;
  display: flex;
  align-items: center;
}

.a2-js-empty-text {
  color: var(--a2-color-text-tertiary);
}

.a2-js-empty-add {
  color: var(--a2-color-primary);
  cursor: pointer;
}

.a2-js-ref {
  position: relative;
}

.a2-js-ref-wrap:hover .a2-js-ref {
  outline: 1px solid var(--a2-color-primary);
  border-radius: 4px;
}

.a2-js-unbind {
  display: none;
  position: absolute;
  top: 0;
  left: 50%;
  transform: translate(-50%, -100%);
  background-color: var(--a2-color-primary);
  color: #fff;
  padding: 2px 15px;
  border-top-left-radius: 5px;
  border-top-right-radius: 5px;
  cursor: pointer;
}

.a2-js-ref-wrap:hover .a2-js-unbind {
  display: flex;
}
</style>
