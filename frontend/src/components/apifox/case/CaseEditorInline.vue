<template>
  <div class="pt-2">
    <div class="mb-2 flex flex-wrap items-center gap-2 px-2">
      <span class="text-sm text-muted-foreground">分类</span>
      <el-select v-model="form.category" size="small" class="w-[110px]" @change="saveCase">
        <el-option v-for="c in CASE_CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
      </el-select>
      <span class="text-xs text-muted-foreground">环境在顶部选择</span>
    </div>
    <CaseEditor
      :form="form"
      :saving="saving"
      :scripts="scripts"
      :datasets="datasets"
      :schemas="schemas"
      :list-index="listIndex"
      allow-contract
      @save="saveCase"
    >
      <template #header-actions>
        <el-button size="small" type="success" :loading="running || saving" @click="runCase">
          运行
        </el-button>
      </template>
    </CaseEditor>
    <RunProgress :events="runEvents" :running="running" @clear="runEvents = []" />
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { SSEEvent } from '@/api/request'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import { emptySpec, normalizeSpec as normSpec } from '@/utils/apifoxSpec'
import { CASE_CATEGORIES } from '@/utils/caseCategory'
import { deriveProcessors } from '@/utils/caseProcessors'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import CaseEditor from '@/components/apifox/case/CaseEditor.vue'
import RunProgress from '@/components/apifox/run/RunProgress.vue'
import type { CaseEditorForm } from '@/types/apifox'

const props = defineProps<{
  caseId: Id
  projectId: Id
  listIndex?: number
  scripts?: Schemas['ScriptBrief'][]
  datasets?: Schemas['DatasetBrief'][]
  schemas?: Schemas['SchemaBrief'][]
}>()
const emit = defineEmits<{ saved: [id: Id, name: string, category: string]; ran: [] }>()

const store = useWorkspaceStore()
const saving = ref(false)
const running = ref(false)
const runEvents = ref<SSEEvent[]>([])
/** 不含 version：保存后 version 递增不应判 dirty */
const savedSnapshot = ref('')

const form = reactive<CaseEditorForm>({
  id: null,
  name: '',
  category: 'other',
  request_spec: emptySpec(),
  variables: [],
  assertions: [],
  extracts: [],
  pre_scripts: [],
  post_scripts: [],
  pre_processors: [],
  post_processors: [],
  data_drive: { enabled: false, source: 'inline', rows: [] },
  version: 1,
})

function serializeForm(): string {
  return JSON.stringify({
    name: form.name,
    category: form.category,
    request_spec: form.request_spec,
    variables: form.variables,
    data_drive: form.data_drive,
    pre_processors: form.pre_processors,
    post_processors: form.post_processors,
  })
}

function isDirty(): boolean {
  return serializeForm() !== savedSnapshot.value
}

function markSaved(): void {
  savedSnapshot.value = serializeForm()
}

function applyCase(c: Schemas['CaseOut']) {
  form.id = c.id
  form.name = c.name
  form.category = c.category || 'other'
  form.request_spec = normSpec(c.request_spec)
  form.variables = ensureKvRows(c.variables || [])
  form.assertions = c.assertions || []
  form.extracts = c.extracts || []
  form.pre_scripts = c.pre_scripts || []
  form.post_scripts = c.post_scripts || []
  form.pre_processors = c.pre_processors || []
  form.post_processors = c.post_processors || []
  deriveProcessors(form) // 存量用例无处理器时由旧字段派生
  form.data_drive =
    c.data_drive?.enabled !== undefined
      ? c.data_drive
      : { enabled: false, source: 'inline', rows: [] }
  form.version = c.version ?? 1
  markSaved()
}

function casePayload() {
  return {
    name: form.name,
    category: form.category,
    request_spec: form.request_spec,
    variables: form.variables,
    data_drive: form.data_drive,
    // 有序处理器为单一事实来源：清空旧分列字段，避免与处理器双写
    assertions: [],
    extracts: [],
    pre_scripts: [],
    post_scripts: [],
    pre_processors: form.pre_processors,
    post_processors: form.post_processors,
  }
}

async function doSaveCase() {
  if (form.id == null) return
  const updated = await apifoxApi.updateCase(form.id, {
    ...casePayload(),
    expected_version: form.version,
  } as Schemas['CaseUpdate'])
  form.version = updated.version
  emit('saved', props.caseId, form.name, form.category ?? 'other')
}

/** @returns 是否已成功落库（409 放弃/加载最新 → false） */
async function saveCase(): Promise<boolean> {
  saving.value = true
  try {
    await doSaveCase()
    markSaved()
    ElMessage.success('已保存')
    return true
  } catch (e: unknown) {
    if (!isConflict(e)) {
      ElMessage.error(e instanceof Error ? e.message : '保存失败')
      return false
    }
    if (form.id == null) return false
    let saved = false
    await resolveSaveConflict({
      reload: () => selectCase(form.id!),
      overwrite: async () => {
        if (form.id == null) return
        const latest = await apifoxApi.getCase(form.id)
        form.version = latest.version
        await doSaveCase()
        markSaved()
        saved = true
      },
    })
    return saved
  } finally {
    saving.value = false
  }
}

async function executeRun() {
  if (form.id == null) return
  runEvents.value = []
  running.value = true
  try {
    await apifoxApi.runCaseStream(form.id, store.currentEnvironmentId ?? undefined, (e) =>
      runEvents.value.push(e),
    )
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '运行失败')
  } finally {
    running.value = false
    emit('ran')
  }
}

async function runCase() {
  if (form.id == null) return
  if (isDirty()) {
    try {
      await ElMessageBox.confirm('当前用例有未保存的改动，需先保存后再运行。', '未保存的改动', {
        confirmButtonText: '保存并运行',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
    if (!(await saveCase())) return
  }
  await executeRun()
}

async function selectCase(cid: Id) {
  applyCase(await apifoxApi.getCase(cid))
}

watch(
  () => props.caseId,
  (cid) => cid != null && selectCase(cid),
  { immediate: true },
)

/** 场景整体保存：仅脏时静默落库（不弹成功 toast） */
async function flushCase() {
  if (form.id == null || !isDirty()) return
  try {
    await doSaveCase()
    markSaved()
  } catch (e: unknown) {
    if (!isConflict(e)) throw e
    await resolveSaveConflict({
      reload: () => selectCase(form.id!),
      overwrite: async () => {
        if (form.id == null) return
        const latest = await apifoxApi.getCase(form.id)
        form.version = latest.version
        await doSaveCase()
        markSaved()
      },
    })
  }
}

defineExpose({ flushCase, isCaseDirty: isDirty })
</script>
