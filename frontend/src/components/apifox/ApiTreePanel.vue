<template>
  <div class="tree-panel">
    <div class="tree-toolbar">
      <el-dropdown trigger="click" @command="onNew">
        <el-button size="small" type="primary">
          <el-icon><Plus /></el-icon> 新建<el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="endpoint"
              ><el-icon><Link /></el-icon> 新建接口</el-dropdown-item
            >
            <el-dropdown-item command="folder"
              ><el-icon><FolderAdd /></el-icon> 新建文件夹</el-dropdown-item
            >
            <el-dropdown-item command="import" divided
              ><el-icon><Download /></el-icon> 导入</el-dropdown-item
            >
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button size="small" @click="openUpdateSwagger">
        <el-icon><Refresh /></el-icon> 更新 Swagger
      </el-button>
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

    <div v-if="showSchemas" class="schema-section">
      <div class="schema-head">
        <el-icon><Box /></el-icon> 数据模型
      </div>
      <div
        v-for="s in filteredSchemas"
        :key="s.id"
        class="schema-item"
        @click="emit('select-schema', s.id)"
      >
        <span class="schema-name">{{ s.name }}</span>
      </div>
      <div v-if="!filteredSchemas.length" class="schema-empty">暂无数据模型</div>
    </div>

    <ImportDialog
      v-model:visible="importVisible"
      :project-id="pid"
      :default-action="importAction"
      @imported="reloadAll"
    />
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

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { emptySpec } from '@/utils/apifoxSpec'
import { useApiTree, type ApiTreeNode } from '@/composables/useApiTree'
import ImportDialog from '@/components/apifox/ImportDialog.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import TreeContextMenu from '@/components/apifox/common/TreeContextMenu.vue'

const props = withDefaults(
  defineProps<{
    projectId: Id
    showSchemas?: boolean
  }>(),
  {
    showSchemas: false,
  },
)
const emit = defineEmits<{
  select: [id: number]
  deleted: [id: number]
  renamed: [id: number, name: string]
  'select-schema': [id: number]
}>()

const pid = computed(() => props.projectId)
const {
  treeData,
  treeRef,
  filterText,
  filterNode,
  allowDrop,
  onDrop,
  reload: loadAll,
} = useApiTree(pid)

const schemas = ref<Schemas['SchemaBrief'][]>([])
const filteredSchemas = computed(() => {
  const kw = filterText.value.trim().toLowerCase()
  return kw ? schemas.value.filter((s) => (s.name || '').toLowerCase().includes(kw)) : schemas.value
})

async function loadSchemas() {
  if (props.showSchemas) schemas.value = await apifoxApi.listSchemas(pid.value)
}

async function reloadAll() {
  await loadAll()
  await loadSchemas()
}

const selectedFolderId = ref<number | null>(null)
const importVisible = ref(false)
const importAction = ref<'import' | 'update'>('import')
const ctx = reactive<{ visible: boolean; x: number; y: number; node: ApiTreeNode | null }>({
  visible: false,
  x: 0,
  y: 0,
  node: null,
})

function onNew(command: string) {
  if (command === 'endpoint') addEndpoint()
  else if (command === 'folder') addFolder()
  else if (command === 'import') openImport()
}

function openUpdateSwagger() {
  importAction.value = 'update'
  importVisible.value = true
}

// ---------- 右键菜单 ----------
const ctxItems = computed(() => {
  if (!ctx.node) return []
  const items = []
  if (ctx.node.type === 'folder') {
    items.push(
      { key: 'add-endpoint', label: '新建接口' },
      { key: 'add-folder', label: '新建子文件夹' },
    )
  }
  items.push({ key: 'rename', label: '重命名' })
  if (ctx.node.type === 'endpoint') items.push({ key: 'duplicate', label: '复制接口' })
  items.push({ key: 'delete', label: '删除', danger: true })
  return items
})

function onContextMenu(e: MouseEvent, data: ApiTreeNode) {
  e.preventDefault()
  ctx.node = data
  ctx.x = e.clientX
  ctx.y = e.clientY
  ctx.visible = true
}

function onCtxSelect(key: string) {
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

async function duplicateEndpoint(node: ApiTreeNode) {
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

function onNodeClick(data: ApiTreeNode) {
  if (data.type === 'folder') selectedFolderId.value = data.id
  else emit('select', data.id)
}

async function addFolder() {
  const { value } = await ElMessageBox.prompt('文件夹名称', '新建文件夹', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  await apifoxApi.createFolder(pid.value, { name: value, parent_id: selectedFolderId.value })
  ElMessage.success('已创建')
  await loadAll()
}

async function addEndpoint() {
  const { value } = await ElMessageBox.prompt('接口名称', '新建接口', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createEndpoint(pid.value, {
    name: value,
    method: 'GET',
    path: '/',
    folder_id: selectedFolderId.value,
    request_spec: emptySpec(),
  })
  ElMessage.success('已创建')
  await loadAll()
  emit('select', created.id)
}

async function renameNode(data: ApiTreeNode) {
  const { value } = await ElMessageBox.prompt('新名称', '改名', {
    inputValue: data.label,
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  if (data.type === 'folder') await apifoxApi.updateFolder(data.id, { name: value })
  else await apifoxApi.updateEndpoint(data.id, { name: value })
  ElMessage.success('已更新')
  await loadAll()
  if (data.type === 'endpoint') emit('renamed', data.id, value)
}

async function deleteNode(data: ApiTreeNode) {
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
  importAction.value = 'import'
  importVisible.value = true
}

defineExpose({ reload: reloadAll, addEndpoint, openImport })

onMounted(reloadAll)
</script>

<style scoped>
.tree-panel {
  width: 280px;
  flex-shrink: 0;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: var(--ax-gap);
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

.schema-section {
  margin-top: 10px;
  border-top: 1px solid var(--ax-border);
  padding-top: 8px;
}

.schema-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--ax-font-xs);
  font-weight: 700;
  color: var(--ax-text-tertiary);
  padding: 4px 8px;
}

.schema-item {
  display: flex;
  align-items: center;
  padding: 6px 8px 6px 26px;
  border-radius: 4px;
  cursor: pointer;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.schema-item:hover {
  background: var(--ax-bg-hover);
}

.schema-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schema-empty {
  padding: 4px 8px 4px 26px;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}
</style>
