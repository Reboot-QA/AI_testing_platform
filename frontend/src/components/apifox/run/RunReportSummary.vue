<template>
  <div class="run-summary">
    <div class="run-summary__hero">
      <div class="donut-wrap">
        <div class="donut" :style="{ background: donutBg }">
          <div class="donut-hole">
            <span class="donut-label">{{ isRunning ? '进度' : '已完成' }}</span>
            <span class="donut-num">{{
              isRunning ? `${totalDone}/${totalTarget}` : totalDone
            }}</span>
          </div>
        </div>
      </div>

      <div class="status-list">
        <div v-for="row in statusRows" :key="row.key" class="status-row">
          <span class="status-dot" :class="`status-dot--${row.key}`" />
          <span class="status-name">{{ row.label }}</span>
          <span class="status-count">{{ row.count }}</span>
          <span class="status-pct">{{ row.percent }}</span>
        </div>
      </div>

      <div class="metrics-panel">
        <div class="metric">
          <span class="metric-label">总耗时</span>
          <span class="metric-val">{{ formatReportDuration(displayDurationMs) }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">接口请求耗时</span>
          <span class="metric-val metric-val--accent">{{
            formatReportDuration(stats.requestTimeMs)
          }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">平均接口请求耗时</span>
          <span class="metric-val metric-val--accent">{{
            formatReportDuration(stats.avgRequestMs)
          }}</span>
        </div>
        <div class="metric-grid">
          <div class="metric-sub">
            <span class="metric-sub-label">循环数</span>
            <span class="metric-sub-row">
              <span>执行: {{ loopStats.executed }}</span>
              <span class="metric-fail">失败: {{ loopStats.failed }}</span>
            </span>
          </div>
          <div class="metric-sub">
            <span class="metric-sub-label">断言数</span>
            <span class="metric-sub-row">
              <span>执行: {{ stats.assertionTotal }}</span>
              <span class="metric-fail">失败: {{ stats.assertionFailed }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="run-summary__footer">
      <span>开始 {{ formatTime(detail.started_at) }}</span>
      <span>结束 {{ isRunning ? '执行中…' : formatTime(detail.finished_at) }}</span>
      <span v-if="detail.triggered_by">触发 {{ detail.triggered_by }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { Schemas } from '@/api/types'
import { formatTime } from '@/utils/runFormat'
import { computeRunStepStats, formatReportDuration, pct } from '@/utils/runReportStats'

const props = withDefaults(defineProps<{ detail: Schemas['RunOut']; running?: boolean }>(), {
  running: false,
})

const steps = computed(() => props.detail.steps || [])
const stats = computed(() => computeRunStepStats(steps.value))
const isRunning = computed(() => props.running || props.detail.status === 'running')

const passed = computed(() => {
  if (isRunning.value) return steps.value.filter((s) => s.status === 'passed').length
  return props.detail.passed_count ?? 0
})
const failed = computed(() => {
  if (isRunning.value) return steps.value.filter((s) => s.status !== 'passed').length
  return props.detail.failed_count ?? 0
})
const totalDone = computed(() => {
  if (isRunning.value) return steps.value.length
  return props.detail.total_count ?? passed.value + failed.value
})
const totalTarget = computed(() => props.detail.total_count ?? totalDone.value)

const nowTick = ref(Date.now())
let tickTimer: ReturnType<typeof setInterval> | null = null

watch(
  isRunning,
  (active) => {
    if (active) {
      tickTimer = setInterval(() => {
        nowTick.value = Date.now()
      }, 1000)
    } else if (tickTimer) {
      clearInterval(tickTimer)
      tickTimer = null
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (tickTimer) clearInterval(tickTimer)
})

const displayDurationMs = computed(() => {
  if (!isRunning.value) return props.detail.duration_ms
  const start = props.detail.started_at ? new Date(props.detail.started_at).getTime() : 0
  if (!start) return props.detail.duration_ms
  return Math.max(0, nowTick.value - start)
})

const statusRows = computed(() => [
  {
    key: 'passed',
    label: '通过',
    count: passed.value,
    percent: pct(passed.value, totalTarget.value),
  },
  {
    key: 'failed',
    label: '失败',
    count: failed.value,
    percent: pct(failed.value, totalTarget.value),
  },
])

const loopStats = computed(() => {
  const steps = props.detail.steps || []
  // 优先用 loop_round 统计内层循环(loop)的实际轮数；无 loop 步骤时回退到 iteration（数据驱动分组）
  const loopRounds = new Set(steps.filter((s) => (s.loop_round ?? 0) > 0).map((s) => s.loop_round))
  const key = loopRounds.size > 0 ? 'loop_round' : 'iteration'
  const idSet = loopRounds.size > 0 ? loopRounds : new Set(steps.map((s) => s.iteration ?? 0))
  const executed = idSet.size || (totalDone.value > 0 ? 1 : 0)
  let failed = 0
  for (const id of idSet) {
    if (steps.some((s) => (s[key] ?? 0) === id && s.status !== 'passed')) {
      failed += 1
    }
  }
  return { executed, failed }
})

const donutBg = computed(() => {
  const total = totalTarget.value || 1
  const okDeg = (passed.value / total) * 360
  const failDeg = (failed.value / total) * 360
  const failColor = 'var(--color-pink-6)'
  const okColor = 'var(--ax-success)'
  const pendingColor = 'color-mix(in srgb, var(--ax-border) 80%, white)'
  if (!isRunning.value && failed.value === 0 && passed.value >= total) return okColor
  if (!isRunning.value && passed.value === 0 && failed.value >= total) return failColor
  if (isRunning.value || passed.value + failed.value < total) {
    return `conic-gradient(${okColor} 0deg ${okDeg}deg, ${failColor} ${okDeg}deg ${okDeg + failDeg}deg, ${pendingColor} ${okDeg + failDeg}deg 360deg)`
  }
  return `conic-gradient(${okColor} 0deg ${okDeg}deg, ${failColor} ${okDeg}deg 360deg)`
})
</script>

<style scoped>
.run-summary {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg);
  margin-bottom: var(--ax-space-4);
  overflow: hidden;
}

.run-summary__hero {
  display: grid;
  grid-template-columns: auto 1fr 1.2fr;
  gap: var(--ax-space-5);
  padding: var(--ax-space-4) var(--ax-space-5);
  align-items: center;
}

.donut-wrap {
  display: flex;
  justify-content: center;
}

.donut {
  width: 132px;
  height: 132px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.donut-hole {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: var(--ax-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 0 1px var(--ax-border);
}

.donut-label {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
}

.donut-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--ax-text);
  line-height: 1.1;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
  min-width: 160px;
}

.status-row {
  display: grid;
  grid-template-columns: 10px 1fr auto auto;
  align-items: center;
  gap: var(--ax-space-2);
  font-size: var(--ax-font-sm);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot--passed {
  background: var(--ax-success);
}

.status-dot--failed {
  background: var(--color-pink-6);
}

.status-name {
  color: var(--ax-text-secondary);
}

.status-count {
  font-weight: 600;
  color: var(--ax-text);
  min-width: 36px;
  text-align: right;
}

.status-pct {
  color: var(--ax-text-secondary);
  min-width: 52px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.metrics-panel {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
  padding: var(--ax-space-3);
  border-radius: var(--ax-radius-sm);
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
}

.metric {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--ax-space-2);
}

.metric-label {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.metric-val {
  font-size: var(--ax-font);
  font-weight: 600;
  color: var(--ax-text);
  font-variant-numeric: tabular-nums;
}

.metric-val--accent {
  color: var(--ax-success);
}

.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ax-space-3);
  margin-top: var(--ax-space-1);
  padding-top: var(--ax-space-2);
  border-top: 1px dashed var(--ax-border);
}

.metric-sub-label {
  display: block;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  margin-bottom: 4px;
}

.metric-sub-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
}

.metric-fail {
  color: var(--color-pink-6);
}

.run-summary__footer {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-space-2) var(--ax-space-4);
  padding: var(--ax-space-2) var(--ax-space-5);
  border-top: 1px solid var(--ax-border);
  background: var(--ax-bg-subtle);
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
}

@media (max-width: 960px) {
  .run-summary__hero {
    grid-template-columns: 1fr;
  }
}
</style>
