<template>
  <PageCard fill>
    <template #toolbar>
      <el-select
        v-if="!scoped"
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
        :maxlength="SEARCH_MAX_LEN"
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
        type="primary"
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
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ row, $index }">{{
            displayRequirementSortOrder(row, $index)
          }}</template>
        </el-table-column>
        <el-table-column
          v-if="isAllProjects"
          prop="project_name"
          label="项目"
          min-width="140"
          show-overflow-tooltip
        />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openReqDetail(row)">{{ row.title }}</el-button>
          </template>
        </el-table-column>
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
            <el-tag :type="statusType[row.status as RequirementStatus]" size="small">{{
              statusMap[row.status as RequirementStatus] || row.status
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="100">
          <template #default="{ row }">{{ row.creator_name || '-' }}</template>
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
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openReqDetail(row)">详情</el-button>
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
        :page-sizes="[...PAGE_SIZE_OPTIONS]"
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
        style="margin-bottom: var(--ax-space-4)"
      />
      <el-form label-width="88px" style="margin-bottom: var(--ax-space-4)">
        <el-form-item label="导入方式">
          <el-radio-group v-model="importMode">
            <el-radio value="append">追加</el-radio>
            <el-radio value="replace">覆盖</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="模版下载">
          <el-button
            link
            type="primary"
            :loading="templateDownloading === 'excel'"
            @click="downloadImportTemplate('excel')"
          >
            Excel 模版
          </el-button>
          <el-button
            link
            type="primary"
            :loading="templateDownloading === 'xmind'"
            @click="downloadImportTemplate('xmind')"
          >
            XMind 模版
          </el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="importMode === 'append'"
        type="info"
        :closable="false"
        show-icon
        title="追加：在现有需求点后追加 Excel 全部行（允许标题重复，序号自动续编）。"
        style="margin-bottom: var(--ax-space-4)"
      />
      <el-alert
        v-else
        type="warning"
        :closable="false"
        show-icon
        title="覆盖：删除当前项目无关联用例的需求点，已关联用例的需求点将保留；Excel 序号若与保留项冲突则自动避让续编。"
        style="margin-bottom: var(--ax-space-4)"
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
            Excel 需包含「标题」列，Excel
            有多少行就导入多少条（允许标题重复）；追加模式下序号自动续编；XMind 导入末级节点
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
          <el-input
            v-model="form.title"
            :maxlength="REQ_CASE_TITLE_MAX_LEN"
            show-word-limit
            data-assistant="requirements.form.title"
          />
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
            :maxlength="LONG_TEXT_MAX_LEN"
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
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ row, $index }">{{
            row.sort_order && row.sort_order > 0 ? row.sort_order : $index + 1
          }}</template>
        </el-table-column>
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
            <el-tag :type="reviewType[row.review_status as ReviewStatus]" size="small">
              {{ reviewMap[row.review_status as ReviewStatus] || row.review_status }}
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

    <el-drawer v-model="reqDetailVisible" title="需求详情" size="480px">
      <template v-if="reqDetail">
        <el-descriptions :column="1" border class="detail-desc" label-width="88px">
          <el-descriptions-item label="标题">{{ reqDetail.title }}</el-descriptions-item>
          <el-descriptions-item v-if="isAllProjects" label="项目">{{
            reqDetail.project_name || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag size="small">{{ typeMap[reqDetail.req_type] || reqDetail.req_type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">{{ reqDetail.priority }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag :type="reqDetail.source === 'ai_document' ? 'warning' : ''" size="small">
              {{ sourceMap[reqDetail.source] || reqDetail.source }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType[reqDetail.status as RequirementStatus]" size="small">
              {{ statusMap[reqDetail.status as RequirementStatus] || reqDetail.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建人">{{
            reqDetail.creator_name || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="关联用例">{{
            reqDetail.testcase_count
          }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{
            formatTime(reqDetail.created_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="描述">
            <pre class="pre-text">{{ reqDetail.description || '-' }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>

    <el-drawer v-model="caseDrawerVisible" title="用例详情" size="480px">
      <template v-if="caseDetail">
        <el-descriptions :column="1" border class="detail-desc" label-width="88px">
          <el-descriptions-item label="标题">{{ caseDetail.title }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ caseDetail.priority }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{
            formatCaseTypeLabel(caseDetail.case_type)
          }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            {{ caseDetail.source === 'ai_generated' ? 'AI生成' : '手动' }}
          </el-descriptions-item>
          <el-descriptions-item label="评审状态">
            {{ reviewMap[caseDetail.review_status as ReviewStatus] || caseDetail.review_status }}
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

<script setup lang="ts">
import { LONG_TEXT_MAX_LEN, REQ_CASE_TITLE_MAX_LEN, SEARCH_MAX_LEN } from '@/constants/limits'
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Search, UploadFilled } from '@element-plus/icons-vue'
import { projectApi, requirementApi, testcaseApi } from '@/api'
import type { ProjectPageOut } from '@/api/project'
import { readWorkspaceListFilter } from '@/composables/useWorkspaceQuery'
import {
  displayRequirementSortOrder as calculateRequirementSortOrder,
  formatRequirementTime as formatTime,
  requirementSourceLabel as sourceMap,
  requirementStatusLabel as statusMap,
  requirementStatusType as statusType,
  requirementTypeLabel as typeMap,
  reviewStatusLabel as reviewMap,
  reviewStatusType as reviewType,
} from '@/composables/useRequirementDisplay'
import { formatCaseTypeLabel } from '@/utils/caseType'
import PageCard from '@/components/PageCard.vue'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS } from '@/constants/pagination'
import {
  registerAssistantHandler,
  unregisterAssistantHandler,
} from '@/utils/assistantActionRegistry'

import {
  ALL_PROJECTS,
  type Project,
  type ProjectFilter,
  type Requirement,
  type RequirementStatus,
  type ReviewStatus,
  type TestCase,
} from '@/types/common'
import type { FormInstance, FormRules } from '@/types/element-plus'
import type { UploadInstance, UploadRawFile } from 'element-plus'

interface RequirementForm {
  title: string
  description: string
  req_type: string
  priority: string
  status: string
}

function displayRequirementSortOrder(row: Requirement, rowIndex: number): number {
  return calculateRequirementSortOrder(row, rowIndex, currentPage.value, pageSize.value)
}

// scopedProjectId 传入时锁定该项目（新壳工作区场景）：隐藏项目下拉、关闭「全部项目」模式；
// 不传时保持独立页原行为（旧顶层路由 /requirements 仍可用）
const props = defineProps<{ scopedProjectId?: number }>()
const scoped = computed(() => props.scopedProjectId != null)
const route = useRoute()

const projects = ref<Project[]>([])
const requirements = ref<Requirement[]>([])
const linkedTestcases = ref<TestCase[]>([])
const selectedIds = ref<number[]>([])
const selectedRows = ref<Requirement[]>([])
const projectId = ref<ProjectFilter>(props.scopedProjectId ?? ALL_PROJECTS)
const filterStatus = ref('')
const filterSource = ref('')
const filterUnreviewed = ref(false)
const filterUnlinked = ref(false)
const keyword = ref('')
const batchStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
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
const reqDetailVisible = ref(false)
const submitting = ref(false)
const editing = ref<Requirement | null>(null)
const currentRequirement = ref<Requirement | null>(null)
const caseDetail = ref<TestCase | null>(null)
const reqDetail = ref<Requirement | null>(null)
const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const importFile = ref<UploadRawFile | null>(null)
const importMode = ref<'append' | 'replace'>('append')
const templateDownloading = ref<'excel' | 'xmind' | ''>('')

const form = reactive<RequirementForm>({
  title: '',
  description: '',
  req_type: 'functional',
  priority: 'P1',
  status: 'draft',
})

const rules: FormRules<RequirementForm> = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    {
      max: REQ_CASE_TITLE_MAX_LEN,
      message: `标题不能超过 ${REQ_CASE_TITLE_MAX_LEN} 字`,
      trigger: 'blur',
    },
  ],
}

function isProjectPage(data: Project[] | ProjectPageOut): data is ProjectPageOut {
  return !Array.isArray(data)
}

const isAllProjects = computed(() => projectId.value === ALL_PROJECTS)

// 新壳切换项目 → 同步锁定并重载
watch(
  () => props.scopedProjectId,
  (v) => {
    if (v == null) return
    projectId.value = v
    currentPage.value = 1
    loadData()
  },
)

const deletableSelectedCount = computed(
  () => selectedRows.value.filter((row) => !row.testcase_count).length,
)
const blockedSelectedCount = computed(
  () => selectedRows.value.filter((row) => row.testcase_count > 0).length,
)

async function loadProjects() {
  const data = await projectApi.list()
  projects.value = isProjectPage(data) ? data.items : data
  await loadData()
}

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
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    if (filterSource.value) {
      params.source = filterSource.value
    }
    if (filterUnreviewed.value) {
      params.unreviewed = true
    }
    if (filterUnlinked.value) {
      params.linked = false
    }
    if (keyword.value.trim()) {
      params.keyword = keyword.value.trim()
    }
    const data = await requirementApi.listPage(undefined, {
      ...params,
      page: currentPage.value,
      page_size: pageSize.value,
    })
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

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function downloadImportTemplate(format: 'excel' | 'xmind') {
  templateDownloading.value = format
  try {
    const blob =
      format === 'excel'
        ? await requirementApi.downloadImportTemplateExcel()
        : await requirementApi.downloadImportTemplateXmind()
    downloadBlob(
      blob,
      format === 'excel'
        ? 'requirements_import_template.xlsx'
        : 'requirements_import_template.xmind',
    )
  } catch (e) {
    ElMessage.error((e as Error).message || '模版下载失败')
  } finally {
    templateDownloading.value = ''
  }
}

function currentProjectName() {
  return projects.value.find((item) => item.id === projectId.value)?.name || 'requirements'
}

async function handleExport(format: string) {
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
  importMode.value = 'append'
  importFile.value = null
  uploadRef.value?.clearFiles()
  importDialogVisible.value = true
}

function handleImportFileChange(uploadFile: { raw?: UploadRawFile }) {
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
  if (importMode.value === 'replace') {
    try {
      await ElMessageBox.confirm(
        '覆盖导入将删除无关联用例的需求点；已关联用例的需求点会保留，并以 Excel 为准导入新需求。是否继续？',
        '确认覆盖导入',
        { type: 'warning', confirmButtonText: '覆盖导入', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
  }
  importing.value = true
  try {
    const res = await requirementApi.importFile(projectId.value, importFile.value, importMode.value)
    if (res.imported_count === 0) {
      ElMessage.warning(res.message || '未导入任何需求')
    } else {
      ElMessage.success(res.message || '导入成功')
    }
    importDialogVisible.value = false
    importFile.value = null
    uploadRef.value?.clearFiles()
    currentPage.value = 1
    loadData()
  } finally {
    importing.value = false
  }
}

defineExpose({ create: () => openDialog() })

function openDialog(row: Requirement | null = null) {
  editing.value = row
  form.title = row?.title || ''
  form.description = row?.description || ''
  form.req_type = row?.req_type || 'functional'
  form.priority = row?.priority || 'P1'
  form.status = row?.status || 'draft'
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value?.validate()
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
      if (typeof projectId.value !== 'number') {
        ElMessage.warning('请选择具体项目')
        return
      }
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

async function handleDelete(row: Requirement) {
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
  await requirementApi.delete(row.id)
  ElMessage.success('删除成功')
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

async function openTestcases(row: Requirement) {
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

async function handleDeleteCase(caseId: number) {
  await testcaseApi.delete(caseId)
  ElMessage.success('删除成功')
  await reloadLinkedTestcases()
  loadData()
}

function openReqDetail(row: Requirement) {
  reqDetail.value = row
  reqDetailVisible.value = true
}

function openCaseDetail(row: TestCase) {
  caseDetail.value = row
  caseDrawerVisible.value = true
}

function handleSelectionChange(rows: Requirement[]) {
  selectedRows.value = rows
  selectedIds.value = rows.map((row) => row.id)
}

function groupRowsByProject(rows: Requirement[]) {
  const groups = new Map<number, Requirement[]>()
  for (const row of rows) {
    if (!groups.has(row.project_id)) groups.set(row.project_id, [])
    groups.get(row.project_id)!.push(row)
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

function applyListFilterFromHash() {
  const filter = readWorkspaceListFilter()
  filterStatus.value = ''
  filterSource.value = ''
  filterUnreviewed.value = false
  filterUnlinked.value = false
  keyword.value = ''
  if (filter?.startsWith('kw:')) keyword.value = filter.slice(3)
  else if (filter === 'unreviewed') filterUnreviewed.value = true
  else if (filter === 'unlinked') filterUnlinked.value = true
  else if (filter === 'ai_document') filterSource.value = 'ai_document'
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

  applyListFilterFromHash()
  await loadProjects()
})

watch(
  () => route.fullPath,
  () => {
    if (!scoped.value) return
    applyListFilterFromHash()
    currentPage.value = 1
    loadData()
  },
)

onUnmounted(() => {
  unregisterAssistantHandler('requirements.ensureProject')
  unregisterAssistantHandler('requirements.createDemo')
})
</script>

<style scoped>
.empty-count {
  color: var(--ax-text-placeholder);
}

/* .table-fill / .pagination-bar 已提取为全局工具类（src/styles/layout.css） */

.pre-text {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  font-size: var(--ax-text-body-size);
  line-height: var(--ax-leading-relaxed);
}

.detail-desc :deep(.el-descriptions__label) {
  width: 88px;
  min-width: 88px;
  white-space: nowrap;
  color: var(--ax-text-secondary);
  font-weight: 600;
}
</style>
