<template>
  <div class="scenario-panel">
    <ScenarioListPanel
      v-model:selected-folder-id="selectedFolderId"
      :scenarios="scenarios"
      :folders="folders"
      :active-id="activeId"
      :loading="listLoading"
      @select="onSelectScenario"
      @del="delScenario"
      @reorder="onReorderScenarios"
      @new-scenario="addScenario"
      @new-folder="onCreateFolder"
      @rename-folder="renameFolder"
      @delete-folder="onDeleteFolder"
    />

    <div class="editor-panel">
      <template v-if="tabs.length">
        <div class="tabbar-row">
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
          <TabbarMoreMenu :disabled="batchDisabled" @command="onBatchClose" />
        </div>

        <div v-if="activeTab" :key="activeTab.id" class="tab-body">
          <div class="row1">
            <el-input
              v-model="activeTab.form.name"
              placeholder="场景名称"
              :maxlength="TITLE_MAX_LEN"
              style="width: 220px"
            />
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
            :maxlength="DESC_MAX_LEN"
            show-word-limit
            class="desc-input"
          />
          <ScenarioRunConfigBar
            v-model:loop-count="activeTab.form.run_config.loop_count"
            v-model:dataset-id="activeTab.form.run_config.dataset_id"
            v-model:propagate-auth="activeTab.form.run_config.propagate_auth"
            :datasets="datasets"
            :disabled="!editorResourcesReady"
          />
          <div class="steps-title">步骤（按序执行 · 可用「分组」嵌套组织，拖拽移动）</div>
          <ScenarioStepsEditor
            v-if="editorResourcesReady"
            ref="stepsEditorRef"
            :project-id="pid"
            :rows="activeTab.form.steps as ScenarioEditorStep[]"
            :cases="projectCases"
            :scenarios="scenarios"
            :current-scenario-id="activeTab.id"
            :scripts="scripts"
            :databases="databases"
            :server-names="serverNames"
            :datasets="datasets"
          />
          <div v-else class="editor-resources-state">
            <el-skeleton v-if="editorResourcesLoading" :rows="5" animated />
            <el-empty v-else description="编辑资源加载失败，请重试" :image-size="60">
              <el-button size="small" @click="ensureEditorResources">重新加载</el-button>
            </el-empty>
          </div>
          <RunProgress
            :events="activeTab.runEvents as RunProgressEvent[]"
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
import { nameInputOptions } from '@/utils/promptLimits'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import type { ScenarioEditorStep } from '@/types/apifox'
import type { ScenarioTab } from '@/stores/scenarioTabs'
import { apifoxApi } from '@/api'
import { DESC_MAX_LEN, TITLE_MAX_LEN } from '@/constants/limits'
import { serializeStep } from '@/utils/scenarioSteps'
import { confirmCloseDirty, isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useTabsRouteGuard } from '@/composables/useTabsRouteGuard'
import { useTabbarBatchClose } from '@/composables/useTabbarBatchClose'
import { useWorkspaceStore } from '@/stores/workspace'
import { useScenarioTabsStore } from '@/stores/scenarioTabs'
import { useDatabaseManageDrawer } from '@/composables/useDatabaseManageDrawer'
import { PRIORITY_OPTIONS } from '@/composables/useScenarioPriority'
import { useScenarioFolders } from '@/composables/useScenarioFolders'
import TabbarMoreMenu from '@/components/apifox/common/TabbarMoreMenu.vue'
import ScenarioListPanel from '@/components/apifox/scenario/ScenarioListPanel.vue'
import ScenarioRunConfigBar from '@/components/apifox/scenario/ScenarioRunConfigBar.vue'
import ScenarioStepsEditor from '@/components/apifox/scenario/ScenarioStepsEditor.vue'
import RunProgress from '@/components/apifox/run/RunProgress.vue'

type RunProgressEvent = { type: string; [key: string]: unknown }

const pid = useRouteParamId()
const store = useWorkspaceStore()
const tabsStore = useScenarioTabsStore()

const stepsEditorRef = ref<InstanceType<typeof ScenarioStepsEditor> | null>(null)
const scenarios = ref<Schemas['ScenarioBrief'][]>([])
const projectCases = ref<Schemas['ProjectCaseBrief'][]>([])
const scripts = ref<Schemas['ScriptBrief'][]>([])
const databases = ref<Schemas['DatabaseOut'][]>([])
const datasets = ref<Schemas['DatasetBrief'][]>([])
const listLoading = ref(false)
const editorResourcesReady = ref(false)
const editorResourcesLoading = ref(false)
let editorResourcesPromise: Promise<void> | null = null

const tabs = computed(() => tabsStore.tabsOf(pid.value))
const activeId = computed(() => tabsStore.activeIdOf(pid.value))
const activeTab = computed(() => tabsStore.findTab(pid.value, activeId.value))

watch(
  activeTab,
  (tab) => {
    if (tab) void ensureEditorResources()
  },
  { immediate: true },
)

// 路由级未保存守卫：切路由/切项目/退出前，有未保存改动则确认
useTabsRouteGuard(() => tabsStore.hasAnyDirty(pid.value))

const { disabled: batchDisabled, onCommand: onBatchClose } = useTabbarBatchClose({
  tabs,
  activeId,
  isDirty: (t) => tabsStore.isDirty(t),
  closeTab: (id) => tabsStore.closeTab(pid.value, id),
})

// 场景 HTTP 步骤的服务名选择（仅当前环境的命名前置 URL）
const serverNames = computed(() => store.currentServerNames)

const { folders, loadFolders, createFolder, renameFolder, deleteFolder } = useScenarioFolders(pid)
/** 侧栏当前选中分组；null=未分组。新建场景挂到此 folder_id */
const selectedFolderId = ref<number | null>(null)

async function onReorderScenarios(items: Schemas['ScenarioReorderRequest']['items']) {
  try {
    const result = await apifoxApi.reorderScenarios(pid.value, {
      expected_order_version: store.currentProject?.scenario_order_version ?? 1,
      items,
    })
    if (store.currentProject?.id === result.project_id) {
      store.currentProject.scenario_order_version = result.order_version
    }
    await loadScenarios()
  } catch (error) {
    if (isConflict(error)) {
      await store.loadProject(pid.value, true)
      await loadScenarios()
      ElMessage.warning('场景排序已被其他操作更新，已刷新最新顺序')
      return
    }
    throw error
  }
}

async function onCreateFolder() {
  const created = await createFolder()
  if (created) selectedFolderId.value = created.id // 新建后自动选中，便于立刻在其下建场景
}

async function onDeleteFolder(folder: Schemas['ScenarioFolderOut']) {
  await deleteFolder(folder) // 后端级联软删其下场景进回收站
  if (selectedFolderId.value === folder.id) selectedFolderId.value = null
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
watch(
  () => store.currentEnvironmentId,
  () => {
    if (editorResourcesReady.value || editorResourcesLoading.value) void loadDatabases()
  },
)

/** 编辑器依赖的数据仅在首次打开场景后并发加载，避免阻塞左侧场景列表的首屏展示。 */
function ensureEditorResources(): Promise<void> {
  if (editorResourcesReady.value) return Promise.resolve()
  if (editorResourcesPromise) return editorResourcesPromise

  editorResourcesLoading.value = true
  editorResourcesPromise = Promise.all([
    loadProjectCases(),
    loadScripts(),
    loadDatasets(),
    loadDatabases(),
  ])
    .then(() => {
      editorResourcesReady.value = true
    })
    .catch(() => {
      // 请求层已提示具体错误；这里保留局部重试入口，避免编辑器长期停在加载态。
      editorResourcesReady.value = false
    })
    .finally(() => {
      editorResourcesLoading.value = false
      editorResourcesPromise = null
    })
  return editorResourcesPromise
}

const { subscribeUpdated } = useDatabaseManageDrawer()

async function onSelectScenario(id: number) {
  void ensureEditorResources()
  try {
    await tabsStore.openScenario(pid.value, id)
  } catch {
    ElMessage.error('场景加载失败')
  }
}

// 切 tab 前先把当前 tab 内嵌用例的编辑落库（flushDetail 带脏检查，未改动不发请求）——
// 避免切 tab 因 :key 重挂载 ScenarioStepDetail 静默丢弃用例编辑
async function onTabChange(id: string | number) {
  const tabId = Number(id)
  try {
    await stepsEditorRef.value?.flushDetail?.()
  } catch {
    /* flush 失败（含冲突取消）不阻断切 tab */
  }
  tabsStore.activate(pid.value, tabId)
}

defineExpose({ create: () => addScenario() })

async function addScenario() {
  const { value } = await ElMessageBox.prompt('场景名称', '新建场景', {
    ...nameInputOptions(),
  })
  const created = await apifoxApi.createScenario(pid.value, {
    name: value,
    priority: 'medium',
    folder_id: selectedFolderId.value,
    steps: [],
  })
  ElMessage.success('已创建')
  await loadScenarios()
  await tabsStore.openScenario(pid.value, created.id)
}

async function runScenario(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return
  // 运行是服务端按 id 从库里取步骤跑的，未保存的改动不会生效 —— 先确认并保存，避免跑成上一版。
  // 场景表单的 isDirty 覆盖不到步骤里内联编辑的引用用例，故一并判断
  const detailDirty =
    tab.id === activeId.value && (stepsEditorRef.value?.isDetailDirty?.() ?? false)
  if (tabsStore.isDirty(tab) || detailDirty) {
    try {
      await ElMessageBox.confirm('当前场景有未保存的改动，需先保存后再运行。', '未保存的改动', {
        confirmButtonText: '保存并运行',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
    if (!(await saveScenario(id))) return
  }
  tab.runEvents = [] as RunProgressEvent[]
  tab.running = true
  try {
    await apifoxApi.runScenarioStream(id, store.currentEnvironmentId ?? undefined, (e) =>
      tab.runEvents.push(e as RunProgressEvent),
    )
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '运行失败')
  } finally {
    tab.running = false
  }
}

async function doSaveScenario(tab: ScenarioTab) {
  // 先把选中步骤里引用用例的编辑（勾选/params）落库，再存场景结构 —— 整体保存一次搞定。
  // 仅当保存的是当前激活 tab 时才 flush（stepsEditorRef 指向激活 tab 的编辑器；关闭非激活 tab 时其编辑器未挂载）
  if (tab.id === activeId.value) await stepsEditorRef.value?.flushDetail?.()
  const updated = await apifoxApi.updateScenario(tab.id, {
    name: tab.form.name,
    description: tab.form.description || null,
    priority: tab.form.priority as 'medium' | 'high' | 'low',
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
  const unsubDb = subscribeUpdated(() => {
    if (editorResourcesReady.value || editorResourcesLoading.value) void loadDatabases()
  })
  onBeforeUnmount(unsubDb)
  listLoading.value = true
  try {
    await Promise.all([loadScenarios(), loadFolders()])
  } finally {
    listLoading.value = false
  }
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnloadHandler))
</script>

<style scoped>
.scenario-panel {
  display: flex;
  gap: var(--ax-space-4);
  height: 100%;
}

.editor-panel {
  flex: 1;
  overflow: auto;
  min-width: 0;
}

.tabbar-row {
  display: flex;
  align-items: flex-start;
  gap: var(--ax-space-1);
  flex-shrink: 0;
}

.tabbar-row .scenario-tabbar {
  flex: 1;
  min-width: 0;
}

.scenario-tabbar :deep(.el-tabs__header) {
  margin-bottom: var(--ax-space-2);
}

.tab-name {
  margin-right: var(--ax-space-1);
}

.dirty-dot {
  color: var(--ax-warning);
  font-size: var(--ax-font-xs);
}

.desc-input {
  margin-bottom: var(--ax-space-3);
}

.steps-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: var(--ax-leading-compact);
  color: var(--ax-brand);
  margin-bottom: var(--ax-space-2-5);
}

.editor-resources-state {
  min-height: 280px;
  padding: var(--ax-space-3);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
}
</style>
