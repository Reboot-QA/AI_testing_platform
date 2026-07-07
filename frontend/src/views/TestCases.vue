<template>
  <div>
    <div class="toolbar">
      <el-select v-model="projectId" placeholder="选择项目" style="width: 200px" @change="handleFilterChange">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="评审状态" clearable style="width: 140px" @change="handleFilterChange">
        <el-option label="草稿" value="draft" />
        <el-option label="待评审" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-button type="primary" :disabled="!projectId" @click="openDialog()">
        <el-icon><Plus /></el-icon> 手动添加
      </el-button>
      <el-button :disabled="!projectId" @click="handleExport">
        <el-icon><Download /></el-icon> 导出 Excel
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
      <el-button
        type="danger"
        plain
        :disabled="!selectedIds.length"
        @click="handleBatchDelete"
      >
        <el-icon><Delete /></el-icon> 批量删除{{ selectedIds.length ? ` (${selectedIds.length})` : '' }}
      </el-button>
    </div>

    <el-table
      :data="testcases"
      v-loading="loading"
      stripe
      border
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="priority" label="优先级" width="80" align="center" />
      <el-table-column prop="case_type" label="类型" width="90" />
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
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button link type="success" v-if="row.review_status === 'pending'" @click="review(row, 'approved')">通过</el-button>
          <el-button link type="warning" v-if="row.review_status === 'pending'" @click="review(row, 'rejected')">驳回</el-button>
          <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

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
            <el-option v-for="p in ['P0','P1','P2','P3']" :key="p" :label="p" :value="p" />
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
          <el-descriptions-item label="优先级">{{ detail.priority }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ detail.case_type }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ detail.source === 'ai_generated' ? 'AI生成' : '手动' }}</el-descriptions-item>
          <el-descriptions-item label="评审状态">{{ reviewMap[detail.review_status] }}</el-descriptions-item>
          <el-descriptions-item label="前置条件">{{ detail.preconditions || '-' }}</el-descriptions-item>
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi, testcaseApi } from '@/api'
import { registerAssistantHandler, unregisterAssistantHandler } from '@/utils/assistantActionRegistry'

const projects = ref([])
const testcases = ref([])
const selectedRows = ref([])
const selectedIds = ref([])
const projectId = ref(null)
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const batchReviewing = ref(false)
const dialogVisible = ref(false)
const drawerVisible = ref(false)
const submitting = ref(false)
const editing = ref(null)
const detail = ref(null)
const formRef = ref()

const reviewMap = { draft: '草稿', pending: '待评审', approved: '已通过', rejected: '已驳回' }
const reviewType = { draft: 'info', pending: 'warning', approved: 'success', rejected: 'danger' }

const form = reactive({
  title: '',
  priority: 'P1',
  preconditions: '',
  steps: '',
  expected_results: '',
  tags: '',
})

const rules = { title: [{ required: true, message: '请输入标题', trigger: 'blur' }] }

const batchSubmitCount = computed(() =>
  selectedRows.value.filter((row) => ['draft', 'rejected'].includes(row.review_status)).length
)
const batchApproveCount = computed(() =>
  selectedRows.value.filter((row) => row.review_status === 'pending').length
)
const batchRejectCount = computed(() =>
  selectedRows.value.filter((row) => row.review_status === 'pending').length
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
  projects.value = await projectApi.list()
  if (projects.value.length && !projectId.value) {
    projectId.value = projects.value[0].id
    loadData()
  }
}

registerAssistantHandler('testcases.ensureProject', async () => {
  if (!projects.value.length) {
    await loadProjects()
  }
  if (!projectId.value && projects.value.length) {
    projectId.value = projects.value[0].id
    await loadData()
  }
  if (!projectId.value) {
    throw new Error('请先创建项目')
  }
})

async function loadData() {
  if (!projectId.value) return
  loading.value = true
  try {
    const params = {
      project_id: projectId.value,
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filterStatus.value) params.review_status = filterStatus.value
    const data = await testcaseApi.list(params)
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
    const res = await testcaseApi.batchReview({
      project_id: projectId.value,
      case_ids: selectedIds.value,
      review_status: status,
    })
    ElMessage.success(res.message || config.success)
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
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  const res = await testcaseApi.batchDelete({
    project_id: projectId.value,
    case_ids: selectedIds.value,
  })
  ElMessage.success(res.message || '批量删除成功')
  loadData()
}

async function handleExport() {
  const blob = await testcaseApi.exportExcel(projectId.value)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `testcases_${projectId.value}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(loadProjects)

onUnmounted(() => {
  unregisterAssistantHandler('testcases.ensureProject')
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pre-text {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
