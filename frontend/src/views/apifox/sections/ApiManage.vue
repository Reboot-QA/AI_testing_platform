<template>
  <div class="api-manage">
    <ApiTreePanel
      ref="treePanel"
      :project-id="pid"
      show-schemas
      @select="onSelectEndpoint"
      @deleted="onDeleted"
      @renamed="onRenamed"
      @select-schema="goSchema"
    />

    <div class="editor-panel">
      <div class="panel-toolbar">
        <el-button size="small" @click="batchAiRef?.open()">
          <el-icon><MagicStick /></el-icon> 批量 AI 生成
        </el-button>
      </div>
      <template v-if="tabs.length">
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
              <span class="tab-name">{{ t.name }}</span>
              <span v-if="tabsStore.isDirty(t)" class="dirty-dot" title="有未保存改动">●</span>
            </template>
          </el-tab-pane>
        </el-tabs>

        <div v-if="activeTab" class="tab-body">
          <el-tabs v-model="activeTab.endpointTab" class="endpoint-tabs">
            <el-tab-pane label="调试" name="debug">
              <ApiDebugPanel
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
            <el-tab-pane label="测试用例" name="cases">
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
        <div class="ec-card" @click="goDataModels">
          <el-icon class="ec-icon" color="var(--color-pink-6)"><Box /></el-icon>
          <span>新建数据模型</span>
        </div>
        <div class="ec-card" @click="treePanel?.openImport()">
          <el-icon class="ec-icon" color="var(--color-green-6)"><Download /></el-icon>
          <span>导入</span>
        </div>
      </div>
    </div>

    <BatchAiGenerateDialog ref="batchAiRef" :project-id="pid" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import type { EndpointEditorForm } from '@/types/apifox'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useApiTabsStore } from '@/stores/apiTabs'
import { useProjectScripts } from '@/composables/useProjectScripts'
import { confirmCloseDirty, isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useTabsRouteGuard } from '@/composables/useTabsRouteGuard'
import ApiTreePanel from '@/components/apifox/ApiTreePanel.vue'
import ApiDebugPanel from '@/components/apifox/ApiDebugPanel.vue'
import ApiDocPreview from '@/components/apifox/ApiDocPreview.vue'
import ApiCasesPanel from '@/components/apifox/ApiCasesPanel.vue'
import BatchAiGenerateDialog from '@/components/apifox/BatchAiGenerateDialog.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'

const router = useRouter()
const pid = useRouteParamId()
const store = useWorkspaceStore()
const tabsStore = useApiTabsStore()
const aiGenStore = useApifoxAiGenerateStore()

const treePanel = ref<InstanceType<typeof ApiTreePanel> | null>(null)
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

const serverNames = computed(() => {
  const names = new Set<string>()
  store.environments.forEach((e) => (e.servers || []).forEach((s) => names.add(s.name)))
  return [...names]
})

function goDataModels() {
  router.push(`/apifox/project/${pid.value}/datamodels`)
}
function goSchema(id: number) {
  router.push(`/apifox/project/${pid.value}/datamodels?schema=${id}`)
}

async function onSelectEndpoint(id: number) {
  try {
    await tabsStore.openEndpoint(pid.value, id)
  } catch {
    ElMessage.error('接口加载失败')
  }
}

function endpointPayload(form: EndpointEditorForm): Schemas['EndpointUpdate'] {
  return {
    name: form.name,
    method: form.method,
    path: form.path,
    server_name: form.server_name,
    description: form.description,
    request_spec: form.request_spec as Schemas['EndpointUpdate']['request_spec'],
    assertions: form.assertions,
    extracts: form.extracts,
    pre_scripts: (form.pre_scripts ?? []).map(({ script_id, enabled }) => ({ script_id, enabled })),
    post_scripts: (form.post_scripts ?? []).map(({ script_id, enabled }) => ({
      script_id,
      enabled,
    })),
    response_schema_id: form.response_schema_id,
    contract_strict: form.contract_strict,
  }
}

// 返回 true=已保存(可安全关闭)，false=未保存/用户取消
async function saveEndpoint(id: number) {
  const tab = tabsStore.findTab(pid.value, id)
  if (!tab) return false
  tab.saving = true
  try {
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
  const choice = await confirmCloseDirty(tab.name)
  if (choice === 'cancel') return
  if (choice === 'save' && !(await saveEndpoint(id))) return
  tabsStore.closeTab(pid.value, id)
}

function onDeleted(id: number) {
  tabsStore.closeTab(pid.value, id)
}
function onRenamed(id: number, name: string) {
  tabsStore.onRenamed(pid.value, id, name)
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
  margin-bottom: 8px;
}

.endpoint-tabbar :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.tab-name {
  margin: 0 4px;
}

.dirty-dot {
  color: var(--ax-warning);
  font-size: var(--ax-font-xs);
}

.empty-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.ec-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
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
