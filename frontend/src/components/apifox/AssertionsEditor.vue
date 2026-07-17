<template>
  <div>
    <div v-for="(row, i) in rows" :key="i" class="a-row">
      <el-checkbox v-model="row.enabled" />
      <el-select v-model="row.type" size="small" style="width: 120px">
        <el-option v-for="t in TYPES" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-input
        v-model="row.path"
        size="small"
        :disabled="!needsPath(row.type)"
        :placeholder="pathPlaceholder(row.type)"
        style="width: 150px"
      />
      <el-select
        v-if="needsOperator(row.type)"
        v-model="row.operator"
        size="small"
        style="width: 110px"
      >
        <el-option v-for="o in OPERATORS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <span v-else class="op-na">{{ impliedOp(row.type) }}</span>
      <el-input
        v-model="row.expected"
        size="small"
        :disabled="row.operator === 'exists' && needsOperator(row.type)"
        placeholder="期望值"
      />
      <el-button link type="danger" size="small" @click="rows.splice(i, 1)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <el-button link type="primary" size="small" @click="rows.push(emptyRow())">+ 添加断言</el-button>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@/api/types'

type AssertionRow = Schemas['AssertionRow']

defineProps<{ rows: AssertionRow[] }>()

const TYPES = [
  { value: 'status_code', label: '状态码' },
  { value: 'json_path', label: 'JSON 字段' },
  { value: 'header', label: '响应头' },
  { value: 'contains', label: '包含文本' },
  { value: 'response_time', label: '响应时间(ms)' },
]

const OPERATORS = [
  { value: 'eq', label: '等于' },
  { value: 'neq', label: '不等于' },
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'gt', label: '大于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lt', label: '小于' },
  { value: 'lte', label: '小于等于' },
  { value: 'regex', label: '正则' },
  { value: 'exists', label: '存在' },
]

// 仅这三类走操作符比较；contains/response_time 操作符隐含
function needsOperator(type: string) {
  return type === 'status_code' || type === 'json_path' || type === 'header'
}

function impliedOp(type: string) {
  return type === 'response_time' ? '≤' : '包含'
}

function needsPath(type: string) {
  return type === 'json_path' || type === 'header'
}

function pathPlaceholder(type: string) {
  if (type === 'json_path') return '$.code'
  if (type === 'header') return 'Header 名'
  return '（无需）'
}

function emptyRow(): AssertionRow {
  return { type: 'status_code', path: '', operator: 'eq', expected: '200', enabled: true }
}
</script>

<style scoped>
.a-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.op-na {
  width: 110px;
  font-size: 12px;
  color: var(--ax-text-placeholder);
  text-align: center;
}
</style>
