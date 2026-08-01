<template>
  <div class="step-detail">
    <div class="sd-field">
      <span class="sd-label">备注</span>
      <el-input
        v-model="step.name"
        size="small"
        :maxlength="TITLE_MAX_LEN"
        placeholder="步骤备注（选填）"
      />
    </div>
    <div class="sd-field">
      <span class="sd-label">启用</span>
      <el-switch v-model="step.enabled" />
    </div>

    <ScenarioCaseStepPanel
      v-if="step.type === 'case'"
      ref="casePanelRef"
      :step="step"
      :cases="cases"
      :scripts="scripts"
      :datasets="datasets"
    />

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
      <div class="sd-field conn-field">
        <span class="sd-label">数据库连接</span>
        <el-select
          v-model="dbConfig.connection_id"
          size="small"
          filterable
          placeholder="选择连接（当前环境内）"
          class="conn-select"
        >
          <el-option
            v-for="d in databases"
            :key="d.id"
            :label="`${d.name}（${d.host}/${d.database}）`"
            :value="d.id"
          />
        </el-select>
        <el-button link type="primary" size="small" @click="openDbManage">管理连接</el-button>
      </div>
      <div v-if="databases.length === 0" class="sd-hint db-hint">
        当前环境暂无连接，点击「管理连接」配置 Host、端口、库名与账号。
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
              :maxlength="KEY_MAX_LEN"
              size="small"
              placeholder="变量名"
              style="width: 120px"
            />
            <span class="db-ex-arrow">← 列</span>
            <el-input
              v-model="ex.column"
              :maxlength="KEY_MAX_LEN"
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
      <ScenarioHttpStepEditor :config="httpConfig" :server-names="serverNames" :project-id="pid" />
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
import { KEY_MAX_LEN, TITLE_MAX_LEN } from '@/constants/limits'
import { computed, ref } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import type { ScenarioEditorStep } from '@/types/apifox'
import { ensureDbConfig, ensureHttpConfig, ensureIfConfig, ensureLoopConfig } from '@/types/apifox'
import type { Schemas } from '@/api/types'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import ConditionEditor from '@/components/apifox/editors/ConditionEditor.vue'
import LoopEditor from '@/components/apifox/editors/LoopEditor.vue'
import ScenarioHttpStepEditor from '@/components/apifox/scenario/ScenarioHttpStepEditor.vue'
import ScenarioCaseStepPanel from '@/components/apifox/scenario/ScenarioCaseStepPanel.vue'
import AssertionsEditor from '@/components/apifox/editors/AssertionsEditor.vue'
import ExtractsEditor from '@/components/apifox/editors/ExtractsEditor.vue'
import { useDatabaseManageDrawer } from '@/composables/useDatabaseManageDrawer'
import { useWorkspaceStore } from '@/stores/workspace'

type ProjectCaseBrief = Schemas['ProjectCaseBrief']
type ScenarioBrief = Schemas['ScenarioBrief']
type ScriptBrief = Schemas['ScriptBrief']
type DatabaseOut = Schemas['DatabaseOut']
type DatasetBrief = Schemas['DatasetBrief']

const props = withDefaults(
  defineProps<{
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
const step = defineModel<ScenarioEditorStep>('step', { required: true })

const pid = useRouteParamId()
const sqlHint = '支持 {{变量}} 插值；写操作(INSERT/UPDATE/DELETE)会实际在目标库执行'
const casePanelRef = ref<InstanceType<typeof ScenarioCaseStepPanel> | null>(null)

// db 步骤 config 由 addStep 初始化；防御性保证 extracts 为数组
const dbConfig = computed(() => {
  if (step.value.type !== 'db') return ensureDbConfig({ type: 'db', enabled: true })
  return ensureDbConfig(step.value)
})

const dbExtracts = computed(() => dbConfig.value.extracts)

function addDbExtract() {
  dbExtracts.value.push({ var_name: '', column: '', scope: 'temporary' })
}

const { open: openDatabaseManage } = useDatabaseManageDrawer()
const workspaceStore = useWorkspaceStore()

function openDbManage() {
  openDatabaseManage(workspaceStore.currentEnvironmentId, { create: props.databases.length === 0 })
}

const ifCondition = computed(() => ensureIfConfig(step.value).condition)
const loopConfig = computed(() => ensureLoopConfig(step.value))
const httpConfig = computed(() => {
  if (step.value.type !== 'http') return ensureHttpConfig({ type: 'http', enabled: true })
  return ensureHttpConfig(step.value)
})

function onElseToggle(enabled: boolean) {
  if (enabled && !Array.isArray(step.value.elseChildren)) step.value.elseChildren = []
}

const availableScenarios = computed(() =>
  props.scenarios.filter((s) => s.id !== props.currentScenarioId),
)

function onScenarioChange(id: number) {
  const s = props.scenarios.find((x) => x.id === id)
  if (s) step.value.scenario_name = s.name
}

async function flushCase() {
  await casePanelRef.value?.flushCase?.()
}

function isCaseDirty(): boolean {
  return casePanelRef.value?.isCaseDirty?.() ?? false
}

defineExpose({ flushCase, isCaseDirty })
</script>

<style scoped>
.step-detail {
  padding: var(--ax-space-1) var(--ax-space-0-5);
}

.sd-field {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.sd-label {
  flex-shrink: 0;
  width: 80px;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.sd-hint {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-placeholder);
}

.conn-field {
  flex-wrap: wrap;
}

.conn-select {
  flex: 1;
  min-width: 160px;
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
  margin: calc(-1 * var(--ax-space-1)) 0 var(--ax-space-2);
  color: var(--ax-danger);
}

.db-ex {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  margin-bottom: var(--ax-space-1-5);
}

.db-ex-arrow {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
}
</style>
