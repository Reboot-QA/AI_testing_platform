<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
      <span class="text-xs text-muted-foreground"
        >仅展示最近一次运行批次（如「全部运行」）；相邻间隔超过 2 分钟视为上一轮</span
      >
      <el-button size="small" @click="load">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>
    <div class="min-h-0 flex-1 overflow-auto">
      <el-table
        v-if="rows.length"
        :data="pagedRows"
        size="small"
        border
        class="report-rows"
        @row-click="openDetail"
      >
        <el-table-column prop="target_name" label="用例" min-width="180" />
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
        <el-table-column label="通过率" width="120">
          <template #default="{ row }">
            {{ row.pass_rate != null ? row.pass_rate + '%' : '-' }}
            <span class="ml-1 text-xs text-muted-foreground"
              >({{ row.passed_count }}/{{ row.total_count }})</span
            >
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="90">
          <template #default="{ row }">{{
            row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-'
          }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="72" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="该接口的用例暂无运行记录" :image-size="60" />
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
    >
      <RunReportDetail
        v-if="detail"
        :detail="detail"
        :environment-name="envName(detail.environment_id)"
      >
        <RunStepGroups :detail="detail" />
      </RunReportDetail>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { formatTime, statusLabel, statusTag } from '@/utils/runFormat'
import RunReportDetail from '@/components/apifox/run/RunReportDetail.vue'
import RunStepGroups from '@/components/apifox/run/RunStepGroups.vue'

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

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return rows.value.slice(start, start + pageSize.value)
})

function onPageSizeChange() {
  page.value = 1
}

const envName = (id: number | null | undefined) =>
  id == null ? '-' : store.environments.find((e) => e.id === id)?.name || '-'

async function load() {
  rows.value = await apifoxApi.listEndpointRuns(props.endpointId)
  page.value = 1
}

async function openDetail(row: Schemas['RunBrief']) {
  detail.value = await apifoxApi.getRun(row.id)
  drawerVisible.value = true
}

watch(() => props.endpointId, load, { immediate: true })
</script>

<style scoped>
.report-rows :deep(.el-table__body tr) {
  cursor: pointer;
}

.report-pager {
  flex: none;
  margin-top: var(--ax-space-2);
  justify-content: flex-end;
}

.run-report-drawer :deep(.el-drawer__body) {
  padding: var(--ax-space-4);
}
</style>
