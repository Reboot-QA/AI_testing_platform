<template>
  <div class="suite-panel">
    <SuiteListPanel
      :suites="suites"
      :active-id="activeId"
      @add="addSuite"
      @select="onSelectSuite"
      @copy="copySuite"
      @del="delSuite"
    />

    <div class="editor-panel">
      <template v-if="tabs.length">
        <div class="tabbar-row">
          <el-tabs
            :model-value="activeId"
            type="card"
            class="suite-tabbar"
            @tab-change="(id: string | number) => tabsStore.activate(pid, Number(id))"
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
              placeholder="套件名称"
              :maxlength="TITLE_MAX_LEN"
              style="width: 260px"
            />
            <el-button type="primary" :loading="activeTab.saving" @click="saveSuite(activeTab.id)">
              保存
            </el-button>
            <el-button type="success" :loading="activeTab.running" @click="runSuite(activeTab.id)">
              运行
            </el-button>
            <span class="run-hint">每项独立执行 · 环境在顶部选择</span>
          </div>
          <el-input
            v-model="activeTab.form.description"
            placeholder="描述（选填）"
            :maxlength="DESC_MAX_LEN"
            show-word-limit
            class="desc-input"
          />

          <SuiteItemsEditor
            v-model="activeTab.form.items"
            :project-id="pid"
            :cases="projectCases"
          />

          <SuiteRunProgress
            :events="activeTab.runEvents as SuiteRunEvent[]"
            :running="activeTab.running"
            @clear="activeTab.runEvents = []"
          />
        </div>
      </template>
      <el-empty v-else description="选择或新建一个套件（把用例/场景成组批量回归）" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { nameInputOptions } from '@/utils/promptLimits'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import type { SuiteTab } from '@/stores/suiteTabs'
import { apifoxApi } from '@/api'
import { DESC_MAX_LEN, TITLE_MAX_LEN } from '@/constants/limits'
import { confirmCloseDirty, isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useTabsRouteGuard } from '@/composables/useTabsRouteGuard'
import { useTabbarBatchClose } from '@/composables/useTabbarBatchClose'
import { useWorkspaceStore } from '@/stores/workspace'
import { useSuiteTabsStore } from '@/stores/suiteTabs'
import { buildSuiteItemGroups, flattenSuiteItemGroups } from '@/composables/useSuiteItemGroups'
import TabbarMoreMenu from '@/components/apifox/common/TabbarMoreMenu.vue'
import SuiteListPanel from '@/components/apifox/suite/SuiteListPanel.vue'
import SuiteItemsEditor from '@/components/apifox/suite/SuiteItemsEditor.vue'
import SuiteRunProgress from '@/components/apifox/run/SuiteRunProgress.vue'

type SuiteRunEvent = { type: string; [key: string]: unknown }

const pid = useRouteParamId()
const store = useWorkspaceStore()
const tabsStore = useSuiteTabsStore()

const suites = ref<Schemas['SuiteBrief'][]>([])
/** 仅用于套件项分组头显示接口名（用例 → 所属接口的映射） */
const projectCases = ref<Schemas['ProjectCaseBrief'][]>([])

const tabs = computed(() => tabsStore.tabsOf(pid.value))
const activeId = computed(() => tabsStore.activeIdOf(pid.value))
const activeTab = computed(() => tabsStore.findTab(pid.value, activeId.value))

// 路由级未保存守卫：切路由/切项目/退出前，有未保存改动则确认
useTabsRouteGuard(() => tabsStore.hasAnyDirty(pid.value))

const { disabled: batchDisabled, onCommand: onBatchClose } = useTabbarBatchClose({
  tabs,
  activeId,
  isDirty: (t) => tabsStore.isDirty(t),
  closeTab: (id) => tabsStore.closeTab(pid.value, id),
})

async function loadSuites() {
  suites.value = await apifoxApi.listSuites(pid.value)
}

async function onSelectSuite(sid: number) {
  try {
    await tabsStore.openSuite(pid.value, sid)
  } catch {
    ElMessage.error('套件加载失败')
  }
}

defineExpose({ create: () => addSuite() })

async function addSuite() {
  const { value } = await ElMessageBox.prompt('套件名称', '新建套件', {
    ...nameInputOptions(),
  })
  const created = await apifoxApi.createSuite(pid.value, { name: value, items: [] })
  ElMessage.success('已创建')
  await loadSuites()
  await tabsStore.openSuite(pid.value, created.id)
}

async function doSaveSuite(tab: SuiteTab) {
  // 按分组展示顺序固化——用户看到的就是保存下去的执行顺序（交错的存量套件在此归位）
  tab.form.items = flattenSuiteItemGroups(buildSuiteItemGroups(tab.form.items, projectCases.value))
  const updated = await apifoxApi.updateSuite(tab.id, {
    name: tab.form.name,
    description: tab.form.description || null,
    items: tab.form.items.map((it: SuiteTab['form']['items'][number]) => ({
      target_type: it.target_type,
      target_id: it.target_id,
      enabled: it.enabled !== false,
    })),
    expected_version: tab.version,
  })
  tabsStore.afterSave(pid.value, tab.id, updated.version)
  await loadSuites()
}

// 返回 true=已保存(可安全关闭)，false=未保存/用户取消
async function saveSuite(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return false
  tab.saving = true
  try {
    await doSaveSuite(tab)
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
        await tabsStore.reloadSuite(pid.value, tab.id)
        resolved = true
      },
      overwrite: async () => {
        const latest = await apifoxApi.getSuite(tab.id)
        tab.version = latest.version
        await doSaveSuite(tab)
        resolved = true
      },
    })
    return resolved
  } finally {
    tab.saving = false
  }
}

async function runSuite(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return
  // 运行是服务端按 id 从库里取用例集合跑的，未保存的改动不会生效 —— 先确认并保存，避免跑成上一版
  if (tabsStore.isDirty(tab)) {
    try {
      await ElMessageBox.confirm('当前套件有未保存的改动，需先保存后再运行。', '未保存的改动', {
        confirmButtonText: '保存并运行',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
    if (!(await saveSuite(id))) return
  }
  tab.runEvents = [] as SuiteRunEvent[]
  tab.running = true
  try {
    await apifoxApi.runSuiteStream(id, store.currentEnvironmentId ?? undefined, (e) =>
      tab.runEvents.push(e as SuiteRunEvent),
    )
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '运行失败')
  } finally {
    tab.running = false
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
  if (choice === 'save' && !(await saveSuite(id))) return
  tabsStore.closeTab(pid.value, id)
}

async function copySuite(s: Schemas['SuiteBrief']) {
  const created = await apifoxApi.copySuite(s.id)
  ElMessage.success('已复制')
  await loadSuites()
  await tabsStore.openSuite(pid.value, created.id)
}

async function delSuite(s: Schemas['SuiteBrief']) {
  await ElMessageBox.confirm(`确认删除套件「${s.name}」？`, '提示', { type: 'warning' })
  await apifoxApi.deleteSuite(s.id)
  tabsStore.closeTab(pid.value, s.id)
  ElMessage.success('已删除')
  await loadSuites()
}

function beforeUnloadHandler(e: BeforeUnloadEvent) {
  if (tabsStore.hasAnyDirty(pid.value)) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(async () => {
  window.addEventListener('beforeunload', beforeUnloadHandler)
  await loadSuites()
  projectCases.value = await apifoxApi.listProjectCases(pid.value)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnloadHandler))
</script>

<style scoped>
.suite-panel {
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

.tabbar-row .suite-tabbar {
  flex: 1;
  min-width: 0;
}

.suite-tabbar :deep(.el-tabs__header) {
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

.tab-body :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}
</style>
