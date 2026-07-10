<template>
  <div class="tiles">
    <div v-for="t in tiles" :key="t.label" class="tile">
      <div class="n" :class="{ live: t.live }">{{ t.value }}</div>
      <div class="l">{{ t.label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, default: () => ({}) },
})

const tiles = computed(() => {
  const s = props.stats
  const rate = s.today_pass_rate == null ? '—' : `${s.today_pass_rate}%`
  return [
    { label: '项目', value: s.project_count ?? 0 },
    { label: '接口', value: s.endpoint_count ?? 0 },
    { label: '测试场景', value: s.scenario_count ?? 0 },
    { label: '正在运行', value: s.running_count ?? 0, live: (s.running_count ?? 0) > 0 },
    { label: '今日通过率', value: rate },
  ]
})
</script>

<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.tile {
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  padding: 15px 16px;
}

.n {
  font-size: 26px;
  font-weight: 700;
  color: var(--ax-brand);
  font-variant-numeric: tabular-nums;
}

.n.live {
  color: var(--color-green-6);
}

.l {
  color: var(--ax-text-secondary);
  font-size: 12.5px;
  margin-top: 4px;
}
</style>
