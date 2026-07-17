<template>
  <div v-if="events.length" class="run-progress">
    <div class="rp-head">
      <span>运行进度</span>
      <el-tag v-if="running" size="small" type="warning">执行中…</el-tag>
      <el-tag
        v-else-if="doneEvent"
        size="small"
        :type="doneEvent.status === 'passed' ? 'success' : 'danger'"
      >
        {{ doneEvent.status === 'passed' ? '通过' : '失败' }} · 通过率 {{ doneEvent.pass_rate }}% ·
        {{ Math.round(doneEvent.duration_ms || 0) }}ms
      </el-tag>
      <el-tag v-else-if="errorEvent" size="small" type="danger">错误</el-tag>
      <el-button v-if="runId" link type="primary" size="small" @click="viewReport">
        查看测试报告
      </el-button>
      <el-button link size="small" @click="$emit('clear')">收起</el-button>
    </div>

    <template v-for="(g, gi) in stepGroups" :key="gi">
      <div v-if="g.label" class="rp-group">{{ g.label }}</div>
      <div v-for="(s, i) in g.steps" :key="gi + '-' + i" class="rp-step">
        <el-icon v-if="s.status === 'passed'" color="var(--ax-success)"><CircleCheck /></el-icon>
        <el-icon v-else color="var(--ax-danger)"><CircleClose /></el-icon>
        <span class="rp-name">{{ s.index }}/{{ s.total }} {{ s.case_name }}</span>
        <span v-if="s.response_status" class="rp-meta">{{ s.response_status }}</span>
        <span v-if="s.duration_ms != null" class="rp-meta">{{ Math.round(s.duration_ms) }}ms</span>
        <span v-if="s.error_message" class="rp-err">{{ s.error_message }}</span>
      </div>
    </template>

    <div v-if="errorEvent" class="rp-err-line">{{ errorEvent.message }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { iterationLabel } from '@/utils/iterationLabel'

interface RunProgressStepEvent {
  type: 'step'
  iteration?: number
  index?: number
  total?: number
  case_name?: string
  status?: string
  response_status?: number
  duration_ms?: number | null
  error_message?: string | null
}

interface RunProgressStartEvent {
  type: 'start'
  run_id?: number
  iterations?: Record<string, unknown>[]
}

interface RunProgressDoneEvent {
  type: 'done'
  status?: string
  pass_rate?: number
  duration_ms?: number | null
}

interface RunProgressErrorEvent {
  type: 'error'
  message?: string
}

type RunProgressEvent =
  | RunProgressStepEvent
  | RunProgressStartEvent
  | RunProgressDoneEvent
  | RunProgressErrorEvent
  | Record<string, unknown>

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

const route = useRoute()
const router = useRouter()

// 本次运行的 run_id（start 事件携带）；有则可跳转到「测试报告」定位该次报告
const runId = computed(() => props.events.find((e) => e.type === 'start')?.run_id as number | undefined)
function viewReport() {
  if (!runId.value) return
  router.push(`/apifox/project/${route.params.projectId}/reports?run=${runId.value}`)
}

const stepEvents = computed(() =>
  props.events.filter((e): e is RunProgressStepEvent => e.type === 'step'),
)
const doneEvent = computed(() =>
  props.events.find((e): e is RunProgressDoneEvent => e.type === 'done'),
)
const errorEvent = computed(() =>
  props.events.find((e): e is RunProgressErrorEvent => e.type === 'error'),
)

// 数据驱动/循环多轮：start 事件带 iterations 时按轮次分组展示；单轮为一组无标题（零视觉变化）
const iterations = computed(
  () => (props.events.find((e) => e.type === 'start') as RunProgressStartEvent | undefined)?.iterations || [],
)
const stepGroups = computed(() => {
  if (iterations.value.length <= 1) return [{ label: '', steps: stepEvents.value }]
  return iterations.value.map((data, i) => ({
    label: iterationLabel(i, data),
    steps: stepEvents.value.filter((s) => s.iteration === i),
  }))
})
</script>

<style scoped>
.run-progress {
  margin-top: 12px;
  border: 1px solid var(--ax-border);
  border-radius: 6px;
  padding: 10px 12px;
  background: var(--ax-bg-subtle);
}

.rp-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 8px;
}

.rp-group {
  font-weight: 600;
  color: var(--ax-brand);
  font-size: 12px;
  margin: 8px 0 2px;
  padding-top: 6px;
  border-top: 1px dashed var(--ax-border);
}

.rp-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 13px;
}

.rp-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rp-meta {
  color: var(--ax-text-secondary);
  font-size: 12px;
}

.rp-err {
  color: var(--ax-danger);
  font-size: 12px;
  max-width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rp-err-line {
  color: var(--ax-danger);
  font-size: 13px;
  margin-top: 6px;
}
</style>
