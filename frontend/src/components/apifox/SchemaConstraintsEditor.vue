<template>
  <div class="sc-editor">
    <template v-if="field.type === 'string'">
      <div class="sc-row">
        <span class="sc-label">长度</span>
        <el-input v-model="field.extra.minLength" size="small" placeholder="最小" class="sc-num" />
        <span class="sc-sep">~</span>
        <el-input v-model="field.extra.maxLength" size="small" placeholder="最大" class="sc-num" />
      </div>
      <div class="sc-row">
        <span class="sc-label">正则</span>
        <el-input v-model="field.extra.pattern" size="small" placeholder="pattern" />
      </div>
      <div class="sc-row">
        <span class="sc-label">格式</span>
        <el-select v-model="field.extra.format" size="small" clearable filterable allow-create placeholder="format" class="sc-fmt">
          <el-option v-for="f in FORMATS" :key="f" :label="f" :value="f" />
        </el-select>
      </div>
    </template>

    <template v-else-if="field.type === 'integer' || field.type === 'number'">
      <div class="sc-row">
        <span class="sc-label">范围</span>
        <el-input v-model="field.extra.minimum" size="small" placeholder="最小" class="sc-num" />
        <span class="sc-sep">~</span>
        <el-input v-model="field.extra.maximum" size="small" placeholder="最大" class="sc-num" />
      </div>
    </template>

    <template v-else-if="field.type === 'array'">
      <div class="sc-row">
        <span class="sc-label">元素数</span>
        <el-input v-model="field.extra.minItems" size="small" placeholder="最小" class="sc-num" />
        <span class="sc-sep">~</span>
        <el-input v-model="field.extra.maxItems" size="small" placeholder="最大" class="sc-num" />
      </div>
      <div class="sc-row">
        <el-checkbox v-model="uniqueItems" size="small">元素唯一(uniqueItems)</el-checkbox>
      </div>
    </template>

    <!-- 枚举：字符串/数值可选值，一行一个 -->
    <div v-if="field.type === 'string' || field.type === 'integer' || field.type === 'number'" class="sc-row sc-top">
      <span class="sc-label">枚举</span>
      <el-input
        v-model="enumText"
        type="textarea"
        :rows="2"
        size="small"
        placeholder="可选值，一行一个"
      />
    </div>

    <div class="sc-row">
      <span class="sc-label">默认值</span>
      <el-input v-model="defaultVal" size="small" placeholder="default" />
    </div>
    <div class="sc-row">
      <span class="sc-label">示例</span>
      <el-input v-model="exampleVal" size="small" placeholder="example" />
    </div>
    <div class="sc-row">
      <el-checkbox v-model="nullable" size="small">可为 null(nullable)</el-checkbox>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SchemaField } from '@/types/apifox'

const props = defineProps<{ field: SchemaField }>()

const FORMATS = ['date-time', 'date', 'time', 'email', 'uri', 'uuid', 'hostname', 'ipv4', 'ipv6', 'byte', 'binary']

function boolFlag(key: string) {
  return computed({
    get: () => !!props.field.extra[key],
    set: (v) => {
      if (v) props.field.extra[key] = true
      else delete props.field.extra[key]
    },
  })
}

const nullable = boolFlag('nullable')
const uniqueItems = boolFlag('uniqueItems')

// 按字段类型把文本值转回正确 JSON 类型（integer/number→数字、boolean→布尔、其余→字符串）
function coerce(s: string) {
  const t = props.field.type
  if (t === 'integer' || t === 'number') {
    const n = Number(s)
    return Number.isNaN(n) ? s : n
  }
  if (t === 'boolean') return s === 'true' ? true : s === 'false' ? false : s
  return s
}

// default/example：文本输入但按类型回写，避免 integer 的 5 被存成 "5"
function typedField(key: string) {
  return computed({
    get: () => {
      const v = props.field.extra[key]
      return v === undefined || v === null ? '' : String(v)
    },
    set: (raw) => {
      const s = String(raw)
      if (s === '') delete props.field.extra[key]
      else props.field.extra[key] = coerce(s)
    },
  })
}

const defaultVal = typedField('default')
const exampleVal = typedField('example')

const enumText = computed({
  get: () => {
    const e = props.field.extra.enum
    return Array.isArray(e) ? e.join('\n') : e || ''
  },
  set: (v) => {
    const arr = String(v).split('\n').map((s) => s.trim()).filter(Boolean).map(coerce)
    if (arr.length) props.field.extra.enum = arr
    else delete props.field.extra.enum
  },
})
</script>

<style scoped>
.sc-editor {
  width: 280px;
}

.sc-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.sc-top {
  align-items: flex-start;
}

.sc-label {
  width: 48px;
  flex-shrink: 0;
  font-size: 12px;
  color: var(--ax-text-secondary);
}

.sc-num {
  width: 72px;
}

.sc-fmt {
  flex: 1;
}

.sc-sep {
  color: var(--ax-text-placeholder);
}
</style>
