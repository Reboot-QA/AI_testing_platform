<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <div class="cases-toolbar">
      <div class="cases-toolbar__filters">
        <el-radio-group v-model="filter" size="small" class="cases-toolbar__categories">
          <el-radio-button v-for="f in CATEGORY_FILTERS" :key="f.value" :value="f.value">
            {{ f.label }} ({{ catCount(f.value) }})
          </el-radio-button>
        </el-radio-group>
        <el-button v-if="!readonly" type="primary" size="small" @click="addCase">
          <el-icon><Plus /></el-icon> 添加用例
        </el-button>
      </div>
      <div class="cases-toolbar__actions">
        <el-input
          v-model="keyword"
          :maxlength="SEARCH_MAX_LEN"
          size="small"
          placeholder="搜索用例名"
          clearable
          class="cases-toolbar__search"
        />
        <el-button v-if="!readonly" size="small" @click="aiGenerate">
          <el-icon><MagicStick /></el-icon> AI 生成
        </el-button>
        <el-button
          v-if="!readonly && selected.size"
          size="small"
          type="danger"
          plain
          @click="batchDelete"
        >
          批量删除 ({{ selected.size }})
        </el-button>
        <el-button size="small" type="primary" plain :loading="runningAll" @click="runAll">
          <el-icon><VideoPlay /></el-icon> 全部运行
        </el-button>
      </div>
    </div>

    <div v-if="!readonly && filteredCases.length" class="case-list-head">
      <el-checkbox
        :model-value="allFilteredSelected"
        :indeterminate="someFilteredSelected"
        class="shrink-0"
        @change="toggleSelectAllFiltered"
      />
      <span class="text-xs text-muted-foreground">全选</span>
      <span v-if="selected.size" class="text-xs text-muted-foreground">
        （已选 {{ selected.size }} / {{ filteredCases.length }}）
      </span>
      <el-button v-if="selected.size" size="small" text @click="selected.clear()"
        >取消选择</el-button
      >
    </div>

    <el-collapse v-model="expanded" class="case-list min-h-0 flex-1 overflow-auto">
      <el-collapse-item v-for="(c, i) in filteredCases" :key="c.id" :name="c.id">
        <template #title>
          <div class="flex w-full items-center gap-1.5 pr-2">
            <el-checkbox
              v-if="!readonly"
              :model-value="selected.has(c.id)"
              class="shrink-0"
              @click.stop
              @change="toggleSelect(c.id)"
            />
            <span class="min-w-4 text-xs text-muted-foreground">{{ i + 1 }}</span>
            <el-tag size="small" :type="tagType(c.category)">{{
              categoryLabel(c.category)
            }}</el-tag>
            <el-tag v-if="c.origin === 'ai'" size="small" type="warning" effect="plain">AI</el-tag>
            <span class="min-w-0 flex-1 truncate" :title="c.name">{{ c.name }}</span>
            <span
              class="case-last-run text-right text-xs tabular-nums text-muted-foreground"
              :title="c.last_run_at || '尚未运行'"
            >
              {{ c.last_run_at ? formatTime(c.last_run_at) : '—' }}
            </span>
            <span
              v-if="c.last_result === 'passed' || c.last_result === 'failed'"
              class="result-cell"
              @click.stop
            >
              <el-tag
                size="small"
                class="result-tag"
                :type="resultTag(c.last_result)"
                @click="openRunDetail(c)"
              >
                {{ resultLabel(c.last_result) }}
              </el-tag>
              <button type="button" class="result-detail-btn" @click="openRunDetail(c)">
                详情
              </button>
            </span>
            <el-tag v-else-if="c.last_result" size="small" :type="resultTag(c.last_result)">
              {{ resultLabel(c.last_result) }}
            </el-tag>
            <span v-if="!readonly" class="case-row-actions">
              <el-button link size="small" @click.stop="copyCase(c)">复制</el-button>
              <el-button link type="danger" size="small" @click.stop="delCase(c)">删除</el-button>
            </span>
          </div>
        </template>
        <CaseEditorInline
          v-if="expanded.includes(c.id)"
          :case-id="c.id"
          :project-id="projectId"
          :list-index="i + 1"
          :scripts="scripts"
          :datasets="datasets"
          :schemas="schemas"
          @saved="onCaseSaved"
          @ran="loadCases"
        />
      </el-collapse-item>
    </el-collapse>
    <el-empty v-if="!filteredCases.length" description="暂无用例" :image-size="60" />

    <el-drawer
      v-model="runDrawerVisible"
      :show-close="true"
      :with-header="false"
      size="65%"
      class="run-report-drawer"
      @closed="onRunDrawerClosed"
    >
      <div v-loading="runDetailLoading" class="run-drawer-body">
        <RunReportDetail v-if="runDetail" :detail="runDetail" :environment-name="runEnvName">
          <RunStepGroups :detail="runDetail" />
        </RunReportDetail>
        <el-empty v-else-if="!runDetailLoading" description="暂无运行详情" :image-size="64" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { nameInputOptions } from '@/utils/promptLimits'
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { emptySpec, normalizeSpec as normSpec } from '@/utils/apifoxSpec'
import { CATEGORY_FILTERS, categoryLabel } from '@/utils/caseCategory'
import { formatTime } from '@/utils/runFormat'
import CaseEditorInline from '@/components/apifox/case/CaseEditorInline.vue'
import RunReportDetail from '@/components/apifox/run/RunReportDetail.vue'
import RunStepGroups from '@/components/apifox/run/RunStepGroups.vue'

const props = withDefaults(
  defineProps<{
    endpointId: Id
    projectId: Id
    readonly?: boolean
  }>(),
  { readonly: false },
)
const emit = defineEmits<{ changed: []; 'open-ai-gen': [startDialog?: boolean]; 'batch-run-done': [] }>()

const store = useWorkspaceStore()
const cases = ref<Schemas['CaseBrief'][]>([])
const scripts = ref<Schemas['ScriptBrief'][]>([])
const datasets = ref<Schemas['DatasetBrief'][]>([])
const schemas = ref<Schemas['SchemaBrief'][]>([])
const filter = ref('all')
const keyword = ref('')
const expanded = ref<number[]>([])
const runningAll = ref(false)
const selected = ref<Set<number>>(new Set())
const runDrawerVisible = ref(false)
const runDetail = ref<Schemas['RunOut'] | null>(null)
const runDetailLoading = ref(false)

const runEnvName = computed(() => {
  const id = runDetail.value?.environment_id
  if (id == null) return '-'
  return store.environments.find((e) => e.id === id)?.name || '-'
})

async function resolveLatestRunId(c: Schemas['CaseBrief']): Promise<number | null> {
  // 先在接口最近运行批次里按用例 id 找
  try {
    const batch = await apifoxApi.listEndpointRuns(props.endpointId)
    const inBatch = batch.find((r) => r.target_type === 'case' && r.target_id === c.id)
    if (inBatch) return inBatch.id
  } catch {
    /* 继续退到项目报告检索 */
  }
  // 再退：项目报告列表按用例名搜，精确匹配 target_id
  try {
    const page = await apifoxApi.listRunsPage(props.projectId, {
      target_types: 'case',
      keyword: c.name,
      page_size: 50,
    })
    const hit = page.items.find((r) => r.target_id === c.id)
    if (hit) return hit.id
  } catch {
    /* ignore */
  }
  return null
}

async function openRunDetail(c: Schemas['CaseBrief']) {
  runDrawerVisible.value = true
  runDetailLoading.value = true
  runDetail.value = null
  try {
    const runId = await resolveLatestRunId(c)
    if (!runId) {
      ElMessage.info('暂无运行详情')
      runDrawerVisible.value = false
      return
    }
    runDetail.value = await apifoxApi.getRun(runId)
  } catch {
    ElMessage.error('加载运行详情失败')
    runDrawerVisible.value = false
  } finally {
    runDetailLoading.value = false
  }
}

function onRunDrawerClosed() {
  runDetail.value = null
}

function toggleSelect(id: number) {
  const next = new Set(selected.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selected.value = next
}

const filteredCases = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return cases.value.filter(
    (c) =>
      (filter.value === 'all' || c.category === filter.value) &&
      (!kw || c.name.toLowerCase().includes(kw)),
  )
})

const filteredIds = computed(() => filteredCases.value.map((c) => c.id))

const allFilteredSelected = computed(() => {
  const ids = filteredIds.value
  return ids.length > 0 && ids.every((id) => selected.value.has(id))
})

const someFilteredSelected = computed(() => {
  const ids = filteredIds.value
  const n = ids.filter((id) => selected.value.has(id)).length
  return n > 0 && n < ids.length
})

function toggleSelectAllFiltered(checked: boolean | string | number) {
  const on = checked === true
  const next = new Set(selected.value)
  for (const id of filteredIds.value) {
    if (on) next.add(id)
    else next.delete(id)
  }
  selected.value = next
}

const catCount = (v: string) =>
  v === 'all' ? cases.value.length : cases.value.filter((c) => c.category === v).length

const tagType = (cat: string) =>
  ({ positive: 'success', negative: 'warning', boundary: '', security: 'danger' })[cat] || 'info'
const resultLabel = (r: string) => (r === 'passed' ? '通过' : r === 'failed' ? '失败' : '运行中')
const resultTag = (r: string) => (r === 'passed' ? 'success' : r === 'failed' ? 'danger' : 'info')

async function loadCases() {
  cases.value = props.endpointId ? await apifoxApi.listCases(props.endpointId) : []
}

// 新增/删除/复制后：刷新列表并通知父级更新左树用例数
async function reload() {
  await loadCases()
  emit('changed')
}

// 供父级在 AI 入库后 / 切回本 tab 时拉新列表（不重复 emit changed）
defineExpose({ loadCases, reload })

function onCaseSaved(id: Id, name: string, category: string) {
  const c = cases.value.find((x) => x.id === Number(id))
  if (c) {
    c.name = name
    c.category = category
  }
  // 保存用例后端会清接口的「待复核」标记，需通知上层 reload 树，否则红点一直不消
  emit('changed')
}

function emptyCasePayload(name: string, category: string): Schemas['CaseCreate'] {
  return {
    name,
    category,
    request_spec: emptySpec() as Schemas['CaseCreate']['request_spec'],
    variables: [],
    data_drive: { enabled: false, source: 'inline', rows: [] },
    assertions: [],
    extracts: [],
    pre_scripts: [],
    post_scripts: [],
  }
}

async function addCase() {
  const { value } = await ElMessageBox.prompt('用例名称', '新建用例', {
    ...nameInputOptions(),
  })
  const category = filter.value === 'all' ? 'other' : filter.value
  const payload = emptyCasePayload(value, category)
  try {
    const ep = await apifoxApi.getEndpoint(props.endpointId)
    if (ep?.request_spec)
      payload.request_spec = normSpec(ep.request_spec) as Schemas['CaseCreate']['request_spec']
  } catch {
    /* 拉取接口失败则用空 spec，不阻塞建用例 */
  }
  const created = await apifoxApi.createCase(props.endpointId, payload)
  ElMessage.success('已创建')
  await reload()
  expanded.value = [created.id] // 新建后直接展开编辑
}

async function copyCase(c: Schemas['CaseBrief']) {
  const created = await apifoxApi.copyCase(c.id)
  ElMessage.success('已复制')
  await reload()
  expanded.value = [created.id]
}

function apiErrorMessage(e: unknown): string {
  if (e && typeof e === 'object' && 'response' in e) {
    const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    if (typeof d === 'string') return d
  }
  return e instanceof Error ? e.message : String(e)
}

async function delCase(c: Schemas['CaseBrief']) {
  await ElMessageBox.confirm(`确认删除用例「${c.name}」？`, '提示', { type: 'warning' })
  try {
    await apifoxApi.deleteCase(c.id)
  } catch (e: unknown) {
    const msg = apiErrorMessage(e)
    if (!/场景|套件/.test(msg)) throw e
    await ElMessageBox.confirm(
      `${msg}\n\n是否同时从测试场景/套件中移除引用并删除该用例？`,
      '无法直接删除',
      { type: 'warning', confirmButtonText: '移除引用并删除' },
    )
    await apifoxApi.batchDeleteCases(props.endpointId, [c.id], { detachRefs: true })
  }
  expanded.value = expanded.value.filter((id) => id !== c.id)
  ElMessage.success('已删除')
  await reload()
}

function formatBlockedDetails(details?: Schemas['CaseBatchDeleteBlockedItem'][]) {
  if (!details?.length) return ''
  return details
    .map((d) => {
      const parts: string[] = []
      if (d.scenarios?.length) parts.push(`场景：${d.scenarios.join('、')}`)
      if (d.suites?.length) parts.push(`套件：${d.suites.join('、')}`)
      return `· ${d.name}${parts.length ? `（${parts.join('；')}）` : ''}`
    })
    .join('\n')
}

async function runBatchDelete(ids: number[], confirmMsg: string, detachRefs = false) {
  if (!ids.length) return
  await ElMessageBox.confirm(confirmMsg, detachRefs ? '清空 AI 用例' : '批量删除', {
    type: 'warning',
  })
  const r = await apifoxApi.batchDeleteCases(props.endpointId, ids, { detachRefs })
  expanded.value = expanded.value.filter((id) => !ids.includes(id))
  selected.value = new Set()

  if (r.blocked?.length && !detachRefs) {
    const blockedIds = cases.value.filter((c) => r.blocked!.includes(c.name)).map((c) => c.id)
    const detail = formatBlockedDetails(r.blocked_details)
    try {
      await ElMessageBox.confirm(
        `已删除 ${r.deleted} 条；另有 ${r.blocked.length} 条被测试场景或套件引用：\n\n${detail}\n\n是否同时移除引用并删除这些用例？`,
        '部分未删除',
        { type: 'warning', confirmButtonText: '移除引用并删除' },
      )
      await runBatchDelete(blockedIds, `确认删除剩余 ${blockedIds.length} 条用例？`, true)
      return
    } catch {
      /* 用户取消二次确认 */
    }
    ElMessage.warning(`已删 ${r.deleted} 条；${r.blocked.length} 条因被引用未删`)
  } else if (r.deleted === 0 && r.blocked?.length) {
    ElMessage.warning('所选用例均被场景或套件引用，未删除')
  } else {
    ElMessage.success(`已删除 ${r.deleted} 条（可在回收站还原）`)
  }
  await reload()
}

function batchDelete() {
  runBatchDelete(
    [...selected.value],
    `确认删除选中的 ${selected.value.size} 条用例？可在回收站还原。`,
  )
}

function aiGenerate() {
  emit('open-ai-gen', true)
}

async function runAll() {
  const targets = filteredCases.value
  if (!targets.length) return
  runningAll.value = true
  try {
    await apifoxApi.runEndpointAllStream(
      props.endpointId,
      store.currentEnvironmentId ?? undefined,
      targets.map((c) => c.id),
      () => {},
    )
    await loadCases()
    ElMessage.success('全部运行完成')
    emit('batch-run-done')
  } catch (e) {
    ElMessage.error((e as Error).message || '全部运行失败')
  } finally {
    runningAll.value = false
  }
}

watch(
  () => props.endpointId,
  () => {
    expanded.value = []
    keyword.value = ''
    selected.value = new Set()
    if (props.endpointId) void reload()
    else cases.value = []
  },
  { immediate: true },
)

apifoxApi.listScripts(props.projectId).then((r) => (scripts.value = r))
apifoxApi.listDatasets(props.projectId).then((r) => (datasets.value = r))
apifoxApi.listSchemas(props.projectId).then((r) => (schemas.value = r))
</script>

<style scoped>
.cases-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
  padding-bottom: var(--ax-space-2);
  border-bottom: 1px solid var(--el-border-color-lighter, var(--ax-raw-hex-ebeef5));
}

.cases-toolbar__filters,
.cases-toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ax-space-2);
}

.cases-toolbar__categories {
  display: flex;
  max-width: 100%;
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-width: none;
}

.cases-toolbar__categories::-webkit-scrollbar {
  display: none;
}

.cases-toolbar__actions {
  justify-content: flex-end;
}

.cases-toolbar__search {
  width: 200px;
}

.cases-toolbar :deep(.el-input),
.cases-toolbar :deep(.el-button) {
  --el-component-size: var(--ax-control-height-sm);
}

.case-list-head {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-1);
  padding: 0 var(--ax-space-1);
}

.case-list :deep(.el-collapse-item__header) {
  height: 36px;
  padding: 0 var(--ax-space-2);
  font-size: var(--ax-font-xs);
  line-height: 36px;
}

.case-list :deep(.el-collapse-item__content) {
  padding-bottom: var(--ax-space-2);
}

.case-last-run {
  width: 96px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-row-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1);
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .cases-toolbar__actions {
    width: 100%;
    justify-content: flex-start;
  }

  .cases-toolbar__search {
    flex: 1;
    min-width: 180px;
  }
}

.result-cell {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1);
  min-width: 52px;
}

.result-tag {
  cursor: pointer;
}

.result-detail-btn {
  flex-shrink: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-blue-6);
  font-size: var(--ax-font-xs);
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
}

.result-detail-btn:hover {
  text-decoration: underline;
}

.run-drawer-body {
  min-height: 200px;
}

.run-report-drawer :deep(.el-drawer__body) {
  padding: var(--ax-space-4);
}
</style>
