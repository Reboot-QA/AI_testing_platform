<template>
  <div class="domain-ov">
    <!-- 头部：统计 + 推荐工作流（对齐自动化概览） -->
    <section class="summary overview-summary">
      <div class="summary-deco" aria-hidden="true">
        <span class="deco-orb deco-orb--a" />
        <span class="deco-orb deco-orb--b" />
      </div>

      <div v-if="stats?.length" class="tiles" :style="tileGridStyle">
        <component
          :is="s.section ? 'button' : 'div'"
          v-for="s in stats"
          :key="s.label"
          :type="s.section ? 'button' : undefined"
          class="tile"
          :class="{ clickable: !!s.section }"
          @click="s.section && emit('nav', s.section, s.filter)"
        >
          <el-icon v-if="s.icon" class="tile-ic" :style="{ color: toneColor(s.tone) }">
            <component :is="s.icon" />
          </el-icon>
          <div class="tile-main">
            <div class="tile-value" :style="{ color: toneColor(s.tone) }">{{ s.value }}</div>
            <div class="tile-label">{{ s.label }}</div>
          </div>
        </component>
      </div>

      <div v-if="normalizedSteps.length" class="flow">
        <span class="flow-title">推荐工作流</span>
        <div class="flow-steps">
          <template v-for="(step, i) in normalizedSteps" :key="step.label">
            <button
              type="button"
              class="flow-step"
              :disabled="!step.section"
              @click="step.section && emit('nav', step.section)"
            >
              <span class="flow-idx">{{ i + 1 }}</span>
              <span class="flow-label">{{ step.label }}</span>
            </button>
            <el-icon v-if="i < normalizedSteps.length - 1" class="flow-arrow">
              <ArrowRight />
            </el-icon>
          </template>
        </div>
      </div>
    </section>

    <!-- 快捷入口 -->
    <div v-if="actions.length" class="quick">
      <button
        v-for="a in actions"
        :key="a.section"
        class="quick-card"
        :class="{ primary: a.primary }"
        type="button"
        @click="emit('nav', a.section)"
      >
        <el-icon class="quick-ic"><component :is="a.icon" /></el-icon>
        <span class="quick-label">{{ a.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import '@/styles/overview-summary.css'
import type { OverviewAction, OverviewStat, OverviewStep } from '@/types/shell'

const props = defineProps<{
  actions: OverviewAction[]
  stats?: OverviewStat[]
  steps?: Array<string | OverviewStep>
}>()
const emit = defineEmits<{ nav: [section: string, filter?: string] }>()

const TONE_COLOR: Record<NonNullable<OverviewStat['tone']>, string> = {
  brand: 'var(--ax-brand)',
  warning: 'var(--ax-warning)',
  success: 'var(--ax-success)',
}

function toneColor(tone?: OverviewStat['tone']) {
  return TONE_COLOR[tone ?? 'brand']
}

const normalizedSteps = computed<OverviewStep[]>(() =>
  (props.steps ?? []).map((s) => (typeof s === 'string' ? { label: s } : s)),
)

const tileGridStyle = computed(() => {
  const n = props.stats?.length ?? 0
  const cols = Math.min(Math.max(n, 1), 5)
  return { gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }
})
</script>

<style scoped>
.domain-ov {
  padding: var(--ax-space-4);
}

.summary {
  position: relative;
  overflow: hidden;
  border-radius: var(--ax-radius-lg);
  padding: var(--ax-space-4);
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--ax-rail-active-bg) 10%, var(--ax-bg)) 0%,
    var(--ax-bg-subtle) 52%,
    color-mix(in srgb, var(--ax-tag-teal-fg) 6%, var(--ax-bg-subtle)) 100%
  );
}

.summary-deco {
  pointer-events: none;
  position: absolute;
  inset: 0;
}

.deco-orb {
  position: absolute;
  border-radius: 50%;
}

.deco-orb--a {
  width: 200px;
  height: 200px;
  top: -70px;
  right: -50px;
  background: color-mix(in srgb, var(--ax-rail-active-bg) 16%, transparent);
}

.deco-orb--b {
  width: 130px;
  height: 130px;
  bottom: -50px;
  left: 16%;
  background: color-mix(in srgb, var(--ax-tag-teal-fg) 12%, transparent);
}

.tiles {
  position: relative;
  z-index: 1;
  display: grid;
  gap: var(--ax-space-2-5);
}

.tile {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2-5);
  padding: var(--ax-space-3);
  border-radius: var(--ax-radius-lg);
  background: color-mix(in srgb, var(--ax-bg) 82%, transparent);
  backdrop-filter: blur(8px);
  border: none;
  text-align: left;
  width: 100%;
}

.tile.clickable {
  cursor: pointer;
  transition:
    background var(--ax-transition),
    transform var(--ax-transition);
}

.tile.clickable:hover {
  background: color-mix(in srgb, var(--ax-rail-active-bg) 8%, var(--ax-bg));
  transform: translateY(-1px);
}

.quick {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--ax-space-3);
  margin-top: var(--ax-space-4);
  padding-top: var(--ax-space-3);
  border-top: 1px solid color-mix(in srgb, var(--ax-rail-active-bg) 12%, transparent);
}

.flow {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ax-space-2-5) var(--ax-space-3);
  margin-top: var(--ax-space-3-5);
  padding-top: var(--ax-space-3);
  border-top: 1px solid color-mix(in srgb, var(--ax-rail-active-bg) 12%, transparent);
}

.flow-title {
  flex: none;
  font-weight: 500;
  color: var(--ax-text-tertiary);
  font-size: var(--ax-font-sm);
}

.flow-steps {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
  min-width: 0;
}

.flow-step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: var(--ax-space-1) var(--ax-space-2-5);
  border: none;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ax-bg) 85%, transparent);
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
  cursor: pointer;
  transition: all var(--ax-transition);
}

.flow-step:disabled {
  cursor: default;
}

.flow-step:not(:disabled):hover {
  color: var(--ax-rail-active-bg);
  background: color-mix(in srgb, var(--ax-rail-active-bg) 10%, var(--ax-bg));
}

.flow-idx {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--ax-rail-active-bg);
  color: var(--ax-rail-active-text);
  font-size: 11px;
  line-height: 18px;
  text-align: center;
}

.flow-arrow {
  color: var(--ax-text-placeholder);
}

.quick-card {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2-5);
  padding: var(--ax-space-3) var(--ax-space-3-5);
  border: none;
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg-subtle);
  cursor: pointer;
  transition: all var(--ax-transition);
  text-align: left;
}

.quick-card:hover {
  background: color-mix(in srgb, var(--ax-rail-active-bg) 8%, var(--ax-bg-subtle));
  transform: translateY(-1px);
  box-shadow: var(--ax-shadow-sm);
}

.quick-card.primary {
  background: color-mix(in srgb, var(--ax-rail-active-bg) 10%, var(--ax-bg-subtle));
}

.quick-ic {
  font-size: 18px;
  color: var(--ax-rail-active-bg);
}

.quick-label {
  font-weight: 600;
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
}

@media (max-width: 900px) {
  .tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}
</style>
