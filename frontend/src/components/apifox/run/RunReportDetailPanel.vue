<template>
  <RunReportDetail
    v-if="detail"
    :detail="detail"
    :environment-name="environmentName"
    :running="detail.status === 'running'"
  >
    <template #actions>
      <el-button v-if="parentDetail" link type="primary" @click="emit('backToParent')">
        ← 返回套件报告
      </el-button>
      <el-dropdown
        split-button
        size="small"
        type="primary"
        :button-props="{ loading: exporting }"
        @click="emit('export', 'excel')"
        @command="(cmd: string) => emit('export', cmd)"
      >
        导出报告
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="excel">Excel (.xlsx)</el-dropdown-item>
            <el-dropdown-item command="word">Word (.docx)</el-dropdown-item>
            <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
            <el-dropdown-item command="json">JSON (.json)</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </template>

    <el-table
      v-if="isSuite"
      :data="detail.children"
      size="small"
      border
      @row-click="(row: Schemas['RunBrief']) => emit('openChild', row)"
    >
      <el-table-column label="套件项" min-width="200">
        <template #default="{ row }">
          <el-tag size="small" :type="targetTag(row.target_type)">{{
            targetTypeLabel(row.target_type)
          }}</el-tag>
          {{ row.target_name }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="通过率" width="110">
        <template #default="{ row }">
          {{ row.pass_rate != null ? row.pass_rate + '%' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="90">
        <template #default="{ row }">{{
          row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-'
        }}</template>
      </el-table-column>
    </el-table>

    <RunStepGroups v-else :detail="detail" />
  </RunReportDetail>
</template>

<script setup lang="ts">
import type { Schemas } from '@/api/types'
import RunReportDetail from '@/components/apifox/run/RunReportDetail.vue'
import RunStepGroups from '@/components/apifox/run/RunStepGroups.vue'
import { statusLabel, statusTag } from '@/utils/runFormat'

defineProps<{
  detail: Schemas['RunOut'] | null
  parentDetail: Schemas['RunOut'] | null
  environmentName: string
  exporting: boolean
  isSuite: boolean
}>()

const emit = defineEmits<{
  backToParent: []
  export: [format: string]
  openChild: [row: Schemas['RunBrief']]
}>()

const targetTypeLabel = (t: string) => (t === 'scenario' ? '场景' : t === 'suite' ? '套件' : '用例')
const targetTag = (t: string) => (t === 'scenario' ? 'info' : t === 'suite' ? 'primary' : 'success')
</script>
