<template>
  <div class="proc-editor">
    <VueDraggable
      v-model="rows"
      handle=".proc-drag"
      :animation="150"
      ghost-class="ax-drag-ghost"
      class="proc-list"
    >
      <div v-for="(op, i) in rows" :key="i" class="proc-item">
        <div
          class="proc-head"
          :class="{ 'proc-head--off': op.enabled === false, 'proc-head--open': isExpanded(op) }"
        >
          <el-icon class="proc-drag" title="拖拽排序"><Rank /></el-icon>
          <button
            type="button"
            class="proc-status"
            :title="op.enabled !== false ? '已启用，点击禁用' : '已禁用，点击启用'"
            @click.stop="toggleEnabled(op)"
          >
            <el-icon :class="op.enabled !== false ? 'proc-status--on' : 'proc-status--off'">
              <CircleCheck v-if="op.enabled !== false" />
              <CircleClose v-else />
            </el-icon>
          </button>
          <button type="button" class="proc-summary" @click="toggleExpand(op)">
            {{ rowSummary(op) }}
          </button>
          <el-dropdown trigger="click" @command="(cmd: string) => onRowMenu(cmd, i)">
            <button type="button" class="proc-more" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="copy">复制</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <button type="button" class="proc-chevron" @click.stop="toggleExpand(op)">
            <el-icon :class="{ 'proc-chevron--open': isExpanded(op) }"><ArrowRight /></el-icon>
          </button>
        </div>

        <div v-show="isExpanded(op)" class="proc-body">
          <template v-if="op.kind === 'script'">
            <el-select
              v-model="op.script_id"
              size="small"
              filterable
              placeholder="选择脚本"
              style="width: 100%"
            >
              <el-option v-for="s in scripts" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </template>

          <template v-else-if="op.kind === 'script_inline'">
            <div class="proc-body-row">
              <span class="proc-lbl">语言</span>
              <el-select v-model="op.script_lang" size="small" style="width: 120px">
                <el-option label="JavaScript" value="javascript" />
                <el-option label="Python" value="python" />
              </el-select>
            </div>
            <ScriptInlineEditor
              v-model="op.content"
              :lang="op.script_lang || 'javascript'"
              :phase="phase"
            />
          </template>

          <template v-else-if="op.kind === 'database' || op.kind === 'database_script'">
            <DbOperationEditor :op="op" :databases="databases" :sql-scripts="sqlScripts" />
          </template>

          <template v-else-if="op.kind === 'wait'">
            <div class="proc-body-row">
              <span class="proc-lbl">等待</span>
              <el-input-number v-model="op.wait_ms" size="small" :min="0" :step="100" />
              <span class="unit">毫秒</span>
            </div>
          </template>

          <template v-else-if="op.kind === 'assertion'">
            <div class="proc-body-stack">
              <div class="proc-body-row">
                <span class="proc-lbl">类型</span>
                <el-select v-model="op.type" size="small" style="width: 140px">
                  <el-option
                    v-for="t in ASSERT_TYPES"
                    :key="t.value"
                    :label="t.label"
                    :value="t.value"
                  />
                </el-select>
                <el-input
                  v-model="op.path"
                  :maxlength="VALUE_MAX_LEN"
                  size="small"
                  :disabled="!needsPath(op.type)"
                  :placeholder="pathPlaceholder(op.type)"
                  style="flex: 1"
                />
              </div>
              <div class="proc-body-row">
                <span class="proc-lbl">条件</span>
                <el-select
                  v-if="needsOperator(op.type)"
                  v-model="op.operator"
                  size="small"
                  style="width: 120px"
                >
                  <el-option
                    v-for="o in OPERATORS"
                    :key="o.value"
                    :label="o.label"
                    :value="o.value"
                  />
                </el-select>
                <VarInput v-model="op.expected" size="small" placeholder="期望值" style="flex: 1" />
              </div>
            </div>
          </template>

          <template v-else-if="op.kind === 'extract'">
            <div class="proc-body-stack">
              <div class="proc-body-row">
                <span class="proc-lbl">变量</span>
                <el-input
                  v-model="op.var_name"
                  :maxlength="KEY_MAX_LEN"
                  size="small"
                  placeholder="变量名"
                  style="width: 120px"
                />
                <el-select v-model="op.scope" size="small" style="width: 100px">
                  <el-option
                    v-for="sc in VARIABLE_SCOPE_OPTIONS"
                    :key="sc.value"
                    :label="sc.label"
                    :value="sc.value"
                  />
                </el-select>
              </div>
              <div class="proc-body-row">
                <span class="proc-lbl">来源</span>
                <el-select v-model="op.source" size="small" style="width: 140px">
                  <el-option
                    v-for="s in EXTRACT_SOURCE_OPTIONS"
                    :key="s.value"
                    :label="s.label"
                    :value="s.value"
                  />
                </el-select>
                <VarInput
                  v-model="op.path"
                  size="small"
                  placeholder="路径/表达式"
                  style="flex: 1"
                />
              </div>
            </div>
          </template>

          <template v-else-if="op.kind === 'contract'">
            <div class="proc-body-row">
              <span class="proc-lbl">模型</span>
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
            </div>
          </template>
        </div>
      </div>
    </VueDraggable>

    <el-empty v-if="rows.length === 0" :image-size="40" description="暂无操作，下方添加" />

    <el-dropdown trigger="click" class="proc-add" @command="addKind">
      <button type="button" class="proc-add-btn">
        {{ addLabel }}
        <el-icon><ArrowDown /></el-icon>
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item v-for="k in kinds" :key="k.value" :command="k.value">
            {{ k.label }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { KEY_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { computed, ref } from 'vue'
import {
  ArrowDown,
  ArrowRight,
  CircleCheck,
  CircleClose,
  MoreFilled,
  Rank,
} from '@element-plus/icons-vue'
import { VueDraggable } from 'vue-draggable-plus'
import type { Schemas } from '@/api/types'
import { EXTRACT_SOURCE_OPTIONS, VARIABLE_SCOPE_OPTIONS } from '@/utils/apiCaseConfig'
import VarInput from '@/components/apifox/common/VarInput.vue'
import ScriptInlineEditor from '@/components/apifox/script/ScriptInlineEditor.vue'
import DbOperationEditor from '@/components/apifox/editors/DbOperationEditor.vue'

type Processor = Schemas['ProcessorRow']

const props = withDefaults(
  defineProps<{
    phase: 'pre' | 'post'
    scripts?: Schemas['ScriptBrief'][]
    databases?: Schemas['DatabaseOut'][]
    sqlScripts?: Schemas['SqlScriptBrief'][]
    schemas?: { id: number; name: string }[]
    allowContract?: boolean
  }>(),
  {
    scripts: () => [],
    databases: () => [],
    sqlScripts: () => [],
    schemas: () => [],
    allowContract: true,
  },
)
const rows = defineModel<Processor[]>('rows', { required: true })

const addLabel = computed(() => (props.phase === 'pre' ? '添加前置操作' : '添加后置操作'))

const KIND_LABELS: Record<string, string> = {
  script: '脚本库',
  script_inline: '脚本',
  database: '数据库操作',
  database_script: '数据库脚本',
  wait: '等待',
  assertion: '断言',
  extract: '提取',
  contract: '契约',
}

const kinds = computed(() => {
  if (props.phase === 'pre')
    return [
      { value: 'script', label: '脚本库' },
      { value: 'script_inline', label: '脚本' },
      { value: 'database', label: '数据库操作' },
      { value: 'database_script', label: '数据库脚本' },
      { value: 'wait', label: '等待' },
    ]
  const post = [
    { value: 'assertion', label: '断言' },
    { value: 'extract', label: '提取' },
    { value: 'script', label: '脚本库' },
    { value: 'script_inline', label: '脚本' },
    { value: 'database', label: '数据库操作' },
    { value: 'database_script', label: '数据库脚本' },
    { value: 'wait', label: '等待' },
  ]
  if (props.allowContract) post.push({ value: 'contract', label: '契约' })
  return post
})

const ASSERT_TYPES = [
  { value: 'status_code', label: '状态码' },
  { value: 'json_path', label: 'Response JSON' },
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

const operatorLabel = (op?: string | null) =>
  OPERATORS.find((o) => o.value === op)?.label || op || ''

const assertTypeLabel = (t?: string | null) =>
  ASSERT_TYPES.find((a) => a.value === t)?.label || t || ''

const extractSourceLabel = (s?: string | null) =>
  EXTRACT_SOURCE_OPTIONS.find((x) => x.value === s)?.label || s || ''

function sqlAction(sql?: string | null): string {
  const head = (sql || '').trim().split(/\s+/)[0]?.toUpperCase()
  if (head === 'SELECT') return '查询'
  return '执行'
}

function oneLine(text: string, max = 48): string {
  const line = text.replace(/\s+/g, ' ').trim()
  if (!line) return ''
  return line.length > max ? `${line.slice(0, max)}…` : line
}

function connectionHost(op: Processor): string {
  const conn = props.databases.find((d) => d.id === op.connection_id)
  if (!conn) return '（未选连接）'
  return conn.host || conn.name
}

function rowSummary(op: Processor): string {
  const kind = KIND_LABELS[op.kind] || op.kind
  switch (op.kind) {
    case 'database': {
      const sql = oneLine(op.sql || '')
      const host = connectionHost(op)
      return sql
        ? `${kind} | ${sqlAction(op.sql)} ${host} ${sql}`
        : `${kind} | ${host}（未填写 SQL）`
    }
    case 'database_script': {
      const host = connectionHost(op)
      const s = props.sqlScripts.find((x) => x.id === op.sql_script_id)
      return s ? `${kind} | ${host} · ${s.name}` : `${kind} | ${host}（未选 SQL 脚本）`
    }
    case 'script': {
      const s = props.scripts.find((x) => x.id === op.script_id)
      return s ? `${kind} | ${s.name}` : `${kind} | （未选脚本）`
    }
    case 'script_inline': {
      const first = (op.content || '').trim().split('\n')[0]
      return first ? `${kind} | ${oneLine(first, 40)}` : `${kind} | （空脚本）`
    }
    case 'wait':
      return `${kind} | ${op.wait_ms ?? 0} ms`
    case 'assertion': {
      const typeLbl = assertTypeLabel(op.type)
      if (op.type === 'json_path') {
        const subject = op.path?.trim() || typeLbl
        const exp = op.expected?.trim() ? op.expected : '()'
        return `${kind} ${subject} ${operatorLabel(op.operator)} ${exp}`
      }
      if (op.type === 'contains' || op.type === 'response_time') {
        return `${kind} ${typeLbl} ${oneLine(op.expected || '', 32)}`
      }
      return `${kind} ${typeLbl} ${operatorLabel(op.operator)} ${oneLine(op.expected || '', 32)}`
    }
    case 'extract': {
      const src = extractSourceLabel(op.source)
      const path = op.path?.trim() ? ` ${op.path}` : ''
      return op.var_name ? `${kind} ${op.var_name} ← ${src}${path}` : `${kind} ← ${src}${path}`
    }
    case 'contract': {
      const s = props.schemas.find((x) => x.id === op.response_schema_id)
      return s ? `${kind} | ${s.name}` : `${kind} | （未选数据模型）`
    }
    default:
      return kind
  }
}

function emptyOp(kind: string): Processor {
  const base = { kind, enabled: true } as Processor
  if (kind === 'wait') return { ...base, wait_ms: 500 }
  if (kind === 'assertion')
    return { ...base, type: 'status_code', operator: 'eq', expected: '200', path: '' }
  if (kind === 'extract')
    return { ...base, var_name: '', source: 'response_json', path: '$.data', scope: 'environment' }
  if (kind === 'contract') return { ...base, response_schema_id: null, contract_strict: false }
  if (kind === 'script_inline') return { ...base, content: '', script_lang: 'javascript' }
  if (kind === 'database') return { ...base, connection_id: null, sql: '', db_extracts: [] }
  if (kind === 'database_script')
    return { ...base, connection_id: null, sql_script_id: null, db_extracts: [] }
  return { ...base, script_id: null }
}

const expandedOps = ref<Set<Processor>>(new Set())

function isExpanded(op: Processor) {
  return expandedOps.value.has(op)
}

function toggleExpand(op: Processor) {
  const next = new Set(expandedOps.value)
  if (next.has(op)) next.delete(op)
  else next.add(op)
  expandedOps.value = next
}

function toggleEnabled(op: Processor) {
  op.enabled = op.enabled === false
}

function addKind(kind: string) {
  const op = emptyOp(kind)
  rows.value.push(op)
  expandedOps.value = new Set(expandedOps.value).add(op)
}

function remove(i: number) {
  const op = rows.value[i]
  rows.value.splice(i, 1)
  if (op) {
    const next = new Set(expandedOps.value)
    next.delete(op)
    expandedOps.value = next
  }
}

function copyAt(i: number) {
  const src = rows.value[i]
  if (!src) return
  const clone = JSON.parse(JSON.stringify(src)) as Processor
  rows.value.splice(i + 1, 0, clone)
  expandedOps.value = new Set(expandedOps.value).add(clone)
}

function onRowMenu(command: string, index: number) {
  if (command === 'copy') copyAt(index)
  else if (command === 'delete') remove(index)
}
</script>

<style scoped>
.proc-editor {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.proc-list {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-1-5);
}

.proc-item {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  overflow: hidden;
}

.proc-head {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  min-height: 36px;
  padding: 0 var(--ax-space-1-5);
  background: var(--ax-bg);
}

.proc-head--off .proc-summary {
  opacity: 0.55;
}

.proc-drag {
  flex-shrink: 0;
  cursor: grab;
  color: var(--ax-text-placeholder);
  font-size: 14px;
}

.proc-drag:active {
  cursor: grabbing;
}

.proc-status {
  display: flex;
  align-items: center;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
}

.proc-status--on {
  color: var(--ax-success);
  font-size: 18px;
}

.proc-status--off {
  color: var(--ax-text-placeholder);
  font-size: 18px;
}

.proc-summary {
  flex: 1;
  min-width: 0;
  padding: var(--ax-space-1) var(--ax-space-1);
  border: none;
  background: transparent;
  text-align: left;
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.proc-summary:hover {
  color: var(--color-blue-6);
}

.proc-more,
.proc-chevron {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: var(--ax-radius-sm);
  background: transparent;
  color: var(--ax-text-secondary);
  cursor: pointer;
  flex-shrink: 0;
}

.proc-more:hover,
.proc-chevron:hover {
  background: var(--ax-bg-hover);
  color: var(--ax-text);
}

.proc-chevron .el-icon {
  transition: transform 0.15s ease;
}

.proc-chevron--open {
  transform: rotate(90deg);
}

.proc-body {
  padding: var(--ax-space-2-5) var(--ax-space-3);
  border-top: 1px solid var(--ax-border);
  background: var(--ax-bg);
}

.proc-body-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  flex-wrap: wrap;
}

.proc-body-stack {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.proc-lbl {
  flex-shrink: 0;
  width: 36px;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
}

.unit {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.proc-add {
  width: 100%;
}

.proc-add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-1);
  width: 100%;
  padding: var(--ax-space-2) var(--ax-space-3);
  border: 1px dashed var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg);
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
  cursor: pointer;
  transition:
    background var(--ax-transition),
    border-color var(--ax-transition),
    color var(--ax-transition);
}

.proc-add-btn:hover {
  background: var(--ax-bg-hover);
  border-color: var(--color-blue-6);
  color: var(--color-blue-6);
}
</style>
