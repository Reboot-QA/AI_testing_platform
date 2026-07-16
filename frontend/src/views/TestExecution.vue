<template>
  <div class="test-execution">
    <div class="toolbar">
      <el-select
        v-model="projectId"
        placeholder="选择项目"
        style="width: 220px"
        @change="handleProjectChange"
      >
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon> 新建测试单
      </el-button>
      <el-button v-if="executingRun" @click="backToList">返回列表</el-button>
    </div>

    <!-- 测试单列表 -->
    <el-card v-if="!executingRun" shadow="never">
      <el-table v-loading="runsLoading" :data="runs" stripe border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="测试单" min-width="180" show-overflow-tooltip />
        <el-table-column prop="build_name" label="版本/构建" width="120">
          <template #default="{ row }">{{ row.build_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="进度" min-width="200">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress
                :percentage="runProgress(row)"
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
                {{ row.total_count - row.pending_count }}/{{ row.total_count }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="220">
          <template #default="{ row }">
            <el-tag type="success" size="small">通过 {{ row.passed_count }}</el-tag>
            <el-tag type="danger" size="small">失败 {{ row.failed_count }}</el-tag>
            <el-tag type="warning" size="small">阻塞 {{ row.blocked_count }}</el-tag>
            <el-tag type="info" size="small">跳过 {{ row.skipped_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="pass_rate" label="通过率" width="90" align="center">
          <template #default="{ row }">{{ row.pass_rate }}%</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="runStatusType[row.status]" size="small">{{
              runStatusLabel[row.status]
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="executor_name" label="执行人" width="100" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="enterExecution(row)">执行</el-button>
            <el-button link type="primary" @click="viewRunDetail(row)">详情</el-button>
            <el-popconfirm title="确认删除该测试单？" @confirm="removeRun(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
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
            <div class="stat-item pass">通过 {{ executingRun.passed_count }}</div>
            <div class="stat-item fail">失败 {{ executingRun.failed_count }}</div>
            <div class="stat-item block">阻塞 {{ executingRun.blocked_count }}</div>
            <div class="stat-item skip">跳过 {{ executingRun.skipped_count }}</div>
            <div class="stat-item pending">待测 {{ executingRun.pending_count }}</div>
            <div class="stat-item rate">通过率 {{ executingRun.pass_rate }}%</div>
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
            <el-select v-model="caseFilter" size="small" style="width: 120px">
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
              v-for="(item, index) in filteredCases"
              :key="item.id"
              class="case-list-item"
              :class="{ active: currentCase?.id === item.id, [item.result]: true }"
              @click="selectCase(item)"
            >
              <span class="case-index">{{ index + 1 }}</span>
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
                <el-tag size="small" type="info">{{ currentCase.case_type }}</el-tag>
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

          <el-descriptions :column="1" border class="case-info">
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
                type="textarea"
                :rows="4"
                placeholder="记录实际执行结果"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input
                v-model="resultForm.remark"
                type="textarea"
                :rows="2"
                placeholder="缺陷编号、环境问题等"
              />
            </el-form-item>
          </el-form>

          <div class="result-actions">
            <el-button
              type="success"
              size="large"
              :loading="submitting"
              @click="submitResult('pass')"
            >
              通过
            </el-button>
            <el-button
              type="danger"
              size="large"
              :loading="submitting"
              @click="submitResult('fail')"
            >
              失败
            </el-button>
            <el-button
              type="warning"
              size="large"
              :loading="submitting"
              @click="submitResult('blocked')"
            >
              阻塞
            </el-button>
            <el-button type="info" size="large" :loading="submitting" @click="submitResult('skip')">
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
            placeholder="请选择项目"
            style="width: 100%"
            @change="handleCreateProjectChange"
          >
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" placeholder="第一轮测试" />
        </el-form-item>
        <el-form-item label="版本/构建">
          <el-input v-model="createForm.build_name" placeholder="例如：V1.2.0" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
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
        <span>选用例（仅已通过评审）</span>
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
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column prop="case_type" label="类型" width="90" />
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
        </el-descriptions>
        <el-table :data="detailRun.cases" stripe border class="detail-table">
          <el-table-column prop="testcase_id" label="用例ID" width="80" />
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
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { projectApi, requirementApi, testExecutionApi } from '@/api'
import { formatBeijingTime } from '@/utils/datetime'

const projects = ref([])
const projectId = ref(null)
const createRequirements = ref([])
const runs = ref([])
const runsLoading = ref(false)

const executingRun = ref(null)
const currentCase = ref(null)
const caseFilter = ref('all')
const submitting = ref(false)
const resultForm = reactive({ actual_result: '', remark: '' })

const createDialogVisible = ref(false)
const createFormRef = ref()
const createForm = reactive({
  project_id: null,
  name: '',
  build_name: '',
  description: '',
  requirement_ids: [],
})
const createRules = {
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
const availableCases = ref([])
const casesLoading = ref(false)
const selectedCaseIds = ref([])
const creating = ref(false)
const caseTableSelection = ref([])
const caseTableRef = ref()

const detailDrawerVisible = ref(false)
const detailRun = ref(null)

const runStatusLabel = { waiting: '待开始', running: '执行中', finished: '已完成' }
const runStatusType = { waiting: 'info', running: 'warning', finished: 'success' }
const resultLabel = { pending: '待测', pass: '通过', fail: '失败', blocked: '阻塞', skip: '跳过' }
const resultType = {
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

const currentCaseIndex = computed(() => {
  if (!currentCase.value || !executingRun.value?.cases) return -1
  return executingRun.value.cases.findIndex((item) => item.id === currentCase.value.id)
})

const prevCase = computed(() => {
  const idx = currentCaseIndex.value
  if (idx <= 0) return null
  return executingRun.value.cases[idx - 1]
})

const nextCase = computed(() => {
  const idx = currentCaseIndex.value
  if (idx < 0 || idx >= executingRun.value.cases.length - 1) return null
  return executingRun.value.cases[idx + 1]
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

function formatTime(value) {
  return formatBeijingTime(value)
}

function runProgress(run) {
  if (!run?.total_count) return 0
  return Math.round(((run.total_count - run.pending_count) / run.total_count) * 100)
}

async function loadProjects() {
  projects.value = await projectApi.list()
  if (projects.value.length && !projectId.value) {
    projectId.value = projects.value[0].id
    await handleProjectChange()
  }
}

async function handleProjectChange() {
  executingRun.value = null
  currentCase.value = null
  if (!projectId.value) return
  await loadRuns()
}

async function loadRuns() {
  if (!projectId.value) return
  runsLoading.value = true
  try {
    runs.value = await testExecutionApi.listRuns(projectId.value)
  } finally {
    runsLoading.value = false
  }
}

function backToList() {
  executingRun.value = null
  currentCase.value = null
  loadRuns()
}

async function enterExecution(row) {
  executingRun.value = await testExecutionApi.getRun(row.id)
  caseFilter.value = 'pending'
  const firstPending = executingRun.value.cases.find((item) => item.result === 'pending')
  selectCase(firstPending || executingRun.value.cases[0] || null)
}

async function viewRunDetail(row) {
  detailRun.value = await testExecutionApi.getRun(row.id)
  detailDrawerVisible.value = true
}

async function removeRun(row) {
  await testExecutionApi.deleteRun(row.id)
  ElMessage.success('已删除')
  await loadRuns()
}

function selectCase(item) {
  if (!item) {
    currentCase.value = null
    return
  }
  currentCase.value = item
  resultForm.actual_result = item.actual_result || ''
  resultForm.remark = item.remark || ''
}

watch(currentCase, (item) => {
  if (!item) return
  resultForm.actual_result = item.actual_result || ''
  resultForm.remark = item.remark || ''
})

async function submitResult(result) {
  if (!currentCase.value || !executingRun.value) return
  const prevIndex = currentCaseIndex.value
  submitting.value = true
  try {
    await testExecutionApi.submitCaseResult(executingRun.value.id, currentCase.value.id, {
      result,
      actual_result: resultForm.actual_result,
      remark: resultForm.remark,
    })
    executingRun.value = await testExecutionApi.getRun(executingRun.value.id)
    ElMessage.success(`已标记为${resultLabel[result]}`)
    const cases = executingRun.value.cases
    const next =
      cases.slice(prevIndex + 1).find((item) => item.result === 'pending') ||
      cases.find((item) => item.result === 'pending') ||
      cases[prevIndex] ||
      cases[0] ||
      null
    selectCase(next)
  } finally {
    submitting.value = false
  }
}

function openCreateDialog() {
  createForm.project_id = projectId.value || null
  createForm.name = '第一轮测试'
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
  createRequirements.value = Array.isArray(data) ? data : data.items || []
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
      availableCases.value.forEach((row) => caseTableRef.value.toggleRowSelection(row, true))
    }
  } finally {
    casesLoading.value = false
  }
}

function handleCaseSelection(rows) {
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
    availableCases.value.forEach((row) => caseTableRef.value.toggleRowSelection(row, true))
    selectedCaseIds.value = availableCases.value.map((item) => item.id)
  }
}

async function createRun() {
  await createFormRef.value.validate()
  if (!selectedCaseIds.value.length) {
    ElMessage.warning('请至少选择一条用例')
    return
  }
  creating.value = true
  try {
    const run = await testExecutionApi.createRun({
      project_id: createForm.project_id,
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
    selectCase(run.cases.find((item) => item.result === 'pending') || run.cases[0] || null)
  } finally {
    creating.value = false
  }
}

onMounted(loadProjects)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-cell :deep(.el-progress) {
  flex: 1;
}

.progress-text {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.run-header-main {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.run-header h3 {
  margin: 0 0 8px;
}

.run-meta {
  display: flex;
  gap: 16px;
  color: #64748b;
  font-size: 13px;
  align-items: center;
}

.run-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-item {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  background: #f1f5f9;
}

.stat-item.pass {
  color: #16a34a;
}
.stat-item.fail {
  color: #dc2626;
}
.stat-item.block {
  color: #d97706;
}
.stat-item.skip {
  color: #64748b;
}
.stat-item.pending {
  color: #2563eb;
}
.stat-item.rate {
  color: #0f172a;
  font-weight: 600;
}

.execute-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  margin-top: 16px;
  min-height: 520px;
}

.case-list-toolbar {
  margin-bottom: 8px;
}

.case-list {
  max-height: 560px;
  overflow-y: auto;
}

.case-list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 8px;
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  transition: background 0.15s;
}

.case-list-item:hover,
.case-list-item.active {
  background: #eff6ff;
}

.case-index {
  width: 24px;
  color: #94a3b8;
  font-size: 12px;
}

.case-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.case-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.case-detail-header h4 {
  margin: 0 0 8px;
}

.case-tags {
  display: flex;
  gap: 8px;
}

.text-block {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  line-height: 1.6;
}

.result-form {
  margin-top: 16px;
}

.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.select-cases-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0 8px;
  font-size: 14px;
}

.selected-count {
  margin-left: auto;
  color: #64748b;
}

.requirement-select-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.detail-table {
  margin-top: 16px;
}

.empty-detail {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
