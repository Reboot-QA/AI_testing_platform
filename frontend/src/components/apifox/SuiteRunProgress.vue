<template>
  <div v-if="events.length" class="run-progress">
    <div class="rp-head">
      <span>套件运行进度</span>
      <el-tag v-if="running" size="small" type="warning">执行中…</el-tag>
      <el-tag
        v-else-if="doneEvent"
        size="small"
        :type="doneEvent.status === 'passed' ? 'success' : 'danger'"
      >
        {{ doneEvent.status === 'passed' ? '通过' : '失败' }} · {{ doneEvent.passed_count }}/{{
          (doneEvent.passed_count || 0) + (doneEvent.failed_count || 0)
        }}
        项通过 · 通过率 {{ doneEvent.pass_rate }}% · {{ Math.round(doneEvent.duration_ms || 0) }}ms
      </el-tag>
      <el-tag v-else-if="errorEvent" size="small" type="danger">错误</el-tag>
      <el-button link size="small" @click="$emit('clear')">收起</el-button>
    </div>

    <div v-for="item in items" :key="item.index" class="rp-item">
      <el-icon v-if="item.status === 'running'" class="is-loading" color="var(--ax-warning)">
        <Loading />
      </el-icon>
      <el-icon v-else-if="item.status === 'passed'" color="var(--ax-success)"
        ><CircleCheck
      /></el-icon>
      <el-icon v-else color="var(--ax-danger)"><CircleClose /></el-icon>
      <span class="rp-type">{{ item.target_type === 'scenario' ? '场景' : '用例' }}</span>
      <span class="rp-name">{{ item.index }}/{{ total }} {{ item.target_name }}</span>
      <span v-if="item.passed_count != null" class="rp-meta">
        {{ item.passed_count }}/{{ (item.passed_count || 0) + (item.failed_count || 0) }} 步
      </span>
      <span v-if="item.duration_ms != null" class="rp-meta"
        >{{ Math.round(item.duration_ms) }}ms</span
      >
      <span v-if="item.error_message" class="rp-err">{{ item.error_message }}</span>
    </div>

    <div v-if="errorEvent" class="rp-err-line">{{ errorEvent.message }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface SuiteRunItem {
  index: number
  target_type?: string
  target_name?: string
  status?: string
  passed_count?: number
  failed_count?: number
  duration_ms?: number | null
  error_message?: string | null
}

interface SuiteRunEvent {
  type: string
  index?: number
  total?: number
  target_type?: string
  target_name?: string
  status?: string
  passed_count?: number
  failed_count?: number
  duration_ms?: number | null
  error_message?: string | null
  message?: string
}

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

const doneEvent = computed(() => props.events.find((e) => e.type === 'suite_done'))
const errorEvent = computed(() => props.events.find((e) => e.type === 'error'))
const total = computed(() => {
  const start = props.events.find((e) => e.type === 'suite_start')
  return start?.total ?? 0
})

// item_start 起一行(running)，item_done 覆盖为终态；按 index 归并保持顺序
const items = computed(() => {
  const map = new Map<number, SuiteRunItem>()
  for (const e of props.events) {
    if (e.type === 'item_start' && e.index != null) {
      map.set(e.index, {
        index: e.index,
        target_type: e.target_type,
        target_name: e.target_name,
        status: 'running',
      })
    } else if (e.type === 'item_done' && e.index != null) {
      const prev = map.get(e.index) || { index: e.index, target_name: e.target_name }
      map.set(e.index, {
        ...prev,
        status: e.status,
        passed_count: e.passed_count,
        failed_count: e.failed_count,
        duration_ms: e.duration_ms,
        error_message: e.error_message,
      })
    }
  }
  return [...map.values()].sort((a, b) => a.index - b.index)
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

.rp-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 13px;
}

.rp-type {
  color: var(--ax-text-secondary);
  font-size: 12px;
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
