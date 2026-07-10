<template>
  <div class="api-manage">
    <div class="tree-panel">
      <div class="tree-toolbar">
        <el-dropdown trigger="click" @command="onNew">
          <el-button size="small" type="primary">
            <el-icon><Plus /></el-icon> 新建<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="endpoint"><el-icon><Link /></el-icon> 新建接口</el-dropdown-item>
              <el-dropdown-item command="folder"><el-icon><FolderAdd /></el-icon> 新建文件夹</el-dropdown-item>
              <el-dropdown-item command="import" divided><el-icon><Download /></el-icon> 导入</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <el-input
        v-model="filterText"
        size="small"
        clearable
        placeholder="搜索接口 / 文件夹"
        class="tree-search"
      />
      <el-tree
        ref="treeRef"
        :data="treeData"
        node-key="key"
        :expand-on-click-node="false"
        :allow-drop="allowDrop"
        :filter-node-method="filterNode"
        highlight-current
        draggable
        @node-click="onNodeClick"
        @node-drop="onDrop"
        @node-contextmenu="onContextMenu"
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
        <div class="ec-card" @click="addEndpoint">
          <el-icon class="ec-icon" color="var(--color-blue-6)"><Link /></el-icon>
          <span>新建 HTTP 接口</span>
        </div>
        <div class="ec-card" @click="goDataModels">
          <el-icon class="ec-icon" color="var(--color-pink-6)"><Box /></el-icon>
          <span>新建数据模型</span>
        </div>
        <div class="ec-card" @click="importVisible = true">
          <el-icon class="ec-icon" color="var(--color-green-6)"><Download /></el-icon>
          <span>导入</span>
        </div>
      </div>
    </div>

    <ImportDialog v-model:visible="importVisible" :project-id="pid" @imported="loadAll" />
    <TreeContextMenu
      :visible="ctx.visible"
      :x="ctx.x"
      :y="ctx.y"
      :items="ctxItems"
      @select="onCtxSelect"
      @close="ctx.visible = false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import { useApiTree } from '@/composables/useApiTree'
import ApiDebugPanel from '@/components/apifox/ApiDebugPanel.vue'
import ApiDocPreview from '@/components/apifox/ApiDocPreview.vue'
import ApiCasesPanel from '@/components/apifox/ApiCasesPanel.vue'
import ImportDialog from '@/components/apifox/ImportDialog.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import TreeContextMenu from '@/components/apifox/common/TreeContextMenu.vue'

const route = useRoute()
const router = useRouter()
const pid = computed(() => route.params.projectId)

function onNew(command) {
  if (command === 'endpoint') addEndpoint()
  else if (command === 'folder') addFolder()
  else if (command === 'import') importVisible.value = true
}

function goDataModels() {
  router.push(`/apifox/project/${pid.value}/datamodels`)
}

const { treeData, treeRef, filterText, filterNode, allowDrop, onDrop, reload: loadAll } = useApiTree(pid)

const selectedFolderId = ref(null)
const saving = ref(false)
const endpointTab = ref('debug')
const environments = ref([])
const importVisible = ref(false)
const ctx = reactive({ visible: false, x: 0, y: 0, node: null })

const form = reactive({ id: null, name: '', method: 'GET', path: '', server_name: null, description: '', request_spec: emptySpec() })

const serverNames = computed(() => {
  const names = new Set()
  environments.value.forEach((e) => (e.servers || []).forEach((s) => names.add(s.name)))
  return [...names]
})

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

// ---------- 右键菜单 ----------
const ctxItems = computed(() => {
  if (!ctx.node) return []
  const items = []
  if (ctx.node.type === 'folder') {
    items.push({ key: 'add-endpoint', label: '新建接口' }, { key: 'add-folder', label: '新建子文件夹' })
  }
  items.push({ key: 'rename', label: '重命名' })
  if (ctx.node.type === 'endpoint') items.push({ key: 'duplicate', label: '复制接口' })
  items.push({ key: 'delete', label: '删除', danger: true })
  return items
})

function onContextMenu(e, data) {
  e.preventDefault()
  ctx.node = data
  ctx.x = e.clientX
  ctx.y = e.clientY
  ctx.visible = true
}

function onCtxSelect(key) {
  const node = ctx.node
  if (!node) return
  if (key === 'add-endpoint') {
    selectedFolderId.value = node.id
    addEndpoint()
  } else if (key === 'add-folder') {
    selectedFolderId.value = node.id
    addFolder()
  } else if (key === 'rename') {
    renameNode(node)
  } else if (key === 'delete') {
    deleteNode(node)
  } else if (key === 'duplicate') {
    duplicateEndpoint(node)
  }
}

async function duplicateEndpoint(node) {
  const e = await apifoxApi.getEndpoint(node.id)
  await apifoxApi.createEndpoint(pid.value, {
    name: `${e.name} 副本`,
    method: e.method,
    path: e.path,
    folder_id: e.folder_id,
    request_spec: e.request_spec,
    description: e.description,
  })
  ElMessage.success('已复制')
  await loadAll()
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
  form.server_name = e.server_name || null
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
      name: form.name, method: form.method, path: form.path, server_name: form.server_name,
      description: form.description, request_spec: form.request_spec,
    })
    ElMessage.success('已保存')
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function loadEnvironments() {
  environments.value = await apifoxApi.listEnvironments(pid.value)
}

onMounted(() => {
  loadAll()
  loadEnvironments()
})
</script>

<style scoped>
.api-manage {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.tree-panel {
  width: 300px;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

.tree-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.tree-search {
  margin-bottom: 8px;
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
