<template>
  <div class="activity">
    <el-tabs v-model="activeTab" class="activity-tabs">
      <el-tab-pane name="running">
        <template #label>
          <span class="tab-label">
            正在运行
            <span v-if="running.length" class="tab-badge">{{ running.length }}</span>
          </span>
        </template>
        <div v-if="running.length" class="rows">
          <div v-for="r in running" :key="r.run_id" class="runrow" @click="$emit('open', r)">
            <div class="pi" :style="{ background: colorOf(r.project_id) }">
              {{ letterOf(r.project_name) }}
            </div>
            <div class="mid">
              <div class="nm">{{ r.target_name }}</div>
              <div class="sb">
                {{ r.project_name }} · {{ r.environment_name || '未选环境' }} ·
                {{ time(r.started_at) }}
              </div>
            </div>
            <span class="pill run">运行中</span>
          </div>
        </div>
        <el-empty v-else description="当前没有正在运行的自动化" :image-size="48" />
      </el-tab-pane>

      <el-tab-pane label="最近报告" name="reports">
        <div v-if="reports.length" class="rows">
          <div v-for="r in reports" :key="r.run_id" class="runrow" @click="$emit('open', r)">
            <div class="pi" :style="{ background: colorOf(r.project_id) }">
              {{ letterOf(r.project_name) }}
            </div>
            <div class="mid">
              <div class="nm">{{ r.target_name }}</div>
              <div class="sb">
                {{ r.project_name }} · {{ r.environment_name || '未选环境' }} ·
                {{ time(r.started_at) }}
              </div>
            </div>
            <span class="pill" :class="pillClass(r)">{{ pillText(r) }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无运行记录" :image-size="48" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  running: { type: Array, default: () => [] },
  reports: { type: Array, default: () => [] },
})
defineEmits(['open'])

const activeTab = ref('running')

const PALETTE = ['#2c5282', '#2b6cb0', '#2c7a7b', '#6b46c1', '#b83280', '#c05621', '#2f855a']
const colorOf = (id) => PALETTE[id % PALETTE.length]
const letterOf = (name) => (name || '?').trim().charAt(0).toUpperCase()
const time = (v) => (v ? new Date(v).toLocaleString('zh-CN', { hour12: false }) : '-')

function pillClass(r) {
  if (r.status === 'running') return 'run'
  return r.status === 'passed' ? 'ok' : 'bad'
}

function pillText(r) {
  if (r.status === 'running') return '运行中'
  const label = r.status === 'passed' ? '通过' : '失败'
  return `${label} ${r.passed_count}/${r.total_count}`
}
</script>

<style scoped>
.activity {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.activity-tabs {
  --el-tabs-header-height: 44px;
}

.activity-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 8px;
  border-bottom: 1px solid var(--ax-border);
}

.activity-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tab-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--color-green-6);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  text-align: center;
}

.rows {
  max-height: 420px;
  overflow-y: auto;
}

.runrow {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ax-border);
  cursor: pointer;
}

.runrow:last-child {
  border-bottom: none;
}

.runrow:hover {
  background: var(--ax-bg-subtle);
}

.pi {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  flex: none;
}

.mid {
  flex: 1;
  overflow: hidden;
}

.nm {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sb {
  color: var(--ax-text-tertiary);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pill {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 20px;
  white-space: nowrap;
  flex: none;
}

.pill.ok {
  color: var(--color-green-6);
  background: color-mix(in srgb, var(--color-green-6) 12%, transparent);
}

.pill.bad {
  color: var(--color-red-6);
  background: color-mix(in srgb, var(--color-red-6) 12%, transparent);
}

.pill.run {
  color: var(--color-blue-6);
  background: color-mix(in srgb, var(--color-blue-6) 12%, transparent);
}
</style>
