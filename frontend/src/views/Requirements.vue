<template>
  <div>
    <div class="toolbar">
      <el-select v-model="projectId" placeholder="选择项目" style="width: 220px" @change="handleProjectChange">
        <el-option label="全部" :value="ALL_PROJECTS" />
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button type="primary" :disabled="isAllProjects" data-assistant="requirements.create_btn" @click="openDialog()">
        <el-icon><Plus /></el-icon> 添加需求
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
      <el-switch
        v-model="selectMode"
        inline-prompt
        active-text="批量选择"
        inactive-text="查看模式"
        @change="handleSelectModeChange"
      />
      <span v-if="requirements.length" class="total-tip">共 {{ requirements.length }} 条需求</span>
    </div>

    <div v-loading="loading" class="mindmap-panel">
      <RequirementMindMap
        v-if="mindTree"
        :tree="mindTree"
        :selected-ids="selectedIds"
        :select-mode="selectMode"
        @node-click="openRequirementDetail"
        @toggle-select="toggleRequirementSelect"
      />
      <el-empty v-else-if="!loading" description="暂无需求点" />
    </div>

    <el-drawer v-model="detailDrawerVisible" title="需求详情" size="480px">
      <template v-if="activeRequirement">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="ID">{{ activeRequirement.id }}</el-descriptions-item>
          <el-descriptions-item v-if="isAllProjects" label="项目">
            {{ activeRequirement.project_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="标题">{{ activeRequirement.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            {{ typeMap[activeRequirement.req_type] || activeRequirement.req_type }}
          </el-descriptions-item>
          <el-descriptions-item label="优先级">{{ activeRequirement.priority }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            {{ sourceMap[activeRequirement.source] || activeRequirement.source }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType[activeRequirement.status]" size="small">
              {{ statusMap[activeRequirement.status] || activeRequirement.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建人">{{ activeRequirement.creator_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联用例">
            <el-button
              v-if="activeRequirement.testcase_count > 0"
              link
              type="primary"
              @click="openTestcases(activeRequirement)"
            >
              {{ activeRequirement.testcase_count }} 条
            </el-button>
            <span v-else>0</span>
          </el-descriptions-item>
          <el-descriptions-item label="描述">
            <pre class="pre-text">{{ activeRequirement.description || '-' }}</pre>
          </el-descriptions-item>
        </el-descriptions>
        <div class="detail-actions">
          <el-button type="primary" @click="openDialog(activeRequirement)">编辑</el-button>
          <el-button
            type="danger"
            plain
            :disabled="activeRequirement.testcase_count > 0"
            @click="handleDelete(activeRequirement)"
          >
            删除
          </el-button>
        </div>
      </template>
    </el-drawer>

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
        <el-button type="primary" data-assistant="requirements.form.submit" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="casesDialogVisible"
      :title="`关联用例 - ${currentRequirement?.title || ''}`"
      width="900px"
    >
      <el-table :data="linkedTestcases" v-loading="casesLoading" stripe border max-height="420">
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
          <el-descriptions-item label="前置条件">{{ caseDetail.preconditions || '-' }}</el-descriptions-item>
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi, requirementApi, testcaseApi } from '@/api'
import { registerAssistantHandler, unregisterAssistantHandler } from '@/utils/assistantActionRegistry'
import RequirementMindMap from '@/components/RequirementMindMap.vue'
import { buildRequirementMindTree } from '@/utils/requirementMindMap'

const ALL_PROJECTS = '__all__'

const projects = ref([])
const requirements = ref([])
const linkedTestcases = ref([])
const selectedIds = ref([])
const selectedRows = ref([])
const projectId = ref(ALL_PROJECTS)
const batchStatus = ref('')
const selectMode = ref(false)
const loading = ref(false)
const batchUpdating = ref(false)
const batchDeleting = ref(false)
const casesLoading = ref(false)
const clearingCases = ref(false)
const dialogVisible = ref(false)
const detailDrawerVisible = ref(false)
const casesDialogVisible = ref(false)
const caseDrawerVisible = ref(false)
const submitting = ref(false)
const editing = ref(null)
const activeRequirement = ref(null)
const currentRequirement = ref(null)
const caseDetail = ref(null)
const formRef = ref()

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

const currentProjectName = computed(() => {
  if (isAllProjects.value) return '需求全景'
  return projects.value.find((item) => item.id === projectId.value)?.name || '项目需求'
})

const mindTree = computed(() =>
  buildRequirementMindTree(requirements.value, {
    projectName: currentProjectName.value,
    isAllProjects: isAllProjects.value,
  })
)

const deletableSelectedCount = computed(
  () => selectedRows.value.filter((row) => !row.testcase_count).length
)
const blockedSelectedCount = computed(
  () => selectedRows.value.filter((row) => row.testcase_count > 0).length
)

async function loadProjects() {
  projects.value = await projectApi.list()
  await loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (!isAllProjects.value) {
      params.project_id = projectId.value
    }
    requirements.value = await requirementApi.list(null, params)
    if (!selectMode.value) {
      selectedIds.value = []
      selectedRows.value = []
    } else {
      const idSet = new Set(requirements.value.map((item) => item.id))
      selectedRows.value = selectedRows.value.filter((row) => idSet.has(row.id))
      selectedIds.value = selectedRows.value.map((row) => row.id)
    }
  } finally {
    loading.value = false
  }
}

function handleProjectChange() {
  selectedIds.value = []
  selectedRows.value = []
  loadData()
}

function handleSelectModeChange(enabled) {
  if (!enabled) {
    selectedIds.value = []
    selectedRows.value = []
  }
}

function openRequirementDetail(row) {
  activeRequirement.value = row
  detailDrawerVisible.value = true
}

function toggleRequirementSelect(row) {
  const index = selectedIds.value.indexOf(row.id)
  if (index >= 0) {
    selectedIds.value.splice(index, 1)
    selectedRows.value = selectedRows.value.filter((item) => item.id !== row.id)
  } else {
    selectedIds.value.push(row.id)
    selectedRows.value.push(row)
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
  if (row) detailDrawerVisible.value = false
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
      `该需求下有 ${row.testcase_count} 条关联用例，请先点击关联用例数字，清理全部关联用例后再删除`
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
  if (activeRequirement.value?.id === row.id) {
    detailDrawerVisible.value = false
    activeRequirement.value = null
  }
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
    }
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

  const deletableIds = selectedRows.value
    .filter((row) => !row.testcase_count)
    .map((row) => row.id)

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
    const groups = groupRowsByProject(
      selectedRows.value.filter((row) => !row.testcase_count)
    )
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
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.mindmap-panel {
  min-height: 620px;
}

.total-tip {
  color: #909399;
  font-size: 13px;
}

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.pre-text {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}
</style>
