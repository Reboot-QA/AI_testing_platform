<template>
  <div class="tree-panel">
    <div class="panel-head">
      <span class="panel-title">接口</span>
      <div class="panel-actions">
        <el-dropdown trigger="click" @command="onNew">
          <el-button type="primary" size="small">
            <el-icon><Plus /></el-icon> 新建<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="api-tree-new-menu">
              <el-dropdown-item command="endpoint">
                <span class="new-menu-row">
                  <span class="new-menu-http">HTTP</span>
                  添加 HTTP 接口
                </span>
              </el-dropdown-item>
              <el-dropdown-item command="folder">
                <span class="new-menu-row">
                  <el-icon><FolderAdd /></el-icon>
                  添加目录
                </span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    <el-input
      v-model="filterText"
      :maxlength="SEARCH_MAX_LEN"
      size="small"
      clearable
      placeholder="搜索接口名 / 路径 / 文件夹"
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
      @node-expand="onNodeExpand"
      @node-collapse="onNodeCollapse"
    >
      <template #default="{ data }">
        <span class="node">
          <MethodTag v-if="data.type === 'endpoint'" :method="data.method" class="tree-method" />
          <el-icon v-else><Folder /></el-icon>
          <span class="node-title">
            <span class="node-label">{{ data.label }}</span>
            <span v-if="data.type === 'folder'" class="node-count"
              >({{ data.endpointCount ?? 0 }})</span
            >
            <span
              v-if="data.type === 'endpoint' && caseCounts"
              class="case-count"
              :class="{ 'case-count--right': readonly }"
              title="该接口的用例数"
              >{{ caseCounts[Number(data.id)] ?? 0 }}</span
            >
            <span
              v-if="data.casesStale"
              class="stale-dot"
              title="接口契约已更新，已有用例可能过时，建议重新生成或复核"
              >●</span
            >
          </span>
          <el-icon
            v-if="!readonly"
            class="node-more"
            title="更多操作"
            @click.stop="onMoreClick($event, data)"
          >
            <MoreFilled />
          </el-icon>
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
import { nameInputOptions } from '@/utils/promptLimits'
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { copyText } from '@/utils/clipboard'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { TreeContextMenuItem } from '@/types/apifox'
import { apifoxApi } from '@/api'
import { emptySpec, normalizeSpec } from '@/utils/apifoxSpec'
import { useApiTree, type ApiTreeNode } from '@/composables/useApiTree'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import TreeContextMenu from '@/components/apifox/common/TreeContextMenu.vue'

const props = withDefaults(
  defineProps<{
    projectId: Id
    showSchemas?: boolean
    // 提供则在接口节点右侧显示用例数徽标（接口用例页用）；不传则不显示（接口管理页）
    caseCounts?: Record<number, number>
    // 只读模式（接口用例页）：隐藏接口行的「...」更多操作与右键菜单，用例数徽标右对齐
    readonly?: boolean
    // 草稿式新建：新建接口时不弹「先输名」，而是 emit('new-draft') 交由外层开草稿编辑器（接口管理页用）
    draftCreate?: boolean
    // 首屏自动展开前 N 层文件夹（root 为第 1 层），只首次生效一次，之后尊重手动展开/收起
    autoExpandLevels?: number
    // 外层当前激活的接口 id：变化时让树自动高亮对应节点（切换 tab 跟随）；null/草稿 tab 时清除高亮
    currentEndpointId?: number | null
  }>(),
  {
    showSchemas: false,
    caseCounts: undefined,
    readonly: false,
    draftCreate: false,
    autoExpandLevels: 1,
    currentEndpointId: null,
  },
)
const emit = defineEmits<{
  select: [id: number]
  deleted: [id: number]
  renamed: [id: number, name: string, version?: number]
  'select-schema': [id: number]
  'generate-ai': [endpointIds: number[]]
  'case-added': []
  'new-draft': [folderId: number | null]
}>()

const pid = computed(() => props.projectId)
const {
  treeData,
  treeRef,
  filterText,
  filterNode,
  allowDrop,
  onDrop,
  onNodeExpand,
  onNodeCollapse,
  highlightEndpoint,
  reload: loadAll,
} = useApiTree(pid, { autoExpandLevels: props.autoExpandLevels })

// 切换编辑器 tab（activeId 变化）时，让左侧树高亮跟随当前接口；树尚未加载完则等 reload 后再补
watch(
  () => props.currentEndpointId,
  (id) => void highlightEndpoint(id),
)

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
  // 初次加载/刷新后按外层当前激活接口补一次高亮（watch 可能在树就绪前已触发过）
  await highlightEndpoint(props.currentEndpointId)
}

const selectedFolderId = ref<number | null>(null)
const ctx = reactive<{
  visible: boolean
  x: number
  y: number
  node: ApiTreeNode | null
  mode: 'full' | 'compact'
}>({
  visible: false,
  x: 0,
  y: 0,
  node: null,
  mode: 'full',
})

function onNew(command: string) {
  if (command === 'endpoint') addEndpoint()
  else if (command === 'folder') addFolder()
}

// ---------- 右键 / ... 菜单 ----------
function buildFullMenuItems(node: ApiTreeNode): TreeContextMenuItem[] {
  if (node.type === 'folder') {
    return [
      { key: 'add-endpoint', label: '添加 HTTP 接口', icon: 'http' },
      { key: 'add-folder', label: '添加目录', icon: 'folder' },
      { key: 'rename', label: '重命名', icon: 'rename', divided: true },
      {
        key: 'delete',
        label: '删除',
        icon: 'delete',
        danger: true,
        divided: true,
        shortcut: 'Del',
      },
    ]
  }
  const items: TreeContextMenuItem[] = []
  if (props.caseCounts !== undefined) {
    items.push({ key: 'add-case', label: '添加用例', icon: 'case' })
  }
  items.push(
    {
      key: 'rename',
      label: '重命名',
      icon: 'rename',
      divided: props.caseCounts === undefined,
    },
    { key: 'duplicate', label: '复制', icon: 'copy', shortcut: 'Ctrl+D' },
    { key: 'copy-curl', label: '复制 cURL', icon: 'curl' },
    {
      key: 'delete',
      label: '删除',
      icon: 'delete',
      danger: true,
      divided: true,
      shortcut: 'Del',
    },
  )
  return items
}

function buildCompactMenuItems(node: ApiTreeNode): TreeContextMenuItem[] {
  if (node.type === 'folder') {
    return [
      {
        key: 'add-group',
        label: '新增',
        icon: 'http',
        children: [
          { key: 'add-endpoint', label: 'HTTP 接口' },
          { key: 'add-folder', label: '目录' },
        ],
      },
      { key: 'rename', label: '重命名', icon: 'rename' },
      { key: 'delete', label: '删除', icon: 'delete', danger: true, divided: true },
    ]
  }
  const items: TreeContextMenuItem[] = [{ key: 'duplicate', label: '复制', icon: 'copy' }]
  if (props.caseCounts !== undefined) {
    items.push({ key: 'add-case', label: '新增', icon: 'case' })
  } else {
    items.push({ key: 'add-endpoint-sibling', label: '新增', icon: 'http' })
  }
  items.push(
    { key: 'rename', label: '重命名', icon: 'rename' },
    { key: 'delete', label: '删除', icon: 'delete', danger: true, divided: true },
  )
  return items
}

const ctxItems = computed(() => {
  if (!ctx.node) return []
  return ctx.mode === 'compact' ? buildCompactMenuItems(ctx.node) : buildFullMenuItems(ctx.node)
})

function onContextMenu(e: MouseEvent, data: ApiTreeNode) {
  if (props.readonly) return
  e.preventDefault()
  ctx.node = data
  ctx.mode = 'full'
  ctx.x = e.clientX
  ctx.y = e.clientY
  ctx.visible = true
}

function onMoreClick(e: MouseEvent, data: ApiTreeNode) {
  const el = e.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  ctx.node = data
  ctx.mode = 'compact'
  ctx.x = Math.max(8, rect.right - 196)
  ctx.y = rect.bottom + 2
  ctx.visible = true
}

function onCtxSelect(key: string) {
  const node = ctx.node
  if (!node) return
  if (key === 'add-endpoint') {
    selectedFolderId.value = node.type === 'folder' ? node.id : (node.folderId ?? null)
    addEndpoint()
  } else if (key === 'add-endpoint-sibling') {
    selectedFolderId.value = node.folderId ?? null
    addEndpoint()
  } else if (key === 'add-folder') {
    selectedFolderId.value = node.type === 'folder' ? node.id : (node.folderId ?? null)
    addFolder()
  } else if (key === 'rename') {
    renameNode(node)
  } else if (key === 'delete') {
    deleteNode(node)
  } else if (key === 'duplicate') {
    duplicateEndpoint(node)
  } else if (key === 'copy-curl') {
    copyEndpointCurl(node)
  } else if (key === 'add-case') {
    addCase(node)
  }
}

async function duplicateEndpoint(node: ApiTreeNode) {
  const e = await apifoxApi.getEndpoint(node.id)
  const created = await apifoxApi.createEndpoint(pid.value, {
    name: `${e.name} 副本`,
    method: e.method,
    path: e.path,
    folder_id: e.folder_id,
    contract_strict: e.contract_strict ?? false,
    request_spec: normalizeSpec(e.request_spec) as Schemas['EndpointCreate']['request_spec'],
    description: e.description,
  })
  ElMessage.success('已复制')
  await loadAll({
    expandFolderId: e.folder_id ?? null,
    currentKey: `e-${created.id}`,
  })
}

function onNodeClick(data: ApiTreeNode) {
  if (data.type === 'folder') selectedFolderId.value = data.id
  else emit('select', data.id)
}

async function addCase(node: ApiTreeNode) {
  const { value } = await ElMessageBox.prompt('用例名称', '添加用例', {
    ...nameInputOptions(),
  })
  let request_spec = emptySpec() as Schemas['CaseCreate']['request_spec']
  try {
    const ep = await apifoxApi.getEndpoint(node.id)
    if (ep?.request_spec) {
      request_spec = normalizeSpec(ep.request_spec) as Schemas['CaseCreate']['request_spec']
    }
  } catch {
    /* 拉取接口失败则用空 spec */
  }
  await apifoxApi.createCase(node.id, {
    name: value,
    category: 'other',
    request_spec,
    variables: [],
    data_drive: { enabled: false, source: 'inline', rows: [] },
    assertions: [],
    extracts: [],
    pre_scripts: [],
    post_scripts: [],
  })
  ElMessage.success('已添加用例')
  emit('select', node.id)
  emit('case-added')
}

async function copyEndpointCurl(node: ApiTreeNode) {
  const ep = await apifoxApi.getEndpoint(node.id)
  const spec = normalizeSpec(ep.request_spec)
  const lines = [`curl -X ${ep.method} '${ep.path}'`]
  for (const h of spec.headers ?? []) {
    if (h.enabled !== false && h.key) lines.push(`  -H '${h.key}: ${h.value ?? ''}'`)
  }
  if (spec.body?.raw) lines.push(`  -d '${spec.body.raw}'`)
  if (await copyText(lines.join(' \\\n'))) ElMessage.success('已复制 cURL')
  else ElMessage.error('复制失败')
}

async function addFolder() {
  const { value } = await ElMessageBox.prompt('目录名称', '添加目录', {
    ...nameInputOptions(),
  })
  const parentId = selectedFolderId.value
  await apifoxApi.createFolder(pid.value, { name: value, parent_id: parentId })
  ElMessage.success('已创建')
  await loadAll({ expandFolderId: parentId })
}

async function addEndpoint() {
  // 草稿式：不先输名，交由外层开一个草稿编辑器 tab，填内容/调试后再保存落库
  if (props.draftCreate) {
    emit('new-draft', selectedFolderId.value)
    return
  }
  const { value } = await ElMessageBox.prompt('接口名称', '添加 HTTP 接口', {
    ...nameInputOptions(),
  })
  const folderId = selectedFolderId.value
  const created = await apifoxApi.createEndpoint(pid.value, {
    name: value,
    method: 'GET',
    path: '/',
    folder_id: folderId,
    contract_strict: false,
    request_spec: emptySpec() as Schemas['EndpointCreate']['request_spec'],
  })
  ElMessage.success('已创建')
  await loadAll({
    expandFolderId: folderId,
    currentKey: `e-${created.id}`,
  })
  emit('select', created.id)
}

async function renameNode(data: ApiTreeNode) {
  const { value } = await ElMessageBox.prompt('新名称', '改名', {
    inputValue: data.label,
    ...nameInputOptions(),
  })
  let newVersion: number | undefined
  if (data.type === 'folder') await apifoxApi.updateFolder(data.id, { name: value })
  else newVersion = (await apifoxApi.updateEndpoint(data.id, { name: value })).version
  ElMessage.success('已更新')
  await loadAll()
  // 带上改名后的新 version：右侧已打开的详情 tab 同步 name+version，
  // 避免详情再保存时用过期 version 误报冲突（7/23-#6）
  if (data.type === 'endpoint') emit('renamed', data.id, value, newVersion)
}

async function deleteNode(data: ApiTreeNode) {
  const confirmMsg =
    data.type === 'folder'
      ? `确认删除文件夹「${data.label}」？其下所有子文件夹与接口将一并移入回收站。`
      : `确认删除「${data.label}」？`
  await ElMessageBox.confirm(confirmMsg, '提示', { type: 'warning' })
  if (data.type === 'folder') await apifoxApi.deleteFolder(data.id)
  else {
    await apifoxApi.deleteEndpoint(data.id)
    emit('deleted', data.id)
  }
  ElMessage.success('已删除')
  await loadAll()
}

defineExpose({ reload: reloadAll, addEndpoint })

onMounted(reloadAll)
</script>

<style scoped>
.tree-panel :deep(.el-tree-node__content) {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding-right: var(--ax-space-1);
}

.tree-panel :deep(.el-tree-node__content:hover .node-more),
.tree-panel :deep(.el-tree-node.is-current > .el-tree-node__content .node-more) {
  opacity: 1;
  color: var(--ax-text-secondary);
}

.node {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  flex: 1;
  min-width: 0;
  width: 100%;
}

.tree-method {
  flex-shrink: 0;
  min-width: 34px;
}

.node-title {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  overflow: hidden;
}

.node-label {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-count {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  font-weight: 400;
  color: var(--ax-text-tertiary);
}

.case-count {
  flex-shrink: 0;
  min-width: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--ax-bg-subtle);
  color: var(--ax-text-tertiary);
  font-size: var(--ax-font-xs);
  line-height: 16px;
  text-align: center;
}

/* 只读模式：无「...」占位，用例数徽标推到接口行右端 */
.case-count--right {
  margin-left: auto;
}

.stale-dot {
  flex-shrink: 0;
  margin-left: 4px;
  font-size: 10px;
  line-height: 1;
  color: var(--ax-warning);
}

.node-more {
  flex-shrink: 0;
  margin-left: auto;
  padding: 2px;
  border-radius: 4px;
  font-size: 14px;
  color: var(--ax-text-tertiary);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
}

.node-more:hover {
  color: var(--ax-text-secondary);
  background: var(--ax-bg-hover);
}

.schema-section {
  margin-top: var(--ax-space-2);
  border-top: 1px solid var(--ax-border);
  padding-top: var(--ax-space-2);
}

.schema-head {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
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

.new-menu-row {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.new-menu-http {
  min-width: 30px;
  padding: 0 4px;
  border-radius: 3px;
  background: #fff7ed;
  color: #ea580c;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}
</style>

<style>
.api-tree-new-menu .el-dropdown-menu__item {
  min-width: 180px;
}
</style>
