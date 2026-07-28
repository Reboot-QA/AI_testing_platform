<template>
  <el-drawer
    v-model="drawerVisible"
    :show-close="true"
    :with-header="false"
    size="65%"
    class="run-report-drawer"
    @closed="onDrawerClosed"
  >
    <template v-if="displayDetail">
      <RunReportDetail
        :detail="displayDetail"
        :environment-name="environmentName"
        :running="displayRunning"
      >
        <template v-if="childDetail" #actions>
          <el-button link type="primary" @click="backToSuite">← 返回套件报告</el-button>
        </template>

        <template v-if="!childDetail">
          <el-table
            :data="suiteDetail?.children || []"
            size="small"
            border
            highlight-current-row
            @row-click="openChild"
          >
            <el-table-column label="套件项" min-width="200">
              <template #default="{ row }">
                <el-tag size="small" :type="targetTag(row.target_type)">
                  {{ targetTypeLabel(row.target_type) }}
                </el-tag>
                {{ row.target_name }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="statusTag(row.status)">
                  {{ statusLabel(row.status) }}
                </el-tag>
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
          </el-table>
        </template>
        <RunStepGroups v-else :detail="childDetail" :live="childLive" />
      </RunReportDetail>
    </template>
    <el-empty v-else description="加载中…" />
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useRunReportDrawer } from '@/composables/useRunReportDrawer'
import { statusLabel, statusTag } from '@/utils/runFormat'
import RunReportDetail from '@/components/apifox/run/RunReportDetail.vue'
import RunStepGroups from '@/components/apifox/run/RunStepGroups.vue'

interface SuiteRunStartEvent {
  type: 'suite_start'
  run_id?: number
}

type SuiteRunEvent = SuiteRunStartEvent | Record<string, unknown>

const props = withDefaults(
  defineProps<{
    events?: SuiteRunEvent[]
    running?: boolean
  }>(),
  {
    events: () => [],
    running: false,
  },
)
defineEmits<{ clear: [] }>()

const store = useWorkspaceStore()
const childDetail = ref<Schemas['RunOut'] | null>(null)
const activeChildId = ref<number | null>(null)
const childManual = ref(false)
let childPollTimer: ReturnType<typeof setInterval> | null = null

const runId = computed(() => {
  const start = props.events.find((e): e is SuiteRunStartEvent => e.type === 'suite_start')
  return start?.run_id
})

const {
  drawerVisible,
  detail: suiteDetail,
  refreshReport,
  onDrawerClosed,
} = useRunReportDrawer({
  runId,
  running: computed(() => props.running),
  eventsLength: computed(() => props.events.length),
})

const environmentName = computed(() => {
  const id = (childDetail.value || suiteDetail.value)?.environment_id
  if (id == null) return '-'
  return store.environments.find((e) => e.id === id)?.name || '-'
})

const displayDetail = computed(() => childDetail.value || suiteDetail.value)
const childLive = computed(
  () => props.running && (childDetail.value?.status === 'running' || !childDetail.value),
)
const displayRunning = computed(
  () => props.running || displayDetail.value?.status === 'running' || childLive.value,
)

const targetTypeLabel = (t: string) => (t === 'scenario' ? '场景' : '用例')
const targetTag = (t: string) => (t === 'scenario' ? 'info' : 'success')

async function refreshChild() {
  if (!activeChildId.value) return
  try {
    childDetail.value = await apifoxApi.getRun(activeChildId.value)
  } catch {
    /* 轮询单次失败忽略 */
  }
}

function startChildPolling() {
  if (childPollTimer) clearInterval(childPollTimer)
  childPollTimer = setInterval(refreshChild, 1200)
}

function stopChildPolling() {
  if (childPollTimer) {
    clearInterval(childPollTimer)
    childPollTimer = null
  }
}

async function openChild(row: Schemas['RunBrief']) {
  childManual.value = true
  activeChildId.value = row.id
  await refreshChild()
  if (row.status === 'running') startChildPolling()
  else stopChildPolling()
}

function backToSuite() {
  childManual.value = false
  activeChildId.value = null
  childDetail.value = null
  stopChildPolling()
}

function followRunningChild() {
  if (!props.running || childManual.value) return
  const runningChild = suiteDetail.value?.children?.find((c) => c.status === 'running')
  if (!runningChild) return
  if (activeChildId.value === runningChild.id) return
  activeChildId.value = runningChild.id
  void refreshChild()
  startChildPolling()
}

watch(suiteDetail, () => followRunningChild())

watch(
  () => props.running,
  (active) => {
    if (active) {
      followRunningChild()
    } else {
      stopChildPolling()
      childManual.value = false
      activeChildId.value = null
      childDetail.value = null
    }
  },
)

watch(
  () => props.events.some((e) => e.type === 'suite_done'),
  (done) => {
    if (done && runId.value) void refreshReport()
  },
)

watch(runId, (rid, prev) => {
  if (prev && prev !== rid) {
    backToSuite()
  }
})

onBeforeUnmount(stopChildPolling)
</script>

<style scoped>
.run-report-drawer :deep(.el-drawer__body) {
  padding: var(--ax-space-4);
}
</style>
