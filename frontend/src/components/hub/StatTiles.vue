<template>
  <div class="stat-tiles">
    <div v-for="t in tiles" :key="t.label" class="tile">
      <div class="ico" :style="{ backgroundColor: tint(t.color), color: t.color }">
        <el-icon :size="18"><component :is="t.icon" /></el-icon>
      </div>
      <div class="meta">
        <div class="n" :class="{ live: t.live }">{{ t.value }}</div>
        <div class="l">{{ t.label }}</div>
      </div>
      <span v-if="t.live" class="live-dot" title="有正在运行的自动化" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Schemas } from '@/api/types'

const props = withDefaults(defineProps<{ stats?: Schemas['WorkbenchStats'] }>(), {
  stats: () => ({}) as Schemas['WorkbenchStats'],
})

const tint = (color: string) => `color-mix(in srgb, ${color} 14%, white)`

const tiles = computed(() => {
  const s = props.stats
  const rate = s.today_pass_rate == null ? '—' : `${s.today_pass_rate}%`
  const running = s.running_count ?? 0
  return [
    { label: '项目', value: s.project_count ?? 0, icon: 'Folder', color: '#2b6cff' },
    { label: '接口', value: s.endpoint_count ?? 0, icon: 'Connection', color: '#0fc6c2' },
    { label: '测试场景', value: s.scenario_count ?? 0, icon: 'Share', color: '#722ed1' },
    { label: '正在运行', value: running, icon: 'VideoPlay', color: '#00b42a', live: running > 0 },
    { label: '今日通过率', value: rate, icon: 'TrendCharts', color: '#ff7d00' },
  ]
})
</script>

<style scoped>
.stat-tiles {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--ax-space-2-5);
  flex: none;
}

.tile {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--ax-space-2-5);
  background: var(--ax-bg);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  box-shadow: var(--ax-shadow-sm);
  padding: var(--ax-space-2-5) var(--ax-space-3);
  transition: all var(--ax-transition);
}

.tile:hover {
  border-color: color-mix(in srgb, var(--ax-rail-active-bg) 30%, var(--ax-border));
  box-shadow: var(--ax-shadow);
}

.ico {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: var(--ax-radius-lg);
  display: grid;
  place-items: center;
}

.meta {
  min-width: 0;
}

.n {
  font-size: var(--ax-text-heading-size);
  font-weight: 700;
  line-height: var(--ax-leading-tight);
  color: var(--ax-text);
  font-variant-numeric: tabular-nums;
}

.n.live {
  color: var(--ax-tag-green-fg);
}

.l {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-caption-size);
  margin-top: var(--ax-space-0-5);
}

.live-dot {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ax-tag-green-fg);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--ax-tag-green-fg) 50%, transparent);
  animation: pulse 1.6s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--ax-tag-green-fg) 50%, transparent);
  }
  70% {
    box-shadow: 0 0 0 6px color-mix(in srgb, var(--ax-tag-green-fg) 0%, transparent);
  }
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--ax-tag-green-fg) 0%, transparent);
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
}

@media (max-width: 1100px) {
  .stat-tiles {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .stat-tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
