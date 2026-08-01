<template>
  <div class="trash-panel">
    <div class="panel-head trash-head">
      <div class="trash-heading">
        <span class="panel-title">回收站</span>
        <span class="tip"
          >已删除的场景、测试套件、接口用例和接口保留 30 天；可还原或彻底删除。</span
        >
      </div>
      <div class="toolbar-actions items-center gap-1 flex">
        <el-input
          v-model="filterKeyword"
          :maxlength="SEARCH_MAX_LEN"
          class="search"
          size="small"
          clearable
          placeholder="搜索名称 / 信息 / 操作人"
          @input="onKeywordInput"
          @clear="onFilterChange"
        >
          <template #prefix
            ><el-icon><Search /></el-icon
          ></template>
        </el-input>
        <el-select
          v-model="kindFilter"
          class="kind-select"
          size="small"
          clearable
          placeholder="全部类型"
          @change="onFilterChange"
        >
          <el-option v-for="(label, k) in KIND_LABEL" :key="k" :label="label" :value="k" />
        </el-select>
        <template v-if="selected.length">
          <span class="sel-count">已选 {{ selected.length }} 项</span>
          <el-button link type="primary" size="small" @click="clearSelection">取消选择</el-button>
          <el-button size="small" :loading="batchBusy" @click="batchRestore">
            <el-icon><RefreshLeft /></el-icon> 恢复
          </el-button>
          <el-button size="small" type="danger" plain :loading="batchBusy" @click="batchPurge">
            <el-icon><Delete /></el-icon> 删除
          </el-button>
        </template>
        <el-button size="small" :loading="loading" @click="load">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="items"
      class="trash-table"
      height="100%"
      size="small"
      border
      row-key="rowId"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="42" reserve-selection />
      <el-table-column label="类型" width="104">
        <template #default="{ row }">
          <el-tag size="small" :type="kindTagType(row.kind)">{{ kindLabel(row.kind) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="名称" prop="name" min-width="180" show-overflow-tooltip />
      <el-table-column label="信息" min-width="180">
        <template #default="{ row }">
          <span class="detail">{{ detailText(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作人" min-width="110">
        <template #default="{ row }">
          <span class="operator">{{ row.operator || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="删除时间" min-width="160">
        <template #default="{ row }">
          <span class="time">{{ fmt(row.deleted_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="剩余保留" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="remainTag(row.remaining_days)" effect="plain">{{
            remainText(row.remaining_days)
          }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            size="small"
            :loading="busyKey === rowKey(row)"
            @click="restore(row)"
            >还原</el-button
          >
          <el-button
            link
            type="danger"
            size="small"
            :loading="busyKey === rowKey(row)"
            @click="purge(row)"
            >彻底删除</el-button
          >
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="emptyText" :image-size="60" />
      </template>
    </el-table>

    <el-pagination
      v-if="total > 0"
      small
      class="pager"
      layout="total, prev, pager, next, sizes"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      :page-sizes="[20, 50, 100]"
      @current-change="onPageChange"
      @size-change="onPageSizeChange"
    />
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TableInstance } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { formatBeijingTime } from '@/utils/datetime'

type TrashItem = Schemas['TrashItem']
type TrashRow = TrashItem & { rowId: string }

const PAGE_SIZE = 20
const KEYWORD_DEBOUNCE_MS = 300

const pid = useRouteParamId()
const items = ref<TrashRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const loading = ref(false)
const busyKey = ref('')
const batchBusy = ref(false)
const selected = ref<TrashRow[]>([])
const tableRef = ref<TableInstance>()

const kindFilter = ref<TrashItem['kind'] | ''>('')
const filterKeyword = ref('')
let keywordTimer: ReturnType<typeof setTimeout> | undefined

const emptyText = computed(() =>
  total.value === 0 && !filterKeyword.value && !kindFilter.value ? '回收站为空' : '无匹配结果',
)

const KIND_LABEL: Record<TrashItem['kind'], string> = {
  scenario: '场景',
  suite: '测试套件',
  case: '接口用例',
  endpoint: '单接口',
}
const kindLabel = (k: TrashItem['kind']) => KIND_LABEL[k]

const DETAIL_PREFIX: Record<TrashItem['kind'], string> = {
  scenario: '优先级',
  case: '接口',
  endpoint: '路径',
  suite: '',
}
function detailText(row: TrashItem): string {
  if (!row.detail) return '—'
  const prefix = DETAIL_PREFIX[row.kind]
  return prefix ? `${prefix}：${row.detail}` : row.detail
}
const KIND_TAG: Record<TrashItem['kind'], 'warning' | 'primary' | 'success' | 'info'> = {
  scenario: 'warning',
  suite: 'primary',
  case: 'success',
  endpoint: 'info',
}
const kindTagType = (k: TrashItem['kind']) => KIND_TAG[k]

const rowKey = (row: TrashItem) => `${row.kind}:${row.id}`
const fmt = (t: string) => formatBeijingTime(t)

// 剩余天数由后端算（deleted_at 与 now 同一时钟），前端只展示，避免跨时区解析偏差
const remainText = (days: number) => (days <= 0 ? '即将清理' : `还剩 ${days} 天`)
const remainTag = (days: number): 'danger' | 'warning' | 'info' => {
  if (days <= 3) return 'danger'
  if (days <= 7) return 'warning'
  return 'info'
}

const batchPayload = computed(() => selected.value.map((row) => ({ kind: row.kind, id: row.id })))

function onSelectionChange(rows: TrashRow[]) {
  selected.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selected.value = []
}

function showBatchResult(
  action: string,
  result: { succeeded: number; failed: number; errors: string[] },
) {
  if (result.failed === 0) {
    ElMessage.success(`${action}成功 ${result.succeeded} 项`)
    return
  }
  if (result.succeeded === 0) {
    ElMessage.error(`${action}失败：${result.errors[0] || '未知错误'}`)
    return
  }
  ElMessage.warning(`${action}：成功 ${result.succeeded} 项，失败 ${result.failed} 项`)
}

function onFilterChange() {
  page.value = 1
  void load()
}

function onKeywordInput() {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(onFilterChange, KEYWORD_DEBOUNCE_MS)
}

function onPageChange(p: number) {
  page.value = p
  void load()
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  void load()
}

async function load() {
  loading.value = true
  try {
    const data = await apifoxApi.listTrash(pid.value, {
      page: page.value,
      page_size: pageSize.value,
      keyword: filterKeyword.value.trim() || undefined,
      kind: kindFilter.value || undefined,
    })
    total.value = data.total
    if (data.total > 0 && data.items.length === 0 && page.value > 1) {
      page.value = Math.max(1, Math.ceil(data.total / pageSize.value))
      await load()
      return
    }
    items.value = data.items.map((row) => ({ ...row, rowId: rowKey(row) }))
    clearSelection()
  } finally {
    loading.value = false
  }
}

async function restore(row: TrashItem) {
  busyKey.value = rowKey(row)
  try {
    await apifoxApi.restoreTrash(row.kind, row.id)
    ElMessage.success('已还原')
    await load()
  } finally {
    busyKey.value = ''
  }
}

async function purge(row: TrashItem) {
  await ElMessageBox.confirm(
    `确认彻底删除${kindLabel(row.kind)}「${row.name}」？此操作不可恢复。`,
    '彻底删除',
    { type: 'warning', confirmButtonText: '彻底删除', confirmButtonClass: 'el-button--danger' },
  )
  busyKey.value = rowKey(row)
  try {
    await apifoxApi.purgeTrash(row.kind, row.id)
    ElMessage.success('已彻底删除')
    await load()
  } finally {
    busyKey.value = ''
  }
}

async function batchRestore() {
  if (!batchPayload.value.length) return
  batchBusy.value = true
  try {
    const result = await apifoxApi.batchRestoreTrash(pid.value, batchPayload.value)
    showBatchResult('恢复', result)
    await load()
  } finally {
    batchBusy.value = false
  }
}

async function batchPurge() {
  if (!batchPayload.value.length) return
  await ElMessageBox.confirm(
    `确认彻底删除已选的 ${selected.value.length} 项？此操作不可恢复。`,
    '批量彻底删除',
    { type: 'warning', confirmButtonText: '彻底删除', confirmButtonClass: 'el-button--danger' },
  )
  batchBusy.value = true
  try {
    const result = await apifoxApi.batchPurgeTrash(pid.value, batchPayload.value)
    showBatchResult('删除', result)
    await load()
  } finally {
    batchBusy.value = false
  }
}

onMounted(load)

watch(pid, () => {
  page.value = 1
  void load()
})

onBeforeUnmount(() => {
  if (keywordTimer) clearTimeout(keywordTimer)
})
</script>

<style scoped>
.trash-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.trash-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-3);
  margin-bottom: var(--ax-space-3);
  flex: none;
}

.trash-heading {
  display: flex;
  align-items: baseline;
  gap: var(--ax-space-2);
  min-width: 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  flex: none;
}

.trash-head :deep(.el-input),
.trash-head :deep(.el-select),
.trash-head :deep(.el-button) {
  --el-component-size: var(--ax-control-height-sm);
}

.search {
  width: 200px;
}

.kind-select {
  width: 120px;
}

.sel-count {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
}

.tip {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
  flex: 1;
  min-width: 0;
}

.trash-table {
  flex: 1;
  min-height: 0;
}

.pager {
  flex: none;
  margin-top: var(--ax-space-2);
  justify-content: flex-end;
}

.detail {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-caption-size);
}

.time {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-tertiary);
}

.operator {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
}
</style>
