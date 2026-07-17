<template>
  <div class="kv-editor">
    <div class="kv-bar">
      <el-button link size="small" @click="toggleBulk">
        <el-icon><Edit /></el-icon> {{ bulkMode ? '表格编辑' : '批量编辑' }}
      </el-button>
    </div>

    <!-- 批量文本模式：整块粘贴 Key: Value -->
    <el-input
      v-if="bulkMode"
      v-model="bulkText"
      type="textarea"
      :rows="7"
      placeholder="每行一个 Key: Value（可整块粘贴；// 或 # 开头表示禁用该行）"
      @input="syncFromText"
    />

    <!-- 表格模式：自动新行 + header 名/值自动补全 -->
    <template v-else>
      <div v-for="(row, i) in rows" :key="i" class="kv-row" :class="{ 'kv-row-off': !row.enabled }">
        <el-checkbox v-model="row.enabled" />
        <el-autocomplete
          v-if="suggest === 'header'"
          v-model="row.key"
          :fetch-suggestions="fetchKeys"
          placeholder="键"
          size="small"
          class="kv-key"
          @select="(item: { value: string }) => onKeySelect(row, item)"
        />
        <el-input v-else v-model="row.key" placeholder="键" size="small" class="kv-key" />

        <el-autocomplete
          v-if="suggest === 'header'"
          v-model="row.value"
          :fetch-suggestions="
            (qs: string, cb: (results: Array<Record<string, string>>) => void) =>
              fetchValues(row, qs, cb)
          "
          placeholder="值"
          size="small"
          class="kv-val"
        />
        <el-input v-else v-model="row.value" placeholder="值" size="small" class="kv-val" />

        <el-select
          v-if="showType"
          :model-value="row.type || 'string'"
          size="small"
          class="kv-type"
          @update:model-value="(v: string) => (row.type = v)"
        >
          <el-option v-for="t in PARAM_TYPES" :key="t" :label="t" :value="t" />
        </el-select>

        <el-button v-if="!isTail(i)" link type="danger" size="small" @click="del(i)">
          <el-icon><Delete /></el-icon>
        </el-button>
        <span v-else class="tail-placeholder" />
      </div>

      <!-- 常用 Header：带默认值、默认不勾选，勾选即加入为启用行（对齐 Apifox 默认 Header） -->
      <div v-if="suggest === 'header'" class="common-headers">
        <el-button link size="small" @click="showCommon = !showCommon">
          <el-icon><component :is="showCommon ? 'ArrowUp' : 'ArrowDown'" /></el-icon> 常用 Header
        </el-button>
        <div v-if="showCommon" class="common-list">
          <el-checkbox
            v-for="h in COMMON_HEADER_PRESETS"
            :key="h.name"
            :model-value="isPresent(h.name)"
            @change="(v: boolean) => toggleCommon(h, v)"
          >
            {{ h.name }}<span v-if="h.value" class="common-def"> : {{ h.value }}</span>
          </el-checkbox>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import type { KvRow } from '@/types/apifox'
import { emptyKvRow } from '@/utils/apiCaseConfig'
import {
  COMMON_HEADER_PRESETS,
  headerDefaultValue,
  rowsToText,
  suggestHeaderKeys,
  suggestHeaderValues,
  textToRows,
} from '@/utils/httpHeaders'

// rows 为父级 reactive 数组（按引用传入），子组件就地增删改，父级自动响应。
// suggest='header' 时键/值走 header 常用清单自动补全；其余场景为普通输入。
const props = withDefaults(
  defineProps<{
    rows: KvRow[]
    suggest?: string
    showType?: boolean
  }>(),
  {
    suggest: '',
    showType: false,
  },
)

// HTTP 参数类型标注（含 file），语义不同于 useJsonSchema 的 SCHEMA_TYPES，故意不复用
const PARAM_TYPES = ['string', 'integer', 'number', 'boolean', 'array', 'object', 'file']

const bulkMode = ref(false)
const bulkText = ref('')
const showCommon = ref(false)
// 进入批量模式时按 key 快照 desc（说明字段表格里不可见/不可编辑，批量文本也不暴露），
// 解析回行时找回，避免批量编辑静默清空导入接口的参数说明。
let descByKey: Record<string, string> = {}
// 同理快照 type：批量文本不表达参数类型，回解析时按 key 找回，避免批量编辑静默清空
let typeByKey: Record<string, string> = {}

const isEmptyRow = (r: KvRow) => !(r.key || '').trim() && !(r.value || '').trim()
const isTail = (i: number) => i === props.rows.length - 1 && isEmptyRow(props.rows[i])

// 自动新行：始终保留恰好一个末尾空行（幂等，稳定后不再变更，不会递归死循环）
function syncTail() {
  const list = props.rows
  while (
    list.length > 1 &&
    isEmptyRow(list[list.length - 1]) &&
    isEmptyRow(list[list.length - 2])
  ) {
    list.pop()
  }
  if (list.length === 0 || !isEmptyRow(list[list.length - 1])) {
    list.push(emptyKvRow())
  }
}

function del(i: number) {
  props.rows.splice(i, 1)
  syncTail()
}

function toggleBulk() {
  if (!bulkMode.value) {
    bulkText.value = rowsToText(props.rows)
    descByKey = {}
    typeByKey = {}
    props.rows.forEach((r) => {
      if (r.key && r.desc) descByKey[r.key] = r.desc
      if (r.key && r.type) typeByKey[r.key] = r.type
    })
  } else {
    syncTail()
  }
  bulkMode.value = !bulkMode.value
}

// 批量文本实时解析回行：保证父级 rows 始终与文本一致（不必切回表格才生效）；desc 按 key 找回不丢
function syncFromText() {
  const parsed = textToRows(bulkText.value)
  parsed.forEach((r) => {
    if (descByKey[r.key]) r.desc = descByKey[r.key]
    if (typeByKey[r.key]) r.type = typeByKey[r.key]
  })
  props.rows.splice(0, props.rows.length, ...parsed)
}

const fetchKeys = (query: string, cb: (results: Array<Record<string, string>>) => void) =>
  cb(suggestHeaderKeys(query))
const fetchValues = (
  row: KvRow,
  query: string,
  cb: (results: Array<Record<string, string>>) => void,
) => cb(suggestHeaderValues(row.key, query))

// 选中常用 header 时，值为空则自动带上该 header 的默认值（不覆盖已填的值）
function onKeySelect(row: KvRow, item: { value: string }) {
  if (!(row.value || '').trim()) {
    const def = headerDefaultValue(item.value)
    if (def) row.value = def
  }
}

// 常用 Header 勾选区：勾选加入启用行（带默认值）、取消移除；已在列表则显示为勾选
const isPresent = (name: string) =>
  props.rows.some((r) => (r.key || '').trim().toLowerCase() === name.toLowerCase())

function toggleCommon(h: (typeof COMMON_HEADER_PRESETS)[number], checked: boolean) {
  const list = props.rows
  if (checked) {
    if (!isPresent(h.name)) {
      const at = list.length && isEmptyRow(list[list.length - 1]) ? list.length - 1 : list.length
      list.splice(at, 0, { ...emptyKvRow(), key: h.name, value: h.value, enabled: true })
    }
  } else {
    for (let i = list.length - 1; i >= 0; i--) {
      if ((list[i].key || '').trim().toLowerCase() === h.name.toLowerCase()) list.splice(i, 1)
    }
  }
  syncTail()
}

onMounted(syncTail)
// 表格模式下任意键值改动后维持末尾空行（深比较，内容变触发）
watch(
  () => props.rows,
  () => {
    if (!bulkMode.value) syncTail()
  },
  { deep: true },
)
// 父级换了整份 rows（切用例/接口）：退出批量模式并重建末尾空行，避免残留旧文本覆盖新数据
watch(
  () => props.rows,
  () => {
    bulkMode.value = false
    syncTail()
  },
)
</script>

<style scoped>
/* 未勾选行置灰：直观表示不会带上；勾选框保持清晰可点 */
.kv-row-off {
  opacity: 0.5;
}
.kv-row-off :deep(.el-checkbox) {
  opacity: 1;
}

.kv-bar {
  margin-bottom: 4px;
}

.kv-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.kv-key {
  width: 220px;
  flex: none;
}

.kv-val {
  flex: 1;
  min-width: 0;
}

.kv-type {
  width: 96px;
  flex: none;
}

.tail-placeholder {
  width: 24px;
  flex: none;
}

.common-headers {
  margin-top: 6px;
}

.common-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  padding: 8px 12px;
  margin-top: 4px;
  background: var(--ax-bg-subtle);
  border-radius: 4px;
}

.common-def {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>
