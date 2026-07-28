<template>
  <div class="steps-editor">
    <div class="steps-col">
      <div class="steps-bar">
        <el-button
          link
          type="danger"
          size="small"
          :disabled="rows.length === 0"
          @click="removeAllSteps"
        >
          全部移除
        </el-button>
      </div>
      <VueDraggable
        v-model="rowList"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
      >
        <ScenarioStepRow
          v-for="(row, i) in rows"
          :key="row._uid"
          :row="row"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="removeTop(i)"
          @add="onAddCommand"
        />
      </VueDraggable>
      <el-empty v-if="rows.length === 0" description="暂无步骤，点击下方添加" :image-size="50" />

      <ScenarioAddStepMenu @command="onAddCommand" />
    </div>

    <div class="detail-col">
      <ScenarioStepDetail
        v-if="selectedStep"
        ref="detailRef"
        :key="selectedStep._uid"
        :step="selectedStep"
        :cases="cases"
        :scenarios="scenarios"
        :current-scenario-id="currentScenarioId"
        :scripts="scripts"
        :databases="databases"
        :server-names="serverNames"
        :datasets="datasets"
      />
      <el-empty v-else description="点击左侧步骤编辑详情" :image-size="60" />
    </div>

    <ImportEndpointTreeDialog
      ref="importEndpointRef"
      :project-id="projectId"
      @confirm="onImportConfirm"
    />

    <el-dialog v-model="curlVisible" title="从 cURL 导入" width="560px">
      <el-input
        v-model="curlText"
        :maxlength="PASTE_MAX_LEN"
        type="textarea"
        :rows="8"
        placeholder="粘贴 curl 命令，如 curl 'https://...' -X POST -H '...' --data-raw '...'"
      />
      <template #footer>
        <el-button @click="curlVisible = false">取消</el-button>
        <el-button type="primary" @click="importFromCurl">解析并添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { PASTE_MAX_LEN } from '@/constants/limits'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { normalizeSpec } from '@/utils/apifoxSpec'
import { parseCurl } from '@/utils/curlParser'
import {
  createCaseRefStep,
  createHttpStep,
  createStepByType,
  nextEditorUid,
} from '@/utils/scenarioStepFactory'
import ScenarioStepRow from '@/components/apifox/scenario/ScenarioStepRow.vue'
import ScenarioStepDetail from '@/components/apifox/scenario/ScenarioStepDetail.vue'
import ScenarioAddStepMenu from '@/components/apifox/scenario/ScenarioAddStepMenu.vue'
import ImportEndpointTreeDialog from '@/components/apifox/import-export/ImportEndpointTreeDialog.vue'
import type { ImportCaseBrief, ImportConfirmPayload } from '@/composables/useImportCaseTree'
import type {
  ScenarioAddStepCommand,
  ScenarioEditorStep,
  ScenarioStepSelection,
} from '@/types/apifox'

type ProjectCaseBrief = Schemas['ProjectCaseBrief']
type ScenarioBrief = Schemas['ScenarioBrief']
type ScriptBrief = Schemas['ScriptBrief']
type DatabaseOut = Schemas['DatabaseOut']
type DatasetBrief = Schemas['DatasetBrief']

const props = withDefaults(
  defineProps<{
    rows: ScenarioEditorStep[]
    projectId: Id
    cases?: ProjectCaseBrief[]
    scenarios?: ScenarioBrief[]
    currentScenarioId?: number | null
    scripts?: ScriptBrief[]
    databases?: DatabaseOut[]
    serverNames?: string[]
    datasets?: DatasetBrief[]
  }>(),
  {
    cases: () => [],
    scenarios: () => [],
    currentScenarioId: null,
    scripts: () => [],
    databases: () => [],
    serverNames: () => [],
    datasets: () => [],
  },
)

// 供父级（场景整体保存）调用：把当前选中步骤详情里未落库的引用用例编辑一并保存
const detailRef = ref<InstanceType<typeof ScenarioStepDetail> | null>(null)
async function flushDetail() {
  await detailRef.value?.flushCase?.()
}
// 选中步骤内联编辑的引用用例是否有未落库改动（场景表单的 isDirty 覆盖不到这部分）
function isDetailDirty(): boolean {
  return detailRef.value?.isCaseDirty?.() ?? false
}
defineExpose({ flushDetail, isDetailDirty })

// 容器步骤的可嵌套子列表：分组一个，条件(if)两个（then=children / else=elseChildren）
function stepChildLists(r: ScenarioEditorStep): ScenarioEditorStep[][] {
  if (r.type === 'group' || r.type === 'loop') {
    if (!Array.isArray(r.children)) r.children = []
    return [r.children]
  }
  if (r.type === 'if') {
    if (!Array.isArray(r.children)) r.children = []
    if (!Array.isArray(r.elseChildren)) r.elseChildren = []
    return [r.children, r.elseChildren]
  }
  return []
}

function ensureUids(rows: ScenarioEditorStep[]) {
  rows.forEach((r) => {
    if (r._uid == null) r._uid = nextEditorUid()
    stepChildLists(r).forEach(ensureUids)
  })
}
onMounted(() => ensureUids(props.rows))
watch(
  () => props.rows.length,
  () => ensureUids(props.rows),
)

// VueDraggable 拖动结束时是「整体赋新数组」（onUpdate/onRemove 内 modelValue = [...]），
// 直接 v-model="props.rows" 会写只读 props：跨列表把步骤拖进循环体/分组时，源列表的移除写不回去，
// 表现为循环体外的原步骤还在（保存后重复一份）。这里用可写 computed 原地 splice，
// 保持父级持有的同一个数组引用。
const rowList = computed<ScenarioEditorStep[]>({
  get: () => props.rows,
  set: (value) => {
    props.rows.splice(0, props.rows.length, ...value)
  },
})

// 选中态用共享 reactive（UI 态，非业务数据，显式传 prop，不走 provide/inject）
const selection = reactive<ScenarioStepSelection>({ uid: null })

function findByUid(
  rows: ScenarioEditorStep[],
  uid: number | string | null,
): ScenarioEditorStep | null {
  for (const r of rows) {
    if (r._uid === uid) return r
    for (const list of stepChildLists(r)) {
      const hit = findByUid(list, uid)
      if (hit) return hit
    }
  }
  return null
}
const selectedStep = computed(() => findByUid(props.rows, selection.uid))

function removeTop(i: number) {
  if (props.rows[i]?._uid === selection.uid) selection.uid = null
  props.rows.splice(i, 1)
}

/** 步骤总数（含分组/条件/循环内的子步骤），与「全部移除」的确认文案口径一致 */
function countSteps(rows: ScenarioEditorStep[]): number {
  let n = 0
  for (const r of rows) {
    n++
    for (const list of stepChildLists(r)) n += countSteps(list)
  }
  return n
}
const totalStepCount = computed(() => countSteps(props.rows))

// 一键清空所有步骤（参考 apifox）：仅改内存态，需再点「保存」才落库
async function removeAllSteps() {
  if (props.rows.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确认移除全部 ${totalStepCount.value} 个步骤？含分组/条件/循环内的子步骤，保存后生效。`,
      '提示',
      { type: 'warning' },
    )
  } catch {
    return // 用户取消
  }
  selection.uid = null
  props.rows.splice(0, props.rows.length)
}

const importEndpointRef = ref<InstanceType<typeof ImportEndpointTreeDialog> | null>(null)
const curlVisible = ref(false)
const curlText = ref('')

function openImportEndpointDialog(mode: 'import-endpoint' | 'import-case' | 'import-debug') {
  importEndpointRef.value?.open(mode)
}

function selectStep(step: ScenarioEditorStep) {
  selection.uid = step._uid ?? null
}

// 新步骤的落点：顶层「添加步骤」为 props.rows，容器内联入口为该容器的子列表。
// 导入类命令要先开对话框，回调时已脱离事件上下文，故用变量把落点记下来。
let addTarget: ScenarioEditorStep[] | null = null
function targetList(): ScenarioEditorStep[] {
  return addTarget ?? props.rows
}

function onAddCommand(command: ScenarioAddStepCommand, target?: ScenarioEditorStep[]) {
  addTarget = target ?? props.rows
  if (command === 'import-endpoint' || command === 'import-case' || command === 'import-debug') {
    openImportEndpointDialog(command)
    return
  }
  if (command === 'import-curl') {
    curlText.value = ''
    curlVisible.value = true
    return
  }
  const step = createStepByType(command)
  if (!step) return
  targetList().push(step)
  selectStep(step)
}

function onImportConfirm(payload: ImportConfirmPayload) {
  if (payload.mode === 'import-case') {
    importFromCases(payload.cases, payload.importAs)
  } else if (payload.mode !== 'pick-suite-item') {
    // pick-suite-item 是套件面板专用模式，场景侧不会触发
    importFromEndpoint(payload.endpointIds)
  }
}

async function importFromEndpoint(ids: number[]) {
  if (ids.length === 0) return
  const list = targetList()
  try {
    let lastStep: ScenarioEditorStep | null = null
    for (const endpointId of ids) {
      const e = await apifoxApi.getEndpoint(endpointId)
      const step = createHttpStep({
        name: e.name,
        method: e.method,
        path: e.path,
        server_name: e.server_name,
        request_spec: normalizeSpec(e.request_spec),
        assertions: e.assertions || [],
        extracts: e.extracts || [],
      })
      list.push(step)
      lastStep = step
    }
    if (lastStep) selectStep(lastStep)
  } catch {
    ElMessage.error('接口加载失败')
  }
}

async function importFromCases(cases: ImportCaseBrief[], importAs: 'copy' | 'reference') {
  if (cases.length === 0) return
  const list = targetList()
  try {
    let lastStep: ScenarioEditorStep | null = null
    for (const item of cases) {
      if (importAs === 'reference') {
        const step = createCaseRefStep({
          ref_case_id: item.id,
          case_name: item.name,
          endpoint_method: item.endpoint_method,
        })
        list.push(step)
        lastStep = step
      } else {
        const [c, e] = await Promise.all([
          apifoxApi.getCase(item.id),
          apifoxApi.getEndpoint(item.endpoint_id),
        ])
        const step = createHttpStep({
          name: c.name,
          method: e.method,
          path: e.path,
          server_name: e.server_name,
          request_spec: normalizeSpec(c.request_spec),
          assertions: c.assertions || [],
          extracts: c.extracts || [],
        })
        list.push(step)
        lastStep = step
      }
    }
    if (lastStep) selectStep(lastStep)
  } catch {
    ElMessage.error('用例加载失败')
  }
}

function importFromCurl() {
  const parsed = parseCurl(curlText.value)
  if (!parsed) {
    ElMessage.error('无法解析，请粘贴以 curl 开头的完整命令')
    return
  }
  const step = createHttpStep({
    name: parsed.name,
    method: parsed.method,
    path: parsed.path,
    request_spec: normalizeSpec(parsed.request_spec),
  })
  targetList().push(step)
  curlVisible.value = false
  curlText.value = ''
  selectStep(step)
}
</script>

<style scoped>
.steps-editor {
  display: flex;
  gap: var(--ax-gap-lg);
  height: 100%;
  min-height: 0;
}

.steps-col {
  width: 400px;
  flex-shrink: 0;
  border-right: 1px solid var(--ax-border);
  min-height: 0;
  overflow-y: auto;
  padding-right: var(--ax-space-2-5);
}

.steps-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: var(--ax-space-1);
}

.steps-bar :deep(.el-button.is-link) {
  padding: 0;
  height: auto;
  font-size: var(--ax-text-caption-size);
}

.detail-col {
  flex: 1;
  overflow: auto;
}

.steps-col :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}
</style>
