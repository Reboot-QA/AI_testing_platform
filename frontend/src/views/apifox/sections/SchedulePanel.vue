<template>
  <div class="schedule-panel">
    <div class="toolbar">
      <span class="tip"
        >定时任务按计划自动执行用例/场景，结果落入测试报告（触发来源标记为「定时」）。</span
      >
      <el-button type="primary" size="small" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新建定时任务
      </el-button>
    </div>

    <div class="filters">
      <el-input
        v-model="filterScheduleId"
        class="schedule-id"
        size="small"
        clearable
        placeholder="任务 ID"
        @keyup.enter="search"
      />
      <el-input
        v-model="filterKeyword"
        class="search"
        size="small"
        clearable
        :maxlength="SEARCH_MAX_LEN"
        placeholder="搜索任务名称"
        @keyup.enter="search"
      >
        <template #prefix
          ><el-icon><Search /></el-icon
        ></template>
      </el-input>
      <el-button type="primary" size="small" @click="search">搜索</el-button>
      <el-button size="small" @click="resetFilters">重置</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="schedules"
      class="schedule-table"
      height="100%"
      size="small"
      border
    >
      <el-table-column label="ID" prop="id" width="72" />
      <el-table-column label="名称" prop="name" min-width="140" />
      <el-table-column label="目标" min-width="180">
        <template #default="{ row }">
          <el-tag size="small" :type="targetTagType(row.target_type)">
            {{ targetTypeLabel(row.target_type) }}
          </el-tag>
          <span class="target-name">{{ row.target_name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="执行计划" prop="schedule_desc" min-width="120" />
      <el-table-column label="启用" width="70">
        <template #default="{ row }">
          <el-switch
            :model-value="row.enabled"
            :loading="togglingId === row.id"
            @change="toggle(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="上次执行" min-width="160">
        <template #default="{ row }">
          <template v-if="row.last_run_at">
            <el-tag size="small" :type="row.last_run_status === 'passed' ? 'success' : 'danger'">
              {{ row.last_run_status === 'passed' ? '通过' : '失败' }}
            </el-tag>
            <span class="time">{{ fmt(row.last_run_at) }}</span>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="下次执行" min-width="150">
        <template #default="{ row }">
          <span :class="row.next_run_at ? 'time' : 'muted'">{{
            row.next_run_at ? fmt(row.next_run_at) : '已停用'
          }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="success"
            size="small"
            :loading="runningId === row.id"
            @click="runNow(row)"
            >立即执行</el-button
          >
          <el-button
            link
            type="primary"
            size="small"
            :disabled="!row.last_run_id"
            @click="viewReport(row)"
            >查看</el-button
          >
          <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无定时任务" :image-size="60" />
      </template>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑定时任务' : '新建定时任务'"
      width="520px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="form.name" :maxlength="TITLE_MAX_LEN" placeholder="任务名称" />
        </el-form-item>
        <el-form-item label="目标类型">
          <el-radio-group v-model="form.target_type" @change="onTargetTypeChange">
            <el-radio value="case">用例</el-radio>
            <el-radio value="scenario">场景</el-radio>
            <el-radio value="suite">套件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="执行目标">
          <div class="schedule-target-picker">
            <div v-if="selectedTargetDisplay" class="schedule-target-display">
              <template v-if="form.target_type === 'case' && selectedCase">
                <MethodTag :method="selectedCase.endpoint_method" />
                <span class="schedule-target-path">{{ selectedCase.endpoint_path }}</span>
                <span class="schedule-target-name">{{ selectedCase.name }}</span>
              </template>
              <template v-else-if="form.target_type === 'scenario' && selectedScenario">
                <span class="target-kind-badge target-kind-badge--scenario">场景</span>
                <span class="schedule-target-name">{{ selectedScenario.name }}</span>
              </template>
              <template v-else-if="form.target_type === 'suite' && selectedSuite">
                <span class="target-kind-badge target-kind-badge--suite">套件</span>
                <span class="schedule-target-name">{{ selectedSuite.name }}</span>
              </template>
              <el-button link type="danger" size="small" @click="clearTarget">清除</el-button>
            </div>
            <span v-else class="schedule-target-placeholder">{{ targetPickPlaceholder }}</span>
            <el-button type="primary" plain @click="openTargetPicker">{{
              targetPickButtonLabel
            }}</el-button>
          </div>
        </el-form-item>
        <el-form-item label="环境">
          <el-select
            v-model="form.environment_id"
            clearable
            :value-on-clear="null"
            placeholder="不指定环境（用绝对地址）"
            style="width: 100%"
          >
            <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度类型">
          <el-select v-model="form.schedule_type" style="width: 100%">
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="固定间隔" value="interval" />
            <el-option label="Cron 表达式" value="cron" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.schedule_type === 'weekly'" label="星期">
          <el-select v-model="form.week_day" style="width: 100%">
            <el-option v-for="(d, i) in weekdays" :key="i" :label="d" :value="i" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="['daily', 'weekly'].includes(form.schedule_type)" label="执行时间">
          <el-time-picker
            v-model="runTime"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="HH:mm"
          />
        </el-form-item>
        <el-form-item v-if="form.schedule_type === 'interval'" label="间隔(分钟)">
          <el-input-number v-model="form.interval_minutes" :min="5" :max="10080" />
        </el-form-item>
        <el-form-item v-if="form.schedule_type === 'cron'" label="Cron 表达式">
          <div style="width: 100%">
            <el-input
              v-model="form.cron_expr"
              :maxlength="VALUE_MAX_LEN"
              placeholder="分 时 日 月 周，如 0 9 * * 1"
            />
            <div class="cron-hint">
              标准 5 段：分(0-59) 时(0-23) 日(1-31) 月(1-12) 周(0-6，0=周日)。 示例：每小时
              <code>0 * * * *</code> · 每天 8:30 <code>30 8 * * *</code> · 工作日 9 点
              <code>0 9 * * 1-5</code>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <ImportEndpointTreeDialog ref="targetPickerRef" :project-id="pid" @confirm="onTargetPicked" />
  </div>
</template>

<script setup lang="ts">
import { TITLE_MAX_LEN, VALUE_MAX_LEN, SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import {
  type ImportConfirmPayload,
  type ImportScenarioBrief,
  type ImportSuiteBrief,
  type ImportSuiteCaseBrief,
} from '@/composables/useImportCaseTree'
import ImportEndpointTreeDialog from '@/components/apifox/import-export/ImportEndpointTreeDialog.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const pid = useRouteParamId()
const route = useRoute()
const router = useRouter()

const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const schedules = ref<Schemas['ScheduleOut'][]>([])
const loading = ref(false)
const filterKeyword = ref('')
const filterScheduleId = ref('')
const cases = ref<Schemas['ProjectCaseBrief'][]>([])
const scenarios = ref<Schemas['ScenarioBrief'][]>([])
const suites = ref<Schemas['SuiteBrief'][]>([])
const environments = ref<Schemas['EnvironmentOut'][]>([])
const endpoints = ref<Schemas['EndpointBrief'][]>([])
const selectedCase = ref<ImportSuiteCaseBrief | null>(null)
const selectedScenario = ref<ImportScenarioBrief | null>(null)
const selectedSuite = ref<ImportSuiteBrief | null>(null)
const targetPickerRef = ref<InstanceType<typeof ImportEndpointTreeDialog> | null>(null)
const dialogVisible = ref(false)
const editing = ref<Schemas['ScheduleOut'] | null>(null)
const saving = ref(false)
const togglingId = ref<number | null>(null)
const runningId = ref<number | null>(null)
const runTime = ref('09:00')

const form = reactive({
  name: '',
  target_type: 'case' as 'case' | 'scenario' | 'suite',
  target_id: null as number | null,
  environment_id: null as number | null,
  schedule_type: 'daily' as string,
  week_day: 0,
  interval_minutes: 60,
  cron_expr: '',
  enabled: true,
})

const selectedTargetDisplay = computed(() => {
  if (form.target_type === 'case') return !!selectedCase.value
  if (form.target_type === 'scenario') return !!selectedScenario.value
  return !!selectedSuite.value
})

const targetPickPlaceholder = computed(() =>
  form.target_type === 'case'
    ? '未选择用例'
    : form.target_type === 'scenario'
      ? '未选择场景'
      : '未选择套件',
)

const targetPickButtonLabel = computed(() =>
  form.target_type === 'case'
    ? '选择用例'
    : form.target_type === 'scenario'
      ? '选择场景'
      : '选择套件',
)

function onTargetTypeChange() {
  selectedCase.value = null
  selectedScenario.value = null
  selectedSuite.value = null
  form.target_id = null
}

function endpointPathFor(endpointId: number): string {
  return endpoints.value.find((e) => e.id === endpointId)?.path ?? ''
}

function caseBriefFromProject(c: Schemas['ProjectCaseBrief']): ImportSuiteCaseBrief {
  return {
    id: c.id,
    name: c.name,
    endpoint_id: c.endpoint_id,
    endpoint_method: c.endpoint_method,
    endpoint_name: c.endpoint_name,
    endpoint_path: endpointPathFor(c.endpoint_id),
  }
}

function openTargetPicker() {
  const mode =
    form.target_type === 'case'
      ? 'pick-schedule-case'
      : form.target_type === 'scenario'
        ? 'pick-schedule-scenario'
        : 'pick-schedule-suite'
  targetPickerRef.value?.open(mode)
}

function clearTarget() {
  selectedCase.value = null
  selectedScenario.value = null
  selectedSuite.value = null
  form.target_id = null
}

function onTargetPicked(payload: ImportConfirmPayload) {
  if (payload.mode === 'pick-schedule-case') {
    selectedCase.value = payload.case
    selectedScenario.value = null
    selectedSuite.value = null
    form.target_id = payload.case.id
  } else if (payload.mode === 'pick-schedule-scenario') {
    selectedScenario.value = payload.scenario
    selectedCase.value = null
    selectedSuite.value = null
    form.target_id = payload.scenario.id
  } else if (payload.mode === 'pick-schedule-suite') {
    selectedSuite.value = payload.suite
    selectedCase.value = null
    selectedScenario.value = null
    form.target_id = payload.suite.id
  }
}

function fillTargetFromRow(row: Schemas['ScheduleOut']) {
  selectedCase.value = null
  selectedScenario.value = null
  selectedSuite.value = null
  if (row.target_type === 'case') {
    const c = cases.value.find((x) => x.id === row.target_id)
    selectedCase.value = c
      ? caseBriefFromProject(c)
      : row.target_id
        ? {
            id: row.target_id,
            name: row.target_name,
            endpoint_id: 0,
            endpoint_method: 'GET',
            endpoint_name: '',
            endpoint_path: '',
          }
        : null
  } else if (row.target_type === 'scenario') {
    const s = scenarios.value.find((x) => x.id === row.target_id)
    selectedScenario.value = s
      ? { id: s.id, name: s.name }
      : row.target_id
        ? { id: row.target_id, name: row.target_name }
        : null
  } else {
    const su = suites.value.find((x) => x.id === row.target_id)
    selectedSuite.value = su
      ? { id: su.id, name: su.name }
      : row.target_id
        ? { id: row.target_id, name: row.target_name }
        : null
  }
}

function fmt(t: string | null | undefined) {
  return t ? String(t).replace('T', ' ').slice(0, 16) : ''
}

function targetTypeLabel(t: string) {
  return t === 'scenario' ? '场景' : t === 'suite' ? '套件' : '用例'
}

function targetTagType(t: string) {
  return t === 'scenario' ? 'warning' : t === 'suite' ? 'primary' : 'success'
}

function parseScheduleIdFilter(raw: string): number | null {
  const text = raw.trim()
  if (!/^\d+$/.test(text)) return null
  const id = Number(text)
  return Number.isInteger(id) && id > 0 ? id : null
}

async function loadSchedules() {
  loading.value = true
  try {
    const params: { keyword?: string; schedule_id?: number } = {}
    const kw = filterKeyword.value.trim()
    if (kw) params.keyword = kw
    const scheduleId = parseScheduleIdFilter(filterScheduleId.value)
    if (scheduleId) params.schedule_id = scheduleId
    schedules.value = await apifoxApi.listSchedules(pid.value, params)
  } finally {
    loading.value = false
  }
}

function search() {
  filterScheduleId.value = filterScheduleId.value.replace(/\D/g, '')
  void loadSchedules()
}

function resetFilters() {
  filterKeyword.value = ''
  filterScheduleId.value = ''
  void loadSchedules()
}

async function loadMeta() {
  const [cs, scn, sui, envs, eps] = await Promise.all([
    apifoxApi.listProjectCases(pid.value),
    apifoxApi.listScenarios(pid.value),
    apifoxApi.listSuites(pid.value),
    apifoxApi.listEnvironments(pid.value),
    apifoxApi.listEndpoints(pid.value),
  ])
  cases.value = cs
  scenarios.value = scn
  suites.value = sui
  environments.value = envs
  endpoints.value = eps
}

async function loadAll() {
  await Promise.all([loadMeta(), loadSchedules()])
}

defineExpose({ create: () => openDialog() })

function openDialog(row?: Schemas['ScheduleOut']) {
  editing.value = row || null
  if (row) {
    Object.assign(form, {
      name: row.name,
      target_type: row.target_type,
      target_id: row.target_id,
      environment_id: row.environment_id,
      schedule_type: row.schedule_type,
      week_day: row.week_day ?? 0,
      interval_minutes: row.interval_minutes ?? 60,
      cron_expr: row.cron_expr || '',
      enabled: row.enabled,
    })
    runTime.value = row.run_time || '09:00'
    fillTargetFromRow(row)
  } else {
    Object.assign(form, {
      name: '',
      target_type: 'case',
      target_id: null,
      environment_id: null,
      schedule_type: 'daily',
      week_day: 0,
      interval_minutes: 60,
      cron_expr: '',
      enabled: true,
    })
    runTime.value = '09:00'
    selectedCase.value = null
    selectedScenario.value = null
    selectedSuite.value = null
  }
  dialogVisible.value = true
}

function buildPayload(): Schemas['ScheduleCreate'] {
  const p: Schemas['ScheduleCreate'] = {
    name: form.name,
    target_type: form.target_type,
    target_id: form.target_id!,
    environment_id: form.environment_id,
    schedule_type: form.schedule_type,
    run_time: runTime.value,
    enabled: form.enabled,
  }
  if (form.schedule_type === 'interval') {
    p.interval_minutes = form.interval_minutes
    p.run_time = null
  } else if (form.schedule_type === 'cron') {
    p.cron_expr = form.cron_expr.trim()
    p.run_time = null
  } else if (form.schedule_type === 'weekly') {
    p.week_day = form.week_day
  }
  return p
}

async function save() {
  if (!form.name.trim()) return ElMessage.warning('请填写名称')
  if (!form.target_id) return ElMessage.warning('请选择执行目标')
  saving.value = true
  try {
    if (editing.value) await apifoxApi.updateSchedule(editing.value.id, buildPayload())
    else await apifoxApi.createSchedule(pid.value, buildPayload())
    ElMessage.success('已保存')
    dialogVisible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function toggle(row: Schemas['ScheduleOut']) {
  togglingId.value = row.id
  try {
    await apifoxApi.updateSchedule(row.id, { enabled: !row.enabled })
    await loadAll()
  } finally {
    togglingId.value = null
  }
}

async function runNow(row: Schemas['ScheduleOut']) {
  runningId.value = row.id
  try {
    // 后端触发即返回（执行体放后台跑，避免套件/多用例长任务占请求线程超时）；结果稍后在测试报告查看
    await apifoxApi.runScheduleNow(row.id)
    ElMessage.success('已触发执行，请稍后在测试报告查看结果')
    await loadAll()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '触发失败')
  } finally {
    runningId.value = null
  }
}

function viewReport(row: Schemas['ScheduleOut']) {
  if (!row.last_run_id) {
    ElMessage.info('该任务尚未产生测试报告')
    return
  }
  void router.push({
    name: 'WorkspaceAutomationReports',
    params: route.params,
    query: { run: String(row.last_run_id), from: 'schedules' },
  })
}

async function del(row: Schemas['ScheduleOut']) {
  await ElMessageBox.confirm(`确认删除定时任务「${row.name}」？`, '提示', { type: 'warning' })
  await apifoxApi.deleteSchedule(row.id)
  ElMessage.success('已删除')
  await loadAll()
}

onMounted(loadAll)
</script>

<style scoped>
.schedule-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.filters {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2-5);
  flex: none;
}

.filters .schedule-id {
  width: 120px;
}

.filters .search {
  width: 220px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-space-3);
  flex: none;
}

.tip {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
}

.schedule-table {
  flex: 1;
  min-height: 0;
}

.target-name {
  margin-left: var(--ax-space-1-5);
}

.target-node {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  min-width: 0;
}

.target-node-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.target-node-path {
  flex-shrink: 0;
  font-family: Consolas, Monaco, monospace;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-placeholder);
}

.time {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-tertiary);
  margin-left: var(--ax-space-1);
}

.muted {
  color: var(--ax-text-disabled);
}

.cron-hint {
  margin-top: var(--ax-space-1-5);
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-leading-relaxed);
  color: var(--ax-text-placeholder);
}

.cron-hint code {
  padding: 0 var(--ax-space-1);
  border-radius: 3px;
  background: var(--ax-bg-subtle);
  color: var(--ax-text-secondary);
}

.schedule-target-picker {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--ax-space-2);
  width: 100%;
}

.schedule-target-display {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ax-space-1-5);
  width: 100%;
  padding: var(--ax-space-2);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  font-size: var(--ax-font-sm);
}

.schedule-target-path {
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
}

.schedule-target-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-target-placeholder {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-placeholder);
}

.target-kind-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 var(--ax-space-1);
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
}

.target-kind-badge--scenario {
  color: var(--ax-tag-orange-fg);
  background: color-mix(in srgb, var(--ax-tag-orange-fg) 14%, transparent);
}

.target-kind-badge--suite {
  color: var(--color-purple-6);
  background: color-mix(in srgb, var(--color-purple-6) 14%, transparent);
}
</style>
