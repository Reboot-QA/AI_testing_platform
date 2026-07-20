<template>
  <div class="card">
    <div class="card-h">
      <span><span class="live-dot" />&nbsp;正在运行的自动化</span>
      <span class="hint">实时</span>
    </div>
    <div v-if="running.length" class="rows">
      <div v-for="r in running" :key="r.run_id" class="runrow" @click="$emit('open', r)">
        <div class="pi" :style="{ background: colorOf(r.project_id) }">
          {{ letterOf(r.project_name) }}
        </div>
        <div class="mid">
          <div class="nm">{{ r.target_name }}</div>
          <div class="sb">
            {{ r.project_name }} · {{ r.environment_name || '未选环境' }} · {{ time(r.started_at) }}
          </div>
        </div>
        <span class="pill run">运行中</span>
      </div>
    </div>
    <el-empty v-else description="当前没有正在运行的自动化" :image-size="48" />
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@/api/types'

type WorkbenchRunning = Schemas['WorkbenchRunning']

withDefaults(defineProps<{ running?: WorkbenchRunning[] }>(), {
  running: () => [],
})
defineEmits<{ open: [run: WorkbenchRunning] }>()

const PALETTE = ['#2c5282', '#2b6cb0', '#2c7a7b', '#6b46c1', '#b83280', '#c05621', '#2f855a']
const colorOf = (id: number) => PALETTE[id % PALETTE.length]
const letterOf = (name: string | null | undefined) => (name || '?').trim().charAt(0).toUpperCase()
const time = (v: string) => (v ? new Date(v).toLocaleString('zh-CN', { hour12: false }) : '-')
</script>

<style scoped>
.card {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.rows {
  max-height: 340px;
  overflow-y: auto;
}

.card-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ax-border);
  font-weight: 600;
}

.hint {
  color: var(--ax-text-tertiary);
  font-size: 12px;
  font-weight: 400;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-green-6);
  display: inline-block;
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-green-6) 50%, transparent);
  animation: pulse 1.6s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-green-6) 50%, transparent);
  }
  70% {
    box-shadow: 0 0 0 6px color-mix(in srgb, var(--color-green-6) 0%, transparent);
  }
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-green-6) 0%, transparent);
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
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
}

.pill {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 20px;
  white-space: nowrap;
  flex: none;
}

.pill.run {
  color: var(--color-blue-6);
  background: color-mix(in srgb, var(--color-blue-6) 12%, transparent);
}
</style>
