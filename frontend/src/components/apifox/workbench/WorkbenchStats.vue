<template>
  <div class="tiles">
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

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, default: () => ({}) },
})

// 图标底色：主色 14% 淡调 + 同色图标，与仪表盘统计卡范式一致
const tint = (color) => `color-mix(in srgb, ${color} 14%, white)`

const tiles = computed(() => {
  const s = props.stats
  const rate = s.today_pass_rate == null ? '—' : `${s.today_pass_rate}%`
  const running = s.running_count ?? 0
  return [
    { label: '项目', value: s.project_count ?? 0, icon: 'Folder', color: '#3182ce' },
    { label: '接口', value: s.endpoint_count ?? 0, icon: 'Connection', color: '#0d9488' },
    { label: '测试场景', value: s.scenario_count ?? 0, icon: 'Share', color: '#805ad5' },
    { label: '正在运行', value: running, icon: 'VideoPlay', color: '#16a34a', live: running > 0 },
    { label: '今日通过率', value: rate, icon: 'TrendCharts', color: '#dd6b20' },
  ]
})
</script>

<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
  flex: none;
}

.tile {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--ax-bg);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  box-shadow: var(--ax-shadow-sm);
  padding: 10px 12px;
  transition: all var(--ax-transition);
}

.tile:hover {
  border-color: color-mix(in srgb, var(--ax-brand) 30%, var(--ax-border));
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
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--ax-text);
  font-variant-numeric: tabular-nums;
}

.n.live {
  color: var(--color-green-6);
}

.l {
  color: var(--ax-text-secondary);
  font-size: 12px;
  margin-top: 2px;
}

.live-dot {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-green-6);
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

@media (max-width: 1100px) {
  .tiles {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
