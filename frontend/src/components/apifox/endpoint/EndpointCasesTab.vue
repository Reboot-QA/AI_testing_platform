<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <el-radio-group v-model="filter" size="small" class="flex-wrap">
          <el-radio-button v-for="f in CATEGORY_FILTERS" :key="f.value" :value="f.value">
            {{ f.label }} ({{ catCount(f.value) }})
          </el-radio-button>
        </el-radio-group>
        <el-button v-if="!readonly" type="primary" size="small" @click="addCase">
          <el-icon><Plus /></el-icon> 添加用例
        </el-button>
      </div>
      <div class="flex items-center gap-1.5">
        <el-input
          v-model="keyword"
          :maxlength="SEARCH_MAX_LEN"
          size="small"
          placeholder="搜索用例名"
          clearable
          class="w-40"
        />
        <el-button v-if="!readonly" size="small" @click="aiGenerate">
          <el-icon><MagicStick /></el-icon> AI 生成用例
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

    <div
      v-if="!readonly && filteredCases.length"
      class="case-list-head mb-1 flex items-center gap-2 px-1"
    >
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

    <el-collapse v-model="expanded" class="min-h-0 flex-1 overflow-auto">
      <el-collapse-item v-for="(c, i) in filteredCases" :key="c.id" :name="c.id">
        <template #title>
          <div class="flex w-full items-center gap-2 pr-2">
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
              class="min-w-[132px] shrink-0 text-right text-xs tabular-nums text-muted-foreground"
              :title="c.last_run_at || '尚未运行'"
            >
              {{ c.last_run_at ? formatTime(c.last_run_at) : '—' }}
            </span>
            <el-tag v-if="c.last_result" size="small" :type="resultTag(c.last_result)">
              {{ resultLabel(c.last_result) }}
            </el-tag>
            <span v-if="!readonly" class="flex items-center gap-1">
              <el-button link size="small" @click.stop="copyCase(c)">复制</el-button>
              <el-button link type="danger" size="small" @click.stop="delCase(c)">删</el-button>
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

const props = withDefaults(
  defineProps<{
    endpointId: Id
    projectId: Id
    readonly?: boolean
  }>(),
  { readonly: false },
)
const emit = defineEmits<{ changed: []; 'open-ai-gen': [startDialog?: boolean] }>()

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

function onCaseSaved(id: Id, name: string, category: string) {
  const c = cases.value.find((x) => x.id === Number(id))
  if (c) {
    c.name = name
    c.category = category
  }
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
    for (const c of targets) {
      // 顺序跑，事件丢弃，仅刷新结果；单条失败不中断其余
      try {
        await apifoxApi.runCaseStream(c.id, store.currentEnvironmentId ?? undefined, () => {})
      } catch {
        /* 单条运行失败，继续下一条 */
      }
    }
    await loadCases() // 回填每条 last_result
    ElMessage.success('全部运行完成')
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
