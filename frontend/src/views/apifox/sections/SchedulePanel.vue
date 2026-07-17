<template>
  <div class="schedule-panel">
    <div class="toolbar">
      <span class="tip"
        >定时任务按计划自动执行用例/场景，结果落入测试报告（触发来源标记为「定时」）。</span
      >
      <el-button size="small" type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新建定时任务
      </el-button>
    </div>

    <el-table :data="schedules" size="small" border>
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
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="success"
            size="small"
            :loading="runningId === row.id"
            @click="runNow(row)"
            >立即执行</el-button
          >
          <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无定时任务</template>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑定时任务' : '新建定时任务'"
      width="520px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="任务名称" />
        </el-form-item>
        <el-form-item label="目标类型">
          <el-radio-group v-model="form.target_type" @change="form.target_id = null">
            <el-radio value="case">用例</el-radio>
            <el-radio value="scenario">场景</el-radio>
            <el-radio value="suite">套件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="执行目标">
          <el-select v-model="form.target_id" filterable placeholder="选择目标" style="width: 100%">
            <el-option v-for="o in targetOptions" :key="o.id" :label="o.label" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="环境">
          <el-select
            v-model="form.environment_id"
            clearable
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
            <el-input v-model="form.cron_expr" placeholder="分 时 日 月 周，如 0 9 * * 1" />
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const schedules = ref<Schemas['ScheduleOut'][]>([])
const cases = ref<Schemas['ProjectCaseBrief'][]>([])
const scenarios = ref<Schemas['ScenarioBrief'][]>([])
const suites = ref<Schemas['SuiteBrief'][]>([])
const environments = ref<Schemas['EnvironmentOut'][]>([])
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

const targetOptions = computed(() => {
  if (form.target_type === 'scenario')
    return scenarios.value.map((s) => ({ id: s.id, label: s.name }))
  if (form.target_type === 'suite') return suites.value.map((s) => ({ id: s.id, label: s.name }))
  return cases.value.map((c) => ({ id: c.id, label: `[${c.endpoint_method}] ${c.name}` }))
})

function fmt(t: string | null | undefined) {
  return t ? String(t).replace('T', ' ').slice(0, 16) : ''
}

function targetTypeLabel(t: string) {
  return t === 'scenario' ? '场景' : t === 'suite' ? '套件' : '用例'
}

function targetTagType(t: string) {
  return t === 'scenario' ? 'warning' : t === 'suite' ? 'primary' : 'success'
}

async function loadAll() {
  const [sch, cs, scn, sui, envs] = await Promise.all([
    apifoxApi.listSchedules(pid.value),
    apifoxApi.listProjectCases(pid.value),
    apifoxApi.listScenarios(pid.value),
    apifoxApi.listSuites(pid.value),
    apifoxApi.listEnvironments(pid.value),
  ])
  schedules.value = sch
  cases.value = cs
  scenarios.value = scn
  suites.value = sui
  environments.value = envs
}

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
  }
  dialogVisible.value = true
}

function buildPayload() {
  const p = {
    name: form.name,
    target_type: form.target_type,
    target_id: form.target_id,
    environment_id: form.environment_id,
    schedule_type: form.schedule_type,
    enabled: form.enabled,
  }
  if (form.schedule_type === 'interval') {
    p.interval_minutes = form.interval_minutes
  } else if (form.schedule_type === 'cron') {
    p.cron_expr = form.cron_expr.trim()
  } else {
    p.run_time = runTime.value
    if (form.schedule_type === 'weekly') p.week_day = form.week_day
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
    const res = await apifoxApi.runScheduleNow(row.id)
    ElMessage.success(
      `执行完成：${res.last_run_status === 'passed' ? '通过' : '失败'}，可在测试报告查看`,
    )
    await loadAll()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '执行失败')
  } finally {
    runningId.value = null
  }
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
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.tip {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}

.target-name {
  margin-left: 6px;
}

.time {
  font-size: 12px;
  color: var(--ax-text-tertiary);
  margin-left: 4px;
}

.muted {
  color: var(--ax-text-disabled);
}

.cron-hint {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ax-text-placeholder);
}

.cron-hint code {
  padding: 0 4px;
  border-radius: 3px;
  background: var(--ax-bg-subtle);
  color: var(--ax-text-secondary);
}
</style>
