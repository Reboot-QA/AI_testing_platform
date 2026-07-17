<template>
  <div class="scenario-panel">
    <ScenarioListPanel
      :scenarios="scenarios"
      :folders="folders"
      :active-id="activeId"
      @select="onSelectScenario"
      @del="delScenario"
      @move="onMoveScenario"
      @new-scenario="addScenario"
      @new-folder="createFolder"
      @rename-folder="renameFolder"
      @delete-folder="onDeleteFolder"
    />

    <div class="editor-panel">
      <template v-if="tabs.length">
        <el-tabs
          :model-value="activeId"
          type="card"
          class="scenario-tabbar"
          @tab-change="onTabChange"
          @tab-remove="onTabRemove"
        >
          <el-tab-pane v-for="t in tabs" :key="t.id" :name="t.id" closable>
            <template #label>
              <span class="tab-name">{{ t.name }}</span>
              <span v-if="tabsStore.isDirty(t)" class="dirty-dot" title="有未保存改动">●</span>
            </template>
          </el-tab-pane>
        </el-tabs>

        <div v-if="activeTab" :key="activeTab.id" class="tab-body">
          <div class="row1">
            <el-input v-model="activeTab.form.name" placeholder="场景名称" style="width: 220px" />
            <el-select v-model="activeTab.form.priority" style="width: 96px">
              <el-option
                v-for="p in PRIORITY_OPTIONS"
                :key="p.value"
                :label="`优先级 ${p.label}`"
                :value="p.value"
              />
            </el-select>
            <el-button
              type="primary"
              :loading="activeTab.saving"
              @click="saveScenario(activeTab.id)"
            >
              保存
            </el-button>
            <el-button
              type="success"
              :loading="activeTab.running"
              @click="runScenario(activeTab.id)"
            >
              运行
            </el-button>
            <span class="run-hint">环境在顶部选择</span>
          </div>
          <el-input
            v-model="activeTab.form.description"
            placeholder="描述（选填）"
            class="desc-input"
          />
          <ScenarioRunConfigBar
            v-model:loop-count="activeTab.form.run_config.loop_count"
            v-model:dataset-id="activeTab.form.run_config.dataset_id"
            v-model:propagate-auth="activeTab.form.run_config.propagate_auth"
            :datasets="datasets"
          />
          <div class="steps-title">步骤（按序执行 · 可用「分组」嵌套组织，拖拽移动）</div>
          <ScenarioStepsEditor
            ref="stepsEditorRef"
            :rows="activeTab.form.steps"
            :cases="projectCases"
            :scenarios="scenarios"
            :current-scenario-id="activeTab.id"
            :scripts="scripts"
            :databases="databases"
            :endpoints="endpoints"
            :server-names="serverNames"
          />
          <RunProgress
            :events="activeTab.runEvents"
            :running="activeTab.running"
            @clear="activeTab.runEvents = []"
          />
        </div>
      </template>

      <el-empty v-else description="选择或新建一个场景（串联接口用例形成业务链路）" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import type { SSEEvent } from '@/api/request'
import { apifoxApi } from '@/api'
import { serializeStep } from '@/utils/scenarioSteps'
import { confirmCloseDirty, isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useTabsRouteGuard } from '@/composables/useTabsRouteGuard'
import { useWorkspaceStore } from '@/stores/workspace'
import { useScenarioTabsStore } from '@/stores/scenarioTabs'
import { PRIORITY_OPTIONS } from '@/composables/useScenarioPriority'
import { useScenarioFolders } from '@/composables/useScenarioFolders'
import ScenarioListPanel from '@/components/apifox/ScenarioListPanel.vue'
import ScenarioRunConfigBar from '@/components/apifox/ScenarioRunConfigBar.vue'
import ScenarioStepsEditor from '@/components/apifox/ScenarioStepsEditor.vue'
import RunProgress from '@/components/apifox/RunProgress.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()
const tabsStore = useScenarioTabsStore()

const stepsEditorRef = ref<InstanceType<typeof ScenarioStepsEditor> | null>(null)
const scenarios = ref<Schemas['ScenarioBrief'][]>([])
const projectCases = ref<Schemas['ProjectCaseBrief'][]>([])
const scripts = ref<Schemas['ScriptBrief'][]>([])
const databases = ref<Schemas['DatabaseOut'][]>([])
const datasets = ref<Schemas['DatasetBrief'][]>([])
const endpoints = ref<Schemas['EndpointBrief'][]>([])

const tabs = computed(() => tabsStore.tabsOf(pid.value))
const activeId = computed(() => tabsStore.activeIdOf(pid.value))
const activeTab = computed(() => tabsStore.findTab(pid.value, activeId.value))

// 路由级未保存守卫：切路由/切项目/退出前，有未保存改动则确认
useTabsRouteGuard(() => tabsStore.hasAnyDirty(pid.value))

// 场景 HTTP 步骤的服务名选择（取自工作区环境的命名前置 URL）
const serverNames = computed(() => {
  const names = new Set<string>()
  store.environments.forEach((e) => (e.servers || []).forEach((s) => names.add(s.name)))
  return [...names]
})

const { folders, loadFolders, createFolder, renameFolder, deleteFolder } = useScenarioFolders(pid)

async function onMoveScenario({ id, folderId }: { id: number; folderId: number | null }) {
  await apifoxApi.updateScenario(id, { folder_id: folderId }) // 轻量移动：仅改 folder_id
  await loadScenarios()
}

async function onDeleteFolder(folder: Schemas['ScenarioFolderOut']) {
  await deleteFolder(folder) // 后端把其下场景移到未分组
  await loadScenarios()
}

async function loadScenarios() {
  scenarios.value = await apifoxApi.listScenarios(pid.value)
}
async function loadProjectCases() {
  projectCases.value = await apifoxApi.listProjectCases(pid.value)
}
async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(pid.value)
}
async function loadDatasets() {
  datasets.value = await apifoxApi.listDatasets(pid.value)
}
async function loadDatabases() {
  databases.value = store.currentEnvironmentId
    ? await apifoxApi.listDatabases(store.currentEnvironmentId)
    : []
}
watch(() => store.currentEnvironmentId, loadDatabases)

async function onSelectScenario(id: number) {
  try {
    await tabsStore.openScenario(pid.value, id)
  } catch {
    ElMessage.error('场景加载失败')
  }
}

// 切 tab 前先把当前 tab 内嵌用例的编辑落库（flushDetail 带脏检查，未改动不发请求）——
// 避免切 tab 因 :key 重挂载 ScenarioStepDetail 静默丢弃用例编辑
async function onTabChange(id: number) {
  try {
    await stepsEditorRef.value?.flushDetail?.()
  } catch {
    /* flush 失败（含冲突取消）不阻断切 tab */
  }
  tabsStore.activate(pid.value, id)
}

async function addScenario() {
  const { value } = await ElMessageBox.prompt('场景名称', '新建场景', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createScenario(pid.value, { name: value, steps: [] })
  ElMessage.success('已创建')
  await loadScenarios()
  await tabsStore.openScenario(pid.value, created.id)
}

async function runScenario(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return
  tab.runEvents = [] as SSEEvent[]
  tab.running = true
  try {
    await apifoxApi.runScenarioStream(id, store.currentEnvironmentId, (e: SSEEvent) =>
      tab.runEvents.push(e),
    )
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '运行失败')
  } finally {
    tab.running = false
  }
}

async function doSaveScenario(tab) {
  // 先把选中步骤里引用用例的编辑（勾选/params）落库，再存场景结构 —— 整体保存一次搞定。
  // 仅当保存的是当前激活 tab 时才 flush（stepsEditorRef 指向激活 tab 的编辑器；关闭非激活 tab 时其编辑器未挂载）
  if (tab.id === activeId.value) await stepsEditorRef.value?.flushDetail?.()
  const updated = await apifoxApi.updateScenario(tab.id, {
    name: tab.form.name,
    description: tab.form.description || null,
    priority: tab.form.priority,
    steps: tab.form.steps.map(serializeStep),
    run_config: {
      loop_count: tab.form.run_config.loop_count || 1,
      dataset_id: tab.form.run_config.dataset_id || null,
      propagate_auth: tab.form.run_config.propagate_auth !== false,
    },
    expected_version: tab.version,
  })
  tabsStore.afterSave(pid.value, tab.id, updated.version)
  await loadScenarios()
}

// 返回 true=已保存(可安全关闭)，false=未保存/用户取消
async function saveScenario(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return false
  tab.saving = true
  try {
    await doSaveScenario(tab)
    ElMessage.success('已保存')
    return true
  } catch (e: unknown) {
    if (!isConflict(e)) {
      ElMessage.error((e as Error).message || '保存失败')
      return false
    }
    let resolved = false
    await resolveSaveConflict({
      reload: async () => {
        await tabsStore.reloadScenario(pid.value, tab.id)
        resolved = true
      },
      overwrite: async () => {
        const latest = await apifoxApi.getScenario(tab.id)
        tab.version = latest.version
        await doSaveScenario(tab)
        resolved = true
      },
    })
    return resolved
  } finally {
    tab.saving = false
  }
}

async function onTabRemove(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return
  if (!tabsStore.isDirty(tab)) {
    tabsStore.closeTab(pid.value, id)
    return
  }
  const choice = await confirmCloseDirty(tab.name)
  if (choice === 'cancel') return
  if (choice === 'save' && !(await saveScenario(id))) return
  tabsStore.closeTab(pid.value, id)
}

async function delScenario(s: Schemas['ScenarioBrief']) {
  await ElMessageBox.confirm(`确认删除场景「${s.name}」？被其他场景引用时会被拦截。`, '提示', {
    type: 'warning',
  })
  await apifoxApi.deleteScenario(s.id)
  tabsStore.closeTab(pid.value, s.id)
  ElMessage.success('已删除')
  await loadScenarios()
}

// 刷新/关浏览器兜底：有未保存改动时浏览器原生确认（store 是内存态，需此兜底）
function beforeUnloadHandler(e: BeforeUnloadEvent) {
  if (tabsStore.hasAnyDirty(pid.value)) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(async () => {
  window.addEventListener('beforeunload', beforeUnloadHandler)
  await loadScenarios()
  await loadFolders()
  await loadProjectCases()
  await loadScripts()
  await loadDatabases()
  await loadDatasets()
  endpoints.value = await apifoxApi.listEndpoints(pid.value)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnloadHandler))
</script>

<style scoped>
.scenario-panel {
  display: flex;
  gap: 16px;
  height: 100%;
}

.editor-panel {
  flex: 1;
  overflow: auto;
  min-width: 0;
}

.scenario-tabbar :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.tab-name {
  margin-right: 4px;
}

.dirty-dot {
  color: var(--ax-warning);
  font-size: 12px;
}

.row1 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.run-hint {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}

.desc-input {
  margin-bottom: 12px;
}

.steps-title {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--ax-brand);
  margin-bottom: 10px;
}
</style>
