<template>
  <div class="suite-panel">
    <div class="list-panel">
      <div class="panel-head">
        <span class="panel-title">测试套件</span>
        <el-button size="small" type="primary" title="新建套件" @click="addSuite">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="s in suites"
        :key="s.id"
        class="suite-row"
        :class="{ 'suite-row--active': activeId === s.id }"
        @click="onSelectSuite(s.id)"
      >
        <el-icon class="suite-row-icon"><Files /></el-icon>
        <el-tooltip :content="s.name" placement="right" :show-after="600">
          <span class="suite-name">{{ s.name }}</span>
        </el-tooltip>
        <span class="suite-meta">{{ s.item_count }} 项</span>
        <el-icon class="suite-action" title="复制套件" @click.stop="copySuite(s)">
          <CopyDocument />
        </el-icon>
        <el-icon class="suite-del" title="删除套件" @click.stop="delSuite(s)">
          <Delete />
        </el-icon>
      </div>
      <el-empty v-if="suites.length === 0" description="暂无套件" :image-size="60" />
    </div>

    <div class="editor-panel">
      <template v-if="tabs.length">
        <el-tabs
          :model-value="activeId"
          type="card"
          class="suite-tabbar"
          @tab-change="(id) => tabsStore.activate(pid, id)"
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
            <el-input v-model="activeTab.form.name" placeholder="套件名称" style="width: 260px" />
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
            class="desc-input"
          />

          <div class="items-title">套件项（按序批量执行 · 拖拽调整顺序）</div>
          <VueDraggable
            v-model="activeTab.form.items"
            handle=".drag-handle"
            :animation="150"
            ghost-class="suite-item-ghost"
          >
            <div v-for="(it, i) in activeTab.form.items" :key="it._uid" class="suite-item">
              <span class="drag-handle" title="拖拽调整顺序" @click.stop>
                <el-icon><Rank /></el-icon>
              </span>
              <el-switch v-model="it.enabled" size="small" />
              <el-tag size="small" :type="it.target_type === 'scenario' ? 'warning' : ''">
                {{ it.target_type === 'scenario' ? '场景' : '用例' }}
              </el-tag>
              <MethodTag v-if="it.endpoint_method" :method="it.endpoint_method" class="si-method" />
              <span class="si-name" :class="{ 'si-gone': !it.target_name }">
                {{ it.target_name || '(目标已删除，建议移除)' }}
              </span>
              <el-button
                link
                type="danger"
                size="small"
                class="si-remove"
                @click="activeTab.form.items.splice(i, 1)"
              >
                移除
              </el-button>
            </div>
          </VueDraggable>
          <el-empty
            v-if="activeTab.form.items.length === 0"
            description="下方添加用例或场景"
            :image-size="50"
          />

          <div class="add-row">
            <el-select
              v-model="pickCase"
              filterable
              clearable
              placeholder="+ 添加用例"
              size="small"
              class="picker"
              @change="onPickCase"
            >
              <el-option v-for="c in projectCases" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select
              v-model="pickScenario"
              filterable
              clearable
              placeholder="+ 添加场景"
              size="small"
              class="picker"
              @change="onPickScenario"
            >
              <el-option v-for="s in scenarios" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </div>

          <SuiteRunProgress
            :events="activeTab.runEvents"
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import type { Schemas } from '@/api/types'
import type { SSEEvent } from '@/api/request'
import { apifoxApi } from '@/api'
import { confirmCloseDirty, isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useTabsRouteGuard } from '@/composables/useTabsRouteGuard'
import { useWorkspaceStore } from '@/stores/workspace'
import { useSuiteTabsStore } from '@/stores/suiteTabs'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import SuiteRunProgress from '@/components/apifox/SuiteRunProgress.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()
const tabsStore = useSuiteTabsStore()

const suites = ref<Schemas['SuiteBrief'][]>([])
const projectCases = ref<Schemas['ProjectCaseBrief'][]>([])
const scenarios = ref<Schemas['ScenarioBrief'][]>([])
const pickCase = ref<number | null>(null)
const pickScenario = ref<number | null>(null)

const tabs = computed(() => tabsStore.tabsOf(pid.value))
const activeId = computed(() => tabsStore.activeIdOf(pid.value))
const activeTab = computed(() => tabsStore.findTab(pid.value, activeId.value))

// 路由级未保存守卫：切路由/切项目/退出前，有未保存改动则确认
useTabsRouteGuard(() => tabsStore.hasAnyDirty(pid.value))

let uid = 0
const nextUid = () => `new-${uid++}`

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

async function addSuite() {
  const { value } = await ElMessageBox.prompt('套件名称', '新建套件', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createSuite(pid.value, { name: value, items: [] })
  ElMessage.success('已创建')
  await loadSuites()
  await tabsStore.openSuite(pid.value, created.id)
}

function onPickCase(id: number | null) {
  if (!id || !activeTab.value) return
  const c = projectCases.value.find((x) => x.id === id)
  activeTab.value.form.items.push({
    _uid: nextUid(),
    target_type: 'case',
    target_id: id,
    target_name: c?.name || '',
    endpoint_method: c?.endpoint_method || '',
    enabled: true,
  })
  pickCase.value = null
}

function onPickScenario(id: number | null) {
  if (!id || !activeTab.value) return
  const s = scenarios.value.find((x) => x.id === id)
  activeTab.value.form.items.push({
    _uid: nextUid(),
    target_type: 'scenario',
    target_id: id,
    target_name: s?.name || '',
    endpoint_method: '',
    enabled: true,
  })
  pickScenario.value = null
}

async function doSaveSuite(tab) {
  const updated = await apifoxApi.updateSuite(tab.id, {
    name: tab.form.name,
    description: tab.form.description || null,
    items: tab.form.items.map((it) => ({
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
  tab.runEvents = [] as SSEEvent[]
  tab.running = true
  try {
    await apifoxApi.runSuiteStream(id, store.currentEnvironmentId, (e: SSEEvent) =>
      tab.runEvents.push(e),
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
  scenarios.value = await apifoxApi.listScenarios(pid.value)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnloadHandler))
</script>

<style scoped>
.suite-panel {
  display: flex;
  gap: 16px;
  height: 100%;
}

.list-panel {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

/* 字号阶梯：面板标题 14 > 套件名 12 > 元信息 11 */
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.panel-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: 1.25;
  color: var(--ax-brand);
}

.suite-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 6px 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.suite-row:hover {
  background: var(--ax-bg-hover);
}

.suite-row--active {
  background: var(--ax-bg-active);
}

.suite-row-icon {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-tertiary);
}

.suite-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
  font-weight: 400;
  line-height: 1.35;
  color: var(--ax-text);
}

.suite-meta {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: 1;
  color: var(--ax-text-placeholder);
  font-variant-numeric: tabular-nums;
}

.suite-action {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  cursor: pointer;
  color: var(--ax-text-placeholder);
  transition: color 0.15s;
}

.suite-action:hover {
  color: var(--ax-brand);
}

.suite-del {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  cursor: pointer;
  color: var(--ax-text-placeholder);
  transition: color 0.15s;
}

.suite-del:hover {
  color: var(--el-color-danger);
}

.list-panel :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}

.editor-panel {
  flex: 1;
  overflow: auto;
  min-width: 0;
}

.suite-tabbar :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.tab-name {
  margin-right: 4px;
}

.dirty-dot {
  color: var(--ax-warning);
  font-size: var(--ax-font-xs);
}

.row1 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.run-hint {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.desc-input {
  margin-bottom: 12px;
}

.items-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: 1.35;
  color: var(--ax-brand);
  margin-bottom: 10px;
}

.suite-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: var(--ax-font-xs);
  line-height: 1.35;
}

.suite-item:hover {
  background: var(--ax-bg-hover);
}

.drag-handle {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  font-size: var(--ax-font-sm);
  cursor: grab;
  color: var(--ax-text-placeholder);
}

.drag-handle:active {
  cursor: grabbing;
}

.suite-item :deep(.el-switch) {
  height: auto;
}

.suite-item :deep(.el-tag) {
  flex-shrink: 0;
  height: 20px;
  padding: 0 6px;
  font-size: var(--ax-font-xs);
  line-height: 18px;
}

.si-method {
  flex-shrink: 0;
  font-size: var(--ax-font-xs) !important;
}

.si-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
  font-weight: 400;
  color: var(--ax-text);
}

.suite-item :deep(.si-remove.el-button.is-link) {
  flex-shrink: 0;
  padding: 0 4px;
  font-size: var(--ax-font-xs);
  height: auto;
}

.tab-body :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}

:global(.suite-item-ghost) {
  opacity: 0.45;
  background: var(--ax-bg-hover);
  border-radius: 4px;
}

.si-gone {
  color: var(--ax-danger);
}

.add-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.picker {
  width: 200px;
}
</style>
