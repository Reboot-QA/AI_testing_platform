<template>
  <div class="proc-editor">
    <div v-for="(op, i) in rows" :key="i" class="p-row">
      <span class="ord">
        <el-button link size="small" :disabled="i === 0" @click="move(i, -1)">↑</el-button>
        <el-button link size="small" :disabled="i === rows.length - 1" @click="move(i, 1)"
          >↓</el-button
        >
      </span>
      <el-checkbox v-model="op.enabled" />
      <el-tag size="small" :type="tagType(op.kind)">{{ label(op.kind) }}</el-tag>

      <!-- 脚本 -->
      <template v-if="op.kind === 'script'">
        <el-select
          v-model="op.script_id"
          size="small"
          filterable
          placeholder="选择脚本"
          style="flex: 1"
        >
          <el-option v-for="s in scripts" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </template>

      <!-- 等待 -->
      <template v-else-if="op.kind === 'wait'">
        <el-input-number
          v-model="op.wait_ms"
          size="small"
          :min="0"
          :step="100"
          style="width: 130px"
        />
        <span class="unit">毫秒</span>
      </template>

      <!-- 断言 -->
      <template v-else-if="op.kind === 'assertion'">
        <el-select v-model="op.type" size="small" style="width: 110px">
          <el-option v-for="t in ASSERT_TYPES" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-input
          v-model="op.path"
          size="small"
          :disabled="!needsPath(op.type)"
          :placeholder="pathPlaceholder(op.type)"
          style="width: 130px"
        />
        <el-select
          v-if="needsOperator(op.type)"
          v-model="op.operator"
          size="small"
          style="width: 100px"
        >
          <el-option v-for="o in OPERATORS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <VarInput v-model="op.expected" placeholder="期望值" style="flex: 1" />
      </template>

      <!-- 提取 -->
      <template v-else-if="op.kind === 'extract'">
        <el-input v-model="op.var_name" size="small" placeholder="变量名" style="width: 110px" />
        <el-select v-model="op.source" size="small" style="width: 130px">
          <el-option
            v-for="s in EXTRACT_SOURCE_OPTIONS"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>
        <VarInput v-model="op.path" placeholder="路径/表达式" style="width: 140px" />
        <el-select v-model="op.scope" size="small" style="width: 100px">
          <el-option
            v-for="sc in VARIABLE_SCOPE_OPTIONS"
            :key="sc.value"
            :label="sc.label"
            :value="sc.value"
          />
        </el-select>
      </template>

      <!-- 契约 -->
      <template v-else-if="op.kind === 'contract'">
        <el-select
          v-model="op.response_schema_id"
          size="small"
          filterable
          clearable
          placeholder="响应数据模型"
          style="flex: 1"
        >
          <el-option v-for="s in schemas" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-checkbox v-model="op.contract_strict">不符判失败</el-checkbox>
      </template>

      <el-button link type="danger" size="small" @click="rows.splice(i, 1)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>

    <el-empty v-if="rows.length === 0" :image-size="40" description="暂无操作，下方添加" />

    <div class="add-bar">
      <el-select v-model="newKind" size="small" style="width: 120px">
        <el-option v-for="k in kinds" :key="k.value" :label="k.label" :value="k.value" />
      </el-select>
      <el-button size="small" type="primary" @click="add">+ 添加</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Schemas } from '@/api/types'
import { EXTRACT_SOURCE_OPTIONS, VARIABLE_SCOPE_OPTIONS } from '@/utils/apiCaseConfig'
import VarInput from '@/components/apifox/common/VarInput.vue'

type Processor = Schemas['ProcessorRow']

const props = withDefaults(
  defineProps<{
    rows: Processor[]
    phase: 'pre' | 'post'
    scripts?: Schemas['ScriptBrief'][]
    schemas?: { id: number; name: string }[]
    allowContract?: boolean
  }>(),
  { scripts: () => [], schemas: () => [], allowContract: true },
)

const KIND_LABELS: Record<string, string> = {
  script: '脚本',
  wait: '等待',
  assertion: '断言',
  extract: '提取',
  contract: '契约',
}
const label = (k: string) => KIND_LABELS[k] || k
const tagType = (k: string) =>
  ({ script: 'success', wait: 'info', assertion: 'warning', extract: '', contract: 'danger' })[k] ||
  'info'

// 前置只允许 脚本/等待；后置允许 断言/提取/脚本/等待（契约仅接口级：allowContract）
const kinds = computed(() => {
  if (props.phase === 'pre')
    return [
      { value: 'script', label: '脚本' },
      { value: 'wait', label: '等待' },
    ]
  const post = [
    { value: 'assertion', label: '断言' },
    { value: 'extract', label: '提取' },
    { value: 'script', label: '脚本' },
    { value: 'wait', label: '等待' },
  ]
  if (props.allowContract) post.push({ value: 'contract', label: '契约' })
  return post
})
const newKind = ref('script')

const ASSERT_TYPES = [
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
const needsOperator = (t?: string | null) =>
  t === 'status_code' || t === 'json_path' || t === 'header'
const needsPath = (t?: string | null) => t === 'json_path' || t === 'header'
const pathPlaceholder = (t?: string | null) =>
  t === 'json_path' ? '$.code' : t === 'header' ? 'Header 名' : '（无需）'

function emptyOp(kind: string): Processor {
  const base = { kind, enabled: true } as Processor
  if (kind === 'wait') return { ...base, wait_ms: 500 }
  if (kind === 'assertion')
    return { ...base, type: 'status_code', operator: 'eq', expected: '200', path: '' }
  if (kind === 'extract')
    return { ...base, var_name: '', source: 'response_json', path: '$.data', scope: 'environment' }
  if (kind === 'contract') return { ...base, response_schema_id: null, contract_strict: false }
  return { ...base, script_id: null } // script
}

function add() {
  props.rows.push(emptyOp(newKind.value))
}

function move(i: number, delta: number) {
  const j = i + delta
  if (j < 0 || j >= props.rows.length) return
  const [item] = props.rows.splice(i, 1)
  props.rows.splice(j, 0, item)
}
</script>

<style scoped>
.proc-editor {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.p-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ord {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.unit {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.add-bar {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
</style>
