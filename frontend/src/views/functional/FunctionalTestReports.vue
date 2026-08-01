<template>
  <div class="func-reports">
    <div class="toolbar">
      <span class="title">功能测试报告</span>
      <div class="toolbar-actions">
        <el-button size="small" @click="load">
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
        placeholder="搜索测试单名称"
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
        start-placeholder="完成起"
        end-placeholder="完成止"
        @change="applyFilters"
      />
    </div>

    <el-card shadow="never" class="list-card">
      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        height="100%"
        class="report-table"
        @row-click="openDetail"
      >
        <el-table-column label="测试单" min-width="200">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="name" :title="row.name">{{ row.name }}</span>
              <span class="sub">{{ row.build_name || '无版本' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="执行人" prop="executor_name" width="100" show-overflow-tooltip />
        <el-table-column label="通过率" width="88" align="center">
          <template #default="{ row }">{{ row.pass_rate }}%</template>
        </el-table-column>
        <el-table-column label="结果" min-width="200">
          <template #default="{ row }">
            <div class="result-tags">
              <el-tag type="success" size="small">通过 {{ row.passed_count }}</el-tag>
              <el-tag type="danger" size="small">失败 {{ row.failed_count }}</el-tag>
              <el-tag type="warning" size="small">阻塞 {{ row.blocked_count }}</el-tag>
              <el-tag type="info" size="small">跳过 {{ row.skipped_count }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="92" align="center">
          <template #default="{ row }">
            <el-tag :type="runStatusType[row.status]" size="small">{{
              runStatusLabel[row.status]
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="完成时间" width="168">
          <template #default="{ row }">{{
            row.finished_at ? formatWallTime(row.finished_at) : formatTime(row.created_at)
          }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" class-name="report-actions-col">
          <template #default="{ row }">
            <div class="report-actions">
              <el-button link type="primary" @click.stop="openDetail(row)">详情</el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => doExport(row, cmd)" @click.stop>
                <el-button link type="primary" :loading="exportingRunId === row.id">下载</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="excel">Excel (.xlsx)</el-dropdown-item>
                    <el-dropdown-item command="word">Word (.docx)</el-dropdown-item>
                    <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
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
        @current-change="load"
        @size-change="onPageSizeChange"
      />
    </el-card>

    <el-drawer v-model="detailVisible" size="640px" destroy-on-close>
      <template #header>
        <div class="drawer-header">
          <span class="drawer-title">测试报告详情</span>
          <el-dropdown
            v-if="detailRun"
            split-button
            size="small"
            type="primary"
            :button-props="{ loading: exporting }"
            @click="doExport(detailRun, 'excel')"
            @command="(cmd: string) => doExport(detailRun!, cmd)"
          >
            下载报告
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="excel">Excel (.xlsx)</el-dropdown-item>
                <el-dropdown-item command="word">Word (.docx)</el-dropdown-item>
                <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
      <template v-if="detailRun">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="名称">{{ detailRun.name }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{
            detailRun.build_name || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="runStatusType[detailRun.status]" size="small">{{
              runStatusLabel[detailRun.status]
            }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="通过率">{{ detailRun.pass_rate }}%</el-descriptions-item>
          <el-descriptions-item label="执行人">{{
            detailRun.executor_name || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ runDurationText(detailRun) }}</el-descriptions-item>
          <el-descriptions-item label="开始">{{
            formatWallTime(detailRun.started_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="结束">{{
            formatWallTime(detailRun.finished_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="说明" :span="2">{{
            detailRun.description || '-'
          }}</el-descriptions-item>
        </el-descriptions>
        <el-table
          :data="detailRun.cases || []"
          stripe
          border
          size="small"
          class="detail-table"
          @row-click="openCaseDetail"
        >
          <el-table-column label="序号" width="64" align="center">
            <template #default="{ row }">{{ row.testcase_sort_order || '—' }}</template>
          </el-table-column>
          <el-table-column prop="case_title" label="用例" min-width="160" show-overflow-tooltip />
          <el-table-column label="结果" width="72">
            <template #default="{ row }">
              <el-tag :type="resultType[row.result]" size="small">{{
                resultLabel[row.result]
              }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="executor_name" label="执行人" width="88" />
        </el-table>
      </template>
    </el-drawer>

    <RunCaseDetailDrawer v-model="caseDetailVisible" :case-item="caseDetailRow" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { testExecutionApi } from '@/api'
import type { Schemas } from '@/api/types'
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { readWorkspaceRunId } from '@/composables/useWorkspaceQuery'
import {
  formatBeijingTime,
  formatBeijingWallClock,
  parseShanghaiNaiveDateTime,
} from '@/utils/datetime'
import type { DateInput } from '@/types/common'
import RunCaseDetailDrawer from '@/components/testexec/RunCaseDetailDrawer.vue'

type RunSummary = Schemas['ManualTestRunSummaryOut']
type RunDetail = Schemas['ManualTestRunDetailOut']
type RunCase = Schemas['ManualTestRunCaseOut']

const props = defineProps<{ projectId: number }>()

const STATUS_OPTIONS = [
  { value: 'finished', label: '已完成' },
  { value: 'running', label: '执行中' },
  { value: 'waiting', label: '待开始' },
]

const runStatusLabel: Record<string, string> = {
  waiting: '待开始',
  running: '执行中',
  finished: '已完成',
}
const runStatusType: Record<string, string> = {
  waiting: 'info',
  running: 'warning',
  finished: 'success',
}
const resultLabel: Record<string, string> = {
  pending: '待测',
  pass: '通过',
  fail: '失败',
  blocked: '阻塞',
  skip: '跳过',
}
const resultType: Record<string, string> = {
  pending: 'info',
  pass: 'success',
  fail: 'danger',
  blocked: 'warning',
  skip: '',
}

const loading = ref(false)
const items = ref<RunSummary[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterKeyword = ref('')
const statusFilter = ref<string | undefined>('finished')
const dateRange = ref<[string, string] | null>(null)
let keywordTimer: ReturnType<typeof setTimeout> | null = null

const detailVisible = ref(false)
const detailRun = ref<RunDetail | null>(null)
const caseDetailVisible = ref(false)
const caseDetailRow = ref<RunCase | null>(null)
const exporting = ref(false)
const exportingRunId = ref<number | null>(null)

const EXPORT_EXT: Record<string, string> = { excel: 'xlsx', word: 'docx', pdf: 'pdf' }

function formatTime(value: DateInput) {
  return formatBeijingTime(value)
}

function formatWallTime(value: DateInput) {
  return formatBeijingWallClock(value)
}

function runDurationText(run: RunDetail | null) {
  if (!run?.started_at || !run.finished_at) return '-'
  const start = parseShanghaiNaiveDateTime(run.started_at)?.getTime()
  const end = parseShanghaiNaiveDateTime(run.finished_at)?.getTime()
  if (start == null || end == null || Number.isNaN(start) || Number.isNaN(end) || end < start)
    return '-'
  const totalSec = Math.round((end - start) / 1000)
  if (totalSec < 60) return `${totalSec} 秒`
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return sec ? `${min} 分 ${sec} 秒` : `${min} 分`
}

function listParams() {
  const [dateFrom, dateTo] = dateRange.value ?? []
  return {
    page: page.value,
    page_size: pageSize.value,
    status: statusFilter.value || undefined,
    keyword: filterKeyword.value.trim() || undefined,
    date_from: dateFrom,
    date_to: dateTo,
  }
}

async function load() {
  if (!props.projectId) return
  loading.value = true
  try {
    const data = await testExecutionApi.listRunsPage(props.projectId, listParams())
    items.value = data.items
    total.value = data.total
    if (page.value > 1 && !data.items.length && data.total > 0) {
      page.value -= 1
      await load()
    }
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  void load()
}

function onKeywordInput() {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(applyFilters, 300)
}

function onPageSizeChange() {
  page.value = 1
  void load()
}

async function openDetail(row: RunSummary) {
  detailRun.value = await testExecutionApi.getRun(row.id)
  detailVisible.value = true
}

async function doExport(row: RunSummary | RunDetail, format: string) {
  const runId = row.id
  const runName = row.name
  if (exporting.value || exportingRunId.value != null) return
  if (detailRun.value?.id === runId) {
    exporting.value = true
  } else {
    exportingRunId.value = runId
  }
  try {
    const blob = await testExecutionApi.exportRun(runId, format)
    const name = `功能测试报告_${runName || 'report'}_${runId}.${EXPORT_EXT[format] || 'bin'}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    /* 全局响应拦截器已提示错误 */
  } finally {
    exporting.value = false
    exportingRunId.value = null
  }
}

function openCaseDetail(row: RunCase) {
  caseDetailRow.value = row
  caseDetailVisible.value = true
}

async function tryOpenFromHash() {
  const runId = readWorkspaceRunId()
  if (!runId) return
  try {
    detailRun.value = await testExecutionApi.getRun(runId)
    detailVisible.value = true
  } catch {
    /* 无效 run 参数忽略 */
  }
}

watch(
  () => props.projectId,
  () => {
    page.value = 1
    void load().then(() => tryOpenFromHash())
  },
  { immediate: true },
)
</script>

<style scoped>
.func-reports {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ax-gap-sm);
  padding: var(--ax-space-3) var(--ax-space-4);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
}

.title {
  font-weight: 600;
  font-size: var(--ax-text-body-size);
  color: var(--ax-text);
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-gap-sm);
  flex: none;
}

.search {
  width: 220px;
}

.status-select {
  width: 120px;
}

.list-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.list-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.report-table {
  flex: 1;
  min-height: 0;
}

.pagination {
  margin-top: var(--ax-space-2);
  justify-content: flex-end;
  flex: none;
}

.name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sub {
  font-size: 12px;
  color: var(--ax-text-secondary);
}

.result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.report-actions {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: var(--ax-space-2);
  white-space: nowrap;
}

.report-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.list-card :deep(.report-actions-col .cell) {
  overflow: visible;
}

.detail-table {
  margin-top: var(--ax-space-3);
  cursor: pointer;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-gap-sm);
  width: 100%;
}

.drawer-title {
  font-weight: 600;
  font-size: var(--ax-text-body-size);
  color: var(--ax-text);
}
</style>
