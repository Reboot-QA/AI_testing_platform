<template>
  <div class="jobs-panel">
    <div class="head">
      <span class="title">AI 任务中心</span>
      <div class="head-actions">
        <el-button type="primary" @click="batchAiRef?.open()">
          <el-icon><Plus /></el-icon> 创建 AI 任务
        </el-button>
        <el-button :loading="loading" @click="reload">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="filters">
      <el-input
        v-model="filterKeyword"
        :maxlength="SEARCH_MAX_LEN"
        class="search"
        size="small"
        clearable
        placeholder="搜索目标 / 创建人"
        @input="onKeywordInput"
        @clear="applyFilters"
      >
        <template #prefix
          ><el-icon><Search /></el-icon
        ></template>
      </el-input>
      <el-select
        v-model="statusFilter"
        class="status-select"
        size="small"
        clearable
        placeholder="全部状态"
        @change="applyFilters"
      >
        <el-option v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        class="date-range"
        type="daterange"
        size="small"
        unlink-panels
        value-format="YYYY-MM-DD"
        range-separator="~"
        start-placeholder="创建起"
        end-placeholder="创建止"
        @change="applyFilters"
      />
    </div>

    <el-table
      v-loading="loading"
      :data="tasks"
      class="jobs-table"
      size="small"
      @row-click="openDetail"
    >
      <template #empty>
        <el-empty description="暂无 AI 任务" :image-size="60" />
      </template>
      <el-table-column label="状态" width="96">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="目标" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.target || `批量 · ${row.total_items} 接口` }}
        </template>
      </el-table-column>
      <el-table-column label="类别" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ categorySummary(row.categories) }}</template>
      </el-table-column>
      <el-table-column label="进度" width="90">
        <template #default="{ row }">{{ row.done_items }}/{{ row.total_items }}</template>
      </el-table-column>
      <el-table-column label="生成用例" width="96">
        <template #default="{ row }">{{ row.generated_total }} 条</template>
      </el-table-column>
      <el-table-column label="已入库" width="96">
        <template #default="{ row }">{{ row.applied_total }}/{{ row.generated_total }}</template>
      </el-table-column>
      <el-table-column label="创建人" min-width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.creator_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="140">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="完成时间" width="140">
        <template #default="{ row }">{{
          row.finished_at ? formatTime(row.finished_at) : '--'
        }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > 0"
      small
      class="pager"
      layout="total, prev, pager, next, sizes"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      :page-sizes="[10, 20, 50]"
      @current-change="onPage"
      @size-change="onPageSizeChange"
    />

    <el-dialog
      v-model="detailVisible"
      title="AI 任务详情"
      width="920px"
      align-center
      destroy-on-close
      class="ai-gen-detail-dialog"
      @closed="detailTaskId = null"
    >
      <AiGenTaskProgress
        v-if="detailTaskId"
        :task-id="detailTaskId"
        :project-id="pid"
        @applied="reload"
      />
    </el-dialog>

    <BatchAiGenerateDialog ref="batchAiRef" :project-id="pid" @created="reload" />
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { categoryLabel } from '@/utils/caseCategory'
import { formatTime } from '@/utils/runFormat'
import AiGenTaskProgress from '@/components/apifox/ai/AiGenTaskProgress.vue'
import BatchAiGenerateDialog from '@/components/apifox/ai/BatchAiGenerateDialog.vue'

type TaskRow = Schemas['AiGenTaskBrief']
const TERMINAL = ['succeeded', 'partial', 'failed', 'canceled']
const POLL_MS = 3000
const KEYWORD_DEBOUNCE_MS = 300
const STATUS_OPTIONS = [
  { value: 'pending', label: '排队中' },
  { value: 'running', label: '生成中' },
  { value: 'succeeded', label: '成功' },
  { value: 'partial', label: '部分成功' },
  { value: 'failed', label: '失败' },
  { value: 'canceled', label: '已取消' },
]

const pid = useRouteParamId()
const store = useApifoxAiGenerateStore()

const tasks = ref<TaskRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const detailVisible = ref(false)
const detailTaskId = ref<number | null>(null)
const batchAiRef = ref<InstanceType<typeof BatchAiGenerateDialog> | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

// 检索状态（分页类：条件下沉后端，轮询/翻页均复用 buildParams 携带当前条件）
const filterKeyword = ref('')
const statusFilter = ref('')
const dateRange = ref<[string, string] | null>(null)
let keywordTimer: ReturnType<typeof setTimeout> | null = null

function buildParams() {
  const params: Parameters<typeof apifoxApi.listAiGenTasks>[1] = {
    page: page.value,
    page_size: pageSize.value,
  }
  const kw = filterKeyword.value.trim()
  if (kw) params.keyword = kw
  if (statusFilter.value) params.status = statusFilter.value
  if (dateRange.value?.[0]) params.date_from = dateRange.value[0]
  if (dateRange.value?.[1]) params.date_to = dateRange.value[1]
  return params
}

async function reload() {
  loading.value = true
  try {
    const res = await apifoxApi.listAiGenTasks(pid.value, buildParams())
    total.value = res.total
    if (res.total > 0 && res.items.length === 0 && page.value > 1) {
      page.value = Math.max(1, Math.ceil(res.total / pageSize.value))
      await reload()
      return
    }
    tasks.value = res.items
  } finally {
    loading.value = false
  }
}

// 任一检索条件变更 → 重置到第 1 页再拉取
function applyFilters() {
  page.value = 1
  reload()
}

function onKeywordInput() {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(applyFilters, KEYWORD_DEBOUNCE_MS)
}

function onPage(p: number) {
  page.value = p
  reload()
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  reload()
}

async function openDetail(row: TaskRow) {
  detailTaskId.value = row.id
  detailVisible.value = true
  try {
    await store.loadTask(row.id) // AiGenTaskProgress 从 store 读该任务
  } catch {
    /* 忽略，抽屉里会显示空 */
  }
}

const statusText = (s: string): string =>
  ({
    pending: '排队中',
    running: '生成中',
    succeeded: '成功',
    partial: '部分成功',
    failed: '失败',
    canceled: '已取消',
  })[s] || s
const statusType = (s: string): string =>
  ({
    succeeded: 'success',
    partial: 'warning',
    failed: 'danger',
    running: 'primary',
    canceled: 'info',
  })[s] || 'info'
const categorySummary = (cats: string[]): string =>
  cats?.length ? cats.map((c) => categoryLabel(c)).join(' · ') : '-'
// 有进行中的任务时轮询刷新列表（进度、状态实时更新）
function tick() {
  if (tasks.value.some((t) => !TERMINAL.includes(t.status))) reload()
}

onMounted(() => {
  reload()
  pollTimer = setInterval(tick, POLL_MS)
})
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (keywordTimer) clearTimeout(keywordTimer)
})
</script>

<style scoped>
.jobs-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-space-2-5);
}

.head-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.filters {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2-5);
  flex: none;
}

.search {
  width: 200px;
}

.status-select {
  width: 120px;
}

.date-range {
  width: 240px;
}

.title {
  font-size: var(--ax-font);
  font-weight: 600;
  color: var(--ax-brand);
}

.jobs-table {
  flex: 1;
  min-height: 0;
  cursor: pointer;
}

.pager {
  margin-top: var(--ax-space-2-5);
  justify-content: flex-end;
}

.ai-gen-detail-dialog :deep(.el-dialog) {
  max-width: calc(100vw - 32px);
  margin: 0 auto;
}

.ai-gen-detail-dialog :deep(.el-dialog__body) {
  max-height: min(78vh, 860px);
  overflow: auto;
  padding-top: var(--ax-space-1);
}

.ai-gen-detail-dialog :deep(.progress) {
  min-width: 0;
}
</style>
