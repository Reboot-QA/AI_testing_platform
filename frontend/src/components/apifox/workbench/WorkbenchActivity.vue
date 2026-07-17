<template>
  <div class="activity">
    <el-tabs v-model="activeTab" class="activity-tabs">
      <el-tab-pane name="running">
        <template #label>
          <span class="tab-label">
            <el-icon class="tab-ico"><VideoPlay /></el-icon>
            正在运行
            <span v-if="runningTotal" class="tab-badge live">{{ runningTotal }}</span>
          </span>
        </template>

        <div v-loading="runningLoading" class="tab-body">
          <div v-if="running.length" class="list">
            <div
              v-for="r in running"
              :key="r.run_id"
              class="row row--running"
              @click="$emit('open', r)"
            >
              <div class="row-main">
                <el-tooltip :content="r.target_name" placement="top" :show-after="400">
                  <div class="title">{{ r.target_name }}</div>
                </el-tooltip>
                <div class="meta">
                  <span>{{ typeLabel(r.target_type) }}</span>
                  <span class="sep">·</span>
                  <span>{{ r.project_name }}</span>
                  <span class="sep">·</span>
                  <el-tooltip :content="fullTime(r.started_at)" placement="top" :show-after="400">
                    <span>{{ relativeTime(r.started_at) }}</span>
                  </el-tooltip>
                </div>
              </div>
              <span class="status run">
                <span class="live-dot" />
                运行中
              </span>
            </div>
          </div>
          <div v-else-if="!runningLoading" class="empty">
            <el-icon class="empty-ico"><VideoPause /></el-icon>
            <p class="empty-title">暂无运行中的自动化</p>
            <p class="empty-hint">在项目里执行场景或用例后，会在这里实时显示</p>
          </div>

          <div v-if="runningTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="runningPage"
              :page-size="pageSize"
              :total="runningTotal"
              layout="total, prev, pager, next"
              small
              background
              @current-change="loadRunning"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="reports">
        <template #label>
          <span class="tab-label">
            <el-icon class="tab-ico"><Histogram /></el-icon>
            最近报告
            <span v-if="reportsTotal" class="tab-badge">{{ reportsTotal }}</span>
          </span>
        </template>

        <div v-loading="reportsLoading" class="tab-body">
          <div v-if="reports.length" class="list">
            <div v-for="r in reports" :key="r.run_id" class="row" @click="$emit('open', r)">
              <div class="row-main">
                <el-tooltip :content="r.target_name" placement="top" :show-after="400">
                  <div class="title">{{ r.target_name }}</div>
                </el-tooltip>
                <div class="meta">
                  <span>{{ typeLabel(r.target_type) }}</span>
                  <span class="sep">·</span>
                  <span>{{ r.project_name }}</span>
                  <span class="sep">·</span>
                  <el-tooltip :content="fullTime(r.started_at)" placement="top" :show-after="400">
                    <span>{{ relativeTime(r.started_at) }}</span>
                  </el-tooltip>
                </div>
              </div>
              <span class="status" :class="statusClass(r)">{{ statusText(r) }}</span>
            </div>
          </div>
          <div v-else-if="!reportsLoading" class="empty">
            <el-icon class="empty-ico"><Document /></el-icon>
            <p class="empty-title">暂无运行记录</p>
            <p class="empty-hint">执行自动化测试后，最近报告会汇总在这里</p>
          </div>

          <div v-if="reportsTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="reportsPage"
              :page-size="pageSize"
              :total="reportsTotal"
              layout="total, prev, pager, next"
              small
              background
              @current-change="loadReports"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { formatBeijingTime, formatRelativeTime } from '@/utils/datetime'

type WorkbenchRunning = Schemas['WorkbenchRunning']
type WorkbenchReport = Schemas['WorkbenchReport']

const props = withDefaults(
  defineProps<{
    /** 概览统计中的运行中数量，用于初始 Tab 切换 */
    runningCount?: number
  }>(),
  {
    runningCount: 0,
  },
)
defineEmits<{ open: [item: WorkbenchRunning | WorkbenchReport] }>()

const pageSize = 20
const activeTab = ref('reports')

const running = ref<WorkbenchRunning[]>([])
const runningPage = ref(1)
const runningTotal = ref(0)
const runningLoading = ref(false)

const reports = ref<WorkbenchReport[]>([])
const reportsPage = ref(1)
const reportsTotal = ref(0)
const reportsLoading = ref(false)

watch(
  () => props.runningCount,
  (n) => {
    if (n > 0) activeTab.value = 'running'
  },
  { immediate: true },
)

const TYPE_LABEL: Record<string, string> = {
  scenario: '场景',
  case: '单接口',
  suite: '套件',
}

const typeLabel = (t: string) => TYPE_LABEL[t] || '用例'
const fullTime = (v: string) => formatBeijingTime(v)
const relativeTime = (v: string) => formatRelativeTime(v)

function statusClass(r: WorkbenchReport) {
  if (r.status === 'running') return 'run'
  return r.status === 'passed' ? 'ok' : 'bad'
}

function statusText(r: WorkbenchReport) {
  if (r.status === 'running') return '运行中'
  const label = r.status === 'passed' ? '通过' : '失败'
  if (r.total_count > 0) return `${label} ${r.passed_count}/${r.total_count}`
  return label
}

async function loadRunning() {
  runningLoading.value = true
  try {
    const data = await apifoxApi.workbenchRunning({
      page: runningPage.value,
      page_size: pageSize,
    })
    running.value = data.items
    runningTotal.value = data.total
  } catch {
    // 全局拦截器已提示
  } finally {
    runningLoading.value = false
  }
}

async function loadReports() {
  reportsLoading.value = true
  try {
    const data = await apifoxApi.workbenchReports({
      page: reportsPage.value,
      page_size: pageSize,
    })
    reports.value = data.items
    reportsTotal.value = data.total
  } catch {
    // 全局拦截器已提示
  } finally {
    reportsLoading.value = false
  }
}

async function refresh() {
  runningPage.value = 1
  reportsPage.value = 1
  await Promise.all([loadRunning(), loadReports()])
}

defineExpose({ refresh })
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
  overflow: hidden;
}

.activity-tabs {
  --el-tabs-header-height: 42px;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.activity-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 12px;
  border-bottom: 1px solid var(--ax-border);
  flex: none;
  background: var(--ax-bg-subtle);
}

.activity-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.activity-tabs :deep(.el-tabs__item) {
  font-size: var(--ax-font-sm);
  font-weight: 500;
  color: var(--ax-text-secondary);
  padding: 0 14px;
}

.activity-tabs :deep(.el-tabs__item.is-active) {
  color: var(--ax-text);
  font-weight: 600;
}

.activity-tabs :deep(.el-tabs__active-bar) {
  height: 2px;
  border-radius: 2px;
}

.activity-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  padding: 0;
}

.activity-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.tab-body {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 0;
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tab-ico {
  font-size: 15px;
}

.tab-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--ax-bg-hover);
  color: var(--ax-text-secondary);
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  text-align: center;
}

.tab-badge.live {
  background: color-mix(in srgb, var(--color-green-6) 15%, white);
  color: var(--ax-success);
}

.row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--ax-border);
  cursor: pointer;
  transition: background var(--ax-transition);
}

.row:last-child {
  border-bottom: none;
}

.row:hover {
  background: var(--ax-bg-subtle);
}

.row--running {
  background: color-mix(in srgb, var(--color-green-6) 3%, white);
}

.row--running:hover {
  background: color-mix(in srgb, var(--color-green-6) 6%, white);
}

.row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title {
  font-weight: 600;
  font-size: var(--ax-font);
  color: var(--ax-text);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--ax-text-tertiary);
  font-size: var(--ax-font-xs);
  line-height: 1.4;
}

.meta .sep {
  color: var(--ax-text-placeholder);
}

.status {
  flex: none;
  margin-top: 2px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--ax-font-xs);
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.status.ok {
  color: var(--ax-success);
  background: color-mix(in srgb, var(--ax-success) 10%, transparent);
}

.status.bad {
  color: var(--ax-danger);
  background: color-mix(in srgb, var(--ax-danger) 10%, transparent);
}

.status.run {
  color: var(--color-blue-6);
  background: color-mix(in srgb, var(--color-blue-6) 10%, transparent);
}

.live-dot {
  width: 6px;
  height: 6px;
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
    box-shadow: 0 0 0 5px color-mix(in srgb, var(--color-green-6) 0%, transparent);
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

.pager {
  flex: none;
  display: flex;
  justify-content: center;
  padding: 8px 12px 10px;
  border-top: 1px solid var(--ax-border);
  background: var(--ax-bg-subtle);
}

.pager :deep(.el-pagination) {
  flex-wrap: wrap;
  justify-content: center;
}

.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 48px 24px 56px;
  text-align: center;
}

.empty-ico {
  font-size: 36px;
  color: var(--ax-text-placeholder);
  margin-bottom: 4px;
}

.empty-title {
  margin: 0;
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.empty-hint {
  margin: 0;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
  max-width: 240px;
  line-height: 1.6;
}
</style>
