<template>
  <div v-if="value" class="a2-jsrow">
    <!-- 名称列 -->
    <div class="a2-jscol a2-jsname">
      <span :style="{ width: `${indentWidth + (fromRef ? INDENT : 0)}px` }" />

      <span
        v-if="showExpandIcon"
        class="a2-expand-icon"
        :class="{ expanded: shouldExpand }"
        :style="{ width: `${INDENT}px` }"
        @click="toggleExpand"
      >
        <ChevronRightIcon :size="12" />
      </span>
      <span v-else :style="{ width: `${INDENT}px` }" />

      <span class="a2-jsname-inner a2-jscol-inner" :class="{ hover: !isRoot && !isItems }">
        <span v-if="isRoot || isItems" class="a2-jstag">{{ isItems ? 'ITEMS' : '根节点' }}</span>
        <span v-else class="a2-jsname-content">
          <template v-if="readOnly">{{ value.name }}</template>
          <input
            v-else
            class="a2-jsinput"
            placeholder="字段名"
            :disabled="disabled"
            :value="value.name"
            @input="patch({ name: ($event.target as HTMLInputElement).value })"
          />
        </span>
      </span>
    </div>

    <!-- 类型列 -->
    <div class="a2-jscol a2-jstype a2-jscol-inner hover">
      <DataTypeSelect
        :type="value.type"
        :disabled="disabled"
        :read-only="readOnly"
        :ref-id="value.type === SchemaType.Refer ? value.$ref : undefined"
        @type-select="onTypeSelect"
      />
    </div>

    <!-- 中文名列 -->
    <div class="a2-jscol a2-jstitle a2-jscol-inner hover">
      <input
        class="a2-jsinput"
        placeholder="中文名"
        :disabled="disabled"
        :value="value.displayName"
        @input="patch({ displayName: ($event.target as HTMLInputElement).value })"
      />
    </div>

    <!-- 说明列 -->
    <div class="a2-jscol a2-jsdesc a2-jscol-inner hover">
      <input
        class="a2-jsinput"
        placeholder="说明"
        :disabled="disabled"
        :value="value.description"
        @input="patch({ description: ($event.target as HTMLInputElement).value })"
      />
    </div>

    <!-- 操作列 -->
    <div class="a2-jscol a2-jsactions">
      <el-tooltip
        v-if="canAddField"
        :content="isRoot ? '添加子节点' : '添加相邻节点'"
        placement="top"
      >
        <span class="a2-jsaction a2-jsaction-add" @click="onAdd">
          <CirclePlusIcon :size="13" />
        </span>
      </el-tooltip>

      <DoubleCheckRemoveBtn v-if="removable" class="a2-jsaction" @remove="onRemove" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronRightIcon, CirclePlusIcon } from 'lucide-vue-next'
import DataTypeSelect from '@/apifox2/components/DataTypeSelect.vue'
import DoubleCheckRemoveBtn from '@/apifox2/components/DoubleCheckRemoveBtn.vue'
import { INDENT, KEY_ITEMS, KEY_PROPERTIES, SchemaType, SEPARATOR } from './constants'
import type { ArraySchema, FieldPath, JsonSchema } from './types'
import { getNodeLevelInfo } from './utils'
import { useJsonSchemaContext } from './context'

const props = defineProps<{
  value?: JsonSchema
  fieldPath?: FieldPath[]
  fromRef?: string
  disabled?: boolean
}>()
const emit = defineEmits<{ change: [JsonSchema | undefined] }>()

const { readOnly, expandedKeys, onExpand, onAddField, onRemoveField } = useJsonSchemaContext()

const fieldPath = computed(() => props.fieldPath ?? [])
const indentWidth = computed(() => getNodeLevelInfo(fieldPath.value).indentWidth)
const isRoot = computed(() => fieldPath.value.length === 0)
const isItems = computed(() => fieldPath.value[fieldPath.value.length - 1] === KEY_ITEMS)
const pathString = computed(() => fieldPath.value.join(SEPARATOR))

const showExpandIcon = computed(
  () =>
    props.value?.type === SchemaType.Object ||
    props.value?.type === SchemaType.Array ||
    props.value?.type === SchemaType.Refer,
)
const shouldExpand = computed(() => expandedKeys.value?.includes(pathString.value) ?? false)
const canAddField = computed(() =>
  isRoot.value ? props.value?.type === SchemaType.Object : !isItems.value,
)
const removable = computed(() => !isRoot.value && !isItems.value)

function patch(partial: Partial<JsonSchema>) {
  if (props.value) emit('change', { ...props.value, ...partial } as JsonSchema)
}

function toggleExpand() {
  const cur = expandedKeys.value ?? []
  const newKeys = shouldExpand.value
    ? cur.filter((k) => k !== pathString.value)
    : [...cur, pathString.value]
  onExpand(newKeys)
}

function onAdd() {
  if (isRoot.value) {
    onAddField([...fieldPath.value, KEY_PROPERTIES, '0'])
  } else {
    onAddField(fieldPath.value)
  }
}

function onRemove() {
  onRemoveField(fieldPath.value)
}

function onTypeSelect(newType: SchemaType) {
  if (!props.value) return
  const oldType = props.value.type
  if (oldType === newType) return

  let newValue = { ...props.value, type: newType } as JsonSchema

  if (oldType === SchemaType.Object) {
    if (newType !== SchemaType.Object) {
      const clone = { ...newValue } as Record<string, unknown>
      delete clone[KEY_PROPERTIES]
      emit('change', clone as unknown as JsonSchema)
    }
  } else if (oldType === SchemaType.Array) {
    if (newType !== SchemaType.Array) {
      const clone = { ...newValue } as Record<string, unknown>
      delete clone[KEY_ITEMS]
      emit('change', clone as unknown as JsonSchema)
    }
  } else {
    if (newType === SchemaType.Array) {
      newValue = { ...newValue, items: { type: SchemaType.String } } as ArraySchema
      onExpand(expandedKeys.value ? [...expandedKeys.value, pathString.value] : [pathString.value])
    }
    emit('change', newValue)
  }
}
</script>

<style scoped>
.a2-jsrow {
  display: flex;
}

.a2-jsrow:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-jsrow:hover :deep(.a2-dts-adv) {
  display: inline-flex;
}

.a2-jscol {
  height: 32px;
  display: flex;
  align-items: center;
  margin: 0 3px;
  font-size: 13px;
  border-bottom: 1px solid var(--a2-color-fill-tertiary);
  transition: border-color 0.2s;
}

.a2-jscol-inner.hover:hover,
.a2-jscol-inner.hover:focus-within {
  border-color: var(--a2-color-primary);
}

.a2-jsinput {
  height: 100%;
  width: 100%;
  padding: 0;
  border: none;
  outline: none;
  font-size: inherit;
  background-color: transparent;
}

.a2-jsinput:disabled {
  color: currentColor;
}

.a2-expand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0.3;
  cursor: pointer;
  font-size: 12px;
  transform: scale(0.75);
}

.a2-expand-icon:hover {
  opacity: 0.8;
}

.a2-expand-icon.expanded {
  transform: scale(0.75) rotate(0.25turn);
}

.a2-jsname {
  flex: 1 1 263px;
  position: relative;
}

.a2-jsname-inner {
  height: 100%;
  flex: 1;
  display: flex;
  align-items: center;
}

.a2-jsname-content {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
}

.a2-jstag {
  padding: 0 5px;
  font-size: 12px;
  border-radius: 3px;
  cursor: default;
  user-select: none;
  color: var(--a2-color-primary);
  background-color: rgba(255, 77, 79, 0.1);
}

.a2-jstype {
  flex: 0 1 182px;
  width: 182px;
}

.a2-jstitle {
  flex: 1 0 36px;
  max-width: 108px;
}

.a2-jsdesc {
  flex: 1 0 54px;
  padding-left: 4px;
}

.a2-jsactions {
  flex: 0 0 48px;
}

.a2-jsaction {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  cursor: pointer;
  user-select: none;
  padding: 2px 5px;
  border-radius: 4px;
}

.a2-jsaction:hover {
  background-color: var(--a2-color-fill-alter);
}

.a2-jsaction-add {
  color: var(--color-green-6, #4caf50);
}
</style>
