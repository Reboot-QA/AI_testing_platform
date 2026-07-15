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
      <div v-for="(row, i) in rows" :key="i" class="kv-row">
        <el-checkbox v-model="row.enabled" />
        <el-autocomplete
          v-if="suggest === 'header'"
          v-model="row.key"
          :fetch-suggestions="fetchKeys"
          placeholder="键"
          size="small"
          class="kv-key"
          @select="(item) => onKeySelect(row, item)"
        />
        <el-input v-else v-model="row.key" placeholder="键" size="small" class="kv-key" />

        <el-autocomplete
          v-if="suggest === 'header'"
          v-model="row.value"
          :fetch-suggestions="(qs, cb) => fetchValues(row, qs, cb)"
          placeholder="值"
          size="small"
          class="kv-val"
        />
        <el-input v-else v-model="row.value" placeholder="值" size="small" class="kv-val" />

        <el-button v-if="!isTail(i)" link type="danger" size="small" @click="del(i)">
          <el-icon><Delete /></el-icon>
        </el-button>
        <span v-else class="tail-placeholder" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { emptyKvRow } from '@/utils/apiCaseConfig'
import { headerDefaultValue, rowsToText, suggestHeaderKeys, suggestHeaderValues, textToRows } from '@/utils/httpHeaders'

// rows 为父级 reactive 数组（按引用传入），子组件就地增删改，父级自动响应。
// suggest='header' 时键/值走 header 常用清单自动补全；其余场景为普通输入。
const props = defineProps({
  rows: { type: Array, required: true },
  suggest: { type: String, default: '' },
})

const bulkMode = ref(false)
const bulkText = ref('')
// 进入批量模式时按 key 快照 desc（说明字段表格里不可见/不可编辑，批量文本也不暴露），
// 解析回行时找回，避免批量编辑静默清空导入接口的参数说明。
let descByKey = {}

const isEmptyRow = (r) => !(r.key || '').trim() && !(r.value || '').trim()
const isTail = (i) => i === props.rows.length - 1 && isEmptyRow(props.rows[i])

// 自动新行：始终保留恰好一个末尾空行（幂等，稳定后不再变更，不会递归死循环）
function syncTail() {
  const list = props.rows
  while (list.length > 1 && isEmptyRow(list[list.length - 1]) && isEmptyRow(list[list.length - 2])) {
    list.pop()
  }
  if (list.length === 0 || !isEmptyRow(list[list.length - 1])) {
    list.push(emptyKvRow())
  }
}

function del(i) {
  props.rows.splice(i, 1)
  syncTail()
}

function toggleBulk() {
  if (!bulkMode.value) {
    bulkText.value = rowsToText(props.rows)
    descByKey = {}
    props.rows.forEach((r) => { if (r.key && r.desc) descByKey[r.key] = r.desc })
  } else {
    syncTail()
  }
  bulkMode.value = !bulkMode.value
}

// 批量文本实时解析回行：保证父级 rows 始终与文本一致（不必切回表格才生效）；desc 按 key 找回不丢
function syncFromText() {
  const parsed = textToRows(bulkText.value)
  parsed.forEach((r) => { if (descByKey[r.key]) r.desc = descByKey[r.key] })
  props.rows.splice(0, props.rows.length, ...parsed)
}

const fetchKeys = (query, cb) => cb(suggestHeaderKeys(query))
const fetchValues = (row, query, cb) => cb(suggestHeaderValues(row.key, query))

// 选中常用 header 时，值为空则自动带上该 header 的默认值（不覆盖已填的值）
function onKeySelect(row, item) {
  if (!(row.value || '').trim()) {
    const def = headerDefaultValue(item.value)
    if (def) row.value = def
  }
}

onMounted(syncTail)
// 表格模式下任意键值改动后维持末尾空行（深比较，内容变触发）
watch(() => props.rows, () => { if (!bulkMode.value) syncTail() }, { deep: true })
// 父级换了整份 rows（切用例/接口）：退出批量模式并重建末尾空行，避免残留旧文本覆盖新数据
watch(() => props.rows, () => { bulkMode.value = false; syncTail() })
</script>

<style scoped>
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

.tail-placeholder {
  width: 24px;
  flex: none;
}
</style>
