<template>
  <div class="sf-row" :style="{ paddingLeft: depth * 18 + 'px' }">
    <el-input
      v-if="!isItem"
      v-model="field.name"
      size="small"
      placeholder="字段名"
      class="f-name"
    />
    <span v-else class="f-item">数组元素</span>

    <el-select v-model="field.type" size="small" class="f-type" @change="onTypeChange">
      <el-option
        v-for="t in FIELD_TYPES"
        :key="t"
        :label="t === 'ref' ? '引用模型' : t"
        :value="t"
      />
    </el-select>

    <el-select
      v-if="field.type === 'ref'"
      v-model="field.refName"
      size="small"
      filterable
      placeholder="选择模型"
      class="f-ref"
    >
      <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.name" />
    </el-select>

    <el-checkbox v-if="!isItem" v-model="field.required" size="small" class="f-req">必填</el-checkbox>

    <el-input v-model="field.description" size="small" placeholder="说明" class="f-desc" />

    <el-popover v-if="showConstraints" trigger="click" :width="300" placement="bottom-end">
      <template #reference>
        <el-button link size="small" :type="hasConstraints ? 'primary' : ''" title="高级约束（枚举/正则/范围/示例等）">
          约束<span v-if="hasConstraints" class="c-dot">●</span>
        </el-button>
      </template>
      <SchemaConstraintsEditor :field="field" />
    </el-popover>

    <el-button v-if="field.type === 'object'" link size="small" @click="addChild">+ 字段</el-button>
    <el-button v-if="!isItem" link type="danger" size="small" @click="remove">删</el-button>
  </div>

  <template v-if="field.type === 'object'">
    <SchemaFieldRow
      v-for="(child, i) in field.children"
      :key="child.uid"
      :field="child"
      :list="field.children"
      :index="i"
      :depth="depth + 1"
      :models="models"
    />
  </template>
  <SchemaFieldRow
    v-else-if="field.type === 'array' && field.children[0]"
    :field="field.children[0]"
    :depth="depth + 1"
    :models="models"
    is-item
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SchemaField } from '@/types/apifox'
import { FIELD_TYPES, newField } from '@/composables/useJsonSchema'
import type { Schemas } from '@/api/types'
import SchemaConstraintsEditor from '@/components/apifox/SchemaConstraintsEditor.vue'

type SchemaBrief = Schemas['SchemaBrief']

const props = withDefaults(
  defineProps<{
    field: SchemaField
    list?: SchemaField[] | null
    index?: number
    depth?: number
    isItem?: boolean
    models?: SchemaBrief[]
  }>(),
  {
    list: null,
    index: -1,
    depth: 0,
    isItem: false,
    models: () => [],
  },
)

const CONSTRAINABLE = ['string', 'integer', 'number', 'array']
const showConstraints = computed(() => CONSTRAINABLE.includes(props.field.type))
const hasConstraints = computed(() => Object.keys(props.field.extra || {}).length > 0)

function onTypeChange(type: string) {
  if (type === 'array') props.field.children = [newField('string')]
  else props.field.children = []
  if (type !== 'ref') props.field.refName = ''
  props.field.extra = {} // 换类型清空旧类型的约束，避免残留非法约束（如 integer 上残留 minLength）
}

function addChild() {
  props.field.children.push(newField('string'))
}

function remove() {
  if (props.list && props.index >= 0) props.list.splice(props.index, 1)
}
</script>

<style scoped>
.sf-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
}

.f-name {
  width: 180px;
}

.f-type {
  width: 110px;
}

.f-ref {
  width: 150px;
}

.f-req {
  flex-shrink: 0;
}

.f-desc {
  flex: 1;
  min-width: 120px;
}

.f-item {
  width: 180px;
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.c-dot {
  font-size: 9px;
  vertical-align: super;
}
</style>
