<template>
  <div v-loading="loading" class="auto-ov flex flex-col">
    <!-- 头部：统计 + 推荐工作流 -->
    <section class="summary overview-summary">
      <div class="summary-deco" aria-hidden="true">
        <span class="deco-orb deco-orb--a" />
        <span class="deco-orb deco-orb--b" />
      </div>

      <div class="tiles">
        <button
          v-for="t in tiles"
          :key="t.key"
          type="button"
          class="tile"
          :class="{ pulse: t.pulse && t.value }"
          @click="emit('nav', t.nav)"
        >
          <el-icon class="tile-ic" :style="{ color: t.color }"><component :is="t.icon" /></el-icon>
          <div class="tile-main">
            <div class="tile-value" :style="{ color: t.color }">{{ t.value }}</div>
            <div class="tile-label">{{ t.label }}</div>
          </div>
        </button>
      </div>

      <div class="flow">
        <span class="flow-title">推荐工作流</span>
        <div class="flow-steps">
          <template v-for="(f, i) in FLOW" :key="f.section">
            <button type="button" class="flow-step" @click="emit('nav', f.section)">
              <span class="flow-idx">{{ i + 1 }}</span>
              <span class="flow-label">{{ f.label }}</span>
            </button>
            <el-icon v-if="i < FLOW.length - 1" class="flow-arrow"><ArrowRight /></el-icon>
          </template>
        </div>
      </div>
    </section>

    <!-- 趋势图：左右并排 -->
    <TrendCharts v-if="stats" :trend="stats.trend" class="ov-section" />

    <!-- 最近执行记录（可翻页） -->
    <section class="records ov-section">
      <header class="rec-head">
        <span class="rec-title"
          ><el-icon><Histogram /></el-icon> 最近执行记录</span
        >
        <el-button link size="small" @click="loadRuns">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </header>
      <div class="rec-body flex-1">
        <el-table
          v-if="runs.length"
          :data="runs"
          size="small"
          class="rec-table"
          @row-click="() => emit('nav', 'reports')"
        >
          <el-table-column label="目标" min-width="180">
            <template #default="{ row }">
              <el-tag size="small" :type="typeTag(row.target_type)">{{
                typeLabel(row.target_type)
              }}</el-tag>
              <span class="rec-name">{{ row.target_name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="statusTag(row.status)">{{
                statusLabel(row.status)
              }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="通过率" width="120">
            <template #default="{ row }">
              {{ row.pass_rate != null ? row.pass_rate + '%' : '-' }}
              <span class="rec-sub">({{ row.passed_count }}/{{ row.total_count }})</span>
            </template>
          </el-table-column>
          <el-table-column label="耗时" width="90">
            <template #default="{ row }">{{
              row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-'
            }}</template>
          </el-table-column>
          <el-table-column label="时间" min-width="160">
            <template #default="{ row }">{{ fmt(row.started_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty
          v-else-if="!loading"
          class="rec-empty"
          description="暂无运行记录（在自动化测试里运行用例/场景）"
          :image-size="60"
        />
      </div>
      <el-pagination
        v-if="runTotal > pageSize"
        v-model:current-page="page"
        class="rec-pager"
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="runTotal"
        @current-change="loadRuns"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import '@/styles/overview-summary.css'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { formatTime, statusLabel, statusTag } from '@/utils/runFormat'
import TrendCharts from '@/components/shell/TrendCharts.vue'

const props = defineProps<{ projectId: number }>()
const emit = defineEmits<{ nav: [section: string] }>()

const FLOW = [
  { label: '维护接口', section: 'apis' },
  { label: '编写用例', section: 'cases' },
  { label: '场景编排', section: 'scenarios' },
  { label: '定时执行', section: 'schedules' },
  { label: '查看报告', section: 'reports' },
]

const loading = ref(false)
const stats = ref<Schemas['ProjectStatsOut'] | null>(null)
const aiTaskCount = ref(0)
const runs = ref<Schemas['RunBrief'][]>([])
const runTotal = ref(0)
const page = ref(1)
const pageSize = 10

const TYPE_LABEL: Record<string, string> = { scenario: '场景', case: '单接口', suite: '套件' }
const typeLabel = (t: string) => TYPE_LABEL[t] || '用例'
const typeTag = (t: string) =>
  t === 'scenario' ? 'warning' : t === 'suite' ? 'primary' : 'success'
const fmt = (v: string) => formatTime(v)

const tiles = computed(() => [
  {
    key: 'ep',
    nav: 'apis',
    label: '接口数',
    value: stats.value?.endpoint_count ?? 0,
    icon: 'Connection',
    color: 'var(--ax-brand)',
  },
  {
    key: 'case',
    nav: 'cases',
    label: '用例数',
    value: stats.value?.case_count ?? 0,
    icon: 'Files',
    color: 'var(--ax-brand)',
  },
  {
    key: 'scn',
    nav: 'scenarios',
    label: '场景数',
    value: stats.value?.scenario_count ?? 0,
    icon: 'Share',
    color: 'var(--ax-brand)',
  },
  {
    key: 'run',
    nav: 'reports',
    label: '运行中',
    value: stats.value?.running_count ?? 0,
    icon: 'VideoPlay',
    color: 'var(--ax-success)',
    pulse: true,
  },
  {
    key: 'ai',
    nav: 'ai',
    label: 'AI 任务',
    value: aiTaskCount.value,
    icon: 'MagicStick',
    color: 'var(--ax-rail-active-bg)',
  },
  {
    key: 'rate',
    nav: 'reports',
    label: '今日通过率',
    value: stats.value?.today_pass_rate != null ? stats.value.today_pass_rate + '%' : '—',
    icon: 'TrendCharts',
    color: 'var(--ax-warning)',
  },
])

async function loadRuns() {
  if (!props.projectId) return
  const data = await apifoxApi.listRunsPage(props.projectId, {
    page: page.value,
    page_size: pageSize,
  })
  runs.value = data.items
  runTotal.value = data.total
}

async function load() {
  if (!props.projectId) return
  loading.value = true
  page.value = 1
  try {
    const [st, ai] = await Promise.all([
      apifoxApi.projectStats(props.projectId),
      apifoxApi.listActiveAiGenTasks(props.projectId),
      loadRuns(),
    ])
    stats.value = st
    aiTaskCount.value = ai.length
  } catch {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

watch(() => props.projectId, load, { immediate: true })
</script>

<style scoped>
.auto-ov {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding: var(--ax-space-4);
}

.ov-section {
  margin-top: var(--ax-space-4);
}

/* ── 头部总结栏 ── */
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
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: var(--ax-space-2-5);
}

.tile {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2-5);
  padding: var(--ax-space-3);
  border: none;
  border-radius: var(--ax-radius-lg);
  background: color-mix(in srgb, var(--ax-bg) 82%, transparent);
  backdrop-filter: blur(8px);
  cursor: pointer;
  text-align: left;
  transition: all var(--ax-transition);
}

.tile:hover {
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  transform: translateY(-1px);
}

.tile.pulse .tile-ic {
  animation: tile-pulse 1.4s ease-in-out infinite;
}

@keyframes tile-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
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

.flow-step:hover {
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

/* 最近执行记录 */
.records {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  padding: var(--ax-space-3) var(--ax-space-3-5);
  display: flex;
  flex-direction: column;
  min-height: 280px;
}

.rec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-space-2);
  flex: none;
}

.rec-title {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  font-weight: 600;
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
}

.rec-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.rec-table {
  cursor: pointer;
}

.rec-name {
  margin-left: 6px;
}

.rec-sub {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.rec-empty {
  flex: 1;
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rec-pager {
  justify-content: flex-end;
  margin-top: var(--ax-space-2-5);
  flex: none;
}

@media (max-width: 900px) {
  .tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
