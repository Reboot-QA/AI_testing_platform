<template>
  <el-drawer
    v-model="drawerVisible"
    :show-close="true"
    :with-header="false"
    size="65%"
    class="run-report-drawer"
    @closed="onDrawerClosed"
  >
    <template v-if="detail">
      <RunReportDetail :detail="detail" :environment-name="environmentName" :running="running">
        <RunStepGroups :detail="detail" :live="running" />
      </RunReportDetail>
    </template>
    <el-empty v-else description="加载中…" />
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { Schemas } from '@/api/types'
import { useWorkspaceStore } from '@/stores/workspace'
import { useRunReportDrawer } from '@/composables/useRunReportDrawer'
import RunReportDetail from '@/components/apifox/run/RunReportDetail.vue'
import RunStepGroups from '@/components/apifox/run/RunStepGroups.vue'

interface RunProgressStartEvent {
  type: 'start'
  run_id?: number
}

type RunProgressEvent = RunProgressStartEvent | Record<string, unknown>

const props = withDefaults(
  defineProps<{
    events?: RunProgressEvent[]
    running?: boolean
  }>(),
  {
    events: () => [],
    running: false,
  },
)
defineEmits<{ clear: [] }>()

const store = useWorkspaceStore()

const environmentName = computed(() => {
  const id = detail.value?.environment_id
  if (id == null) return '-'
  return store.environments.find((e) => e.id === id)?.name || '-'
})

const runId = computed(() => {
  const start = props.events.find((e): e is RunProgressStartEvent => e.type === 'start')
  return start?.run_id
})

const { drawerVisible, detail, refreshReport, onDrawerClosed } = useRunReportDrawer({
  runId,
  running: computed(() => props.running),
  eventsLength: computed(() => props.events.length),
})

watch(
  () => props.events.some((e) => e.type === 'done'),
  (done) => {
    if (done && runId.value) void refreshReport()
  },
)
</script>

<style scoped>
.run-report-drawer :deep(.el-drawer__body) {
  padding: var(--ax-space-4);
}
</style>
