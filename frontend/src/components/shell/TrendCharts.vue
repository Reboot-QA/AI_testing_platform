<template>
  <div class="trend-charts">
    <section class="chart-card">
      <div class="chart-title">近 7 天通过率</div>
      <div class="chart-host">
        <div v-if="hasPassRate" class="chart-wrap">
          <Line :data="passRateData" :options="passRateOptions" />
        </div>
        <p v-else class="chart-empty">暂无数据</p>
      </div>
    </section>
    <section class="chart-card">
      <div class="chart-title">近 7 天执行（通过 / 失败）</div>
      <div class="chart-host">
        <div class="chart-wrap">
          <Line :data="execData" :options="execOptions" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  CategoryScale,
  Chart,
  type ChartOptions,
  Filler,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js'
import { Line } from 'vue-chartjs'
import type { Schemas } from '@/api/types'

Chart.register(
  LineController,
  LinearScale,
  CategoryScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
)

const props = defineProps<{ trend: Schemas['DailyTrendItem'][] }>()

function tok(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
const cBrand = () => tok('--ax-brand', '#2b6cff')
const cSuccess = () => tok('--ax-success', '#00b42a')
const cDanger = () => tok('--ax-danger', '#f53f3f')
const cGrid = () => tok('--ax-border', '#e5e6eb')
const cText = () => tok('--ax-text-tertiary', '#86909c')

const labels = computed(() => props.trend.map((d) => d.date.slice(5)))
const hasPassRate = computed(() => props.trend.some((d) => d.pass_rate != null))

const passRateData = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '通过率(%)',
      data: props.trend.map((d) => d.pass_rate ?? null),
      borderColor: cBrand(),
      backgroundColor: cBrand() + '18',
      fill: true,
      tension: 0.35,
      spanGaps: true,
      pointRadius: 2.5,
      borderWidth: 2,
    },
  ],
}))

const execData = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '通过',
      data: props.trend.map((d) => d.passed),
      borderColor: cSuccess(),
      backgroundColor: cSuccess() + '14',
      fill: true,
      tension: 0.35,
      pointRadius: 2.5,
      borderWidth: 2,
    },
    {
      label: '失败',
      data: props.trend.map((d) => d.failed),
      borderColor: cDanger(),
      backgroundColor: cDanger() + '14',
      fill: true,
      tension: 0.35,
      pointRadius: 2.5,
      borderWidth: 2,
    },
  ],
}))

const passRateOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: cText(), font: { size: 11 } },
      border: { display: false },
    },
    y: {
      min: 0,
      max: 100,
      grid: { color: cGrid() },
      ticks: { color: cText(), font: { size: 11 } },
      border: { display: false },
    },
  },
}))

const execOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom',
      labels: { color: cText(), boxWidth: 10, boxHeight: 2, usePointStyle: true },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: cText(), font: { size: 11 } },
      border: { display: false },
    },
    y: {
      beginAtZero: true,
      grid: { color: cGrid() },
      ticks: { color: cText(), font: { size: 11 }, precision: 0 },
      border: { display: false },
    },
  },
}))
</script>

<style scoped>
.trend-charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--ax-space-3);
}

.chart-card {
  min-width: 0;
  padding: var(--ax-space-3) var(--ax-space-3-5);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg-subtle);
}

.chart-title {
  font-weight: 600;
  color: var(--ax-text);
  font-size: var(--ax-font-sm);
  margin-bottom: var(--ax-space-2);
}

.chart-host {
  height: 180px;
  position: relative;
}

.chart-wrap {
  height: 100%;
}

.chart-empty {
  margin: 0;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-sm);
}

@media (max-width: 800px) {
  .trend-charts {
    grid-template-columns: 1fr;
  }
}
</style>
