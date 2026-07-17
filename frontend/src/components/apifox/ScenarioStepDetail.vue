<template>
  <div class="step-detail">
    <div class="sd-field">
      <span class="sd-label">备注</span>
      <el-input v-model="step.name" size="small" placeholder="步骤备注（选填）" />
    </div>
    <div class="sd-field">
      <span class="sd-label">启用</span>
      <el-switch v-model="step.enabled" />
    </div>

    <template v-if="step.type === 'case'">
      <div class="sd-field">
        <span class="sd-label">引用用例</span>
        <el-select
          v-model="step.ref_case_id"
          filterable
          size="small"
          style="flex: 1"
          @change="onCaseChange"
        >
          <el-option
            v-for="c in cases"
            :key="c.id"
            :label="`[${c.endpoint_method}] ${c.endpoint_name} / ${c.name}`"
            :value="c.id"
          />
        </el-select>
      </div>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="用例为共享：这里的改动会影响所有引用它的场景/接口"
        class="sd-alert"
      />
      <CaseEditor
        v-if="caseForm.id"
        :form="caseForm"
        :saving="savingCase"
        :scripts="scripts"
        @save="saveCase"
      />
    </template>

    <div v-else-if="step.type === 'wait'" class="sd-field">
      <span class="sd-label">等待时长(ms)</span>
      <el-input-number v-model="step.wait_ms" :min="1" :step="100" size="small" />
    </div>

    <div v-else-if="step.type === 'scenario'" class="sd-field">
      <span class="sd-label">子场景</span>
      <el-select
        v-model="step.ref_scenario_id"
        filterable
        size="small"
        style="flex: 1"
        @change="onScenarioChange"
      >
        <el-option v-for="s in availableScenarios" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
    </div>

    <template v-else-if="step.type === 'if'">
      <div class="sd-field">
        <span class="sd-label">条件</span>
        <ConditionEditor :condition="ifCondition" />
      </div>
      <div class="sd-field">
        <span class="sd-label">否则分支</span>
        <el-switch v-model="step.elseEnabled" @change="onElseToggle" />
        <span class="sd-hint">条件不成立时执行 else 分支</span>
      </div>
    </template>

    <div v-else-if="step.type === 'loop'" class="sd-field sd-field-top">
      <span class="sd-label">循环</span>
      <LoopEditor :config="loopConfig" />
    </div>

    <div v-else-if="step.type === 'break' || step.type === 'continue'" class="sd-field">
      <span class="sd-label">说明</span>
      <span class="sd-hint">{{
        step.type === 'break'
          ? '立即跳出所在循环，不再执行后续轮次'
          : '跳过循环体剩余步骤，直接进入下一轮'
      }}</span>
    </div>

    <template v-else-if="step.type === 'db'">
      <div class="sd-field">
        <span class="sd-label">数据库连接</span>
        <el-select
          v-model="dbConfig.connection_id"
          size="small"
          filterable
          placeholder="选择连接（当前环境内）"
          style="flex: 1"
        >
          <el-option
            v-for="d in databases"
            :key="d.id"
            :label="`${d.name}（${d.host}/${d.database}）`"
            :value="d.id"
          />
        </el-select>
      </div>
      <div v-if="databases.length === 0" class="sd-hint db-hint">
        当前环境无数据库连接，请先到「环境」页添加，并在顶部选中该环境后运行。
      </div>
      <div class="sd-field sd-field-top">
        <span class="sd-label">SQL</span>
        <div class="db-sql">
          <CodeEditor v-model="dbConfig.sql" language="sql" height="140px" />
          <span class="sd-hint">{{ sqlHint }}</span>
        </div>
      </div>
      <div class="sd-field sd-field-top">
        <span class="sd-label">提取变量</span>
        <div class="db-extracts">
          <div v-for="(ex, i) in dbExtracts" :key="i" class="db-ex">
            <el-input
              v-model="ex.var_name"
              size="small"
              placeholder="变量名"
              style="width: 120px"
            />
            <span class="db-ex-arrow">← 列</span>
            <el-input
              v-model="ex.column"
              size="small"
              placeholder="结果列名"
              style="width: 120px"
            />
            <el-select v-model="ex.scope" size="small" style="width: 96px">
              <el-option label="临时" value="temporary" />
              <el-option label="环境" value="environment" />
              <el-option label="全局" value="global" />
            </el-select>
            <el-button link type="danger" size="small" @click="dbExtracts.splice(i, 1)"
              >删</el-button
            >
          </div>
          <el-button link type="primary" size="small" @click="addDbExtract"
            >+ 提取（取查询结果首行的列）</el-button
          >
        </div>
      </div>
    </template>

    <template v-else-if="step.type === 'http'">
      <ApiEndpointEditor
        :form="httpConfig"
        show-meta
        :server-names="serverNames"
        :project-id="pid"
      />
      <div class="sd-field sd-field-top">
        <span class="sd-label">断言</span>
        <div class="http-proc"><AssertionsEditor :rows="httpConfig.assertions" /></div>
      </div>
      <div class="sd-field sd-field-top">
        <span class="sd-label">提取</span>
        <div class="http-proc"><ExtractsEditor :rows="httpConfig.extracts" /></div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import type { ScenarioEditorStep } from '@/types/apifox'
import { ensureDbConfig, ensureHttpConfig, ensureIfConfig, ensureLoopConfig } from '@/types/apifox'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import { emptySpec, normalizeSpec } from '@/utils/apifoxSpec'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import CaseEditor from '@/components/apifox/CaseEditor.vue'
import ConditionEditor from '@/components/apifox/ConditionEditor.vue'
import LoopEditor from '@/components/apifox/LoopEditor.vue'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import ApiEndpointEditor from '@/components/apifox/ApiEndpointEditor.vue'
import AssertionsEditor from '@/components/apifox/AssertionsEditor.vue'
import ExtractsEditor from '@/components/apifox/ExtractsEditor.vue'
import type { CaseEditorForm } from '@/components/apifox/CaseEditor.vue'

type ProjectCaseBrief = Schemas['ProjectCaseBrief']
type ScenarioBrief = Schemas['ScenarioBrief']
type ScriptBrief = Schemas['ScriptBrief']
type DatabaseOut = Schemas['DatabaseOut']

const props = withDefaults(
  defineProps<{
    step: ScenarioEditorStep
    cases?: ProjectCaseBrief[]
    scenarios?: ScenarioBrief[]
    currentScenarioId?: number | null
    scripts?: ScriptBrief[]
    databases?: DatabaseOut[]
    serverNames?: string[]
  }>(),
  {
    cases: () => [],
    scenarios: () => [],
    currentScenarioId: null,
    scripts: () => [],
    databases: () => [],
    serverNames: () => [],
  },
)

const pid = useRouteParamId()
const sqlHint = '支持 {{变量}} 插值；写操作(INSERT/UPDATE/DELETE)会实际在目标库执行'

// db 步骤 config 由 addStep 初始化；防御性保证 extracts 为数组
const dbConfig = computed(() => {
  if (props.step.type !== 'db') return ensureDbConfig({ type: 'db', enabled: true })
  return ensureDbConfig(props.step)
})

const dbExtracts = computed(() => dbConfig.value.extracts)

function addDbExtract() {
  dbExtracts.value.push({ var_name: '', column: '', scope: 'temporary' })
}

const ifCondition = computed(() => ensureIfConfig(props.step).condition)
const loopConfig = computed(() => ensureLoopConfig(props.step))
const httpConfig = computed(() => {
  if (props.step.type !== 'http') return ensureHttpConfig({ type: 'http', enabled: true })
  return ensureHttpConfig(props.step)
})

function onElseToggle(enabled: boolean) {
  if (enabled && !Array.isArray(props.step.elseChildren)) props.step.elseChildren = []
}

const savingCase = ref(false)
const caseForm = reactive<CaseEditorForm>({
  id: null,
  name: '',
  request_spec: emptySpec(),
  variables: [],
  assertions: [],
  extracts: [],
  pre_scripts: [],
  post_scripts: [],
  data_drive: { enabled: false, source: 'inline', rows: [] },
  version: 1,
})

const availableScenarios = computed(() =>
  props.scenarios.filter((s) => s.id !== props.currentScenarioId),
)

// 加载/保存时的内容快照，用于整体保存时判断引用用例是否真被编辑过（脏检查）
let caseSnapshot = ''

function applyCase(c: Schemas['CaseOut']) {
  caseForm.id = c.id
  caseForm.name = c.name
  caseForm.request_spec = normalizeSpec(c.request_spec)
  caseForm.variables = ensureKvRows(c.variables || [])
  caseForm.assertions = c.assertions || []
  caseForm.extracts = c.extracts || []
  caseForm.pre_scripts = c.pre_scripts || []
  caseForm.post_scripts = c.post_scripts || []
  caseForm.data_drive =
    c.data_drive?.enabled !== undefined
      ? c.data_drive
      : { enabled: false, source: 'inline', rows: [] }
  caseForm.version = c.version ?? 1
  caseSnapshot = JSON.stringify(caseFormPayload())
}

async function loadCase(id: number | null | undefined) {
  if (!id) {
    caseForm.id = null
    return
  }
  applyCase(await apifoxApi.getCase(id))
}

// 选中步骤（uid）或引用用例变化 → 重载内嵌用例
watch(
  () => (props.step.type === 'case' ? [props.step._uid, props.step.ref_case_id] : null),
  () => {
    if (props.step.type === 'case') loadCase(props.step.ref_case_id)
  },
  { immediate: true },
)

function onCaseChange(id: number) {
  const c = props.cases.find((x) => x.id === id)
  if (c) {
    props.step.case_name = c.name
    props.step.endpoint_method = c.endpoint_method
  }
}

function onScenarioChange(id: number) {
  const s = props.scenarios.find((x) => x.id === id)
  if (s) props.step.scenario_name = s.name
}

function caseFormPayload() {
  return {
    name: caseForm.name,
    request_spec: caseForm.request_spec,
    variables: caseForm.variables,
    data_drive: caseForm.data_drive,
    assertions: caseForm.assertions,
    extracts: caseForm.extracts,
    pre_scripts: caseForm.pre_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
    post_scripts: caseForm.post_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
  }
}

async function doSaveCase() {
  if (caseForm.id == null) return
  const updated = await apifoxApi.updateCase(caseForm.id, {
    ...caseFormPayload(),
    expected_version: caseForm.version,
  } as Schemas['CaseUpdate'])
  caseForm.version = updated.version
  props.step.case_name = caseForm.name // 同步步骤显示名
  caseSnapshot = JSON.stringify(caseFormPayload()) // 保存后即为干净态
}

async function saveCaseWithConflict() {
  if (caseForm.id == null) return
  try {
    await doSaveCase()
  } catch (e) {
    if (!isConflict(e)) throw e
    await resolveSaveConflict({
      reload: () => loadCase(caseForm.id),
      overwrite: async () => {
        if (caseForm.id == null) return
        const latest = await apifoxApi.getCase(caseForm.id)
        caseForm.version = latest.version
        await doSaveCase()
      },
    })
  }
}

async function saveCase() {
  savingCase.value = true
  try {
    await saveCaseWithConflict()
    ElMessage.success('用例已保存')
  } finally {
    savingCase.value = false
  }
}

// 供场景整体保存调用：选中的是引用用例步骤且确有编辑（脏检查）时，才落库——
// 避免对未改动的共享用例做无意义写入 + version 自增 + 误触发并发 409
async function flushCase() {
  if (props.step.type !== 'case' || !caseForm.id) return
  if (JSON.stringify(caseFormPayload()) === caseSnapshot) return
  await saveCaseWithConflict()
}

defineExpose({ flushCase })
</script>

<style scoped>
.step-detail {
  padding: 4px 2px;
}

.sd-field {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.sd-label {
  flex-shrink: 0;
  width: 80px;
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.sd-alert {
  margin-bottom: 12px;
}

.sd-hint {
  font-size: 12px;
  color: var(--ax-text-placeholder);
}

.sd-field-top {
  align-items: flex-start;
}

.http-proc {
  flex: 1;
  min-width: 0;
}

.db-sql,
.db-extracts {
  flex: 1;
}

.db-hint {
  margin: -4px 0 8px 0;
  color: var(--ax-danger);
}

.db-ex {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.db-ex-arrow {
  font-size: 12px;
  color: var(--ax-text-secondary);
}
</style>
