<template>
  <div class="reports-page">
    <template v-if="embeddedRunId && reportReturnFrom === 'schedules'">
      <div class="toolbar toolbar--embedded">
        <el-button link type="primary" class="back-btn" @click="backFromEmbedded">
          ← {{ embeddedBackLabel }}
        </el-button>
      </div>
      <div v-loading="embeddedLoading" class="report-detail-pane">
        <RunReportDetailPanel
          v-if="detail"
          :detail="detail"
          :parent-detail="parentDetail"
          :environment-name="detail ? envName(detail.environment_id) : '-'"
          :exporting="exporting"
          :is-suite="isSuite"
          :child-search-placeholder="childSearchPlaceholder"
          :back-label="detailBackLabel"
          @back-to-parent="backToParent"
          @export="doExport"
          @open-child="openChild"
        />
        <el-empty v-else-if="!embeddedLoading" description="报告不存在或无权访问" :image-size="60" />
      </div>
    </template>

    <template v-else>
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="title">测试报告</span>
          <el-checkbox-group
            v-model="typeFilter"
            size="small"
            class="type-filter"
            @change="handleTypeFilterChange"
          >
            <el-checkbox-button value="scenario">场景</el-checkbox-button>
            <el-checkbox-button value="suite">套件</el-checkbox-button>
            <el-checkbox-button value="case">用例</el-checkbox-button>
          </el-checkbox-group>
        </div>
        <div class="toolbar-actions">
          <el-button
            type="danger"
            size="small"
            plain
            :disabled="!selectedIds.length"
            :loading="batchDeleting"
            @click="handleBatchDelete"
          >
            批量删除{{ selectedIds.length ? ` (${selectedIds.length})` : '' }}
          </el-button>
          <el-button size="small" @click="loadRuns">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>

      <div class="filters">
        <el-input
          v-model="filterRunId"
          class="run-id"
          size="small"
          clearable
          placeholder="运行 ID"
          @keyup.enter="applyFilters"
        />
        <el-input
          v-model="filterKeyword"
          :maxlength="SEARCH_MAX_LEN"
          class="search"
          size="small"
          clearable
          placeholder="搜索报告目标名"
          @keyup.enter="applyFilters"
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
          start-placeholder="运行起"
          end-placeholder="运行止"
        />
        <el-button type="primary" size="small" @click="applyFilters">搜索</el-button>
        <el-button size="small" @click="resetFilters">重置</el-button>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="foldedRuns"
        row-key="id"
        :tree-props="{ children: 'children' }"
        class="report-table"
        height="100%"
        size="small"
        border
        @row-click="openDetail"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="目标" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="target-cell">
              <el-tag size="small" :type="targetTag(row.target_type)">
                {{ targetTypeLabel(row.target_type) }}
              </el-tag>
              {{ row.target_name }}
              <el-tag
                v-if="row.retryCount"
                size="small"
                type="warning"
                class="retry-badge"
                title="失败自动重跑，展开看各次尝试"
              >
                重试 {{ row.retryCount }} 次
              </el-tag>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="环境" width="120">
          <template #default="{ row }">{{ envName(row.environment_id) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status)">{{
              statusLabel(row.status)
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="通过率" width="110">
          <template #default="{ row }">
            {{ row.pass_rate != null ? row.pass_rate + '%' : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="90">
          <template #default="{ row }">
            {{ row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="170">
          <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
        </el-table-column>
        <el-table-column label="触发人" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.triggered_by || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openDetail(row)">查看</el-button>
            <el-popconfirm title="确认删除该报告？" @confirm="removeRun(row)">
              <template #reference>
                <el-button link type="danger" @click.stop>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <span>暂无运行记录（运行场景或套件后产生）</span>
        </template>
      </el-table>
      <el-pagination
        v-if="total > 0"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        class="pagination"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        @current-change="loadRuns"
        @size-change="handlePageSizeChange"
      />

      <el-drawer
        v-model="drawerVisible"
        :show-close="true"
        :with-header="false"
        size="65%"
        class="run-report-drawer"
        @closed="onDrawerClosed"
      >
        <RunReportDetailPanel
          :detail="detail"
          :parent-detail="parentDetail"
          :environment-name="detail ? envName(detail.environment_id) : '-'"
          :exporting="exporting"
          :is-suite="isSuite"
          :child-search-placeholder="childSearchPlaceholder"
          :back-label="detailBackLabel"
          @back-to-parent="backToParent"
          @export="doExport"
          @open-child="openChild"
        />
      </el-drawer>
    </template>
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { readWorkspaceRunId, useWorkspaceReturnRoute } from '@/composables/useWorkspaceQuery'
import RunReportDetailPanel from '@/components/apifox/run/RunReportDetailPanel.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TableInstance } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { formatTime, statusLabel, statusTag } from '@/utils/runFormat'
import { RUN_LIST_SEARCH_CASE, RUN_LIST_SEARCH_SUITE } from '@/utils/runReportList'

const pid = useRouteParamId()
const store = useWorkspaceStore()
const route = useRoute()
const router = useRouter()
const { from: reportReturnFrom } = useWorkspaceReturnRoute()

const envName = (id: number | null | undefined) =>
  id == null ? '-' : store.environments.find((e) => e.id === id)?.name || '-'

const runs = ref<Schemas['RunBriefWithRetries'][]>([])
const detail = ref<Schemas['RunOut'] | null>(null)
const parentDetail = ref<Schemas['RunOut'] | null>(null)
const drawerVisible = ref(false)
const embeddedRunId = ref<number | null>(null)
const embeddedLoading = ref(false)
const embeddedBackLabel = computed(() =>
  reportReturnFrom.value === 'schedules' ? '返回定时任务' : '返回报告列表',
)
const exporting = ref(false)
const loading = ref(false)
const batchDeleting = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedIds = ref<number[]>([])
const tableRef = ref<TableInstance>()
// 报告类型筛选：默认只显场景+套件，勾选「用例」才纳入 case 级单跑（避免调试跑淹没列表）
const DEFAULT_TYPES = ['scenario', 'suite']
// 按项目持久化用户勾选，避免刷新后回退默认（如手动勾的「用例」丢失）
const TYPE_FILTER_STORAGE_PREFIX = 'apifox:run-reports:type-filter'
function readTypeFilter(): string[] {
  try {
    const raw = localStorage.getItem(`${TYPE_FILTER_STORAGE_PREFIX}:${pid.value}`)
    const arr = raw ? JSON.parse(raw) : null
    if (Array.isArray(arr)) return arr.filter((t): t is string => typeof t === 'string')
  } catch {
    /* 存储损坏/隐私模式读失败时回落默认 */
  }
  return [...DEFAULT_TYPES]
}
const typeFilter = ref<string[]>(readTypeFilter())

// 检索状态（分页类：关键字/状态/运行时间区间下沉后端）
const STATUS_OPTIONS = [
  { value: 'passed', label: '通过' },
  { value: 'failed', label: '失败' },
  { value: 'running', label: '运行中' },
]
const filterKeyword = ref('')
const filterRunId = ref('')
const statusFilter = ref('')
const dateRange = ref<[string, string] | null>(null)

// 定时重试链折叠：后端已按「重试链」分页，每项是最后一次尝试（=整体结果），
// retries 是此前各次尝试；这里只把 retries 挂成表格子行，行上标「重试 N 次」。
type FoldedRun = Schemas['RunBriefWithRetries'] & {
  children?: Schemas['RunBrief'][]
  retryCount?: number
}
const foldedRuns = computed<FoldedRun[]>(() =>
  runs.value.map((r) => {
    const retries = r.retries ?? []
    return retries.length ? { ...r, children: retries, retryCount: retries.length } : r
  }),
)

const isSuite = computed(
  () => detail.value?.target_type === 'suite' || detail.value?.target_type === 'endpoint',
)

const childSearchPlaceholder = computed(() =>
  detail.value?.target_type === 'endpoint' ? RUN_LIST_SEARCH_CASE : RUN_LIST_SEARCH_SUITE,
)
const detailBackLabel = computed(() =>
  parentDetail.value?.target_type === 'endpoint' ? '返回批次报告' : '返回套件报告',
)

const EXPORT_EXT: Record<string, string> = { excel: 'xlsx', word: 'docx', pdf: 'pdf', json: 'json' }

async function doExport(format: keyof typeof EXPORT_EXT | string) {
  if (!detail.value) return
  exporting.value = true
  try {
    // 拦截器返回 blob；文件名前端拼（响应头拿不到），交由浏览器下载
    const blob = await apifoxApi.exportRun(detail.value.id, format)
    const name = `测试报告_${detail.value.target_name || 'report'}_${detail.value.id}.${EXPORT_EXT[format] || 'bin'}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // 全局响应拦截器已提示错误，这里仅避免未捕获 rejection
  } finally {
    exporting.value = false
  }
}

const targetTypeLabel = (t: string) => (t === 'scenario' ? '场景' : t === 'suite' ? '套件' : '用例')
const targetTag = (t: string) => (t === 'scenario' ? 'info' : t === 'suite' ? 'primary' : 'success')

function handleTypeFilterChange() {
  try {
    localStorage.setItem(
      `${TYPE_FILTER_STORAGE_PREFIX}:${pid.value}`,
      JSON.stringify(typeFilter.value),
    )
  } catch {
    /* 配额/隐私模式写失败时忽略，仅影响跨会话记忆 */
  }
  page.value = 1
  loadRuns()
}

async function loadRuns() {
  loading.value = true
  try {
    const params: Parameters<typeof apifoxApi.listRunsPage>[1] = {
      page: page.value,
      page_size: pageSize.value,
    }
    const kw = filterKeyword.value.trim()
    if (kw) params.keyword = kw
    const runId = parseRunIdFilter(filterRunId.value)
    if (runId) {
      // 精确 ID 查询时不限类型，避免 case 级运行被默认「场景+套件」筛掉
      params.run_id = runId
    } else {
      const types = typeFilter.value.length ? typeFilter.value : DEFAULT_TYPES
      params.target_types = types.join(',')
    }
    if (statusFilter.value) params.status = statusFilter.value
    if (dateRange.value?.[0]) params.date_from = dateRange.value[0]
    if (dateRange.value?.[1]) params.date_to = dateRange.value[1]
    const data = await apifoxApi.listRunsPage(pid.value, params)
    runs.value = data.items
    total.value = data.total
    if (page.value > 1 && data.items.length === 0 && data.total > 0) {
      page.value -= 1
      await loadRuns()
    }
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  filterRunId.value = filterRunId.value.replace(/\D/g, '')
  page.value = 1
  loadRuns()
}

function resetFilters() {
  filterKeyword.value = ''
  filterRunId.value = ''
  statusFilter.value = ''
  dateRange.value = null
  clearRunQuery()
  page.value = 1
  loadRuns()
}

function parseRunIdFilter(raw: string): number | null {
  const text = raw.trim()
  if (!/^\d+$/.test(text)) return null
  const id = Number(text)
  return Number.isInteger(id) && id > 0 ? id : null
}

function handleSelectionChange(rows: Schemas['RunBrief'][]) {
  selectedIds.value = rows.map((row) => row.id)
}

function closeDetailIfDeleted(runIds: number[]) {
  if (detail.value && runIds.includes(detail.value.id)) {
    drawerVisible.value = false
    detail.value = null
    parentDetail.value = null
  }
}

async function removeRun(row: Schemas['RunBrief']) {
  await apifoxApi.deleteRun(row.id)
  ElMessage.success('已删除')
  closeDetailIfDeleted([row.id])
  tableRef.value?.clearSelection()
  selectedIds.value = selectedIds.value.filter((id) => id !== row.id)
  await loadRuns()
}

async function handleBatchDelete() {
  if (!selectedIds.value.length) return
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条报告？`, '批量删除', {
    type: 'warning',
    confirmButtonText: '删除',
    confirmButtonClass: 'el-button--danger',
  })
  batchDeleting.value = true
  try {
    const res = await apifoxApi.batchDeleteRuns(pid.value, selectedIds.value)
    closeDetailIfDeleted(selectedIds.value)
    tableRef.value?.clearSelection()
    selectedIds.value = []
    if (res.failed > 0) {
      ElMessage.warning(`已删除 ${res.succeeded} 条，${res.failed} 条失败`)
    } else {
      ElMessage.success(`已删除 ${res.succeeded} 条`)
    }
    await loadRuns()
  } finally {
    batchDeleting.value = false
  }
}

async function handlePageSizeChange() {
  page.value = 1
  await loadRuns()
}

async function openDetail(row: Schemas['RunBrief']) {
  parentDetail.value = null
  detail.value = await apifoxApi.getRun(row.id)
  drawerVisible.value = true
}

async function openDetailById(runId: number) {
  parentDetail.value = null
  try {
    detail.value = await apifoxApi.getRun(runId)
    drawerVisible.value = true
  } catch {
    detail.value = null
    drawerVisible.value = false
  }
}

function clearRunQuery() {
  if (!route.query.run) return
  const query = { ...route.query }
  delete query.run
  void router.replace({ query })
}

function onDrawerClosed() {
  detail.value = null
  parentDetail.value = null
  clearRunQuery()
}

async function openChild(row: Schemas['RunBrief']) {
  parentDetail.value = detail.value
  detail.value = await apifoxApi.getRun(row.id)
}

function backToParent() {
  detail.value = parentDetail.value
  parentDetail.value = null
}

function backToReportList() {
  const query = { ...route.query }
  delete query.run
  delete query.from
  void router.replace({ query })
}

function backFromEmbedded() {
  if (reportReturnFrom.value === 'schedules') {
    void router.push({ name: 'WorkspaceAutomationSchedules', params: route.params })
    return
  }
  backToReportList()
}

async function loadEmbeddedDetail(runId: number) {
  embeddedLoading.value = true
  drawerVisible.value = false
  try {
    parentDetail.value = null
    detail.value = await apifoxApi.getRun(runId)
  } catch {
    detail.value = null
  } finally {
    embeddedLoading.value = false
  }
}

async function bootstrapFromRoute() {
  const runId = readWorkspaceRunId()
  const fromSchedules = reportReturnFrom.value === 'schedules'

  if (runId) {
    filterRunId.value = String(runId)
    page.value = 1
  }

  await loadRuns()

  if (!runId) {
    embeddedRunId.value = null
    return
  }

  if (fromSchedules) {
    embeddedRunId.value = runId
    await loadEmbeddedDetail(runId)
    return
  }

  embeddedRunId.value = null
  const row = runs.value.find((r) => r.id === runId) ?? (runs.value.length === 1 ? runs.value[0] : undefined)
  if (row) {
    await openDetail(row)
    return
  }
  await openDetailById(runId)
}

onMounted(() => {
  void bootstrapFromRoute()
})

watch(
  () => [route.query.run, route.query.from],
  () => void bootstrapFromRoute(),
)
</script>

<style scoped>
.reports-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-gap-sm);
  flex: none;
}

.filters {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-gap-sm);
  flex: none;
}

.filters .run-id {
  width: 120px;
}

.filters .search {
  width: 200px;
}

.filters .status-select {
  width: 120px;
}

.filters .date-range {
  width: 240px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
}

.type-filter {
  display: flex;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.title {
  font-size: var(--ax-font);
  font-weight: 600;
  color: var(--ax-brand);
}

.report-table {
  flex: 1;
  min-height: 0;
}

.report-table :deep(.el-table__body td .cell) {
  white-space: nowrap;
}

.target-cell {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1);
  max-width: 100%;
  vertical-align: middle;
}

.retry-badge {
  margin-left: var(--ax-space-1);
}

.pagination {
  flex: none;
  justify-content: flex-end;
  margin-top: var(--ax-gap-sm);
}

.report-detail-pane {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 var(--ax-space-1);
}

.toolbar--embedded {
  margin-bottom: var(--ax-space-2);
}

.back-btn {
  margin-bottom: var(--ax-space-2);
}

.run-report-drawer :deep(.el-drawer__body) {
  padding: var(--ax-space-4);
}
</style>
