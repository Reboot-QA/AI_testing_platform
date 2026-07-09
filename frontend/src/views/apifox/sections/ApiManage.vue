<template>
  <div class="api-manage">
    <div class="tree-panel">
      <div class="tree-toolbar">
        <el-button size="small" @click="addFolder">
          <el-icon><FolderAdd /></el-icon> 文件夹
        </el-button>
        <el-button size="small" type="primary" @click="addEndpoint">
          <el-icon><Plus /></el-icon> 接口
        </el-button>
        <el-button size="small" @click="importVisible = true">
          <el-icon><Download /></el-icon> 导入
        </el-button>
      </div>
      <el-tree
        :data="treeData"
        node-key="key"
        :expand-on-click-node="false"
        highlight-current
        @node-click="onNodeClick"
      >
        <template #default="{ data }">
          <span class="node">
            <MethodTag v-if="data.type === 'endpoint'" :method="data.method" class="tree-method" />
            <el-icon v-else><Folder /></el-icon>
            <span class="node-label">{{ data.label }}</span>
            <span class="node-ops">
              <el-button link size="small" @click.stop="renameNode(data)">改名</el-button>
              <el-button link size="small" type="danger" @click.stop="deleteNode(data)">删</el-button>
            </span>
          </span>
        </template>
      </el-tree>
    </div>

    <div class="editor-panel">
      <ApiEndpointEditor v-if="form.id" :form="form" :saving="saving" @save="saveEndpoint" />
      <el-empty v-else description="选择或新建一个接口开始编辑" />
    </div>

    <ImportDialog v-model:visible="importVisible" :project-id="pid" @imported="loadAll" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import ApiEndpointEditor from '@/components/apifox/ApiEndpointEditor.vue'
import ImportDialog from '@/components/apifox/ImportDialog.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const folders = ref([])
const endpoints = ref([])
const selectedFolderId = ref(null)
const saving = ref(false)
const importVisible = ref(false)

const form = reactive({ id: null, name: '', method: 'GET', path: '', description: '', request_spec: emptySpec() })

function emptySpec() {
  return {
    query: [],
    path_params: [],
    headers: [],
    body: { type: 'none', raw: '', form: [] },
    auth: { type: 'none', token: '', username: '', password: '' },
  }
}

function normalizeSpec(spec) {
  const s = spec || {}
  const body = s.body || {}
  return {
    query: ensureKvRows(s.query || []),
    path_params: ensureKvRows(s.path_params || []),
    headers: ensureKvRows(s.headers || []),
    body: {
      type: body.type || 'none',
      raw: body.raw || '',
      form: ensureKvRows(body.form || []),
    },
    auth: {
      type: s.auth?.type || 'none',
      token: s.auth?.token || '',
      username: s.auth?.username || '',
      password: s.auth?.password || '',
    },
  }
}

const treeData = computed(() => {
  const map = {}
  folders.value.forEach((f) => {
    map[f.id] = { key: `f-${f.id}`, id: f.id, type: 'folder', label: f.name, children: [] }
  })
  const roots = []
  folders.value.forEach((f) => {
    const node = map[f.id]
    if (f.parent_id && map[f.parent_id]) map[f.parent_id].children.push(node)
    else roots.push(node)
  })
  endpoints.value.forEach((e) => {
    const node = { key: `e-${e.id}`, id: e.id, type: 'endpoint', label: e.name, method: e.method }
    if (e.folder_id && map[e.folder_id]) map[e.folder_id].children.push(node)
    else roots.push(node)
  })
  return roots
})

async function loadAll() {
  const [fs, es] = await Promise.all([apifoxApi.listFolders(pid.value), apifoxApi.listEndpoints(pid.value)])
  folders.value = fs
  endpoints.value = es
}

function onNodeClick(data) {
  if (data.type === 'folder') {
    selectedFolderId.value = data.id
  } else {
    loadEndpoint(data.id)
  }
}

async function loadEndpoint(id) {
  const e = await apifoxApi.getEndpoint(id)
  form.id = e.id
  form.name = e.name
  form.method = e.method
  form.path = e.path
  form.description = e.description || ''
  form.request_spec = normalizeSpec(e.request_spec)
  selectedFolderId.value = e.folder_id
}

async function addFolder() {
  const { value } = await ElMessageBox.prompt('文件夹名称', '新建文件夹', { inputPattern: /\S/, inputErrorMessage: '不能为空' })
  await apifoxApi.createFolder(pid.value, { name: value, parent_id: selectedFolderId.value })
  ElMessage.success('已创建')
  await loadAll()
}

async function addEndpoint() {
  const { value } = await ElMessageBox.prompt('接口名称', '新建接口', { inputPattern: /\S/, inputErrorMessage: '不能为空' })
  const created = await apifoxApi.createEndpoint(pid.value, {
    name: value, method: 'GET', path: '/', folder_id: selectedFolderId.value, request_spec: emptySpec(),
  })
  ElMessage.success('已创建')
  await loadAll()
  await loadEndpoint(created.id)
}

async function renameNode(data) {
  const { value } = await ElMessageBox.prompt('新名称', '改名', { inputValue: data.label, inputPattern: /\S/, inputErrorMessage: '不能为空' })
  if (data.type === 'folder') await apifoxApi.updateFolder(data.id, { name: value })
  else await apifoxApi.updateEndpoint(data.id, { name: value })
  ElMessage.success('已更新')
  await loadAll()
  if (data.type === 'endpoint' && form.id === data.id) form.name = value
}

async function deleteNode(data) {
  await ElMessageBox.confirm(`确认删除「${data.label}」？`, '提示', { type: 'warning' })
  if (data.type === 'folder') await apifoxApi.deleteFolder(data.id)
  else {
    await apifoxApi.deleteEndpoint(data.id)
    if (form.id === data.id) form.id = null
  }
  ElMessage.success('已删除')
  await loadAll()
}

async function saveEndpoint() {
  saving.value = true
  try {
    await apifoxApi.updateEndpoint(form.id, {
      name: form.name, method: form.method, path: form.path,
      description: form.description, request_spec: form.request_spec,
    })
    ElMessage.success('已保存')
    await loadAll()
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.api-manage {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.tree-panel {
  width: 300px;
  border-right: 1px solid #e2e8f0;
  overflow: auto;
  padding-right: 8px;
}

.tree-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.editor-panel {
  flex: 1;
  overflow: auto;
}

.node {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.tree-method {
  flex-shrink: 0;
  min-width: 34px;
}

.node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-ops {
  display: none;
}

.node:hover .node-ops {
  display: inline-flex;
}
</style>
