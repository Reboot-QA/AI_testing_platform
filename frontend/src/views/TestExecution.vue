<template>
  <div class="test-execution">
    <div class="toolbar" :class="{ 'list-toolbar': !executingRun }">
      <el-select
        v-if="!scoped"
        v-model="projectId"
        filterable
        placeholder="选择项目"
        style="width: 220px"
        @change="handleProjectChange"
      >
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button v-if="!executingRun" type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon> 新建测试单
      </el-button>
      <el-button v-if="executingRun" @click="backToList">返回测试单</el-button>
    </div>

    <!-- 测试单列表 -->
    <el-card v-if="!executingRun" shadow="never" class="list-card">
      <el-table
        v-loading="runsLoading"
        :data="runs"
        stripe
        border
        class="runs-table"
        height="100%"
      >
        <el-table-column label="测试单" min-width="180">
          <template #default="{ row }">
            <div class="run-name-cell">
              <span class="run-name" :title="row.name">{{ row.name }}</span>
              <span class="run-sub">
                {{ row.build_name || '无版本' }} / {{ row.executor_name || '未分配' }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="160">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress
                :percentage="runProgress(row)"
                :show-text="false"
                :status="
                  row.status === 'finished' && row.failed_count
                    ? 'exception'
                    : row.status === 'finished'
                      ? 'success'
                      : ''
                "
                :stroke-width="8"
              />
              <span class="progress-text">
                {{ row.total_count - row.pending_count }}/{{ row.total_count }} ({{
                  runProgress(row)
                }}%)
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="结果" min-width="180">
          <template #default="{ row }">
            <div class="result-tags">
              <el-tag
                type="success"
                :class="{ 'result-tag-clickable': row.passed_count > 0 }"
                @click="openRunCasesByResult(row, 'pass', row.passed_count)"
              >
                通过 {{ row.passed_count }}
              </el-tag>
              <el-tag
                type="danger"
                :class="{ 'result-tag-clickable': row.failed_count > 0 }"
                @click="openRunCasesByResult(row, 'fail', row.failed_count)"
              >
                失败 {{ row.failed_count }}
              </el-tag>
              <el-tag
                type="warning"
                :class="{ 'result-tag-clickable': row.blocked_count > 0 }"
                @click="openRunCasesByResult(row, 'blocked', row.blocked_count)"
              >
                阻塞 {{ row.blocked_count }}
              </el-tag>
              <el-tag
                type="info"
                :class="{ 'result-tag-clickable': row.skipped_count > 0 }"
                @click="openRunCasesByResult(row, 'skip', row.skipped_count)"
              >
                跳过 {{ row.skipped_count }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="92" align="center">
          <template #default="{ row }">
            <el-tag :type="runStatusType[row.status]" size="small">{{
              runStatusLabel[row.status]
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" class-name="run-actions-col">
          <template #default="{ row }">
            <div class="run-actions">
              <el-button link type="primary" @click="enterExecution(row)">执行</el-button>
              <el-button link type="primary" @click="viewRunDetail(row)">详情</el-button>
              <el-popconfirm title="确认删除该测试单？" @confirm="removeRun(row)">
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="runsTotal > 0"
        v-model:current-page="runsPage"
        v-model:page-size="runsPageSize"
        class="runs-pagination"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50, 100]"
        :total="runsTotal"
        @current-change="loadRuns"
        @size-change="handleRunsPageSizeChange"
      />
    </el-card>

    <!-- 用例执行界面（禅道风格） -->
    <div v-else class="execute-panel">
      <el-card shadow="never" class="run-header">
        <div class="run-header-main">
          <div>
            <h3>{{ executingRun.name }}</h3>
            <div class="run-meta">
              <span v-if="executingRun.build_name">版本：{{ executingRun.build_name }}</span>
              <span>执行人：{{ executingRun.executor_name || '-' }}</span>
              <el-tag :type="runStatusType[executingRun.status]" size="small">
                {{ runStatusLabel[executingRun.status] }}
              </el-tag>
            </div>
          </div>
          <div class="run-stats">
            <div class="stat-item pass">
              <strong>{{ executingRun.passed_count }}</strong
              ><span>通过</span>
            </div>
            <div class="stat-item fail">
              <strong>{{ executingRun.failed_count }}</strong
              ><span>失败</span>
            </div>
            <div class="stat-item block">
              <strong>{{ executingRun.blocked_count }}</strong
              ><span>阻塞</span>
            </div>
            <div class="stat-item skip">
              <strong>{{ executingRun.skipped_count }}</strong
              ><span>跳过</span>
            </div>
            <div class="stat-item pending">
              <strong>{{ executingRun.pending_count }}</strong
              ><span>待测</span>
            </div>
            <div class="stat-item rate">
              <strong>{{ executingRun.pass_rate }}%</strong><span>通过率</span>
            </div>
          </div>
        </div>
        <el-progress
          :percentage="runProgress(executingRun)"
          :stroke-width="10"
          :status="
            executingRun.status === 'finished' && executingRun.failed_count
              ? 'exception'
              : executingRun.status === 'finished'
                ? 'success'
                : ''
          "
        />
      </el-card>

      <div class="execute-body">
        <el-card shadow="never" class="case-list-card">
          <div class="case-list-toolbar">
            <el-select v-model="caseFilter" style="width: 120px" @change="onCaseFilterChange">
              <el-option label="全部" value="all" />
              <el-option label="待测" value="pending" />
              <el-option label="通过" value="pass" />
              <el-option label="失败" value="fail" />
              <el-option label="阻塞" value="blocked" />
              <el-option label="跳过" value="skip" />
            </el-select>
          </div>
          <div class="case-list">
            <div
              v-for="item in filteredCases"
              :key="item.id"
              class="case-list-item"
              :class="{ active: currentCase?.id === item.id, [item.result]: true }"
              @click="selectCase(item)"
            >
              <span class="case-index">{{ item.testcase_sort_order || '—' }}</span>
              <span class="case-title" :title="item.case_title">{{ item.case_title }}</span>
              <el-tag :type="resultType[item.result]" size="small">{{
                resultLabel[item.result]
              }}</el-tag>
            </div>
            <el-empty v-if="!filteredCases.length" description="暂无匹配用例" />
          </div>
        </el-card>

        <el-card v-if="currentCase" shadow="never" class="case-detail-card">
          <div class="case-detail-header">
            <div>
              <h4>{{ currentCase.case_title }}</h4>
              <div class="case-tags">
                <el-tag size="small">{{ currentCase.case_priority }}</el-tag>
                <el-tag size="small" type="info">{{
                  formatCaseTypeLabel(currentCase.case_type)
                }}</el-tag>
                <el-tag :type="resultType[currentCase.result]" size="small">
                  {{ resultLabel[currentCase.result] }}
                </el-tag>
              </div>
            </div>
            <div class="case-nav">
              <el-button :disabled="!prevCase" @click="selectCase(prevCase)">上一条</el-button>
              <el-button :disabled="!nextCase" @click="selectCase(nextCase)">下一条</el-button>
            </div>
          </div>

          <el-descriptions :column="1" class="case-info">
            <el-descriptions-item label="前置条件">
              <pre class="text-block">{{ currentCase.preconditions || '无' }}</pre>
            </el-descriptions-item>
            <el-descriptions-item label="测试步骤">
              <pre class="text-block">{{ currentCase.steps || '无' }}</pre>
            </el-descriptions-item>
            <el-descriptions-item label="预期结果">
              <pre class="text-block">{{ currentCase.expected_results || '无' }}</pre>
            </el-descriptions-item>
          </el-descriptions>

          <el-form label-width="90px" class="result-form">
            <el-form-item label="实际结果">
              <el-input
                v-model="resultForm.actual_result"
                :maxlength="LONG_TEXT_MAX_LEN"
                type="textarea"
                :rows="4"
                placeholder="记录实际执行结果"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input
                v-model="resultForm.remark"
                :maxlength="LONG_TEXT_MAX_LEN"
                type="textarea"
                :rows="2"
                placeholder="缺陷编号、环境问题等"
              />
            </el-form-item>
          </el-form>

          <div class="result-actions">
            <el-button type="success" :loading="submitting" @click="submitResult('pass')">
              通过
            </el-button>
            <el-button type="danger" :loading="submitting" @click="submitResult('fail')">
              失败
            </el-button>
            <el-button type="warning" :loading="submitting" @click="submitResult('blocked')">
              阻塞
            </el-button>
            <el-button type="info" :loading="submitting" @click="submitResult('skip')">
              跳过
            </el-button>
          </div>
        </el-card>

        <el-card v-else shadow="never" class="case-detail-card empty-detail">
          <el-empty description="请从左侧选择用例开始执行" />
        </el-card>
      </div>
    </div>

    <!-- 新建测试单 -->
    <el-dialog v-model="createDialogVisible" title="新建测试单" width="760px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="项目" prop="project_id">
          <el-select
            v-model="createForm.project_id"
            filterable
            placeholder="请选择项目"
            style="width: 100%"
            @change="handleCreateProjectChange"
          >
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="createForm.name"
            :maxlength="TITLE_MAX_LEN"
            placeholder="请输入测试单名称"
          />
        </el-form-item>
        <el-form-item label="版本/构建">
          <el-input
            v-model="createForm.build_name"
            :maxlength="VALUE_MAX_LEN"
            placeholder="例如：V1.2.0"
          />
        </el-form-item>
        <el-form-item label="说明">
          <el-input
            v-model="createForm.description"
            :maxlength="LONG_TEXT_MAX_LEN"
            type="textarea"
            :rows="2"
          />
        </el-form-item>
        <el-form-item label="需求点" prop="requirement_ids">
          <div class="requirement-select-row">
            <el-select
              v-model="createForm.requirement_ids"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :disabled="!createForm.project_id"
              :placeholder="createForm.project_id ? '请选择需求点' : '请先选择项目'"
              style="flex: 1"
              @change="loadAvailableCases"
            >
              <el-option
                v-for="r in createRequirements"
                :key="r.id"
                :label="r.title"
                :value="r.id"
              />
            </el-select>
            <el-button
              link
              type="primary"
              :disabled="!createRequirements.length"
              @click="toggleSelectAllRequirements"
            >
              {{ allRequirementsSelected ? '取消全选' : '全选' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <div class="select-cases-toolbar">
        <span>选用例<span class="select-cases-hint">（仅已通过评审）</span></span>
        <el-button
          link
          type="primary"
          :disabled="!createForm.requirement_ids.length || !availableCases.length"
          @click="toggleSelectAll"
        >
          {{ allSelected ? '取消全选' : '全选' }}
        </el-button>
        <span class="selected-count">已选 {{ selectedCaseIds.length }} 条</span>
      </div>
      <el-table
        v-if="createForm.requirement_ids.length"
        ref="caseTableRef"
        v-loading="casesLoading"
        :data="availableCases"
        max-height="320"
        stripe
        border
        @selection-change="handleCaseSelection"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ row }">{{ row.sort_order || '—' }}</template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column prop="case_type" label="类型" width="90">
          <template #default="{ row }">{{ formatCaseTypeLabel(row.case_type) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="请先选择项目与需求点，系统将自动加载关联用例" />

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createRun">创建并开始</el-button>
      </template>
    </el-dialog>

    <!-- 测试单详情 -->
    <el-drawer v-model="detailDrawerVisible" title="测试单详情" size="640px">
      <template v-if="detailRun">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ detailRun.name }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{
            detailRun.build_name || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="runStatusType[detailRun.status]" size="small">
              {{ runStatusLabel[detailRun.status] }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="通过率">{{ detailRun.pass_rate }}%</el-descriptions-item>
          <el-descriptions-item label="执行人">{{
            detailRun.executor_name || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{
            formatTime(detailRun.created_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{
            formatTime(detailRun.started_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{
            formatTime(detailRun.finished_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ runDurationText(detailRun) }}</el-descriptions-item>
          <el-descriptions-item label="说明" :span="2">{{
            detailRun.description || '-'
          }}</el-descriptions-item>
        </el-descriptions>
        <el-table
          :data="detailRun.cases"
          stripe
          border
          class="detail-table"
          @row-click="openCaseDetail"
        >
          <el-table-column label="序号" width="70" align="center">
            <template #default="{ row }">{{ row.testcase_sort_order || '—' }}</template>
          </el-table-column>
          <el-table-column prop="case_title" label="标题" min-width="180" show-overflow-tooltip />
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="resultType[row.result]" size="small">{{
                resultLabel[row.result]
              }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="executor_name" label="执行人" width="90" />
          <el-table-column label="执行时间" width="160">
            <template #default="{ row }">{{ formatTime(row.executed_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="72" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click.stop="openCaseDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>

    <!-- 单条用例只读执行详情 -->
    <RunCaseDetailDrawer v-model="caseDetailVisible" :case-item="caseDetailItem" />
  </div>
</template>

<script setup lang="ts">
import { LONG_TEXT_MAX_LEN, TITLE_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { TableInstance } from 'element-plus'
import { projectApi, requirementApi, testExecutionApi } from '@/api'
import { unwrapProjectList } from '@/api/project'
import type { Schemas } from '@/api/types'
import { formatBeijingTime } from '@/utils/datetime'
import { formatCaseTypeLabel } from '@/utils/caseType'
import type { DateInput, Project, Requirement, TestCase } from '@/types/common'
import type { FormInstance, FormRules } from '@/types/element-plus'
import RunCaseDetailDrawer from '@/components/testexec/RunCaseDetailDrawer.vue'

type TestRunSummary = Schemas['ManualTestRunSummaryOut']
type TestRunDetail = Schemas['ManualTestRunDetailOut']
type TestRunCase = Schemas['ManualTestRunCaseOut']
type CaseResult = 'pass' | 'fail' | 'blocked' | 'skip'
type CaseFilter = 'all' | 'pending' | 'pass' | 'fail' | 'blocked' | 'skip'

interface CreateRunForm {
  project_id: number | null
  name: string
  build_name: string
  description: string
  requirement_ids: number[]
}

interface ResultForm {
  actual_result: string
  remark: string
}

const projects = ref<Project[]>([])
// scopedProjectId 传入时锁定该项目（新壳工作区）：隐藏项目下拉；不传保持独立页原行为
const props = defineProps<{ scopedProjectId?: number }>()
const scoped = computed(() => props.scopedProjectId != null)
const projectId = ref<number | null>(props.scopedProjectId ?? null)
const createRequirements = ref<Requirement[]>([])
const runs = ref<TestRunSummary[]>([])
const runsLoading = ref(false)
const runsPage = ref(1)
const runsPageSize = ref(20)
const runsTotal = ref(0)

const executingRun = ref<TestRunDetail | null>(null)
const currentCase = ref<TestRunCase | null>(null)
const caseFilter = ref<CaseFilter>('all')
const submitting = ref(false)
const resultForm = reactive<ResultForm>({ actual_result: '', remark: '' })

const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive<CreateRunForm>({
  project_id: null,
  name: '',
  build_name: '',
  description: '',
  requirement_ids: [],
})
const createRules: FormRules<CreateRunForm> = {
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  name: [{ required: true, message: '请输入测试单名称', trigger: 'blur' }],
  requirement_ids: [
    {
      type: 'array',
      required: true,
      min: 1,
      message: '请至少选择一个需求点',
      trigger: 'change',
    },
  ],
}
const availableCases = ref<TestCase[]>([])
const casesLoading = ref(false)
const selectedCaseIds = ref<number[]>([])
const creating = ref(false)
const caseTableSelection = ref<TestCase[]>([])
const caseTableRef = ref<TableInstance>()

const detailDrawerVisible = ref(false)
const detailRun = ref<TestRunDetail | null>(null)
const caseDetailVisible = ref(false)
const caseDetailItem = ref<TestRunCase | null>(null)

const runStatusLabel: Record<string, string> = {
  waiting: '待开始',
  running: '执行中',
  finished: '已完成',
}
const runStatusType: Record<string, string> = {
  waiting: 'info',
  running: 'warning',
  finished: 'success',
}
const resultLabel: Record<string, string> = {
  pending: '待测',
  pass: '通过',
  fail: '失败',
  blocked: '阻塞',
  skip: '跳过',
}
const resultType: Record<string, string> = {
  pending: 'info',
  pass: 'success',
  fail: 'danger',
  blocked: 'warning',
  skip: '',
}

const filteredCases = computed(() => {
  if (!executingRun.value?.cases) return []
  if (caseFilter.value === 'all') return executingRun.value.cases
  return executingRun.value.cases.filter((item) => item.result === caseFilter.value)
})

/** 当前选中项在「筛选后列表」中的下标；不在列表内则为 -1 */
const filteredCaseIndex = computed(() => {
  const caseId = currentCase.value?.id
  if (caseId == null) return -1
  return filteredCases.value.findIndex((item) => item.id === caseId)
})

const prevCase = computed(() => {
  const idx = filteredCaseIndex.value
  if (idx <= 0) return null
  return filteredCases.value[idx - 1] ?? null
})

const nextCase = computed(() => {
  const idx = filteredCaseIndex.value
  if (idx < 0 || idx >= filteredCases.value.length - 1) return null
  return filteredCases.value[idx + 1] ?? null
})

const allSelected = computed(
  () =>
    availableCases.value.length > 0 && selectedCaseIds.value.length === availableCases.value.length,
)

const allRequirementsSelected = computed(
  () =>
    createRequirements.value.length > 0 &&
    createForm.requirement_ids.length === createRequirements.value.length,
)

function formatTime(value: DateInput) {
  return formatBeijingTime(value)
}

function runProgress(run: TestRunSummary | TestRunDetail | null) {
  if (!run?.total_count) return 0
  return Math.round(((run.total_count - run.pending_count) / run.total_count) * 100)
}

async function loadProjects() {
  projects.value = unwrapProjectList(await projectApi.list())
  if (projects.value.length && !projectId.value) {
    projectId.value = projects.value[0].id
    await handleProjectChange()
  }
}

async function handleProjectChange() {
  executingRun.value = null
  currentCase.value = null
  if (!projectId.value) return
  runsPage.value = 1
  await loadRuns()
}

// 新壳锁定/切换项目 → 同步并加载测试单（immediate 覆盖 loadProjects 跳过默认项的场景）
watch(
  () => props.scopedProjectId,
  (v) => {
    if (v == null) return
    projectId.value = v
    handleProjectChange()
  },
  { immediate: true },
)

async function loadRuns() {
  if (!projectId.value) return
  runsLoading.value = true
  try {
    const data = await testExecutionApi.listRunsPage(projectId.value, {
      page: runsPage.value,
      page_size: runsPageSize.value,
    })
    runs.value = data.items
    runsTotal.value = data.total
    if (runsPage.value > 1 && data.items.length === 0 && data.total > 0) {
      runsPage.value -= 1
      await loadRuns()
    }
  } finally {
    runsLoading.value = false
  }
}

async function handleRunsPageSizeChange() {
  runsPage.value = 1
  await loadRuns()
}

function backToList() {
  executingRun.value = null
  currentCase.value = null
  loadRuns()
}

async function enterExecution(row: TestRunSummary, filter: CaseFilter = 'pending') {
  executingRun.value = await testExecutionApi.getRun(row.id)
  caseFilter.value = filter
  const cases = executingRun.value.cases || []
  if (filter === 'all') {
    selectCase(cases[0] || null)
    return
  }
  const matched = cases.filter((item) => item.result === filter)
  selectCase(matched[0] || null)
}

function openRunCasesByResult(row: TestRunSummary, filter: CaseFilter, count: number) {
  if (count <= 0) return
  void enterExecution(row, filter)
}

async function viewRunDetail(row: TestRunSummary) {
  detailRun.value = await testExecutionApi.getRun(row.id)
  detailDrawerVisible.value = true
}

function openCaseDetail(row: TestRunCase) {
  caseDetailItem.value = row
  caseDetailVisible.value = true
}

/** 测试单耗时：结束-开始，缺任一端返回 '-' */
function runDurationText(run: TestRunDetail | null) {
  if (!run?.started_at || !run.finished_at) return '-'
  const start = new Date(run.started_at).getTime()
  const end = new Date(run.finished_at).getTime()
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return '-'
  const totalSec = Math.round((end - start) / 1000)
  if (totalSec < 60) return `${totalSec} 秒`
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  if (min < 60) return sec ? `${min} 分 ${sec} 秒` : `${min} 分`
  const hour = Math.floor(min / 60)
  const remMin = min % 60
  return remMin ? `${hour} 时 ${remMin} 分` : `${hour} 时`
}

async function removeRun(row: TestRunSummary) {
  await testExecutionApi.deleteRun(row.id)
  ElMessage.success('已删除')
  await loadRuns()
}

function selectCase(item: TestRunCase | null) {
  if (!item) {
    currentCase.value = null
    return
  }
  currentCase.value = item
  resultForm.actual_result = item.actual_result || ''
  resultForm.remark = item.remark || ''
}

/** 切换状态筛选：选中该状态下第一条（空则清空详情） */
function onCaseFilterChange() {
  selectCase(filteredCases.value[0] || null)
}

watch(currentCase, (item) => {
  if (!item) return
  resultForm.actual_result = item.actual_result || ''
  resultForm.remark = item.remark || ''
})

async function submitResult(result: CaseResult) {
  if (!currentCase.value || !executingRun.value) return
  const prevId = currentCase.value.id
  const fullIndex = executingRun.value.cases?.findIndex((item) => item.id === prevId) ?? -1
  const filter = caseFilter.value
  submitting.value = true
  try {
    await testExecutionApi.submitCaseResult(executingRun.value.id, currentCase.value.id, {
      result,
      actual_result: resultForm.actual_result,
      remark: resultForm.remark,
    })
    executingRun.value = await testExecutionApi.getRun(executingRun.value.id)
    ElMessage.success(`已标记为${resultLabel[result]}`)

    const cases = executingRun.value.cases || []
    const matched = filter === 'all' ? cases : cases.filter((item) => item.result === filter)

    // 待测 / 全部：执行流优先跳下一条待测；待测筛选下无待测则清空，避免右侧仍展示已执行项
    if (filter === 'pending' || filter === 'all') {
      const nextPending =
        cases.slice(fullIndex + 1).find((item) => item.result === 'pending') ||
        cases.find((item) => item.result === 'pending') ||
        null
      if (filter === 'pending') {
        selectCase(nextPending)
        return
      }
      selectCase(nextPending || cases[fullIndex] || cases[0] || null)
      return
    }

    // 其他状态筛选：结果变更后若仍在列表则保留，否则选列表首条
    const stillHere = matched.find((item) => item.id === prevId)
    selectCase(stillHere || matched[0] || null)
  } finally {
    submitting.value = false
  }
}

function openCreateDialog() {
  createForm.project_id = projectId.value || null
  createForm.name = ''
  createForm.build_name = ''
  createForm.description = ''
  createForm.requirement_ids = []
  createRequirements.value = []
  availableCases.value = []
  selectedCaseIds.value = []
  caseTableSelection.value = []
  createDialogVisible.value = true
  if (createForm.project_id) {
    loadCreateRequirements()
  }
}

async function loadCreateRequirements() {
  if (!createForm.project_id) {
    createRequirements.value = []
    return
  }
  const data = await requirementApi.list(createForm.project_id, { status: 'approved' })
  createRequirements.value = data
}

function handleCreateProjectChange() {
  createForm.requirement_ids = []
  createRequirements.value = []
  availableCases.value = []
  selectedCaseIds.value = []
  caseTableSelection.value = []
  loadCreateRequirements()
}

async function loadAvailableCases() {
  if (!createForm.project_id || !createForm.requirement_ids.length) {
    availableCases.value = []
    selectedCaseIds.value = []
    caseTableSelection.value = []
    return
  }
  casesLoading.value = true
  try {
    availableCases.value = await testExecutionApi.listAvailableCases(createForm.project_id, {
      requirement_ids: createForm.requirement_ids,
    })
    selectedCaseIds.value = availableCases.value.map((item) => item.id)
    await nextTick()
    if (caseTableRef.value) {
      caseTableRef.value.clearSelection()
      availableCases.value.forEach((row) => caseTableRef.value?.toggleRowSelection(row, true))
    }
  } finally {
    casesLoading.value = false
  }
}

function handleCaseSelection(rows: TestCase[]) {
  caseTableSelection.value = rows
  selectedCaseIds.value = rows.map((item) => item.id)
}

function toggleSelectAllRequirements() {
  if (allRequirementsSelected.value) {
    createForm.requirement_ids = []
  } else {
    createForm.requirement_ids = createRequirements.value.map((item) => item.id)
  }
  loadAvailableCases()
}

function toggleSelectAll() {
  if (!caseTableRef.value) return
  if (allSelected.value) {
    caseTableRef.value.clearSelection()
    selectedCaseIds.value = []
  } else {
    availableCases.value.forEach((row) => caseTableRef.value?.toggleRowSelection(row, true))
    selectedCaseIds.value = availableCases.value.map((item) => item.id)
  }
}

async function createRun() {
  await createFormRef.value?.validate()
  if (!selectedCaseIds.value.length) {
    ElMessage.warning('请至少选择一条用例')
    return
  }
  creating.value = true
  try {
    const run = await testExecutionApi.createRun({
      project_id: createForm.project_id!,
      name: createForm.name,
      build_name: createForm.build_name || undefined,
      description: createForm.description || undefined,
      requirement_ids: createForm.requirement_ids,
      case_ids: selectedCaseIds.value,
    })
    createDialogVisible.value = false
    projectId.value = createForm.project_id
    ElMessage.success('测试单已创建')
    executingRun.value = run
    caseFilter.value = 'pending'
    const runCases = run.cases || []
    selectCase(runCases.find((item) => item.result === 'pending') || runCases[0] || null)
  } finally {
    creating.value = false
  }
}

onMounted(loadProjects)
</script>

<style scoped>
/* 页面撑满 el-main 高度：工具栏固定，列表卡/执行面板吃掉剩余高度、内部滚动 */
.test-execution {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  gap: var(--ax-gap-sm);
  margin-bottom: var(--ax-gap-sm);
  align-items: center;
  flex: none;
}

.list-toolbar {
  justify-content: flex-end;
}

/* 测试单列表：卡片吃剩余高度，表格在卡片内部滚动 */
.list-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.list-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.runs-table {
  flex: 1;
  min-height: 0;
}

.runs-pagination {
  flex: none;
  justify-content: flex-end;
  margin-top: var(--ax-gap-sm);
  padding: 0 var(--ax-space-1);
}

/* 执行模式：摘要固定，左侧列表与右侧详情各自滚动 */
.execute-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: var(--ax-gap);
  min-width: 0;
  overflow: hidden;
}

.run-name-cell {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--ax-gap-xs);
}

.run-name {
  overflow: hidden;
  color: var(--ax-text);
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-sub {
  overflow: hidden;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-card :deep(.el-table__body .el-table__cell .cell) {
  overflow: hidden;
}

.list-card :deep(.el-table__body-wrapper) {
  overflow-x: auto;
}

.result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-gap-xs);
  overflow: hidden;
}

.result-tag-clickable {
  cursor: pointer;
}

.result-tag-clickable:hover {
  opacity: 0.85;
}

.run-actions {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: var(--ax-space-2);
  white-space: nowrap;
}

.run-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.list-card :deep(.run-actions-col .cell) {
  overflow: visible;
}

.progress-cell :deep(.el-progress) {
  flex: 1;
}

.progress-text {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

.run-header {
  flex: none;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.run-header :deep(.el-card__body) {
  padding: var(--ax-gap-lg) var(--ax-gap-lg) var(--ax-gap-sm);
}

.run-header-main {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--ax-gap-xl);
  margin-bottom: var(--ax-gap-lg);
}

.run-header h3 {
  margin: 0 0 var(--ax-gap);
  color: var(--ax-text);
  font-size: var(--ax-font-lg);
}

.run-meta {
  display: flex;
  gap: var(--ax-gap-lg);
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
  align-items: center;
}

.run-stats {
  display: grid;
  grid-template-columns: repeat(6, auto);
}

.stat-item {
  display: flex;
  min-width: 58px;
  flex-direction: column;
  gap: var(--ax-gap-xs);
  padding: 0 var(--ax-gap-sm);
  border-left: 1px solid var(--ax-border);
  font-size: var(--ax-font-xs);
  text-align: center;
}

.stat-item:first-child {
  border-left: 0;
}

.stat-item strong {
  font-size: var(--ax-font-md);
  line-height: var(--ax-leading-tight);
  font-variant-numeric: tabular-nums;
}

.stat-item span {
  color: var(--ax-text-secondary);
  font-weight: 400;
}

.stat-item.pass {
  color: var(--ax-success);
}
.stat-item.fail {
  color: var(--ax-danger);
}
.stat-item.block {
  color: var(--ax-warning);
}
.stat-item.skip {
  color: var(--ax-info);
}
.stat-item.pending {
  color: var(--ax-brand);
}
.stat-item.rate {
  color: var(--ax-text);
  font-weight: 600;
}

.execute-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  flex: 1;
  min-height: 0;
  border-top: 1px solid var(--ax-border);
  background: var(--ax-bg);
}

.case-list-card,
.case-detail-card {
  min-height: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.case-list-card {
  border-right: 1px solid var(--ax-border);
}

.case-list-card :deep(.el-card__body) {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: var(--ax-gap-sm) var(--ax-gap);
}

.case-detail-card :deep(.el-card__body) {
  height: 100%;
  overflow-y: auto;
  padding: var(--ax-gap-lg);
}

.case-list-toolbar {
  flex: none;
  margin-bottom: var(--ax-gap);
}

.case-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.case-list-item {
  display: flex;
  align-items: center;
  gap: var(--ax-gap);
  padding: var(--ax-space-2-5) var(--ax-gap);
  border-radius: var(--ax-radius);
  cursor: pointer;
  transition: background var(--ax-transition);
}

.case-list-item:hover,
.case-list-item.active {
  background: var(--ax-brand-subtle);
}

.case-index {
  width: 24px;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.case-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
}

.case-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--ax-gap-lg);
}

.case-detail-header h4 {
  margin: 0 0 var(--ax-gap);
  color: var(--ax-text);
  font-size: var(--ax-font-md);
}

.case-tags {
  display: flex;
  gap: var(--ax-gap);
}

.case-info :deep(.el-descriptions__body) {
  background: transparent;
}

.case-info :deep(.el-descriptions__cell) {
  padding-bottom: var(--ax-gap-sm);
}

.case-info :deep(.el-descriptions__label) {
  width: 84px;
  color: var(--ax-text-secondary);
  font-weight: 600;
}

.text-block {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: var(--ax-text-body-size);
  line-height: var(--ax-leading-relaxed);
}

.result-form {
  margin-top: var(--ax-gap-lg);
}

.result-actions {
  display: flex;
  gap: var(--ax-gap-sm);
  margin-top: var(--ax-gap);
}

.select-cases-toolbar {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
  margin: var(--ax-space-3) 0 var(--ax-space-2);
  font-size: var(--ax-text-body-size);
}

.select-cases-hint {
  color: var(--ax-danger);
}

.selected-count {
  margin-left: auto;
  color: var(--ax-text-secondary);
}

.requirement-select-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  width: 100%;
}

.detail-table {
  margin-top: var(--ax-space-4);
}

.detail-table :deep(.el-table__body tr) {
  cursor: pointer;
}

.empty-detail {
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 1100px) {
  .run-header-main {
    align-items: flex-start;
    flex-direction: column;
  }

  .run-stats {
    width: 100%;
    grid-template-columns: repeat(6, 1fr);
  }
}
</style>
