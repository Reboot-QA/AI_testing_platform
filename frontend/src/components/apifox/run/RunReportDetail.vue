<template>
  <div class="run-report-detail">
    <div class="report-topbar">
      <div class="report-topbar__info">
        <el-tag size="small" type="info" effect="plain">{{ environmentName || '未选环境' }}</el-tag>
        <span class="report-topbar__title">{{ detail.target_name }}</span>
        <el-tag v-if="targetTypeLabel" size="small">{{ targetTypeLabel }}</el-tag>
        <el-tag v-if="running || detail.status === 'running'" size="small" type="warning">
          执行中…
        </el-tag>
      </div>
      <div class="report-topbar__actions">
        <slot name="actions" />
      </div>
    </div>

    <RunReportSummary :detail="detail" :running="running || detail.status === 'running'" />
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Schemas } from '@/api/types'
import RunReportSummary from '@/components/apifox/run/RunReportSummary.vue'

const props = defineProps<{
  detail: Schemas['RunOut']
  environmentName?: string
  running?: boolean
}>()

const TARGET_LABELS: Record<string, string> = {
  case: '用例',
  scenario: '场景',
  suite: '套件',
}

const targetTypeLabel = computed(() => TARGET_LABELS[props.detail.target_type] || '')
</script>

<style scoped>
.run-report-detail {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.report-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-3);
  margin-bottom: var(--ax-space-4);
  flex-wrap: wrap;
}

.report-topbar__info {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  min-width: 0;
}

.report-topbar__title {
  font-size: var(--ax-font-lg);
  font-weight: 600;
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-topbar__actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  flex-shrink: 0;
}
</style>
