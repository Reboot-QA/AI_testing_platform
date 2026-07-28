<template>
  <div class="step-groups">
    <div class="list-toolbar">
      <div class="filter-tabs">
        <button
          v-for="tab in filterTabs"
          :key="tab.value"
          type="button"
          class="filter-tab"
          :class="{ active: stepFilter === tab.value }"
          @click="stepFilter = tab.value"
        >
          {{ tab.label }} ({{ tab.count }})
        </button>
      </div>
      <el-input
        v-model="keyword"
        :maxlength="SEARCH_MAX_LEN"
        class="search-input"
        size="small"
        clearable
        placeholder="搜索步骤名称或路径"
        :prefix-icon="Search"
      />
    </div>

    <el-empty v-if="visibleSteps.length === 0" :description="emptyHint" :image-size="64" />

    <div v-for="(g, gi) in visibleGroups" :key="gi" class="step-group">
      <div v-if="g.label" class="group-title">{{ g.label }}</div>
      <div class="step-list">
        <template v-for="s in g.steps" :key="s.id">
          <button
            type="button"
            class="step-row"
            :class="{
              'step-row--active': expandedId === s.id,
              'step-row--failed': s.status !== 'passed',
            }"
            @click="toggleExpand(s.id)"
          >
            <span
              class="status-pill"
              :class="s.status === 'passed' ? 'status-pill--ok' : 'status-pill--fail'"
            >
              {{ s.status === 'passed' ? '通过' : '失败' }}
            </span>
            <span class="step-name" :title="s.case_name">{{ s.case_name || '未命名步骤' }}</span>
            <MethodTag v-if="s.method" :method="s.method" />
            <span class="step-path" :title="s.url">{{ displayRequestPath(s.url) }}</span>
            <span class="step-code" :class="{ 'step-code--fail': s.status !== 'passed' }">
              {{ s.response_status ?? '-' }}
            </span>
            <span class="step-time">{{ formatReportDuration(s.duration_ms) }}</span>
            <el-icon class="step-arrow" :class="{ open: expandedId === s.id }">
              <ArrowRight />
            </el-icon>
          </button>
          <RunStepDetailPanel v-if="expandedId === s.id" :step="s" />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, ref, watch } from 'vue'
import { ArrowRight, Search } from '@element-plus/icons-vue'
import type { Schemas } from '@/api/types'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import RunStepDetailPanel from '@/components/apifox/run/RunStepDetailPanel.vue'
import { iterationLabel } from '@/utils/iterationLabel'
import { displayRequestPath, formatReportDuration } from '@/utils/runReportStats'

type StepFilter = 'all' | 'passed' | 'failed'
type RunStep = Schemas['RunStepOut']

const props = withDefaults(defineProps<{ detail: Schemas['RunOut']; live?: boolean }>(), {
  live: false,
})

const stepFilter = ref<StepFilter>('all')
const keyword = ref('')
const expandedId = ref<number | null>(null)

const allSteps = computed(() => props.detail?.steps || [])

const counts = computed(() => {
  const passed = allSteps.value.filter((s) => s.status === 'passed').length
  return { all: allSteps.value.length, passed, failed: allSteps.value.length - passed }
})

const filterTabs = computed(() => [
  { value: 'all' as const, label: '全部', count: counts.value.all },
  { value: 'passed' as const, label: '通过', count: counts.value.passed },
  { value: 'failed' as const, label: '失败', count: counts.value.failed },
])

const stepGroups = computed(() => {
  const steps = allSteps.value
  const iters = props.detail?.iterations || []
  if (iters.length <= 1) return [{ label: '', steps }]
  return iters.map((data, i) => ({
    label: iterationLabel(i, data),
    steps: steps.filter((s) => s.iteration === i),
  }))
})

function matchFilter(step: RunStep) {
  if (stepFilter.value !== 'all' && step.status !== stepFilter.value) return false
  const q = keyword.value.trim().toLowerCase()
  if (!q) return true
  const path = displayRequestPath(step.url).toLowerCase()
  return (
    (step.case_name || '').toLowerCase().includes(q) ||
    path.includes(q) ||
    (step.method || '').toLowerCase().includes(q)
  )
}

const visibleGroups = computed(() =>
  stepGroups.value
    .map((g) => ({ ...g, steps: g.steps.filter(matchFilter) }))
    .filter((g) => g.steps.length > 0),
)

const visibleSteps = computed(() => visibleGroups.value.flatMap((g) => g.steps))

const emptyHint = computed(() => {
  if (props.live && allSteps.value.length === 0) return '等待步骤执行…'
  if (keyword.value.trim()) return '无匹配步骤'
  if (stepFilter.value === 'failed') return '没有失败步骤'
  if (stepFilter.value === 'passed') return '没有通过步骤'
  return '暂无步骤'
})

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

watch(stepFilter, (v) => {
  expandedId.value = null
  if (v === 'failed' && visibleSteps.value.length === 1) {
    expandedId.value = visibleSteps.value[0].id
  }
})

watch(
  () => props.detail?.id,
  () => {
    stepFilter.value = 'all'
    keyword.value = ''
    expandedId.value = null
  },
)

watch(
  () => (props.live ? allSteps.value.length : 0),
  (len, prev) => {
    if (!props.live || len <= 0 || len === prev) return
    const latest = allSteps.value[allSteps.value.length - 1]
    if (latest) expandedId.value = latest.id
  },
)
</script>

<style scoped>
.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-3);
  margin-bottom: var(--ax-space-3);
  position: sticky;
  top: 0;
  z-index: 2;
  padding: var(--ax-space-1) 0 var(--ax-space-2);
  background: var(--ax-bg);
  border-bottom: 1px solid var(--ax-border);
}

.filter-tabs {
  display: flex;
  gap: var(--ax-space-4);
}

.filter-tab {
  padding: var(--ax-space-1) 0;
  border: none;
  background: none;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition:
    color 0.15s,
    border-color 0.15s;
}

.filter-tab:hover {
  color: var(--ax-brand);
}

.filter-tab.active {
  color: var(--ax-brand);
  font-weight: 600;
  border-bottom-color: var(--ax-brand);
}

.search-input {
  width: 220px;
}

.step-group {
  margin-bottom: var(--ax-space-3);
}

.group-title {
  font-size: var(--ax-font-xs);
  font-weight: 600;
  color: var(--ax-text-secondary);
  margin: var(--ax-space-2) 0 var(--ax-space-1);
}

.step-list {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  overflow: hidden;
  background: var(--ax-bg);
}

.step-row {
  display: grid;
  grid-template-columns: 52px minmax(80px, 1fr) auto minmax(120px, 2fr) 48px 72px 20px;
  align-items: center;
  gap: var(--ax-space-2);
  width: 100%;
  padding: var(--ax-space-2) var(--ax-space-3);
  border: none;
  border-bottom: 1px solid var(--ax-border);
  background: var(--ax-bg);
  text-align: left;
  cursor: pointer;
  transition: background 0.12s;
}

.step-row:last-of-type {
  border-bottom: none;
}

.step-row:hover,
.step-row--active {
  background: color-mix(in srgb, var(--color-purple-6) 6%, var(--ax-bg));
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
}

.status-pill--ok {
  color: var(--ax-success);
  background: color-mix(in srgb, var(--ax-success) 12%, var(--ax-bg));
}

.status-pill--fail {
  color: var(--color-pink-6);
  background: color-mix(in srgb, var(--color-pink-6) 12%, var(--ax-bg));
}

.step-name {
  font-size: var(--ax-font-sm);
  font-weight: 500;
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-path {
  font-size: var(--ax-font-xs);
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-code {
  font-size: var(--ax-font-sm);
  font-weight: 600;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--ax-text);
}

.step-code--fail {
  color: var(--color-pink-6);
}

.step-time {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.step-arrow {
  color: var(--ax-text-placeholder);
  transition: transform 0.15s;
}

.step-arrow.open {
  transform: rotate(90deg);
}
</style>
