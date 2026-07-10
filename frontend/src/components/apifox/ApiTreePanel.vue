<template>
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
    <el-input v-model="filterText" size="small" clearable placeholder="搜索接口 / 文件夹" class="tree-search" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { emptySpec } from '@/utils/apifoxSpec'
import { useApiTree } from '@/composables/useApiTree'
import ImportDialog from '@/components/apifox/ImportDialog.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import TreeContextMenu from '@/components/apifox/common/TreeContextMenu.vue'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
})
const emit = defineEmits(['select', 'deleted', 'renamed'])

const pid = computed(() => props.projectId)
const { treeData, treeRef, filterText, filterNode, allowDrop, onDrop, reload: loadAll } = useApiTree(pid)

const selectedFolderId = ref(null)
const importVisible = ref(false)
const ctx = reactive({ visible: false, x: 0, y: 0, node: null })

function onNew(command) {
  if (command === 'endpoint') addEndpoint()
  else if (command === 'folder') addFolder()
  else if (command === 'import') importVisible.value = true
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
    name: `${e.name} 副本`, method: e.method, path: e.path,
    folder_id: e.folder_id, request_spec: e.request_spec, description: e.description,
  })
  ElMessage.success('已复制')
  await loadAll()
}

function onNodeClick(data) {
  if (data.type === 'folder') selectedFolderId.value = data.id
  else emit('select', data.id)
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
  emit('select', created.id)
}

async function renameNode(data) {
  const { value } = await ElMessageBox.prompt('新名称', '改名', { inputValue: data.label, inputPattern: /\S/, inputErrorMessage: '不能为空' })
  if (data.type === 'folder') await apifoxApi.updateFolder(data.id, { name: value })
  else await apifoxApi.updateEndpoint(data.id, { name: value })
  ElMessage.success('已更新')
  await loadAll()
  if (data.type === 'endpoint') emit('renamed', data.id, value)
}

async function deleteNode(data) {
  await ElMessageBox.confirm(`确认删除「${data.label}」？`, '提示', { type: 'warning' })
  if (data.type === 'folder') await apifoxApi.deleteFolder(data.id)
  else {
    await apifoxApi.deleteEndpoint(data.id)
    emit('deleted', data.id)
  }
  ElMessage.success('已删除')
  await loadAll()
}

function openImport() {
  importVisible.value = true
}

defineExpose({ reload: loadAll, addEndpoint, openImport })

onMounted(loadAll)
</script>

<style scoped>
.tree-panel {
  width: 300px;
  flex-shrink: 0;
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
