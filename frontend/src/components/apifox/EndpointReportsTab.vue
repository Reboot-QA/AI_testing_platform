<template>
  <div class="reports-tab">
    <div class="bar">
      <span class="hint">该接口用例的运行记录（在「测试用例」里运行用例后产生）</span>
      <el-button size="small" @click="load"><el-icon><Refresh /></el-icon> 刷新</el-button>
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
        <template #default="{ row }">{{ row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-' }}</template>
      </el-table-column>
      <el-table-column label="时间" min-width="170">
        <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="该接口的用例暂无运行记录" :image-size="60" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps({
  endpointId: { type: [String, Number], required: true },
  projectId: { type: [String, Number], required: true },
})

const store = useWorkspaceStore()
const rows = ref([])

const statusLabel = (s) => ({ running: '执行中', passed: '通过', failed: '失败' }[s] || s)
const statusTag = (s) => ({ running: 'warning', passed: 'success', failed: 'danger' }[s] || 'info')
const envName = (id) => (id == null ? '-' : store.environments.find((e) => e.id === id)?.name || '-')
const formatTime = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-')

async function load() {
  const cases = await apifoxApi.listCases(props.endpointId)
  const caseIds = new Set(cases.map((c) => c.id))
  const runs = await apifoxApi.listRuns(props.projectId)
  // 仅本接口用例的运行（用例级 run：target_type=case 且 target_id 属于本接口）
  rows.value = runs.filter((r) => r.target_type === 'case' && caseIds.has(r.target_id))
}

watch(() => props.endpointId, load, { immediate: true })
</script>

<style scoped>
.reports-tab {
  height: calc(100vh - 360px);
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
