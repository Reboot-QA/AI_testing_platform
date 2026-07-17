<template>
  <PageCard fill>
    <template #toolbar>
      <el-select
        v-model="projectId"
        filterable
        placeholder="选择项目"
        style="width: 200px"
        @change="handleFilterChange"
      >
        <el-option label="全部" :value="ALL_PROJECTS" />
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select
        v-model="filterStatus"
        placeholder="评审状态"
        clearable
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option label="草稿" value="draft" />
        <el-option label="待评审" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索标题/需求点/步骤"
        style="width: 220px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-button type="primary" plain @click="handleSearch">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>
      <el-button type="primary" :disabled="isAllProjects" @click="openDialog()">
        <el-icon><Plus /></el-icon> 手动添加
      </el-button>
      <el-dropdown :disabled="isAllProjects" @command="handleExport">
        <el-button :disabled="isAllProjects" :loading="exporting">
          导出
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
            <el-dropdown-item command="xmind">导出 XMind</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button :disabled="isAllProjects" :loading="importing" @click="openImportDialog">
        导入
      </el-button>
      <el-button
        plain
        :disabled="!canBatchSubmit"
        :loading="batchReviewing"
        @click="handleBatchReview('pending')"
      >
        批量审批{{ batchSubmitCount ? ` (${batchSubmitCount})` : '' }}
      </el-button>
      <el-button
        type="success"
        plain
        :disabled="!canBatchApprove"
        :loading="batchReviewing"
        @click="handleBatchReview('approved')"
      >
        批量通过{{ batchApproveCount ? ` (${batchApproveCount})` : '' }}
      </el-button>
      <el-button
        type="warning"
        plain
        :disabled="!canBatchReject"
        :loading="batchReviewing"
        @click="handleBatchReview('rejected')"
      >
        批量驳回{{ batchRejectCount ? ` (${batchRejectCount})` : '' }}
      </el-button>
      <el-button type="danger" plain :disabled="!selectedIds.length" @click="handleBatchDelete">
        <el-icon><Delete /></el-icon> 批量删除{{
          selectedIds.length ? ` (${selectedIds.length})` : ''
        }}
      </el-button>
    </template>

    <div class="table-fill">
      <el-table
        v-loading="loading"
        :data="testcases"
        stripe
        border
        height="100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column
          v-if="isAllProjects"
          prop="project_name"
          label="项目"
          min-width="140"
          show-overflow-tooltip
        />
        <el-table-column
          prop="requirement_title"
          label="需求点"
          min-width="160"
          show-overflow-tooltip
        >
          <template #default="{ row }">{{ row.requirement_title || '-' }}</template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column prop="case_type" label="类型" width="90">
          <template #default="{ row }">{{ formatCaseTypeLabel(row.case_type) }}</template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }">
            <el-tag :type="row.source === 'ai_generated' ? 'warning' : ''" size="small">
              {{ row.source === 'ai_generated' ? 'AI生成' : '手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="100">
          <template #default="{ row }">{{ row.creator_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="review_status" label="评审" width="100">
          <template #default="{ row }">
            <el-tag :type="reviewType[row.review_status]" size="small">
              {{ reviewMap[row.review_status] || row.review_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-if="row.review_status === 'pending'"
              link
              type="success"
              @click="review(row, 'approved')"
              >通过</el-button
            >
            <el-button
              v-if="row.review_status === 'pending'"
              link
              type="warning"
              @click="review(row, 'rejected')"
              >驳回</el-button
            >
            <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="loadData"
        @size-change="handlePageSizeChange"
      />
    </div>

    <!-- 新建/编辑 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用例' : '添加用例'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 120px">
            <el-option v-for="p in ['P0', 'P1', 'P2', 'P3']" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="前置条件">
          <el-input v-model="form.preconditions" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="测试步骤">
          <el-input v-model="form.steps" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="预期结果">
          <el-input v-model="form.expected_results" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-drawer v-model="drawerVisible" title="用例详情" size="480px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="需求点">{{
            detail.requirement_title || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ detail.priority }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ formatCaseTypeLabel(detail.case_type) }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{
            detail.source === 'ai_generated' ? 'AI生成' : '手动'
          }}</el-descriptions-item>
          <el-descriptions-item label="评审状态">{{
            reviewMap[detail.review_status]
          }}</el-descriptions-item>
          <el-descriptions-item label="前置条件">{{
            detail.preconditions || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="测试步骤">
            <pre class="pre-text">{{ detail.steps || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="预期结果">
            <pre class="pre-text">{{ detail.expected_results || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="标签">{{ detail.tags || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>

    <el-dialog v-model="importDialogVisible" title="导入用例" width="520px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="支持 Excel (.xlsx) 与 XMind (.xmind) 格式。请先选择具体项目后再导入。"
        style="margin-bottom: 16px"
      />
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xmind"
        :on-change="handleImportFileChange"
        :on-remove="handleImportFileRemove"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">
            Excel 需包含「标题」列，导入后评审状态均为「草稿」；XMind 导入末级节点作为用例
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="importing"
          :disabled="!importFile"
          @click="handleImport"
        >
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </PageCard>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Search, UploadFilled } from '@element-plus/icons-vue'
import { projectApi, testcaseApi } from '@/api'
import { formatBeijingTime } from '@/utils/datetime'
import { formatCaseTypeLabel } from '@/utils/caseType'
import PageCard from '@/components/PageCard.vue'
import {
  registerAssistantHandler,
  unregisterAssistantHandler,
} from '@/utils/assistantActionRegistry'

import {
  ALL_PROJECTS,
  type DateInput,
  type Project,
  type ProjectFilter,
  type TestCase,
  type TestCasePage,
} from '@/types/common'
import type { FormInstance, FormRules } from '@/types/element-plus'
import type { UploadInstance, UploadRawFile } from 'element-plus'

interface TestCaseForm {
  title: string
  priority: string
  preconditions: string
  steps: string
  expected_results: string
  tags: string
}

function formatTime(value: DateInput) {
  return formatBeijingTime(value)
}

const route = useRoute()
const projects = ref<Project[]>([])
const testcases = ref<TestCase[]>([])
const selectedRows = ref<TestCase[]>([])
const selectedIds = ref<number[]>([])
const projectId = ref<ProjectFilter>(ALL_PROJECTS)
const filterStatus = ref('')
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const batchReviewing = ref(false)
const exporting = ref(false)
const importing = ref(false)
const dialogVisible = ref(false)
const importDialogVisible = ref(false)
const drawerVisible = ref(false)
const submitting = ref(false)
const editing = ref<TestCase | null>(null)
const detail = ref<TestCase | null>(null)
const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const importFile = ref<UploadRawFile | null>(null)

const reviewMap: Record<string, string> = {
  draft: '草稿',
  pending: '待评审',
  approved: '已通过',
  rejected: '已驳回',
}
const reviewType: Record<string, 'info' | 'warning' | 'success' | 'danger'> = {
  draft: 'info',
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
}

const form = reactive<TestCaseForm>({
  title: '',
  priority: 'P1',
  preconditions: '',
  steps: '',
  expected_results: '',
  tags: '',
})

const rules: FormRules<TestCaseForm> = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
}

const isAllProjects = computed(() => projectId.value === ALL_PROJECTS)

const batchSubmitCount = computed(
  () =>
    selectedRows.value.filter((row) => ['draft', 'rejected'].includes(row.review_status)).length,
)
const batchApproveCount = computed(
  () => selectedRows.value.filter((row) => row.review_status === 'pending').length,
)
const batchRejectCount = computed(
  () => selectedRows.value.filter((row) => row.review_status === 'pending').length,
)
const canBatchSubmit = computed(() => batchSubmitCount.value > 0)
const canBatchApprove = computed(() => batchApproveCount.value > 0)
const canBatchReject = computed(() => batchRejectCount.value > 0)

const batchReviewConfig = {
  pending: {
    title: '批量审批',
    message: (count) => `确认将选中的 ${count} 条用例提交评审（设为待评审）？`,
    success: '批量审批成功',
  },
  approved: {
    title: '批量通过',
    message: (count) => `确认通过选中的 ${count} 条待评审用例？`,
    success: '批量通过成功',
  },
  rejected: {
    title: '批量驳回',
    message: (count) => `确认驳回选中的 ${count} 条待评审用例？`,
    success: '批量驳回成功',
  },
}

async function loadProjects() {
  const data = await projectApi.list()
  projects.value = Array.isArray(data) ? data : data.items
  await loadData()
}

registerAssistantHandler('testcases.ensureProject', async () => {
  if (!projects.value.length) {
    await loadProjects()
  }
  if (isAllProjects.value) {
    throw new Error('请先选择具体项目')
  }
  if (!projectId.value) {
    throw new Error('请先创建项目')
  }
})

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (!isAllProjects.value) {
      params.project_id = projectId.value
    }
    if (filterStatus.value) params.review_status = filterStatus.value
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const data = (await testcaseApi.list(params)) as TestCasePage
    testcases.value = data.items || []
    total.value = data.total || 0
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value) || 1)
    if (currentPage.value > maxPage) {
      currentPage.value = maxPage
      if (maxPage !== params.page) {
        return loadData()
      }
    }
    selectedRows.value = []
    selectedIds.value = []
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  currentPage.value = 1
  loadData()
}

function handleSearch() {
  currentPage.value = 1
  loadData()
}

function handlePageSizeChange() {
  currentPage.value = 1
  loadData()
}

function openDialog(row = null) {
  editing.value = row
  form.title = row?.title || ''
  form.priority = row?.priority || 'P1'
  form.preconditions = row?.preconditions || ''
  form.steps = row?.steps || ''
  form.expected_results = row?.expected_results || ''
  form.tags = row?.tags || ''
  dialogVisible.value = true
}

function openDetail(row) {
  detail.value = row
  drawerVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = { ...form, project_id: projectId.value, case_type: 'functional' }
    if (editing.value) {
      await testcaseApi.update(editing.value.id, form)
      ElMessage.success('更新成功')
    } else {
      await testcaseApi.create(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function review(row, status) {
  await testcaseApi.update(row.id, { review_status: status })
  ElMessage.success(status === 'approved' ? '已通过' : '已驳回')
  loadData()
}

async function handleDelete(id) {
  await testcaseApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
  selectedIds.value = rows.map((row) => row.id)
}

function groupRowsByProject(rows) {
  const groups = new Map()
  for (const row of rows) {
    if (!groups.has(row.project_id)) groups.set(row.project_id, [])
    groups.get(row.project_id).push(row)
  }
  return groups
}

async function handleBatchReview(status) {
  const countMap = {
    pending: batchSubmitCount.value,
    approved: batchApproveCount.value,
    rejected: batchRejectCount.value,
  }
  const count = countMap[status]
  if (!count) return

  const config = batchReviewConfig[status]
  await ElMessageBox.confirm(config.message(count), config.title, {
    type: status === 'rejected' ? 'warning' : 'info',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  })

  batchReviewing.value = true
  try {
    const groups = groupRowsByProject(selectedRows.value)
    let message = ''
    for (const [pid, rows] of groups) {
      const res = await testcaseApi.batchReview({
        project_id: Number(pid),
        case_ids: rows.map((row) => row.id),
        review_status: status,
      })
      message = res.message || message
    }
    ElMessage.success(message || config.success)
    loadData()
  } finally {
    batchReviewing.value = false
  }
}

async function handleBatchDelete() {
  if (!selectedIds.value.length) return
  await ElMessageBox.confirm(
    `确认删除选中的 ${selectedIds.value.length} 条用例？此操作不可恢复。`,
    '批量删除',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  const groups = groupRowsByProject(selectedRows.value)
  let message = ''
  for (const [pid, rows] of groups) {
    const res = await testcaseApi.batchDelete({
      project_id: Number(pid),
      case_ids: rows.map((row) => row.id),
    })
    message = res.message || message
  }
  ElMessage.success(message || '批量删除成功')
  loadData()
}

async function handleExport(format) {
  if (isAllProjects.value) {
    ElMessage.warning('请先选择具体项目')
    return
  }
  exporting.value = true
  try {
    const name = projects.value.find((item) => item.id === projectId.value)?.name || 'testcases'
    if (format === 'xmind') {
      const blob = await testcaseApi.exportXmind(projectId.value)
      downloadBlob(blob, `${name}_testcases.xmind`)
    } else {
      const blob = await testcaseApi.exportExcel(projectId.value)
      downloadBlob(blob, `${name}_testcases.xlsx`)
    }
    ElMessage.success('导出成功')
  } finally {
    exporting.value = false
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function openImportDialog() {
  if (isAllProjects.value) {
    ElMessage.warning('请先选择具体项目')
    return
  }
  importFile.value = null
  uploadRef.value?.clearFiles()
  importDialogVisible.value = true
}

function handleImportFileChange(uploadFile) {
  importFile.value = uploadFile.raw || null
}

function handleImportFileRemove() {
  importFile.value = null
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  importing.value = true
  try {
    const res = await testcaseApi.importFile(projectId.value, importFile.value)
    ElMessage.success(res.message || '导入成功')
    importDialogVisible.value = false
    importFile.value = null
    uploadRef.value?.clearFiles()
    currentPage.value = 1
    loadData()
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  if (route.query.review_status) {
    filterStatus.value = String(route.query.review_status)
  }
  await loadProjects()
})

onUnmounted(() => {
  unregisterAssistantHandler('testcases.ensureProject')
})
</script>

<style scoped>
.pre-text {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}

/* .pagination-bar 已提取为全局工具类（src/styles/layout.css） */
</style>
