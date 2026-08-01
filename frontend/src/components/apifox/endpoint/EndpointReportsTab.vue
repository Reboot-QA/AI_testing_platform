<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <div class="mb-1.5 flex flex-wrap items-center justify-between gap-2">
      <span class="text-xs text-muted-foreground"
        >每次「全部运行」生成一条批次报告；点击查看该次所有用例执行情况</span
      >
      <div class="flex items-center gap-2">
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
        <el-button size="small" @click="load">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>
    <div class="min-h-0 flex-1 overflow-auto">
      <el-table
        v-if="rows.length"
        ref="tableRef"
        :data="pagedRows"
        row-key="id"
        size="small"
        border
        class="report-rows"
        @row-click="openDetail"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="目标" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="target-cell">
              <MethodTag
                v-if="parseTarget(row.target_name).method"
                :method="parseTarget(row.target_name).method"
                :class="{ 'target-method--post': parseTarget(row.target_name).method === 'POST' }"
              />
              <span class="target-path">{{ parseTarget(row.target_name).path }}</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="环境" width="110">
          <template #default="{ row }">{{ envName(row.environment_id) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status)">{{
              statusLabel(row.status)
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="用例通过" width="120">
          <template #default="{ row }">
            {{ row.passed_count }}/{{ row.total_count }}
            <span v-if="row.pass_rate != null" class="ml-1 text-xs text-muted-foreground">
              ({{ row.pass_rate }}%)
            </span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="90">
          <template #default="{ row }">{{
            row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-'
          }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="执行人" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.triggered_by || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openDetail(row)">查看</el-button>
            <el-popconfirm title="确认删除该报告？" @confirm="removeRun(row)">
              <template #reference>
                <el-button link type="danger" @click.stop>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无批次报告，可点击「全部运行」生成" :image-size="60" />
    </div>

    <el-pagination
      v-if="rows.length"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      class="report-pager"
      background
      small
      layout="total, sizes, prev, pager, next"
      :page-sizes="[10, 20, 50, 100]"
      :total="rows.length"
      @size-change="onPageSizeChange"
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
        :environment-name="detail ? envName(detail.environment_id) : '-'"
        :exporting="false"
        :show-export="false"
        :child-search-placeholder="childSearchPlaceholder"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import RunReportDetailPanel from '@/components/apifox/run/RunReportDetailPanel.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TableInstance } from 'element-plus'
import { useWorkspaceStore } from '@/stores/workspace'
import { formatTime, statusLabel, statusTag } from '@/utils/runFormat'
import { RUN_LIST_SEARCH_CASE, RUN_LIST_SEARCH_SUITE } from '@/utils/runReportList'

const props = defineProps<{
  endpointId: Id
  projectId: Id
}>()

const store = useWorkspaceStore()
const rows = ref<Schemas['RunBrief'][]>([])
const page = ref(1)
const pageSize = ref(20)
const detail = ref<Schemas['RunOut'] | null>(null)
const drawerVisible = ref(false)
const selectedIds = ref<number[]>([])
const batchDeleting = ref(false)
const tableRef = ref<TableInstance>()

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return rows.value.slice(start, start + pageSize.value)
})

const childSearchPlaceholder = computed(() =>
  detail.value?.target_type === 'endpoint' ? RUN_LIST_SEARCH_CASE : RUN_LIST_SEARCH_SUITE,
)

function onPageSizeChange() {
  page.value = 1
}

const envName = (id: number | null | undefined) =>
  id == null ? '—' : store.environments.find((e) => e.id === id)?.name || '—'

const HTTP_METHODS = new Set(['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE'])

function parseTarget(name: string) {
  const trimmed = (name || '').trim()
  const space = trimmed.indexOf(' ')
  if (space <= 0) return { method: '', path: trimmed }
  const method = trimmed.slice(0, space).toUpperCase()
  if (!HTTP_METHODS.has(method)) return { method: '', path: trimmed }
  return { method, path: trimmed.slice(space + 1) }
}

async function load() {
  rows.value = await apifoxApi.listEndpointRuns(props.endpointId)
  page.value = 1
}

async function openDetail(row: Schemas['RunBrief']) {
  detail.value = await apifoxApi.getRun(row.id)
  drawerVisible.value = true
}

function handleSelectionChange(selection: Schemas['RunBrief'][]) {
  selectedIds.value = selection.map((row) => row.id)
}

function closeDetailIfDeleted(runIds: number[]) {
  if (detail.value && runIds.includes(detail.value.id)) {
    drawerVisible.value = false
    detail.value = null
  }
}

async function removeRun(row: Schemas['RunBrief']) {
  await apifoxApi.deleteRun(row.id)
  ElMessage.success('已删除')
  closeDetailIfDeleted([row.id])
  tableRef.value?.clearSelection()
  selectedIds.value = selectedIds.value.filter((id) => id !== row.id)
  await load()
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
    const res = await apifoxApi.batchDeleteRuns(props.projectId, selectedIds.value)
    closeDetailIfDeleted(selectedIds.value)
    tableRef.value?.clearSelection()
    selectedIds.value = []
    if (res.failed > 0) {
      ElMessage.warning(`已删除 ${res.succeeded} 条，${res.failed} 条失败`)
    } else {
      ElMessage.success(`已删除 ${res.succeeded} 条`)
    }
    await load()
  } finally {
    batchDeleting.value = false
  }
}

function onDrawerClosed() {
  detail.value = null
}

watch(() => props.endpointId, load, { immediate: true })

defineExpose({ load })
</script>

<style scoped>
.report-rows :deep(.el-table__body tr) {
  cursor: pointer;
}

.report-rows :deep(.el-table__cell) {
  padding: 5px 8px;
}

.report-rows :deep(.el-table__body td .cell) {
  white-space: nowrap;
}

.target-cell {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1);
  max-width: 100%;
  vertical-align: middle;
}

.target-method--post :deep(.method-tag) {
  color: var(--color-green-6) !important;
}

.target-path {
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-pager {
  flex: none;
  margin-top: var(--ax-space-1);
  justify-content: flex-end;
}

.run-report-drawer :deep(.el-drawer__body) {
  padding: var(--ax-space-4);
}
</style>
