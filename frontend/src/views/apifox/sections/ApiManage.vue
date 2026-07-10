<template>
  <div class="api-manage">
    <ApiTreePanel
      ref="treePanel"
      :project-id="pid"
      show-schemas
      @select="loadEndpoint"
      @deleted="onDeleted"
      @renamed="onRenamed"
      @select-schema="goSchema"
    />

    <div class="editor-panel">
      <el-tabs v-if="form.id" v-model="endpointTab" class="endpoint-tabs">
        <el-tab-pane label="调试" name="debug">
          <ApiDebugPanel
            :form="form"
            :saving="saving"
            :server-names="serverNames"
            :project-id="pid"
            :scripts="scripts"
            :schemas="schemas"
            @save="saveEndpoint"
          />
        </el-tab-pane>
        <el-tab-pane label="文档预览" name="doc">
          <ApiDocPreview :form="form" />
        </el-tab-pane>
        <el-tab-pane label="测试用例" name="cases">
          <ApiCasesPanel :endpoint-id="form.id" :project-id="pid" />
        </el-tab-pane>
      </el-tabs>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apifoxApi } from '@/api'
import { emptySpec, normalizeSpec } from '@/utils/apifoxSpec'
import { useWorkspaceStore } from '@/stores/workspace'
import { useProjectScripts } from '@/composables/useProjectScripts'
import ApiTreePanel from '@/components/apifox/ApiTreePanel.vue'
import ApiDebugPanel from '@/components/apifox/ApiDebugPanel.vue'
import ApiDocPreview from '@/components/apifox/ApiDocPreview.vue'
import ApiCasesPanel from '@/components/apifox/ApiCasesPanel.vue'

const route = useRoute()
const router = useRouter()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()

const treePanel = ref(null)
const saving = ref(false)
const endpointTab = ref('debug')
const { scripts, loadScripts } = useProjectScripts(pid)

const schemas = ref([])
const form = reactive({
  id: null, name: '', method: 'GET', path: '', server_name: null, description: '',
  request_spec: emptySpec(), assertions: [], extracts: [], pre_scripts: [], post_scripts: [],
  response_schema_id: null, contract_strict: false,
})

// server 名取自工作区环境（顶部统一加载），供接口选择前置服务
const serverNames = computed(() => {
  const names = new Set()
  store.environments.forEach((e) => (e.servers || []).forEach((s) => names.add(s.name)))
  return [...names]
})

function goDataModels() {
  router.push(`/apifox/project/${pid.value}/datamodels`)
}

// 树内数据模型点击 → 数据模型 tab（带 schema 便于自动选中）
function goSchema(id) {
  router.push(`/apifox/project/${pid.value}/datamodels?schema=${id}`)
}

async function loadEndpoint(id) {
  const e = await apifoxApi.getEndpoint(id)
  form.id = e.id
  form.name = e.name
  form.method = e.method
  form.path = e.path
  form.server_name = e.server_name || null
  form.description = e.description || ''
  form.request_spec = normalizeSpec(e.request_spec)
  form.assertions = e.assertions || []
  form.extracts = e.extracts || []
  form.pre_scripts = e.pre_scripts || []
  form.post_scripts = e.post_scripts || []
  form.response_schema_id = e.response_schema_id || null
  form.contract_strict = e.contract_strict || false
}

function onDeleted(id) {
  if (form.id === id) form.id = null
}

function onRenamed(id, name) {
  if (form.id === id) form.name = name
}

async function saveEndpoint() {
  saving.value = true
  try {
    await apifoxApi.updateEndpoint(form.id, {
      name: form.name, method: form.method, path: form.path, server_name: form.server_name,
      description: form.description, request_spec: form.request_spec,
      assertions: form.assertions, extracts: form.extracts,
      pre_scripts: form.pre_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
      post_scripts: form.post_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
      response_schema_id: form.response_schema_id, contract_strict: form.contract_strict,
    })
    ElMessage.success('已保存')
    treePanel.value?.reload()
  } finally {
    saving.value = false
  }
}

async function loadSchemas() {
  schemas.value = await apifoxApi.listSchemas(pid.value)
}

onMounted(() => {
  loadScripts()
  loadSchemas()
})
</script>

<style scoped>
.api-manage {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.editor-panel {
  flex: 1;
  overflow: auto;
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
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.ec-card:hover {
  border-color: var(--ax-brand);
  transform: translateY(-2px);
}

.ec-icon {
  font-size: 30px;
}
</style>
