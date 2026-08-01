<template>
  <div class="child-runs">
    <div class="list-toolbar">
      <div class="filter-tabs">
        <button
          v-for="tab in filterTabs"
          :key="tab.value"
          type="button"
          class="filter-tab"
          :class="{ active: runFilter === tab.value }"
          @click="runFilter = tab.value"
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
        :placeholder="searchPlaceholder"
        :prefix-icon="Search"
      />
    </div>

    <el-empty v-if="visibleRows.length === 0" :description="emptyHint" :image-size="64" />

    <div v-else class="run-list">
      <template v-for="row in visibleRows" :key="row.id">
        <button
          type="button"
          class="run-row"
          :class="{
            'run-row--active': expandInline && expandedId === row.id,
            'run-row--failed': row.status !== 'passed',
          }"
          @click="onRowClick(row)"
        >
          <span
            class="status-pill"
            :class="row.status === 'passed' ? 'status-pill--ok' : 'status-pill--fail'"
          >
            {{ statusLabel(row.status) }}
          </span>
          <span class="run-name" :title="row.target_name">{{
            row.target_name || RUN_LIST_UNNAMED
          }}</span>
          <span v-if="row.pass_rate != null" class="run-rate">{{ row.pass_rate }}%</span>
          <span class="run-time">{{ formatReportDuration(row.duration_ms) }}</span>
          <el-icon class="run-arrow" :class="{ open: expandInline && expandedId === row.id }">
            <ArrowRight />
          </el-icon>
        </button>
        <div
          v-if="expandInline && expandedId === row.id"
          v-loading="loadingId === row.id"
          class="run-expand"
        >
          <RunStepGroups
            v-if="childDetails[row.id]"
            :detail="childDetails[row.id]"
            auto-expand-first
            hide-toolbar
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, reactive, ref, watch } from 'vue'
import { ArrowRight, Search } from '@element-plus/icons-vue'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import RunStepGroups from '@/components/apifox/run/RunStepGroups.vue'
import { statusLabel } from '@/utils/runFormat'
import { formatReportDuration } from '@/utils/runReportStats'
import {
  RUN_LIST_SEARCH_CASE,
  RUN_LIST_UNNAMED,
  buildRunListFilterTabs,
  runListEmptyHint,
  type RunListFilter,
} from '@/utils/runReportList'

type RunBrief = Schemas['RunBrief']

const props = withDefaults(
  defineProps<{
    children: RunBrief[]
    searchPlaceholder?: string
    /** \u63a5\u53e3\u6279\u6b21\uff1a\u884c\u5185\u5c55\u5f00\u6b65\u9aa4\u8be6\u60c5\uff0c\u4e0d\u5207\u6362\u6574\u9875 */
    expandInline?: boolean
  }>(),
  { searchPlaceholder: RUN_LIST_SEARCH_CASE, expandInline: false },
)

const emit = defineEmits<{ openChild: [row: RunBrief] }>()

const runFilter = ref<RunListFilter>('all')
const keyword = ref('')
const expandedId = ref<number | null>(null)
const loadingId = ref<number | null>(null)
const childDetails = reactive<Record<number, Schemas['RunOut']>>({})

const counts = computed(() => {
  const passed = props.children.filter((r) => r.status === 'passed').length
  return { all: props.children.length, passed, failed: props.children.length - passed }
})

const filterTabs = computed(() => buildRunListFilterTabs(counts.value))

function matchFilter(row: RunBrief) {
  if (runFilter.value === 'passed' && row.status !== 'passed') return false
  if (runFilter.value === 'failed' && row.status === 'passed') return false
  const q = keyword.value.trim().toLowerCase()
  if (!q) return true
  return (row.target_name || '').toLowerCase().includes(q)
}

const visibleRows = computed(() => props.children.filter(matchFilter))

const emptyHint = computed(() => runListEmptyHint(runFilter.value, !!keyword.value.trim()))

async function onRowClick(row: RunBrief) {
  if (!props.expandInline) {
    emit('openChild', row)
    return
  }
  if (expandedId.value === row.id) {
    expandedId.value = null
    return
  }
  expandedId.value = row.id
  if (childDetails[row.id]) return
  loadingId.value = row.id
  try {
    childDetails[row.id] = await apifoxApi.getRun(row.id)
  } finally {
    loadingId.value = null
  }
}

watch(
  () => props.children,
  () => {
    runFilter.value = 'all'
    keyword.value = ''
    expandedId.value = null
    for (const key of Object.keys(childDetails)) delete childDetails[Number(key)]
  },
)

watch(runFilter, () => {
  expandedId.value = null
})
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

.run-list {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  overflow: hidden;
  background: var(--ax-bg);
}

.run-row {
  display: grid;
  grid-template-columns: 52px minmax(120px, 1fr) 56px 72px 20px;
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

.run-row:last-of-type {
  border-bottom: none;
}

.run-row:hover,
.run-row--active {
  background: color-mix(in srgb, var(--color-purple-6) 6%, var(--ax-bg));
}

.run-expand {
  padding: var(--ax-space-2) var(--ax-space-3) var(--ax-space-3);
  border-bottom: 1px solid var(--ax-border);
  background: color-mix(in srgb, var(--color-purple-6) 4%, var(--ax-bg));
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

.run-name {
  font-size: var(--ax-font-sm);
  font-weight: 500;
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-rate {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.run-time {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.run-arrow {
  color: var(--ax-text-placeholder);
  transition: transform 0.15s;
}

.run-arrow.open {
  transform: rotate(90deg);
}
</style>
