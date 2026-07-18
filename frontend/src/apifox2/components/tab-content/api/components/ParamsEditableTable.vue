<template>
  <table class="a2-etable">
    <colgroup>
      <col width="25%" />
      <col width="90" />
      <col width="25%" />
      <col width="40%" />
      <col width="90" />
    </colgroup>
    <thead>
      <tr>
        <th>参数名</th>
        <th>类型</th>
        <th>示例值</th>
        <th>说明</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(record, ridx) in internalDataSource" :key="`${ridx}_${record.id}`">
        <!-- 参数名 -->
        <td>
          <ParamsEditableCell :validate-error="isValidateError(record, ridx)">
            <div class="a2-name-cell">
              <input
                class="a2-cell-input"
                placeholder="添加参数"
                :readonly="isPathParamsTable"
                :value="record.name ?? ''"
                @blur="onNameBlur(record, ridx)"
                @input="handleChange(ridx, { name: ($event.target as HTMLInputElement).value })"
              />
              <el-tooltip
                v-if="isNameEmpty(record, ridx) || isDuplicate(record, ridx)"
                :content="isNameEmpty(record, ridx) ? '参数名不能为空' : '此列不能重复'"
                placement="top"
              >
                <span class="a2-err-icon"><CircleXIcon :size="14" /></span>
              </el-tooltip>
            </div>
          </ParamsEditableCell>
        </td>

        <!-- 类型 -->
        <td>
          <ParamsEditableCell :class="{ 'a2-newrow-type': testIsNewRow(record) }">
            <el-select
              class="a2-type-select"
              :model-value="record.type ?? ''"
              :style="{ color: record.type ? `var(${paramColor(record.type)})` : '' }"
              @change="onTypeChange(ridx, record, $event)"
            >
              <el-option
                v-for="t in typeOptions"
                :key="t.value"
                :label="t.label"
                :value="t.value"
              />
            </el-select>
          </ParamsEditableCell>
        </td>

        <!-- 示例值 -->
        <td>
          <template v-if="record.type === ParamType.Array">
            <div v-for="(v, vIdx) in exampleArray(record)" :key="vIdx" class="a2-example-row">
              <ParamsEditableCell>
                <input
                  class="a2-cell-input"
                  :value="v"
                  @input="
                    onArrayExampleInput(
                      ridx,
                      record,
                      vIdx,
                      ($event.target as HTMLInputElement).value,
                    )
                  "
                />
              </ParamsEditableCell>
              <span class="a2-example-add" @click="onArrayExampleAdd(ridx, record, vIdx)">
                <PlusCircleIcon :size="15" />
              </span>
              <span
                class="a2-example-del"
                :class="{ invisible: exampleArray(record).length <= 1 }"
                @click="onArrayExampleRemove(ridx, record, vIdx)"
              >
                <XCircleIcon :size="15" />
              </span>
            </div>
          </template>
          <ParamsEditableCell v-else>
            <input
              class="a2-cell-input"
              :value="typeof record.example === 'string' ? record.example : ''"
              @input="handleChange(ridx, { example: ($event.target as HTMLInputElement).value })"
            />
          </ParamsEditableCell>
        </td>

        <!-- 说明 -->
        <td>
          <ParamsEditableCell class="a2-desc-cell">
            <textarea
              class="a2-cell-textarea"
              :value="typeof record.description === 'string' ? record.description : ''"
              @input="
                handleChange(ridx, { description: ($event.target as HTMLTextAreaElement).value })
              "
            />
          </ParamsEditableCell>
        </td>

        <!-- 操作 -->
        <td>
          <div v-if="!testIsNewRow(record) && removable" class="a2-remove-cell">
            <DoubleCheckRemoveBtn @remove="removeRow(ridx)" />
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CircleXIcon, PlusCircleIcon, XCircleIcon } from 'lucide-vue-next'
import ParamsEditableCell from './ParamsEditableCell.vue'
import DoubleCheckRemoveBtn from '@/apifox2/components/DoubleCheckRemoveBtn.vue'
import { nanoid } from '@/apifox2/lib/nanoid'
import { PARAMS_CONFIG } from '@/apifox2/configs/static'
import { ParamType } from '@/apifox2/enums'
import type { Parameter } from '@/apifox2/types'

const props = withDefaults(
  defineProps<{
    value?: Parameter[]
    isPathParamsTable?: boolean
    autoNewRow?: boolean
    removable?: boolean
  }>(),
  { isPathParamsTable: false, removable: true },
)
const emit = defineEmits<{ change: [Parameter[] | undefined] }>()

const newRowRecordId = nanoid(6)

const autoNewRow = computed(() => props.autoNewRow ?? !props.isPathParamsTable)

const typeOptions = computed(() =>
  [
    { label: 'string', value: ParamType.String },
    { label: 'integer', value: ParamType.Integer },
    { label: 'boolean', value: ParamType.Boolean },
    { label: 'number', value: ParamType.Number },
    { label: 'array', value: ParamType.Array, hidden: props.isPathParamsTable },
  ].filter((it) => !it.hidden),
)

const internalDataSource = computed<Parameter[]>(() =>
  autoNewRow.value
    ? [...(props.value ?? []), { id: newRowRecordId, type: ParamType.String } as Parameter]
    : (props.value ?? []),
)

function paramColor(type: ParamType) {
  return PARAMS_CONFIG[type].varColor
}

function testIsNewRow(target: Parameter | undefined) {
  return !target?.id || target.id === newRowRecordId
}

function isNameEmpty(record: Parameter, ridx: number) {
  return !record.name && !testIsNewRow(record) && ridx < (props.value?.length ?? 0)
}

function isDuplicate(record: Parameter, ridx: number) {
  return (
    !testIsNewRow(record) && !!props.value?.some((it, i) => i < ridx && it.name === record.name)
  )
}

function isValidateError(record: Parameter, ridx: number) {
  return isNameEmpty(record, ridx) || isDuplicate(record, ridx)
}

function exampleArray(record: Parameter): string[] {
  const ex = record.example
  return Array.isArray(ex) && ex.length > 0 ? ex : ['']
}

function transformExampleValue(type: ParamType, example: Parameter['example']) {
  return type === ParamType.Array && !Array.isArray(example)
    ? [example ?? '']
    : Array.isArray(example)
      ? example.join(',')
      : example
}

function handleDuplicate(rowIdx: number, v: Partial<Parameter>) {
  emit(
    'change',
    props.value
      ?.filter((_, i) => i !== rowIdx)
      .map((it) => {
        if (it.name === v.name) {
          if (it.type === ParamType.Array) {
            return {
              ...it,
              example:
                typeof v.example === 'string'
                  ? [...((it.example as string[]) ?? []), v.example]
                  : it.example,
            } as Parameter
          }
          return {
            ...it,
            type: ParamType.Array,
            example: [it.example ?? '', typeof v.example === 'string' ? v.example : ''],
          } as Parameter
        }
        return it
      }),
  )
}

function handleChange(rowIdx: number, v: Partial<Record<keyof Parameter, unknown>>) {
  const target = props.value?.[rowIdx]
  const isNewRow = testIsNewRow(target)

  if (isNewRow) {
    const dup = props.value?.some((it, i) => it.name === v.name && i < rowIdx)
    if (dup) {
      handleDuplicate(rowIdx, v as Partial<Parameter>)
    } else {
      emit('change', [
        ...(props.value ?? []),
        { id: newRowRecordId, ...target, ...v, type: ParamType.String } as Parameter,
      ])
    }
  } else {
    emit(
      'change',
      props.value?.map((it, i) => (i === rowIdx ? ({ ...it, ...v } as Parameter) : it)),
    )
  }
}

function onNameBlur(record: Parameter, ridx: number) {
  if (isDuplicate(record, ridx)) {
    handleDuplicate(ridx, { name: record.name })
  }
}

function onTypeChange(ridx: number, record: Parameter, paramType: ParamType) {
  handleChange(ridx, {
    type: paramType,
    example: transformExampleValue(paramType, record.example),
  })
}

function onArrayExampleInput(ridx: number, record: Parameter, vIdx: number, val: string) {
  const arr = [...exampleArray(record)]
  arr.splice(vIdx, 1, val)
  handleChange(ridx, { example: arr })
}

function onArrayExampleAdd(ridx: number, record: Parameter, vIdx: number) {
  const arr = [...exampleArray(record)]
  arr.splice(vIdx + 1, 0, '')
  handleChange(ridx, { example: arr })
}

function onArrayExampleRemove(ridx: number, record: Parameter, vIdx: number) {
  const arr = exampleArray(record)
  if (arr.length > 1) {
    handleChange(ridx, { example: arr.filter((_, i) => i !== vIdx) })
  }
}

function removeRow(idx: number) {
  emit(
    'change',
    props.value?.filter((_, i) => i !== idx),
  )
}
</script>

<style scoped>
.a2-etable {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 6px;
}

.a2-etable th {
  padding: 4px;
  text-align: left;
  font-weight: normal;
  color: var(--a2-color-text-tertiary);
  border-bottom: 1px solid var(--a2-color-border-secondary);
}

.a2-etable td {
  color: var(--a2-color-text-secondary);
  border-bottom: 1px solid var(--a2-color-border-secondary);
  overflow: hidden;
  vertical-align: top;
}

.a2-etable tbody tr:last-child td {
  border-bottom: none;
}

.a2-cell-input {
  width: 100%;
  min-height: 32px;
  padding: 0 5px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: inherit;
}

.a2-cell-textarea {
  width: 100%;
  height: 32px;
  min-height: 32px;
  padding: 5px;
  border: none;
  outline: none;
  background: transparent;
  resize: none;
  font-size: 13px;
  color: inherit;
  font-family: inherit;
  overflow-y: hidden;
}

.a2-name-cell {
  display: flex;
  width: 100%;
  align-items: center;
}

.a2-err-icon {
  padding-right: 4px;
  color: var(--color-red-6, #f5222d);
  display: inline-flex;
}

.a2-type-select {
  width: 100%;
}

.a2-type-select :deep(.el-select__wrapper) {
  box-shadow: none;
  background: transparent;
  min-height: 32px;
  padding: 0 5px;
}

.a2-newrow-type {
  opacity: 0;
}

.a2-newrow-type:hover {
  opacity: 1;
}

.a2-example-row {
  display: flex;
  align-items: center;
  color: var(--a2-color-text-tertiary);
}

.a2-example-row:hover {
  color: var(--a2-color-primary);
}

.a2-example-add,
.a2-example-del {
  display: flex;
  align-items: center;
  padding: 0 8px;
  cursor: pointer;
}

.a2-example-del.invisible {
  visibility: hidden;
}

.a2-remove-cell {
  display: flex;
  justify-content: center;
  padding: 4px;
  font-size: 12px;
}
</style>
