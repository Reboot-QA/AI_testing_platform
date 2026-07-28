<template>
  <div class="ws-main">
    <!-- 自动化域：按 biz/section 一次点达对应面板 -->
    <div v-if="domain === 'automation'" class="auto-domain">
      <div class="auto-content">
        <ApiManage v-if="biz === 'apis'" ref="apiManageRef" />
        <RunReports v-else-if="biz === 'reports'" />
        <AiGenJobsPanel v-else-if="biz === 'ai'" />
        <template v-else>
          <ScenarioPanel v-if="isScn" ref="scenarioRef" />
          <SuitePanel v-else-if="isSuite" ref="suiteRef" />
          <SchedulePanel v-else-if="section === 'schedules'" ref="scheduleRef" />
          <SchemaManage v-else-if="section === 'datamodels'" ref="schemaRef" />
          <TrashPanel v-else-if="section === 'trash'" />
          <ApiCasesExplorer v-else-if="isCases" :project-id="projectId" />
          <AutomationOverview v-else :project-id="pid" @nav="(s) => emit('navSection', s)" />
        </template>
      </div>
    </div>

    <template v-else-if="domain === 'requirements'">
      <RequirementDocs v-if="section === 'req-docs'" :scoped-project-id="pid" />
      <Requirements v-else-if="section === 'req-points'" ref="reqRef" :scoped-project-id="pid" />
      <RequirementsOverview v-else :project-id="pid" @nav="(s, f) => emit('navSection', s, f)" />
    </template>
    <template v-else-if="domain === 'functional'">
      <TestCases v-if="section === 'func-cases'" ref="tcRef" :scoped-project-id="pid" />
      <AIGenerate v-else-if="section === 'ai'" :scoped-project-id="pid" />
      <TestExecution
        v-else-if="section === 'func-runs' || section === 'func-exec'"
        :scoped-project-id="pid"
      />
      <FunctionalOverview v-else :project-id="pid" @nav="(s, f) => emit('navSection', s, f)" />
    </template>
    <SettingsDomain v-else :open="open" :project-id="pid" @nav="(v) => emit('navSettings', v)" />
    <DatabaseManageDrawer />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { AutomationBiz, SettingsSection, WorkspaceDomain } from '@/types/shell'
import ApiManage from '@/views/apifox/sections/ApiManage.vue'
import RunReports from '@/views/apifox/sections/RunReports.vue'
import SchemaManage from '@/views/apifox/sections/SchemaManage.vue'
import AiGenJobsPanel from '@/views/apifox/sections/AiGenJobsPanel.vue'
import ScenarioPanel from '@/views/apifox/sections/ScenarioPanel.vue'
import SuitePanel from '@/views/apifox/sections/SuitePanel.vue'
import SchedulePanel from '@/views/apifox/sections/SchedulePanel.vue'
import TrashPanel from '@/views/apifox/sections/TrashPanel.vue'
import ApiCasesExplorer from '@/views/apifox/sections/ApiCasesExplorer.vue'
import Requirements from '@/views/Requirements.vue'
import RequirementDocs from '@/views/RequirementDocs.vue'
import TestCases from '@/views/TestCases.vue'
import AIGenerate from '@/views/AIGenerate.vue'
import TestExecution from '@/views/TestExecution.vue'
import SettingsDomain from './SettingsDomain.vue'
import RequirementsOverview from './RequirementsOverview.vue'
import FunctionalOverview from './FunctionalOverview.vue'
import AutomationOverview from './AutomationOverview.vue'
import DatabaseManageDrawer from '@/components/apifox/project/DatabaseManageDrawer.vue'

const props = defineProps<{
  domain: WorkspaceDomain
  biz: AutomationBiz
  section: string
  open: SettingsSection
  projectId: Id
}>()

const emit = defineEmits<{
  navSettings: [open: SettingsSection]
  navSection: [section: string, filter?: string]
}>()

const pid = computed(() => Number(props.projectId))
const isScn = computed(() => props.section === 'scenarios' || props.section.startsWith('scn-'))
const isSuite = computed(() => props.section === 'suites' || props.section.startsWith('suite-'))
const isCases = computed(() => props.section === 'cases' || props.section.startsWith('case-'))

// 导航树「＋新建」：转发到当前挂载 section 暴露的 create()（随域/section 变化）
type Creatable = { create: () => void } | null
const apiManageRef = ref<Creatable>(null)
const scenarioRef = ref<Creatable>(null)
const suiteRef = ref<Creatable>(null)
const scheduleRef = ref<Creatable>(null)
const schemaRef = ref<Creatable>(null)
const reqRef = ref<Creatable>(null)
const tcRef = ref<Creatable>(null)

function triggerCreate() {
  if (props.domain === 'automation') {
    if (props.biz === 'apis') apiManageRef.value?.create()
    else if (isScn.value) scenarioRef.value?.create()
    else if (isSuite.value) suiteRef.value?.create()
    else if (props.section === 'schedules') scheduleRef.value?.create()
    else if (props.section === 'datamodels') schemaRef.value?.create()
    else ElMessage.info('该页无「新建」——请到接口目录/用例/场景/套件等页新建')
  } else if (props.domain === 'requirements') {
    if (props.section === 'req-points') reqRef.value?.create()
    else ElMessage.info('请到「需求点」新建需求')
  } else if (props.domain === 'functional') {
    if (props.section === 'func-cases') tcRef.value?.create()
    else ElMessage.info('请到「功能用例库」新建用例')
  } else {
    ElMessage.info('设置域无「新建」')
  }
}

defineExpose({ triggerCreate })
</script>

<style scoped>
.ws-main {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.ws-main > :deep(*) {
  height: 100%;
  min-height: 0;
}

/* 自动化域外壳：顶部返回栏 + 内容区（内容区仍撑满剩余高度、内部滚动） */
.auto-domain {
  display: flex;
  flex-direction: column;
}

.auto-content {
  flex: 1;
  min-height: 0;
}

.auto-content > :deep(*) {
  height: 100%;
  min-height: 0;
}
</style>
