<template>
  <div class="activity">
    <div class="panel-head">
      <div class="panel-title">动态</div>
    </div>
    <el-tabs v-model="activeTab" class="activity-tabs">
      <el-tab-pane name="fail">
        <template #label>
          <span class="tl"
            >失败聚焦<span v-if="failuresTotal" class="badge fail">{{ failuresTotal }}</span></span
          >
        </template>
        <div v-loading="failuresLoading" class="tab-body">
          <div v-if="failures.length" class="list">
            <ActivityRow
              v-for="r in failures"
              :key="r.run_id"
              :title="r.target_name"
              :sub="reportSub(r)"
              :reason="r.error_message"
              :status-text="statusText(r)"
              status-class="bad"
              @click="openAutomationRun(r)"
            />
          </div>
          <ActivityEmpty
            v-else-if="!failuresLoading"
            icon="CircleCheck"
            title="暂无失败项"
            hint="跨项目最近失败运行会聚合在此，附失败原因"
          />
          <div v-if="failuresTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="pages.failures"
              :page-size="pageSize"
              :total="failuresTotal"
              layout="prev, pager, next"
              small
              background
              @current-change="loadFailures"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="running">
        <template #label>
          <span class="tl"
            >正在运行<span v-if="runningTotal" class="badge live">{{ runningTotal }}</span></span
          >
        </template>
        <div v-loading="runningLoading" class="tab-body">
          <div v-if="running.length" class="list">
            <ActivityRow
              v-for="r in running"
              :key="r.run_id"
              row-class="live-row"
              :title="r.target_name"
              :sub="`${typeLabel(r.target_type)} · ${r.project_name} · ${rel(r.started_at)}`"
              status-text="运行中"
              status-class="run"
              live
              @click="openAutomationRun(r)"
            />
          </div>
          <ActivityEmpty
            v-else-if="!runningLoading"
            icon="VideoPause"
            title="暂无运行中的自动化"
            hint="执行场景或用例后在此实时显示"
          />
          <div v-if="runningTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="pages.running"
              :page-size="pageSize"
              :total="runningTotal"
              layout="prev, pager, next"
              small
              background
              @current-change="loadRunning"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="reports">
        <template #label>
          <span class="tl"
            >最近报告<span v-if="reportsTotal" class="badge">{{ reportsTotal }}</span></span
          >
        </template>
        <div v-loading="reportsLoading" class="tab-body">
          <div v-if="reports.length" class="list">
            <ActivityRow
              v-for="r in reports"
              :key="r.run_id"
              :title="r.target_name"
              :sub="reportSub(r)"
              :reason="r.error_message"
              :status-text="statusText(r)"
              :status-class="statusClass(r)"
              @click="openAutomationRun(r)"
            />
          </div>
          <ActivityEmpty
            v-else-if="!reportsLoading"
            icon="Document"
            title="暂无运行记录"
            hint="执行自动化测试后最近报告汇总在此"
          />
          <div v-if="reportsTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="pages.reports"
              :page-size="pageSize"
              :total="reportsTotal"
              layout="prev, pager, next"
              small
              background
              @current-change="loadReports"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="sched">
        <template #label>
          <span class="tl"
            >定时<span v-if="schedulesTotal" class="badge">{{ schedulesTotal }}</span></span
          >
        </template>
        <div v-loading="schedulesLoading" class="tab-body">
          <div v-if="schedules.length" class="list">
            <ActivityRow
              v-for="s in schedules"
              :key="s.schedule_id"
              :title="s.name"
              :sub="`${s.project_name} · 下次 ${fullTime(s.next_run_at)}`"
              @click="openSchedule(s)"
            />
          </div>
          <ActivityEmpty
            v-else-if="!schedulesLoading"
            icon="Clock"
            title="暂无即将执行的定时任务"
            hint="启用定时任务后按下次执行时间聚合"
          />
          <div v-if="schedulesTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="pages.schedules"
              :page-size="pageSize"
              :total="schedulesTotal"
              layout="prev, pager, next"
              small
              background
              @current-change="loadSchedules"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="manual">
        <template #label>
          <span class="tl"
            >手工<span v-if="manualTotal" class="badge">{{ manualTotal }}</span></span
          >
        </template>
        <div v-loading="manualLoading" class="tab-body">
          <div v-if="manual.length" class="list">
            <ActivityRow
              v-for="m in manual"
              :key="m.run_id"
              :title="m.name"
              :sub="`${m.project_name} · ${rel(m.created_at)}`"
              :status-text="manualStatusText(m)"
              :status-class="manualStatusClass(m)"
              @click="openManualRun(m)"
            />
          </div>
          <ActivityEmpty
            v-else-if="!manualLoading"
            icon="Edit"
            title="暂无手工测试单"
            hint="新建测试单执行后在此汇总"
          />
          <div v-if="manualTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="pages.manual"
              :page-size="pageSize"
              :total="manualTotal"
              layout="prev, pager, next"
              small
              background
              @current-change="loadManual"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="ai">
        <template #label>
          <span class="tl"
            >AI 任务<span v-if="aiTotal" class="badge">{{ aiTotal }}</span></span
          >
        </template>
        <div v-loading="aiLoading" class="tab-body">
          <div v-if="aiTasks.length" class="list">
            <ActivityRow
              v-for="t in aiTasks"
              :key="t.task_key"
              :title="t.title"
              :sub="`${aiCategoryLabel(t.category)} · ${t.project_name} · ${rel(t.updated_at)}`"
              :status-text="aiStatusText(t)"
              :status-class="aiStatusClass(t)"
              :live="t.status === 'running'"
              @click="onAiTaskClick(t)"
            />
          </div>
          <ActivityEmpty
            v-else-if="!aiLoading"
            icon="MagicStick"
            title="暂无 AI 任务"
            hint="需求解析、用例生成或接口 AI 生成后会在此汇总"
          />
          <div v-if="aiTotal > pageSize" class="pager">
            <el-pagination
              v-model:current-page="pages.ai"
              :page-size="pageSize"
              :total="aiTotal"
              layout="prev, pager, next"
              small
              background
              @current-change="loadAiTasks"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { Schemas } from '@/api/types'
import type {
  WorkbenchAiTaskItem,
  WorkbenchManualItem,
  WorkbenchReportItem,
  WorkbenchScheduleItem,
} from '@/api/apifox'
import { apifoxApi } from '@/api'
import { formatBeijingTime, formatRelativeTime } from '@/utils/datetime'
import { hubStatusText } from '@/utils/hubAiTaskStatus'
import { type WorkspaceNavPayload } from '@/composables/useWorkspaceOverviewNav'
import type { WorkspaceDomain } from '@/types/shell'
import ActivityRow from './ActivityRow.vue'
import ActivityEmpty from './ActivityEmpty.vue'

export type ActivityOpenNav = WorkspaceNavPayload

const emit = defineEmits<{ open: [projectId: number, nav?: ActivityOpenNav] }>()

const pageSize = 20
const pages = reactive({
  failures: 1,
  running: 1,
  reports: 1,
  schedules: 1,
  manual: 1,
  ai: 1,
})
const activeTab = ref('fail') // 默认「失败聚焦」——专业测试人员的首要关注

const failures = ref<WorkbenchReportItem[]>([])
const failuresTotal = ref(0)
const failuresLoading = ref(false)
const running = ref<Schemas['WorkbenchRunning'][]>([])
const runningTotal = ref(0)
const runningLoading = ref(false)
const reports = ref<WorkbenchReportItem[]>([])
const reportsTotal = ref(0)
const reportsLoading = ref(false)
const schedules = ref<WorkbenchScheduleItem[]>([])
const schedulesTotal = ref(0)
const schedulesLoading = ref(false)
const manual = ref<WorkbenchManualItem[]>([])
const manualTotal = ref(0)
const manualLoading = ref(false)
const aiTasks = ref<WorkbenchAiTaskItem[]>([])
const aiTotal = ref(0)
const aiLoading = ref(false)

const TYPE_LABEL: Record<string, string> = { scenario: '场景', case: '单接口', suite: '套件' }
const typeLabel = (t: string) => TYPE_LABEL[t] || '用例'
const rel = (v: string) => formatRelativeTime(v)
const fullTime = (v?: string | null) => (v ? formatBeijingTime(v) : '—')
const reportSub = (r: WorkbenchReportItem) =>
  `${typeLabel(r.target_type)} · ${r.project_name} · ${rel(r.started_at)}`

function statusClass(r: WorkbenchReportItem) {
  if (r.status === 'running') return 'run'
  return r.status === 'passed' ? 'ok' : 'bad'
}
function statusText(r: WorkbenchReportItem) {
  if (r.status === 'running') return '运行中'
  const label = r.status === 'passed' ? '通过' : '失败'
  return r.total_count > 0 ? `${label} ${r.passed_count}/${r.total_count}` : label
}
const manualStatusText = (m: WorkbenchManualItem) => {
  if (m.failed_count > 0) return `失败 ${m.failed_count}`
  if (m.status === 'running') return '执行中'
  return m.total_count > 0 ? `通过 ${m.passed_count}/${m.total_count}` : '待执行'
}
const manualStatusClass = (m: WorkbenchManualItem) =>
  m.failed_count > 0 ? 'bad' : m.status === 'running' ? 'run' : 'ok'

const AI_CATEGORY_LABEL: Record<string, string> = {
  requirement: 'AI 需求',
  functional: 'AI 用例',
  endpoint: 'AI 接口',
}
const aiCategoryLabel = (c: string) => AI_CATEGORY_LABEL[c] || 'AI'

const AI_SECTION: Record<string, string> = {
  requirement: 'ai-req',
  functional: 'ai-case',
  endpoint: 'ai-api',
}

function aiStatusText(t: WorkbenchAiTaskItem) {
  const label = hubStatusText(t.status)
  const total = t.total_items ?? 0
  if (t.status === 'pending') {
    return total > 0 ? `${label} · 0/${total}` : label
  }
  if (t.status === 'running' && total > 0) {
    return `${label} ${t.done_items ?? 0}/${total}`
  }
  return label
}

function aiStatusClass(t: WorkbenchAiTaskItem) {
  if (t.status === 'running') return 'run'
  if (t.status === 'pending') return 'run'
  if (t.status === 'failed') return 'bad'
  if (t.status === 'partial') return 'bad'
  return 'ok'
}

function openActivityNav(
  projectId: number,
  domain: WorkspaceDomain,
  section: string,
  query?: Record<string, string>,
) {
  emit('open', projectId, { domain, section, query })
}

/** 与自动化概览「最近执行记录」一致：跳转测试报告并打开 run 详情。 */
function openAutomationRun(item: { project_id: number; run_id: number }) {
  openActivityNav(item.project_id, 'automation', 'reports', { run: String(item.run_id) })
}

function openSchedule(item: WorkbenchScheduleItem) {
  openActivityNav(item.project_id, 'automation', 'schedules')
}

function openManualRun(item: WorkbenchManualItem) {
  openActivityNav(item.project_id, 'functional', 'func-runs')
}

function onAiTaskClick(t: WorkbenchAiTaskItem) {
  const section = AI_SECTION[t.category] || 'ai-overview'
  openActivityNav(t.project_id, 'ai_tasks', section, { task: String(t.task_id) })
}

async function loadPage<T>(
  fn: (p: { page: number; page_size: number }) => Promise<{ items: T[]; total: number }>,
  items: { value: T[] },
  total: { value: number },
  loading: { value: boolean },
  page: number,
) {
  loading.value = true
  try {
    const data = await fn({ page, page_size: pageSize })
    items.value = data.items
    total.value = data.total
  } catch {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

const loadFailures = () =>
  loadPage(apifoxApi.workbenchFailures, failures, failuresTotal, failuresLoading, pages.failures)
const loadRunning = () =>
  loadPage(apifoxApi.workbenchRunning, running, runningTotal, runningLoading, pages.running)
const loadReports = () =>
  loadPage(apifoxApi.workbenchReports, reports, reportsTotal, reportsLoading, pages.reports)
const loadSchedules = () =>
  loadPage(
    apifoxApi.workbenchSchedules,
    schedules,
    schedulesTotal,
    schedulesLoading,
    pages.schedules,
  )
const loadManual = () =>
  loadPage(apifoxApi.workbenchManual, manual, manualTotal, manualLoading, pages.manual)
const loadAiTasks = () =>
  loadPage(apifoxApi.workbenchAiTasks, aiTasks, aiTotal, aiLoading, pages.ai)

async function refresh() {
  await Promise.all([
    loadFailures(),
    loadRunning(),
    loadReports(),
    loadSchedules(),
    loadManual(),
    loadAiTasks(),
  ])
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

.panel-head {
  height: 32px;
  padding: 0 var(--ax-space-3-5);
  display: flex;
  align-items: baseline;
  flex: none;
}

.panel-title {
  color: var(--ax-text);
  font-size: var(--ax-text-body-sm-size);
  font-weight: 600;
  line-height: 32px;
}

.activity-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.activity-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 var(--ax-space-2);
  border-bottom: 1px solid var(--ax-border);
  flex: none;
  background: transparent;
}

.activity-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.activity-tabs :deep(.el-tabs__item) {
  height: 36px;
  font-size: var(--ax-text-caption-size);
  padding: 0 var(--ax-space-2);
  color: var(--ax-text-secondary);
}

.activity-tabs :deep(.el-tabs__item.is-active) {
  color: var(--ax-brand);
  font-weight: 600;
}

.activity-tabs :deep(.el-tabs__active-bar) {
  height: 2px;
  border-radius: 1px;
}

.activity-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  padding: 0;
}

.activity-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.tl {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1);
}

.badge {
  min-width: 16px;
  height: 16px;
  padding: 0 var(--ax-space-1);
  border-radius: var(--ax-radius-sm);
  background: var(--ax-bg-hover);
  color: var(--ax-text-secondary);
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  text-align: center;
}

.badge.live {
  background: var(--ax-tag-green-bg);
  color: var(--ax-tag-green-fg);
}

.badge.fail {
  background: var(--ax-tag-red-bg);
  color: var(--ax-tag-red-fg);
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
  padding: var(--ax-space-2);
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-1);
}

.pager {
  flex: none;
  display: flex;
  justify-content: center;
  padding: var(--ax-space-2);
  border-top: 1px solid var(--ax-border);
}
</style>
