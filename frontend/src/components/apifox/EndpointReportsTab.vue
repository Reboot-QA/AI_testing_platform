<template>
  <div class="reports-tab">
    <div class="bar">
      <span class="hint">该接口用例的运行记录（在「测试用例」里运行用例后产生）</span>
      <el-button size="small" @click="load"
        ><el-icon><Refresh /></el-icon> 刷新</el-button
      >
    </div>
    <el-table v-if="rows.length" :data="rows" size="small" border>
      <el-table-column prop="target_name" label="用例" min-width="180" />
      <el-table-column label="环境" width="110">
        <template #default="{ row }">{{ envName(row.environment_id) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="通过率" width="120">
        <template #default="{ row }">
          {{ row.pass_rate != null ? row.pass_rate + '%' : '-' }}
          <span class="sub">({{ row.passed_count }}/{{ row.total_count }})</span>
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
    </el-table>
    <el-empty v-else description="该接口的用例暂无运行记录" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { formatTime, statusLabel, statusTag } from '@/utils/runFormat'

const props = defineProps<{
  endpointId: Id
  projectId: Id
}>()

const store = useWorkspaceStore()
const rows = ref<Schemas['RunBrief'][]>([])

const envName = (id: number | null | undefined) =>
  id == null ? '-' : store.environments.find((e) => e.id === id)?.name || '-'

async function load() {
  // 后端按接口的用例精确过滤，不受项目级「最近 100 条」窗口影响（评审#1）
  rows.value = await apifoxApi.listEndpointRuns(props.endpointId)
}

watch(() => props.endpointId, load, { immediate: true })
</script>

<style scoped>
.reports-tab {
  height: 100%;
  overflow: auto;
}

.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.hint {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}

.sub {
  color: var(--ax-text-placeholder);
  font-size: 12px;
  margin-left: 4px;
}
</style>
