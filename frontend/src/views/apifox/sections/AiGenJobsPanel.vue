<template>
  <div class="jobs-panel">
    <div class="head">
      <span class="title">{{ panelTitle }}</span>
      <div class="head-actions">
        <el-button type="primary" size="small" @click="batchAiRef?.open()">
          <el-icon><Plus /></el-icon> 创建 AI 任务
        </el-button>
        <el-button size="small" :loading="loading" @click="reload">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="filters">
      <el-input
        v-model="filterTaskId"
        class="task-id"
        size="small"
        clearable
        placeholder="任务 ID"
        @keyup.enter="search"
      />
      <el-input
        v-model="filterKeyword"
        :maxlength="SEARCH_MAX_LEN"
        class="search"
        size="small"
        clearable
        placeholder="搜索目标 / 创建人"
        @keyup.enter="search"
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
      />
      <el-button type="primary" size="small" @click="search">搜索</el-button>
      <el-button size="small" @click="resetFilters">重置</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tasks"
      row-key="id"
      class="jobs-table"
      size="small"
      @row-click="openDetail"
    >
      <template #empty>
        <el-empty description="暂无 AI 任务" :image-size="60" />
      </template>
      <el-table-column label="ID" prop="id" width="72" />
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
      <el-table-column label="模型" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ aiTaskModelDisplay(row.model_label) }}</template>
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
      <el-table-column label="操作" width="112" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="openDetail(row)">查看</el-button>
          <el-button
            v-if="canStopTask(row)"
            link
            type="danger"
            size="small"
            :loading="stopTaskId === row.id"
            @click.stop="stopTask(row)"
          >
            停止
          </el-button>
        </template>
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
      :title="detailDialogTitle"
      width="920px"
      align-center
      destroy-on-close
      class="ai-gen-detail-dialog"
      @closed="onDetailClosed"
    >
      <AiGenTaskProgress
        v-if="detailTaskId"
        :task-id="detailTaskId"
        :project-id="pid"
        hide-multi-endpoint-batch
        @applied="reload"
      />
    </el-dialog>

    <BatchAiGenerateDialog ref="batchAiRef" :project-id="pid" @created="reload" />
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { onBeforeUnmount, onMounted, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'
import { useRouteParamId } from '@/composables/useRouteParamId'
import {
  parseWorkspaceKeywordFromRoute,
  parseWorkspaceTaskIdFromRoute,
} from '@/composables/useWorkspaceQuery'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { categoryLabel } from '@/utils/caseCategory'
import { mergeRowsInPlace } from '@/utils/mergeRows'
import { aiTaskModelDisplay } from '@/utils/aiTaskModelLabel'
import { formatTime } from '@/utils/runFormat'
import AiGenTaskProgress from '@/components/apifox/ai/AiGenTaskProgress.vue'
import BatchAiGenerateDialog from '@/components/apifox/ai/BatchAiGenerateDialog.vue'

type TaskRow = Schemas['AiGenTaskBrief']
const props = withDefaults(
  defineProps<{
    panelTitle?: string
  }>(),
  { panelTitle: 'AI 任务中心' },
)
const TERMINAL = ['succeeded', 'partial', 'failed', 'canceled']
const POLL_MS = 3000
const STATUS_OPTIONS = [
  { value: 'pending', label: '排队中' },
  { value: 'running', label: '生成中' },
  { value: 'succeeded', label: '成功' },
  { value: 'partial', label: '部分成功' },
  { value: 'failed', label: '失败' },
  { value: 'canceled', label: '已取消' },
]

const pid = useRouteParamId()
const route = useRoute()
const router = useRouter()
const store = useApifoxAiGenerateStore()

const detailDialogTitle = computed(() => `${props.panelTitle}详情`)

const tasks = ref<TaskRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const detailVisible = ref(false)
const detailTaskId = ref<number | null>(null)
const batchAiRef = ref<InstanceType<typeof BatchAiGenerateDialog> | null>(null)
const stopTaskId = ref<number | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

// 检索状态（分页类：条件下沉后端，轮询/翻页均复用 buildParams 携带当前条件）
const filterKeyword = ref('')
const filterTaskId = ref('')
const statusFilter = ref('')
const dateRange = ref<[string, string] | null>(null)

function buildParams() {
  const params: Parameters<typeof apifoxApi.listAiGenTasks>[1] = {
    page: page.value,
    page_size: pageSize.value,
  }
  const kw = filterKeyword.value.trim()
  if (kw) params.keyword = kw
  const taskId = parseTaskIdFilter(filterTaskId.value)
  if (taskId) params.task_id = taskId
  if (statusFilter.value) params.status = statusFilter.value
  if (dateRange.value?.[0]) params.date_from = dateRange.value[0]
  if (dateRange.value?.[1]) params.date_to = dateRange.value[1]
  return params
}

// silent=true 用于轮询刷新：不动 loading，避免每次 tick 闪一层遮罩
async function fetchTasks(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await apifoxApi.listAiGenTasks(pid.value, buildParams())
    total.value = res.total
    if (res.total > 0 && res.items.length === 0 && page.value > 1) {
      page.value = Math.max(1, Math.ceil(res.total / pageSize.value))
      await fetchTasks(silent)
      return
    }
    tasks.value = mergeRowsInPlace(tasks.value, res.items)
  } finally {
    if (!silent) loading.value = false
  }
}

function reload() {
  return fetchTasks()
}

function parseTaskIdFilter(raw: string): number | null {
  const text = raw.trim()
  if (!/^\d+$/.test(text)) return null
  const id = Number(text)
  return Number.isInteger(id) && id > 0 ? id : null
}

function search() {
  filterTaskId.value = filterTaskId.value.replace(/\D/g, '')
  page.value = 1
  reload()
}

function resetFilters() {
  filterKeyword.value = ''
  filterTaskId.value = ''
  statusFilter.value = ''
  dateRange.value = null
  clearTaskQuery()
  page.value = 1
  reload()
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

async function openDetailById(taskId: number) {
  detailTaskId.value = taskId
  detailVisible.value = true
  try {
    await store.loadTask(taskId)
  } catch {
    /* 忽略，抽屉里会显示空 */
  }
}

async function openDetail(row: TaskRow) {
  await openDetailById(row.id)
}

function clearTaskQuery() {
  if (!route.query.task) return
  const query = { ...route.query }
  delete query.task
  void router.replace({ query })
}

function onDetailClosed() {
  detailTaskId.value = null
  clearTaskQuery()
}

function applyListFiltersFromRoute() {
  const taskId = parseWorkspaceTaskIdFromRoute(route)
  if (taskId) filterTaskId.value = String(taskId)
  const kw = parseWorkspaceKeywordFromRoute(route)
  if (kw) filterKeyword.value = kw
}

async function syncDetailFromQuery() {
  const taskId = parseWorkspaceTaskIdFromRoute(route)
  if (!taskId) return
  if (detailVisible.value && detailTaskId.value === taskId) return
  await openDetailById(taskId)
}

async function bootstrapFromRoute() {
  applyListFiltersFromRoute()
  page.value = 1
  await reload()
  await syncDetailFromQuery()
}

function canStopTask(row: TaskRow): boolean {
  return row.status === 'pending' || row.status === 'running'
}

async function stopTask(row: TaskRow) {
  if (!canStopTask(row)) return
  try {
    await ElMessageBox.confirm(
      '停止后任务将标记为已取消，已生成的用例预览会保留。确认停止？',
      '停止任务',
      { confirmButtonText: '停止', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  stopTaskId.value = row.id
  try {
    await store.cancel(row.id)
    ElMessage.success('任务已停止')
    if (detailTaskId.value === row.id) {
      detailVisible.value = false
    }
    await reload()
  } catch (e) {
    ElMessage.error((e as Error).message || '停止失败')
  } finally {
    stopTaskId.value = null
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
    pending: 'warning',
    canceled: 'info',
  })[s] || 'info'
const categorySummary = (cats: string[]): string =>
  cats?.length ? cats.map((c) => categoryLabel(c)).join(' · ') : '-'
// 有进行中的任务时轮询刷新列表（进度、状态实时更新）；静默刷新，单次失败忽略
function tick() {
  if (tasks.value.some((t) => !TERMINAL.includes(t.status))) {
    fetchTasks(true).catch(() => {})
  }
}

onMounted(async () => {
  await bootstrapFromRoute()
  pollTimer = setInterval(tick, POLL_MS)
})
watch(
  () => [route.query.task, route.query.filter, route.query.keyword] as const,
  () => void bootstrapFromRoute(),
)
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
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

.task-id {
  width: 120px;
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
