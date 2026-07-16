<template>
  <PageCard fill>
    <template #toolbar>
      <el-select
        v-model="projectId"
        filterable
        placeholder="选择项目"
        style="width: 220px"
        @change="handleProjectChange"
      >
        <el-option label="全部" :value="ALL_PROJECTS" />
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button
        type="primary"
        :disabled="isAllProjects"
        data-assistant="requirements.create_btn"
        @click="openDialog()"
      >
        <el-icon><Plus /></el-icon> 添加需求
      </el-button>
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 120px">
        <el-option label="草稿" value="draft" />
        <el-option label="已评审" value="approved" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索标题/描述"
        style="width: 220px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-button type="primary" plain @click="handleSearch">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>
      <el-select v-model="batchStatus" placeholder="批量改状态" clearable style="width: 140px">
        <el-option label="草稿" value="draft" />
        <el-option label="已评审" value="approved" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-button
        :disabled="!selectedIds.length || !batchStatus"
        :loading="batchUpdating"
        @click="handleBatchStatus"
      >
        应用状态{{ selectedIds.length ? ` (${selectedIds.length})` : '' }}
      </el-button>
      <el-button
        type="danger"
        plain
        :disabled="!deletableSelectedCount"
        :loading="batchDeleting"
        @click="handleBatchDelete"
      >
        批量删除{{ deletableSelectedCount ? ` (${deletableSelectedCount})` : '' }}
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
    </template>

    <div class="table-fill">
      <el-table
        v-loading="loading"
        :data="requirements"
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
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="req_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ typeMap[row.req_type] || row.req_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="90" align="center" />
        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }">
            <el-tag :type="row.source === 'ai_document' ? 'warning' : ''" size="small">
              {{ sourceMap[row.source] || row.source }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType[row.status]" size="small">{{
              statusMap[row.status] || row.status
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="100">
          <template #default="{ row }">{{ row.creator_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="testcase_count" label="关联用例" width="100" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.testcase_count > 0"
              link
              type="primary"
              @click="openTestcases(row)"
            >
              {{ row.testcase_count }}
            </el-button>
            <span v-else class="empty-count">0</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button
              link
              type="danger"
              :disabled="row.testcase_count > 0"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
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

    <el-dialog v-model="importDialogVisible" title="导入需求" width="520px">
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
            Excel 需包含「标题」列，导入后状态均为「草稿」；XMind 导入末级节点作为需求点
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

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑需求' : '添加需求'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" data-assistant="requirements.form.title" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.req_type" style="width: 100%">
            <el-option label="功能测试" value="functional" />
            <el-option label="接口测试" value="api" />
            <el-option label="性能测试" value="performance" />
            <el-option label="安全测试" value="security" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            data-assistant="requirements.form.description"
            type="textarea"
            :rows="5"
            placeholder="详细需求描述，可用于 AI 生成用例"
          />
        </el-form-item>
        <el-form-item v-if="editing" label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="已评审" value="approved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          data-assistant="requirements.form.submit"
          :loading="submitting"
          @click="handleSubmit"
          >确定</el-button
        >
      </template>
    </el-dialog>

    <el-dialog
      v-model="casesDialogVisible"
      :title="`关联用例 - ${currentRequirement?.title || ''}`"
      width="900px"
    >
      <el-table v-loading="casesLoading" :data="linkedTestcases" stripe border max-height="420">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column prop="source" label="来源" width="90">
          <template #default="{ row }">
            <el-tag :type="row.source === 'ai_generated' ? 'warning' : ''" size="small">
              {{ row.source === 'ai_generated' ? 'AI生成' : '手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_status" label="评审" width="90">
          <template #default="{ row }">
            <el-tag :type="reviewType[row.review_status]" size="small">
              {{ reviewMap[row.review_status] || row.review_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openCaseDetail(row)">详情</el-button>
            <el-popconfirm title="确认删除该用例？" @confirm="handleDeleteCase(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="casesDialogVisible = false">关闭</el-button>
        <el-button
          type="danger"
          plain
          :disabled="!linkedTestcases.length"
          :loading="clearingCases"
          @click="handleClearTestcases"
        >
          清理全部关联用例
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="caseDrawerVisible" title="用例详情" size="480px">
      <template v-if="caseDetail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ caseDetail.title }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ caseDetail.priority }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ caseDetail.case_type }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            {{ caseDetail.source === 'ai_generated' ? 'AI生成' : '手动' }}
          </el-descriptions-item>
          <el-descriptions-item label="评审状态">
            {{ reviewMap[caseDetail.review_status] || caseDetail.review_status }}
          </el-descriptions-item>
          <el-descriptions-item label="前置条件">{{
            caseDetail.preconditions || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="测试步骤">
            <pre class="pre-text">{{ caseDetail.steps || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="预期结果">
            <pre class="pre-text">{{ caseDetail.expected_results || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="标签">{{ caseDetail.tags || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>
  </PageCard>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Search, UploadFilled } from '@element-plus/icons-vue'
import { projectApi, requirementApi, testcaseApi } from '@/api'
import { formatBeijingTime } from '@/utils/datetime'
import PageCard from '@/components/PageCard.vue'
import {
  registerAssistantHandler,
  unregisterAssistantHandler,
} from '@/utils/assistantActionRegistry'

const ALL_PROJECTS = '__all__'

function formatTime(value) {
  return formatBeijingTime(value)
}

const projects = ref([])
const requirements = ref([])
const linkedTestcases = ref([])
const selectedIds = ref([])
const selectedRows = ref([])
const projectId = ref(ALL_PROJECTS)
const filterStatus = ref('')
const keyword = ref('')
const batchStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const exporting = ref(false)
const importing = ref(false)
const batchUpdating = ref(false)
const batchDeleting = ref(false)
const casesLoading = ref(false)
const clearingCases = ref(false)
const dialogVisible = ref(false)
const importDialogVisible = ref(false)
const casesDialogVisible = ref(false)
const caseDrawerVisible = ref(false)
const submitting = ref(false)
const editing = ref(null)
const currentRequirement = ref(null)
const caseDetail = ref(null)
const formRef = ref()
const uploadRef = ref()
const importFile = ref(null)

const typeMap = { functional: '功能', api: '接口', performance: '性能', security: '安全' }
const sourceMap = { manual: '手动', ai_document: '文档解析' }
const statusMap = { draft: '草稿', approved: '已评审', closed: '已关闭' }
const statusType = { draft: 'info', approved: 'success', closed: 'warning' }
const reviewMap = { draft: '草稿', pending: '待评审', approved: '已通过', rejected: '已驳回' }
const reviewType = { draft: 'info', pending: 'warning', approved: 'success', rejected: 'danger' }

const form = reactive({
  title: '',
  description: '',
  req_type: 'functional',
  priority: 'P1',
  status: 'draft',
})

const rules = { title: [{ required: true, message: '请输入标题', trigger: 'blur' }] }

const isAllProjects = computed(() => projectId.value === ALL_PROJECTS)

const deletableSelectedCount = computed(
  () => selectedRows.value.filter((row) => !row.testcase_count).length,
)
const blockedSelectedCount = computed(
  () => selectedRows.value.filter((row) => row.testcase_count > 0).length,
)

async function loadProjects() {
  projects.value = await projectApi.list()
  await loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (!isAllProjects.value) {
      params.project_id = projectId.value
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    if (keyword.value.trim()) {
      params.keyword = keyword.value.trim()
    }
    const data = await requirementApi.list(null, params)
    requirements.value = data.items || []
    total.value = data.total || 0
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value) || 1)
    if (currentPage.value > maxPage) {
      currentPage.value = maxPage
      if (maxPage !== params.page) {
        return loadData()
      }
    }
    selectedIds.value = []
    selectedRows.value = []
  } finally {
    loading.value = false
  }
}

function handleProjectChange() {
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

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function currentProjectName() {
  return projects.value.find((item) => item.id === projectId.value)?.name || 'requirements'
}

async function handleExport(format) {
  if (isAllProjects.value) {
    ElMessage.warning('请先选择具体项目')
    return
  }
  exporting.value = true
  try {
    const name = currentProjectName()
    if (format === 'xmind') {
      const blob = await requirementApi.exportXmind(projectId.value)
      downloadBlob(blob, `${name}_requirements.xmind`)
    } else {
      const blob = await requirementApi.exportExcel(projectId.value)
      downloadBlob(blob, `${name}_requirements.xlsx`)
    }
    ElMessage.success('导出成功')
  } finally {
    exporting.value = false
  }
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
    const res = await requirementApi.importFile(projectId.value, importFile.value)
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

function openDialog(row = null) {
  editing.value = row
  form.title = row?.title || ''
  form.description = row?.description || ''
  form.req_type = row?.req_type || 'functional'
  form.priority = row?.priority || 'P1'
  form.status = row?.status || 'draft'
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (editing.value) {
      await requirementApi.update(editing.value.id, {
        title: form.title,
        description: form.description,
        req_type: form.req_type,
        priority: form.priority,
        status: form.status,
      })
      ElMessage.success('更新成功')
    } else {
      await requirementApi.create({
        project_id: projectId.value,
        title: form.title,
        description: form.description,
        req_type: form.req_type,
        priority: form.priority,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  if (row.testcase_count > 0) {
    ElMessage.warning(
      `该需求下有 ${row.testcase_count} 条关联用例，请先点击关联用例数字，清理全部关联用例后再删除`,
    )
    return
  }

  await ElMessageBox.confirm('确认删除该需求？', '确认删除', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  const res = await requirementApi.delete(row.id)
  ElMessage.success(res.message || '删除成功')
  loadData()
}

async function handleClearTestcases() {
  if (!currentRequirement.value) return
  await ElMessageBox.confirm(
    `确认清理「${currentRequirement.value.title}」下的全部 ${linkedTestcases.value.length} 条关联用例？`,
    '清理关联用例',
    {
      type: 'warning',
      confirmButtonText: '清理',
      cancelButtonText: '取消',
    },
  )
  clearingCases.value = true
  try {
    const res = await requirementApi.clearTestcases(currentRequirement.value.id)
    ElMessage.success(res.message || '清理成功')
    linkedTestcases.value = []
    casesDialogVisible.value = false
    loadData()
  } finally {
    clearingCases.value = false
  }
}

async function openTestcases(row) {
  currentRequirement.value = row
  casesDialogVisible.value = true
  await reloadLinkedTestcases()
}

async function reloadLinkedTestcases() {
  if (!currentRequirement.value) return
  casesLoading.value = true
  try {
    linkedTestcases.value = await testcaseApi.list({
      project_id: currentRequirement.value.project_id,
      requirement_id: currentRequirement.value.id,
    })
  } finally {
    casesLoading.value = false
  }
}

async function handleDeleteCase(caseId) {
  await testcaseApi.delete(caseId)
  ElMessage.success('删除成功')
  await reloadLinkedTestcases()
  loadData()
}

function openCaseDetail(row) {
  caseDetail.value = row
  caseDrawerVisible.value = true
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

async function handleBatchDelete() {
  if (!deletableSelectedCount.value) return

  const deletableIds = selectedRows.value.filter((row) => !row.testcase_count).map((row) => row.id)

  let confirmMessage = `确认删除选中的 ${deletableIds.length} 条需求？此操作不可恢复。`
  if (blockedSelectedCount.value) {
    confirmMessage += `\n\n另有 ${blockedSelectedCount.value} 条需求因存在关联用例将被跳过。`
  }

  await ElMessageBox.confirm(confirmMessage, '批量删除', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })

  batchDeleting.value = true
  try {
    const groups = groupRowsByProject(selectedRows.value.filter((row) => !row.testcase_count))
    let message = ''
    for (const [pid, rows] of groups) {
      const res = await requirementApi.batchDelete({
        project_id: Number(pid),
        requirement_ids: rows.map((row) => row.id),
      })
      message = res.message || message
    }
    ElMessage.success(message || '批量删除成功')
    loadData()
  } finally {
    batchDeleting.value = false
  }
}

async function handleBatchStatus() {
  if (!selectedIds.value.length || !batchStatus.value) return
  batchUpdating.value = true
  try {
    const groups = groupRowsByProject(selectedRows.value)
    let message = ''
    for (const [pid, rows] of groups) {
      const res = await requirementApi.batchUpdateStatus({
        project_id: Number(pid),
        requirement_ids: rows.map((row) => row.id),
        status: batchStatus.value,
      })
      message = res.message || message
    }
    ElMessage.success(message || '批量更新成功')
    batchStatus.value = ''
    loadData()
  } finally {
    batchUpdating.value = false
  }
}

onMounted(async () => {
  registerAssistantHandler('requirements.ensureProject', async () => {
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

  registerAssistantHandler('requirements.createDemo', async () => {
    if (isAllProjects.value) {
      throw new Error('请先选择具体项目')
    }
    openDialog()
    form.title = 'AI演示需求'
    form.description = '演示需求：用户可以使用账号密码登录系统，登录成功后进入首页。'
    form.req_type = 'functional'
    form.priority = 'P1'
    form.status = 'draft'
    await nextTick()
    await handleSubmit()
  })

  await loadProjects()
})

onUnmounted(() => {
  unregisterAssistantHandler('requirements.ensureProject')
  unregisterAssistantHandler('requirements.createDemo')
})
</script>

<style scoped>
.empty-count {
  color: #909399;
}

/* .table-fill / .pagination-bar 已提取为全局工具类（src/styles/layout.css） */

.pre-text {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}
</style>
