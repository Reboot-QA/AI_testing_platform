<template>
  <div v-if="events.length" class="run-progress">
    <div class="rp-head">
      <span>运行进度</span>
      <el-tag v-if="running" size="small" type="warning">执行中…</el-tag>
      <el-tag v-else-if="doneEvent" size="small" :type="doneEvent.status === 'passed' ? 'success' : 'danger'">
        {{ doneEvent.status === 'passed' ? '通过' : '失败' }} · 通过率 {{ doneEvent.pass_rate }}%
        · {{ Math.round(doneEvent.duration_ms || 0) }}ms
      </el-tag>
      <el-tag v-else-if="errorEvent" size="small" type="danger">错误</el-tag>
      <el-button link size="small" @click="$emit('clear')">收起</el-button>
    </div>

    <div v-for="(s, i) in stepEvents" :key="i" class="rp-step">
      <el-icon v-if="s.status === 'passed'" color="var(--ax-success)"><CircleCheck /></el-icon>
      <el-icon v-else color="var(--ax-danger)"><CircleClose /></el-icon>
      <span class="rp-name">{{ s.index }}/{{ s.total }} {{ s.case_name }}</span>
      <span v-if="s.response_status" class="rp-meta">{{ s.response_status }}</span>
      <span v-if="s.duration_ms != null" class="rp-meta">{{ Math.round(s.duration_ms) }}ms</span>
      <span v-if="s.error_message" class="rp-err">{{ s.error_message }}</span>
    </div>

    <div v-if="errorEvent" class="rp-err-line">{{ errorEvent.message }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  events: { type: Array, default: () => [] },
  running: { type: Boolean, default: false },
})
defineEmits(['clear'])

const stepEvents = computed(() => props.events.filter((e) => e.type === 'step'))
const doneEvent = computed(() => props.events.find((e) => e.type === 'done'))
const errorEvent = computed(() => props.events.find((e) => e.type === 'error'))
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
