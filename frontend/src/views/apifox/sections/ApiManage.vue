<template>
  <div class="api-manage">
    <ApiTreePanel
      ref="treePanel"
      :project-id="pid"
      :current-endpoint-id="activeId"
      draft-create
      @select="onSelectEndpoint"
      @deleted="onDeleted"
      @renamed="onRenamed"
      @new-draft="onNewDraft"
      @generate-ai="(ids: number[]) => batchAiRef?.open(ids)"
    />

    <div class="editor-panel">
      <div class="panel-toolbar">
        <el-button size="small" @click="batchAiRef?.open()">
          <el-icon><MagicStick /></el-icon> 批量 AI 生成
        </el-button>
      </div>
      <template v-if="tabs.length">
        <div class="tabbar-row">
          <el-tabs
            :model-value="activeId"
            type="card"
            class="endpoint-tabbar"
            @tab-change="(id: string | number) => tabsStore.activate(pid, Number(id))"
            @tab-remove="onTabRemove"
          >
            <el-tab-pane v-for="t in tabs" :key="t.id" :name="t.id" closable>
              <template #label>
                <MethodTag :method="t.method" />
                <span class="tab-name">{{ t.name || '未命名接口' }}</span>
                <el-tag v-if="t.draft" size="small" type="info" class="draft-tag">草稿</el-tag>
                <span v-if="tabsStore.isDirty(t)" class="dirty-dot" title="有未保存改动">●</span>
              </template>
            </el-tab-pane>
          </el-tabs>
          <TabbarMoreMenu :disabled="batchDisabled" @command="onBatchClose" />
        </div>

        <div v-if="activeTab" class="tab-body">
          <el-tabs v-model="activeTab.endpointTab" class="endpoint-tabs">
            <el-tab-pane label="调试" name="debug">
              <ApiDebugPanel
                :key="activeTab.id"
                :endpoint-id="activeTab.id"
                :form="activeTab.form"
                :saving="activeTab.saving"
                :server-names="serverNames"
                :project-id="pid"
                :scripts="scripts"
                :schemas="schemas"
                @save="saveEndpoint(activeTab.id)"
              />
            </el-tab-pane>
            <el-tab-pane label="文档预览" name="doc">
              <ApiDocPreview :form="activeTab.form" />
            </el-tab-pane>
            <!-- 草稿接口尚未落库，无用例可查；保存后再显示，避免用负 id 调接口报「接口不存在」 -->
            <el-tab-pane v-if="!activeTab.draft" label="测试用例" name="cases">
              <ApiCasesPanel :endpoint-id="activeTab.id" :project-id="pid" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </template>

      <div v-else class="empty-cards">
        <div class="ec-card" @click="treePanel?.addEndpoint()">
          <el-icon class="ec-icon" color="var(--color-blue-6)"><Link /></el-icon>
          <span>新建 HTTP 接口</span>
        </div>
        <div class="ec-card" @click="goDataManage">
          <el-icon class="ec-icon" color="var(--color-green-6)"><Download /></el-icon>
          <span>导入</span>
        </div>
      </div>
    </div>

    <BatchAiGenerateDialog ref="batchAiRef" :project-id="pid" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import type { EndpointEditorForm } from '@/types/apifox'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useApiTabsStore } from '@/stores/apiTabs'
import { provideProjectPostProcessors } from '@/composables/useEditorVariables'
import { processorsToLegacy } from '@/utils/caseProcessors'
import { useProjectScripts } from '@/composables/useProjectScripts'
import { confirmCloseDirty, isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useTabsRouteGuard } from '@/composables/useTabsRouteGuard'
import { useTabbarBatchClose } from '@/composables/useTabbarBatchClose'
import TabbarMoreMenu from '@/components/apifox/common/TabbarMoreMenu.vue'
import ApiTreePanel from '@/components/apifox/endpoint/ApiTreePanel.vue'
import ApiDebugPanel from '@/components/apifox/endpoint/ApiDebugPanel.vue'
import ApiDocPreview from '@/components/apifox/endpoint/ApiDocPreview.vue'
import ApiCasesPanel from '@/components/apifox/endpoint/ApiCasesPanel.vue'
import BatchAiGenerateDialog from '@/components/apifox/ai/BatchAiGenerateDialog.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'

const pid = useRouteParamId()
const router = useRouter()
const store = useWorkspaceStore()

// 导入能力已收敛到「设置 → 导入数据」，空状态「导入」卡片跳转过去
function goDataManage() {
  router.push({ hash: '#domain=settings&open=import' })
}
const tabsStore = useApiTabsStore()
const aiGenStore = useApifoxAiGenerateStore()

provideProjectPostProcessors(() => tabsStore.projectPostProcessors(pid.value))

const treePanel = ref<InstanceType<typeof ApiTreePanel> | null>(null)
defineExpose({ create: () => treePanel.value?.addEndpoint() })
const batchAiRef = ref<InstanceType<typeof BatchAiGenerateDialog> | null>(null)
const { scripts, loadScripts } = useProjectScripts(pid)
const schemas = ref<Schemas['SchemaBrief'][]>([])

const tabs = computed(() => tabsStore.tabsOf(pid.value))
const activeId = computed(() => tabsStore.activeIdOf(pid.value))
const activeTab = computed(() => {
  const id = activeId.value
  return id != null ? tabsStore.findTab(pid.value, id) : null
})

// 路由级未保存守卫：切路由/切项目/退出前，有未保存改动则确认
useTabsRouteGuard(() => tabsStore.hasAnyDirty(pid.value))

const { disabled: batchDisabled, onCommand: onBatchClose } = useTabbarBatchClose({
  tabs,
  activeId,
  isDirty: (t) => tabsStore.isDirty(t),
  closeTab: (id) => tabsStore.closeTab(pid.value, id),
})

const serverNames = computed(() => store.currentServerNames)

watch(
  () => store.currentEnvironmentId,
  () => {
    const names = new Set(store.currentServerNames)
    for (const tab of tabsStore.tabsOf(pid.value)) {
      if (tab.form.server_name && !names.has(tab.form.server_name)) {
        tab.form.server_name = null
      }
    }
  },
)

async function onSelectEndpoint(id: number) {
  try {
    await tabsStore.openEndpoint(pid.value, id)
  } catch {
    ElMessage.error('接口加载失败')
  }
}

// 新建接口：开一个草稿 tab（不落库），填内容/调试后由 saveEndpoint 走 create
function onNewDraft(folderId: number | null) {
  tabsStore.openDraft(pid.value, folderId)
}

function endpointCreatePayload(
  form: EndpointEditorForm,
  folderId: number | null,
): Schemas['EndpointCreate'] {
  const legacy = processorsToLegacy(form.pre_processors ?? [], form.post_processors ?? [])
  return {
    name: form.name,
    method: form.method,
    path: form.path,
    folder_id: folderId,
    server_name: form.server_name,
    description: form.description,
    request_spec: form.request_spec as Schemas['EndpointCreate']['request_spec'],
    contract_strict: legacy.contract_strict,
    response_schema_id: legacy.response_schema_id,
    assertions: [],
    extracts: [],
    pre_scripts: [],
    post_scripts: [],
    pre_processors: form.pre_processors ?? [],
    post_processors: form.post_processors ?? [],
  }
}

function endpointPayload(form: EndpointEditorForm): Schemas['EndpointUpdate'] {
  const legacy = processorsToLegacy(form.pre_processors ?? [], form.post_processors ?? [])
  return {
    name: form.name,
    method: form.method,
    path: form.path,
    server_name: form.server_name,
    description: form.description,
    request_spec: form.request_spec as Schemas['EndpointUpdate']['request_spec'],
    // 有序处理器为单一事实来源：清空旧分列字段；契约字段从处理器同步（供 debug 直发与回退）
    assertions: [],
    extracts: [],
    pre_scripts: [],
    post_scripts: [],
    pre_processors: form.pre_processors ?? [],
    post_processors: form.post_processors ?? [],
    response_schema_id: legacy.response_schema_id,
    contract_strict: legacy.contract_strict,
  }
}

// 返回 true=已保存(可安全关闭)，false=未保存/用户取消
async function saveEndpoint(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return false
  // 草稿态首次保存：校验名称后走 create，成功再把临时 tab 换成真实接口
  if (tab.draft && !tab.form.name.trim()) {
    ElMessage.warning('请先填写接口名称')
    return false
  }
  tab.saving = true
  try {
    if (tab.draft) {
      const created = await apifoxApi.createEndpoint(
        pid.value,
        endpointCreatePayload(tab.form, tab.folderId ?? null),
      )
      tabsStore.promoteDraft(pid.value, tab.id, created)
      treePanel.value?.reload()
      ElMessage.success('已保存')
      return true
    }
    const updated = await apifoxApi.updateEndpoint(tab.id, {
      ...endpointPayload(tab.form),
      expected_version: tab.version,
    })
    tabsStore.afterSave(pid.value, tab.id, updated)
    treePanel.value?.reload()
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
        await tabsStore.reloadEndpoint(pid.value, tab.id)
        resolved = true
      },
      overwrite: async () => {
        const latest = await apifoxApi.getEndpoint(tab.id)
        tab.version = latest.version
        const updated = await apifoxApi.updateEndpoint(tab.id, {
          ...endpointPayload(tab.form),
          expected_version: tab.version,
        })
        tabsStore.afterSave(pid.value, tab.id, updated)
        treePanel.value?.reload()
        resolved = true
      },
    })
    return resolved
  } finally {
    tab.saving = false
  }
}

// 关闭接口 tab：dirty 时弹「保存并关闭/不保存关闭/取消」
async function onTabRemove(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return
  if (!tabsStore.isDirty(tab)) {
    tabsStore.closeTab(pid.value, id)
    return
  }
  const choice = await confirmCloseDirty(tab.name || '未命名接口')
  if (choice === 'cancel') return
  if (choice === 'save' && !(await saveEndpoint(id))) return
  tabsStore.closeTab(pid.value, id)
}

function onDeleted(id: number) {
  tabsStore.closeTab(pid.value, id)
}
function onRenamed(id: number, name: string, version?: number) {
  tabsStore.onRenamed(pid.value, id, name, version)
}

async function loadSchemas() {
  schemas.value = await apifoxApi.listSchemas(pid.value)
}

// 刷新/关浏览器兜底：有未保存改动时浏览器原生确认（store 是内存态，需此兜底）
function beforeUnloadHandler(e: BeforeUnloadEvent) {
  if (tabsStore.hasAnyDirty(pid.value)) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  loadScripts()
  loadSchemas()
  aiGenStore.resumeActive(Number(pid.value)).catch(() => {}) // 刷新/重登后恢复进行中的 AI 生成任务
  window.addEventListener('beforeunload', beforeUnloadHandler)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnloadHandler))
</script>

<style scoped>
.api-manage {
  display: flex;
  gap: var(--ax-gap-lg);
  height: 100%;
  min-height: 0;
}

.editor-panel {
  flex: 1;
  overflow: hidden;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.panel-toolbar {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  margin-bottom: var(--ax-space-2);
}

.tabbar-row {
  display: flex;
  align-items: flex-start;
  gap: var(--ax-space-1);
  flex-shrink: 0;
}

.tabbar-row .endpoint-tabbar {
  flex: 1;
  min-width: 0;
}

.endpoint-tabbar :deep(.el-tabs__header) {
  margin-bottom: var(--ax-space-2);
}

.tab-name {
  margin: 0 var(--ax-space-1);
}

.dirty-dot {
  color: var(--ax-warning);
  font-size: var(--ax-font-xs);
}

.draft-tag {
  margin-right: var(--ax-space-1);
  transform: scale(0.85);
}

.empty-cards {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-space-4);
  align-items: center;
  justify-content: center;
  height: 100%;
}

.ec-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-3);
  width: 160px;
  height: 130px;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg-subtle);
  color: var(--ax-text-secondary);
  font-size: var(--ax-font);
  cursor: pointer;
  transition: all 0.15s;
}

.ec-card:hover {
  border-color: var(--ax-brand);
  transform: translateY(-2px);
}

.ec-icon {
  font-size: var(--ax-font-2xl);
}
</style>
