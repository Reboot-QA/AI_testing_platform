<template>
  <div class="api-manage">
    <ApiTreePanel
      ref="treePanel"
      :project-id="pid"
      @select="loadEndpoint"
      @deleted="onDeleted"
      @renamed="onRenamed"
    />

    <div class="editor-panel">
      <el-tabs v-if="form.id" v-model="endpointTab" class="endpoint-tabs">
        <el-tab-pane label="调试" name="debug">
          <ApiDebugPanel
            :form="form"
            :saving="saving"
            :environments="environments"
            :server-names="serverNames"
            :project-id="pid"
            @save="saveEndpoint"
          />
        </el-tab-pane>
        <el-tab-pane label="文档预览" name="doc">
          <ApiDocPreview :form="form" />
        </el-tab-pane>
        <el-tab-pane label="测试用例" name="cases">
          <ApiCasesPanel :endpoint-id="form.id" :project-id="pid" :environments="environments" />
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
import ApiTreePanel from '@/components/apifox/ApiTreePanel.vue'
import ApiDebugPanel from '@/components/apifox/ApiDebugPanel.vue'
import ApiDocPreview from '@/components/apifox/ApiDocPreview.vue'
import ApiCasesPanel from '@/components/apifox/ApiCasesPanel.vue'

const route = useRoute()
const router = useRouter()
const pid = computed(() => route.params.projectId)

const treePanel = ref(null)
const saving = ref(false)
const endpointTab = ref('debug')
const environments = ref([])

const form = reactive({ id: null, name: '', method: 'GET', path: '', server_name: null, description: '', request_spec: emptySpec() })

const serverNames = computed(() => {
  const names = new Set()
  environments.value.forEach((e) => (e.servers || []).forEach((s) => names.add(s.name)))
  return [...names]
})

function goDataModels() {
  router.push(`/apifox/project/${pid.value}/datamodels`)
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
    })
    ElMessage.success('已保存')
    treePanel.value?.reload()
  } finally {
    saving.value = false
  }
}

async function loadEnvironments() {
  environments.value = await apifoxApi.listEnvironments(pid.value)
}

onMounted(loadEnvironments)
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
