<template>
  <div class="jobs-panel">
    <div class="head">
      <span class="title">{{ panelTitle }}</span>
      <div class="head-actions">
        <el-button type="primary" size="small" @click="createVisible = true">
          <el-icon><Plus /></el-icon> 创建 AI 任务
        </el-button>
        <el-button size="small" :loading="loading" @click="reload">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="filters">
      <el-input
        v-model="filterTaskId"
        class="task-id"
        size="small"
        clearable
        placeholder="任务 ID"
        @keyup.enter="search"
      />
      <el-input
        v-model="filterKeyword"
        :maxlength="SEARCH_MAX_LEN"
        class="search"
        size="small"
        clearable
        placeholder="搜索目标 / 创建人"
        @keyup.enter="search"
      >
        <template #prefix
          ><el-icon><Search /></el-icon
        ></template>
      </el-input>
      <el-select
        v-model="statusFilter"
        class="status-select"
        size="small"
        clearable
        placeholder="全部状态"
      >
        <el-option v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        class="date-range"
        type="daterange"
        size="small"
        unlink-panels
        value-format="YYYY-MM-DD"
        range-separator="~"
        start-placeholder="创建起"
        end-placeholder="创建止"
      />
      <el-button type="primary" size="small" @click="search">搜索</el-button>
      <el-button size="small" @click="resetFilters">重置</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tasks"
      row-key="id"
      class="jobs-table"
      size="small"
      @row-click="openDetail"
    >
      <template #empty>
        <el-empty description="暂无 AI 任务" :image-size="60" />
      </template>
      <el-table-column label="ID" prop="id" width="72" />
      <el-table-column label="状态" width="96">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="目标" min-width="180" show-overflow-tooltip prop="target" />
      <el-table-column
        v-if="taskType === 'requirement'"
        label="模型"
        min-width="200"
        show-overflow-tooltip
      >
        <template #default="{ row }">{{
          aiTaskModelDisplay(row.model_label)
        }}</template>
      </el-table-column>
      <el-table-column
        v-else
        label="类别"
        min-width="150"
        show-overflow-tooltip
      >
        <template #default="{ row }">{{ formatHubTaskCategoryLabel(row.category_label) }}</template>
      </el-table-column>
      <el-table-column
        v-if="taskType === 'functional'"
        label="模型"
        min-width="200"
        show-overflow-tooltip
      >
        <template #default="{ row }">{{
          aiTaskModelDisplay(row.model_label)
        }}</template>
      </el-table-column>
      <el-table-column label="进度" width="120">
        <template #default="{ row }">
          <template v-if="taskType === 'requirement'">
            <span>{{ row.generated_total }} 条</span>
          </template>
          <template v-else>{{ row.done_items }}/{{ row.total_items }}</template>
        </template>
      </el-table-column>
      <el-table-column :label="generatedColumnLabel" width="108">
        <template #default="{ row }">{{ row.generated_total }} 条</template>
      </el-table-column>
      <el-table-column label="已入库" width="96">
        <template #default="{ row }">{{ row.applied_total }}/{{ row.generated_total }}</template>
      </el-table-column>
      <el-table-column label="创建人" min-width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.creator_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="140">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="完成时间" width="140">
        <template #default="{ row }">{{
          row.finished_at ? formatTime(row.finished_at) : '--'
        }}</template>
      </el-table-column>
      <el-table-column label="操作" width="112" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="openDetail(row)">查看</el-button>
          <el-button
            v-if="canStopTask(row)"
            link
            type="danger"
            size="small"
            :loading="stopTaskId === row.id"
            @click.stop="stopTask(row)"
          >
            停止
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > 0"
      small
      class="pager"
      layout="total, prev, pager, next, sizes"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      :page-sizes="[10, 20, 50]"
      @current-change="onPage"
      @size-change="onPageSizeChange"
    />

    <el-dialog
      v-model="detailVisible"
      :title="detailDialogTitle"
      width="min(920px, 96vw)"
      align-center
      destroy-on-close
      class="hub-ai-detail-dialog"
      @closed="onDetailClosed"
    >
      <template v-if="detailTask">
        <el-descriptions :column="2" border size="small" class="detail-summary">
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusType(detailTask.status)">{{
              statusText(detailTask.status)
            }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="目标">{{ detailTask.target }}</el-descriptions-item>
          <el-descriptions-item v-if="taskType === 'requirement'" label="模型">{{
            aiTaskModelDisplay(detailTask.model_label, detailTask.meta)
          }}</el-descriptions-item>
          <el-descriptions-item v-else label="类别">{{
            formatHubTaskCategoryLabel(detailTask.category_label)
          }}</el-descriptions-item>
          <el-descriptions-item v-if="taskType === 'functional'" label="模型">{{
            aiTaskModelDisplay(detailTask.model_label, detailTask.meta)
          }}</el-descriptions-item>
          <el-descriptions-item label="进度">
            <template v-if="taskType === 'requirement'">
              已提取 {{ detailTask.generated_total }} 条
              <span v-if="detailTask.total_items">
                · 文档段 {{ detailTask.done_items }}/{{ detailTask.total_items }}
                <span
                  v-if="detailSegmentInFlight > detailTask.done_items && detailTaskStillRunning"
                >
                  （正在解析第 {{ detailSegmentInFlight }} 段）
                </span>
              </span>
            </template>
            <template v-else>
              已生成 {{ detailTask.generated_total }} 条
              <span v-if="detailTask.total_items">
                · 计划 {{ detailTask.done_items }}/{{ detailTask.total_items }}
              </span>
            </template>
          </el-descriptions-item>
          <el-descriptions-item :label="generatedColumnLabel"
            >{{ detailTask.generated_total }} 条</el-descriptions-item
          >
          <el-descriptions-item label="已入库"
            >{{ detailTask.applied_total }}/{{ detailTask.generated_total }}</el-descriptions-item
          >
          <el-descriptions-item label="创建人">{{
            detailTask.creator_name || '—'
          }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{
            formatTime(detailTask.created_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="完成时间" :span="2">{{
            detailTask.finished_at ? formatTime(detailTask.finished_at) : '—'
          }}</el-descriptions-item>
          <el-descriptions-item v-if="detailTask.error" label="错误" :span="2">
            <span class="err-text">{{ detailTask.error }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailMetaMessage" label="说明" :span="2">{{
            detailMetaMessage
          }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="taskType === 'requirement'" class="detail-req-section">
          <div
            v-if="detailTaskStillRunning && detailTask.total_items"
            class="detail-chunk-progress"
          >
            <span class="detail-chunk-label">文档分段解析</span>
            <el-progress
              :percentage="chunkProgressPercent"
              :stroke-width="10"
              :status="detailTask.status === 'failed' ? 'exception' : undefined"
            />
          </div>
          <div class="detail-req-head">
            <div class="detail-req-head-left">
              <span class="detail-req-title">提取的需求点</span>
              <el-tag size="small" type="primary">
                {{ detailItemsTotal }}/{{ detailTask.generated_total || detailItemsTotal }} 条
              </el-tag>
            </div>
          </div>
          <el-empty
            v-if="!detailItemsTotal && !detailTaskStillRunning"
            description="暂无存档的需求点（该任务可能在明细落库功能上线前完成，请重新解析）"
            :image-size="48"
          />
          <div
            v-else-if="!detailItemsTotal && detailTaskStillRunning"
            v-loading="true"
            class="detail-req-loading"
            :element-loading-text="
              detailTask.status === 'pending'
                ? '排队中，等待使用同一模型的其他任务完成…'
                : '正在写入需求点明细…'
            "
          />
          <template v-else>
            <el-table
              v-loading="detailReqSyncing && detailTaskStillRunning"
              :data="detailRequirements"
              size="small"
              class="detail-req-table"
              max-height="360"
              border
              row-key="id"
            >
              <el-table-column type="index" label="序号" width="56" :index="detailRowIndex" />
              <el-table-column label="标题" min-width="160" prop="title" show-overflow-tooltip />
              <el-table-column label="类型" width="100">
                <template #default="{ row }">{{ reqTypeLabel(row.req_type) }}</template>
              </el-table-column>
              <el-table-column label="优先级" width="80" align="center" prop="priority" />
              <el-table-column label="描述" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">{{ row.description || '—' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.imported_at || row.requirement_id" size="small" type="success"
                    >已入库</el-tag
                  >
                  <span v-else class="req-pending">待入库</span>
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-if="detailItemsTotal > 0"
              small
              background
              class="detail-items-pager"
              layout="total, prev, pager, next, sizes"
              :total="detailItemsTotal"
              :page-size="detailItemsPageSize"
              :current-page="detailItemsPage"
              :page-sizes="[...DETAIL_PAGE_SIZE_OPTIONS]"
              @current-change="onDetailItemsPage"
              @size-change="onDetailItemsPageSizeChange"
            />
          </template>
        </div>

        <div v-else-if="taskType === 'functional'" class="detail-req-section">
          <div
            v-if="detailTaskStillRunning && detailTask.total_items"
            class="detail-chunk-progress"
          >
            <span class="detail-chunk-label">用例生成进度</span>
            <el-progress
              :percentage="chunkProgressPercent"
              :stroke-width="10"
              :status="detailTask.status === 'failed' ? 'exception' : undefined"
            />
          </div>
          <div class="detail-req-head">
            <span class="detail-req-title">生成的用例</span>
            <el-tag size="small" type="primary">
              {{ detailItemsTotal }}/{{ detailTask.generated_total || detailItemsTotal }} 条
            </el-tag>
          </div>
          <el-empty
            v-if="!detailItemsTotal && !detailTaskStillRunning"
            description="暂无存档的用例明细（该任务可能在明细落库功能上线前完成，请重新生成）"
            :image-size="48"
          />
          <div
            v-else-if="!detailItemsTotal && detailTaskStillRunning"
            v-loading="true"
            class="detail-req-loading"
            :element-loading-text="
              detailTask.status === 'pending'
                ? '排队中，等待使用同一模型的其他任务完成…'
                : '正在写入用例明细…'
            "
          />
          <template v-else>
            <el-table
              v-if="detailCases.length"
              v-loading="detailReqSyncing && detailTaskStillRunning"
              :data="detailCases"
              size="small"
              class="detail-req-table"
              max-height="360"
              border
              :row-key="caseRowKey"
            >
              <el-table-column type="index" label="序号" width="56" :index="detailRowIndex" />
              <el-table-column label="优先级" width="80" align="center" prop="priority" />
              <el-table-column label="标题" min-width="200" prop="title" show-overflow-tooltip />
              <el-table-column
                label="关联需求"
                min-width="140"
                prop="requirement_title"
                show-overflow-tooltip
              />
              <el-table-column label="评审" width="88" align="center">
                <template #default="{ row }">
                  <el-tag
                    size="small"
                    :type="row.review_status === 'approved' ? 'success' : 'warning'"
                  >
                    {{ row.review_status === 'approved' ? '已通过' : '待评审' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="72" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openCaseDetail(row)">
                    详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty
              v-else-if="detailItemsTotal > 0"
              description="用例明细加载异常，请关闭后重试或点击刷新"
              :image-size="48"
            />
            <el-pagination
              v-if="detailItemsTotal > 0"
              small
              background
              class="detail-items-pager"
              layout="total, prev, pager, next, sizes"
              :total="detailItemsTotal"
              :page-size="detailItemsPageSize"
              :current-page="detailItemsPage"
              :page-sizes="[...DETAIL_PAGE_SIZE_OPTIONS]"
              @current-change="onDetailItemsPage"
              @size-change="onDetailItemsPageSizeChange"
            />
          </template>
        </div>
      </template>
      <div v-else v-loading="detailLoading" class="detail-loading" />
    </el-dialog>

    <el-dialog
      v-model="caseDetailVisible"
      title="用例详情"
      width="min(560px, 92vw)"
      append-to-body
      align-center
      destroy-on-close
      class="hub-ai-case-detail-dialog"
    >
      <el-descriptions
        v-if="caseDetailRow"
        :column="1"
        border
        size="small"
        class="case-detail-desc"
      >
        <el-descriptions-item label="标题">{{ caseDetailRow.title }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ caseDetailRow.priority }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{
          formatCaseTypeLabel(caseDetailRow.case_type)
        }}</el-descriptions-item>
        <el-descriptions-item label="关联需求">{{
          caseDetailRow.requirement_title || '—'
        }}</el-descriptions-item>
        <el-descriptions-item label="评审">
          <el-tag
            size="small"
            :type="caseDetailRow.review_status === 'approved' ? 'success' : 'warning'"
          >
            {{ caseReviewLabel(caseDetailRow.review_status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="前置条件">{{
          caseDetailRow.preconditions || '—'
        }}</el-descriptions-item>
        <el-descriptions-item label="测试步骤">
          <pre class="pre-text">{{ caseDetailRow.steps || '—' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="预期结果">
          <pre class="pre-text">{{ caseDetailRow.expected_results || '—' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="标签">{{ caseDetailRow.tags || '—' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog
      v-model="createVisible"
      :title="createDialogTitle"
      width="min(1120px, 96vw)"
      top="4vh"
      align-center
      destroy-on-close
      class="hub-ai-create-dialog"
      @closed="onCreateClosed"
    >
      <div class="create-body">
        <RequirementDocs
          v-if="taskType === 'requirement'"
          :scoped-project-id="Number(pid)"
          embedded
        />
        <AIGenerate v-else :scoped-project-id="Number(pid)" embedded />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import {
  hubAiTasksApi,
  formatHubTaskCategoryLabel,
  type HubAiTaskBrief,
  type HubAiTaskCaseBrief,
  type HubAiTaskOut,
  type HubAiTaskRequirementItem,
  type HubAiTaskType,
} from '@/api/hubAiTasks'
import { useRouteParamId } from '@/composables/useRouteParamId'
import {
  parseWorkspaceKeywordFromRoute,
  parseWorkspaceTaskIdFromRoute,
} from '@/composables/useWorkspaceQuery'
import { mergeRowsInPlace } from '@/utils/mergeRows'
import { formatTime } from '@/utils/runFormat'
import { formatCaseTypeLabel } from '@/utils/caseType'
import { aiTaskModelDisplay } from '@/utils/aiTaskModelLabel'
import RequirementDocs from '@/views/RequirementDocs.vue'
import AIGenerate from '@/views/AIGenerate.vue'
import { useRequirementExtractStore } from '@/stores/requirementExtract'
import { useAiGenerateStore } from '@/stores/aiGenerate'

const props = withDefaults(
  defineProps<{
    panelTitle: string
    taskType: HubAiTaskType
    generatedColumnLabel?: string
    createDialogTitle?: string
  }>(),
  {
    generatedColumnLabel: '生成数',
    createDialogTitle: '创建 AI 任务',
  },
)

const TERMINAL = ['succeeded', 'partial', 'failed', 'canceled']
const DETAIL_PAGE_SIZE_OPTIONS = [10, 20, 50] as const
const POLL_MS = 5000
const DETAIL_POLL_MS = 4000
const STATUS_OPTIONS = [
  { value: 'pending', label: '排队中' },
  { value: 'running', label: '生成中' },
  { value: 'succeeded', label: '成功' },
  { value: 'partial', label: '部分成功' },
  { value: 'failed', label: '失败' },
  { value: 'canceled', label: '已取消' },
]

const pid = useRouteParamId()
const route = useRoute()
const router = useRouter()

const tasks = ref<HubAiTaskBrief[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const detailVisible = ref(false)
const detailTask = ref<HubAiTaskOut | null>(null)
const detailRequirements = ref<HubAiTaskRequirementItem[]>([])
const detailCases = ref<HubAiTaskCaseBrief[]>([])
const detailTaskId = ref<number | null>(null)
const detailLoading = ref(false)
const detailReqSyncing = ref(false)
const detailItemsPage = ref(1)
const detailItemsPageSize = ref(DEFAULT_PAGE_SIZE)
const detailItemsTotal = ref(0)
const caseDetailVisible = ref(false)
const caseDetailRow = ref<HubAiTaskCaseBrief | null>(null)
const createVisible = ref(false)
const stopTaskId = ref<number | null>(null)
const requirementExtractStore = useRequirementExtractStore()
const aiGenerateStore = useAiGenerateStore()
let pollTimer: ReturnType<typeof setInterval> | null = null
let detailPollTimer: ReturnType<typeof setInterval> | null = null
let listReloadInFlight = false
let detailPollInFlight = false

const filterKeyword = ref('')
const filterTaskId = ref('')
const statusFilter = ref('')
const dateRange = ref<[string, string] | null>(null)

const detailMetaMessage = computed(() => {
  const m = detailTask.value?.meta?.message
  return typeof m === 'string' ? m : ''
})

const detailSegmentInFlight = computed(() => {
  const raw = detailTask.value?.meta?.segment_in_flight
  const n = typeof raw === 'number' ? raw : Number(raw)
  return Number.isFinite(n) && n > 0 ? n : 0
})

const detailDialogTitle = computed(() => `${props.panelTitle}详情`)

const detailTaskStillRunning = computed(
  () => detailTask.value != null && !TERMINAL.includes(detailTask.value.status),
)

const chunkProgressPercent = computed(() => {
  const t = detailTask.value
  if (!t?.total_items) return 0
  return Math.min(100, Math.round((t.done_items / t.total_items) * 100))
})

const REQ_TYPE_LABELS: Record<string, string> = {
  functional: '功能测试',
  api: '接口测试',
  performance: '性能测试',
  security: '安全测试',
}
function reqTypeLabel(t: string) {
  return REQ_TYPE_LABELS[t] || t || '—'
}

const CASE_REVIEW_LABELS: Record<string, string> = {
  draft: '草稿',
  pending: '待评审',
  approved: '已通过',
  rejected: '已驳回',
}

function caseReviewLabel(status: string) {
  return CASE_REVIEW_LABELS[status] || (status === 'approved' ? '已通过' : '待评审')
}

function canStopTask(row: HubAiTaskBrief): boolean {
  return row.status === 'pending' || row.status === 'running'
}

async function stopTask(row: HubAiTaskBrief) {
  if (!pid.value || !canStopTask(row)) return
  try {
    await ElMessageBox.confirm(
      '停止后任务将标记为已取消，已写入的需求点/用例会保留。确认停止？',
      '停止任务',
      { confirmButtonText: '停止', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  stopTaskId.value = row.id
  try {
    await hubAiTasksApi.cancelTask(pid.value, row.id)
    if (props.taskType === 'requirement' && requirementExtractStore.hubTaskId === row.id) {
      requirementExtractStore.cancelExtract('任务已停止')
    }
    if (props.taskType === 'functional' && aiGenerateStore.hubTaskId === row.id) {
      aiGenerateStore.cancelGeneration('任务已停止')
    }
    ElMessage.success('任务已停止')
    if (detailTaskId.value === row.id) {
      detailVisible.value = false
    }
    await reload()
  } catch (e) {
    ElMessage.error((e as Error).message || '停止失败')
  } finally {
    stopTaskId.value = null
  }
}

function openCaseDetail(row: HubAiTaskCaseBrief) {
  caseDetailRow.value = row
  caseDetailVisible.value = true
}

function buildParams() {
  const params: Parameters<typeof hubAiTasksApi.listTasks>[1] = {
    task_type: props.taskType,
    page: page.value,
    page_size: pageSize.value,
  }
  const kw = filterKeyword.value.trim()
  if (kw) params.keyword = kw
  const taskId = parseTaskIdFilter(filterTaskId.value)
  if (taskId) params.task_id = taskId
  if (statusFilter.value) params.status = statusFilter.value
  if (dateRange.value?.[0]) params.date_from = dateRange.value[0]
  if (dateRange.value?.[1]) params.date_to = dateRange.value[1]
  return params
}

// silent=true 用于轮询刷新：不动 loading，避免每次 tick 闪一层遮罩
async function fetchTasks(silent = false) {
  if (listReloadInFlight) return
  listReloadInFlight = true
  if (!silent) loading.value = true
  try {
    const res = await hubAiTasksApi.listTasks(pid.value, buildParams())
    total.value = res.total
    if (res.total > 0 && res.items.length === 0 && page.value > 1) {
      page.value = Math.max(1, Math.ceil(res.total / pageSize.value))
      listReloadInFlight = false
      await fetchTasks(silent)
      return
    }
    tasks.value = mergeRowsInPlace(tasks.value, res.items)
  } finally {
    if (!silent) loading.value = false
    listReloadInFlight = false
  }
}

function reload() {
  return fetchTasks()
}

function parseTaskIdFilter(raw: string): number | null {
  const text = raw.trim()
  if (!/^\d+$/.test(text)) return null
  const id = Number(text)
  return Number.isInteger(id) && id > 0 ? id : null
}

function search() {
  filterTaskId.value = filterTaskId.value.replace(/\D/g, '')
  page.value = 1
  reload()
}

function resetFilters() {
  filterKeyword.value = ''
  filterTaskId.value = ''
  statusFilter.value = ''
  dateRange.value = null
  clearTaskQuery()
  page.value = 1
  reload()
}

function onPage(p: number) {
  page.value = p
  reload()
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  reload()
}

function caseRowKey(row: HubAiTaskCaseBrief) {
  return String(row.link_id ?? row.id)
}

function detailRowIndex(index: number) {
  return (detailItemsPage.value - 1) * detailItemsPageSize.value + index + 1
}

async function loadDetailItems(taskId: number) {
  if (props.taskType === 'requirement') {
    const req = await hubAiTasksApi.listRequirements(pid.value, taskId, {
      page: detailItemsPage.value,
      page_size: detailItemsPageSize.value,
    })
    if (req.total > 0 && req.items.length === 0 && detailItemsPage.value > 1) {
      detailItemsPage.value = Math.max(1, Math.ceil(req.total / detailItemsPageSize.value))
      return loadDetailItems(taskId)
    }
    detailRequirements.value = mergeRowsInPlace(detailRequirements.value, req.items)
    detailItemsTotal.value = req.total
    detailCases.value = []
  } else {
    detailRequirements.value = []
    const cases = await hubAiTasksApi.listCases(pid.value, taskId, {
      page: detailItemsPage.value,
      page_size: detailItemsPageSize.value,
    })
    if (cases.total > 0 && cases.items.length === 0 && detailItemsPage.value > 1) {
      detailItemsPage.value = Math.max(1, Math.ceil(cases.total / detailItemsPageSize.value))
      return loadDetailItems(taskId)
    }
    detailCases.value = mergeRowsInPlace(detailCases.value, cases.items ?? [])
    detailItemsTotal.value = cases.total ?? detailCases.value.length
  }
}

async function onDetailItemsPage(p: number) {
  detailItemsPage.value = p
  if (detailTaskId.value == null) return
  detailReqSyncing.value = true
  try {
    await loadDetailItems(detailTaskId.value)
  } finally {
    detailReqSyncing.value = false
  }
}

async function onDetailItemsPageSizeChange(size: number) {
  detailItemsPageSize.value = size
  detailItemsPage.value = 1
  if (detailTaskId.value == null) return
  detailReqSyncing.value = true
  try {
    await loadDetailItems(detailTaskId.value)
  } finally {
    detailReqSyncing.value = false
  }
}

async function refreshDetail(taskId: number, opts: { silent?: boolean } = {}) {
  if (!opts.silent) detailReqSyncing.value = true
  try {
    const task = await hubAiTasksApi.getTask(pid.value, taskId)
    // 同一任务只覆盖字段，避免详情区每轮轮询整体重建
    if (detailTask.value?.id === task.id) {
      Object.assign(detailTask.value, task)
    } else {
      detailTask.value = task
    }
    await loadDetailItems(taskId)
    return task
  } finally {
    if (!opts.silent) detailReqSyncing.value = false
  }
}

async function openDetailById(taskId: number) {
  detailVisible.value = true
  detailLoading.value = true
  detailTask.value = null
  detailRequirements.value = []
  detailCases.value = []
  detailTaskId.value = taskId
  detailItemsPage.value = 1
  detailItemsTotal.value = 0
  try {
    const task = await refreshDetail(taskId)
    if (task && !TERMINAL.includes(task.status)) {
      startDetailPoll()
    }
  } finally {
    detailLoading.value = false
  }
}

async function openDetail(row: HubAiTaskBrief) {
  await openDetailById(row.id)
}

function startDetailPoll() {
  stopDetailPoll()
  const tick = async () => {
    if (!detailVisible.value || detailTaskId.value == null) {
      stopDetailPoll()
      return
    }
    if (detailPollInFlight) return
    detailPollInFlight = true
    try {
      const task = await refreshDetail(detailTaskId.value, { silent: true })
      if (task && TERMINAL.includes(task.status)) {
        stopDetailPoll()
        reload()
      }
    } catch {
      /* 单次轮询失败忽略 */
    } finally {
      detailPollInFlight = false
    }
  }
  void tick()
  detailPollTimer = setInterval(tick, DETAIL_POLL_MS)
}

function stopDetailPoll() {
  if (detailPollTimer) {
    clearInterval(detailPollTimer)
    detailPollTimer = null
  }
}

function clearTaskQuery() {
  if (!route.query.task) return
  const query = { ...route.query }
  delete query.task
  void router.replace({ query })
}

function applyListFiltersFromRoute() {
  const taskId = parseWorkspaceTaskIdFromRoute(route)
  if (taskId) filterTaskId.value = String(taskId)
  const kw = parseWorkspaceKeywordFromRoute(route)
  if (kw) filterKeyword.value = kw
}

async function syncDetailFromQuery() {
  const taskId = parseWorkspaceTaskIdFromRoute(route)
  if (!taskId) return
  if (detailVisible.value && detailTaskId.value === taskId) return
  await openDetailById(taskId)
}

async function bootstrapFromRoute() {
  applyListFiltersFromRoute()
  page.value = 1
  await reload()
  await syncDetailFromQuery()
}

function onDetailClosed() {
  stopDetailPoll()
  detailTask.value = null
  detailRequirements.value = []
  detailCases.value = []
  detailTaskId.value = null
  detailItemsPage.value = 1
  detailItemsTotal.value = 0
  clearTaskQuery()
}

function onCreateClosed() {
  reload()
}

const statusText = (s: string): string =>
  ({
    pending: '排队中',
    running: '生成中',
    succeeded: '成功',
    partial: '部分成功',
    failed: '失败',
    canceled: '已取消',
  })[s] || s
const statusType = (s: string): string =>
  ({
    succeeded: 'success',
    partial: 'warning',
    failed: 'danger',
    running: 'primary',
    pending: 'warning',
    canceled: 'info',
  })[s] || 'info'

// 静默刷新，单次失败忽略，避免遮罩闪烁与未捕获拒绝
function tick() {
  if (tasks.value.some((t) => !TERMINAL.includes(t.status))) {
    fetchTasks(true).catch(() => {})
  }
}

onMounted(async () => {
  await bootstrapFromRoute()
  pollTimer = setInterval(tick, POLL_MS)
})
watch(
  () => [route.query.task, route.query.filter, route.query.keyword] as const,
  () => void bootstrapFromRoute(),
)
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  stopDetailPoll()
})
</script>

<style scoped>
.jobs-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: var(--ax-space-3);
  box-sizing: border-box;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-space-2-5);
}

.head-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.filters {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2-5);
  flex: none;
}

.task-id {
  width: 120px;
}

.search {
  width: 200px;
}

.status-select {
  width: 120px;
}

.date-range {
  width: 240px;
}

.title {
  font-size: var(--ax-font);
  font-weight: 600;
  color: var(--ax-brand);
}

.jobs-table {
  flex: 1;
  min-height: 0;
  cursor: pointer;
}

.pager {
  margin-top: var(--ax-space-2-5);
  justify-content: flex-end;
}

.detail-loading {
  min-height: 120px;
}

.err-text {
  color: var(--el-color-danger);
  word-break: break-word;
}

.create-body {
  height: min(78vh, 820px);
  min-height: 420px;
  overflow: hidden;
}

.create-body :deep(.requirement-docs),
.create-body :deep(.ai-generate) {
  height: 100%;
}

.hub-ai-create-dialog :deep(.el-dialog__body) {
  padding-top: var(--ax-space-1);
}

.hub-ai-detail-dialog :deep(.el-dialog__body) {
  max-height: min(82vh, 900px);
  overflow: auto;
}

.detail-summary {
  margin-bottom: var(--ax-space-3);
}

.detail-req-section {
  margin-top: var(--ax-space-1);
}

.detail-req-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.detail-req-head-left {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.req-pending {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
}

.detail-req-title {
  font-weight: 600;
  color: var(--ax-text);
}

.detail-req-table {
  width: 100%;
}

.detail-chunk-progress {
  margin-bottom: var(--ax-space-2-5);
}

.detail-chunk-label {
  display: block;
  margin-bottom: var(--ax-space-1);
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.detail-req-loading {
  min-height: 160px;
}

.case-expand-desc {
  margin: 4px 0;
}

.case-detail-desc :deep(.el-descriptions__label) {
  width: 88px;
}

.detail-items-pager {
  margin-top: var(--ax-space-2);
  justify-content: flex-end;
}

.pre-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: var(--ax-text-body-sm-size);
}
</style>
