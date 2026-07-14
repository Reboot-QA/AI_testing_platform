<template>
  <div class="mindmap-shell">
    <div class="mindmap-toolbar">
      <el-button-group>
        <el-button size="small" @click="expandAll">展开全部</el-button>
        <el-button size="small" @click="collapseAll">收起全部</el-button>
      </el-button-group>
      <el-button-group>
        <el-button size="small" @click="zoomOut">缩小</el-button>
        <el-button size="small" @click="resetView">{{ Math.round(scale * 100) }}%</el-button>
        <el-button size="small" @click="zoomIn">放大</el-button>
      </el-button-group>
      <span class="mindmap-hint">滚轮缩放 · 拖拽平移 · 点击需求节点查看详情</span>
    </div>

    <div
      ref="viewportRef"
      class="mindmap-viewport"
      :class="{ panning: isPanning }"
      @wheel.prevent="onWheel"
      @mousedown="onPanStart"
    >
      <div class="mindmap-canvas" :style="canvasStyle">
        <MindMapNode
          :node="tree"
          :depth="0"
          :collapsed-ids="collapsedIds"
          :selected-ids="selectedIds"
          :select-mode="selectMode"
          @toggle="toggleCollapse"
          @node-click="handleNodeClick"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import MindMapNode from './MindMapNode.vue'
import { SOURCE_LABELS, STATUS_LABELS, TYPE_LABELS } from '@/utils/requirementMindMap'

const props = defineProps({
  tree: { type: Object, required: true },
  selectedIds: { type: Array, default: () => [] },
  selectMode: { type: Boolean, default: false },
})

const emit = defineEmits(['node-click', 'toggle-select'])

const viewportRef = ref(null)
const scale = ref(0.85)
const offset = reactive({ x: 40, y: 40 })
const collapsedIds = ref(new Set())
const isPanning = ref(false)
const panStart = reactive({ x: 0, y: 0, offsetX: 0, offsetY: 0 })

const canvasStyle = computed(() => ({
  transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale.value})`,
  transformOrigin: '0 0',
}))

function collectCollapsibleIds(node, ids = []) {
  if (node.children?.length) {
    ids.push(node.id)
    for (const child of node.children) collectCollapsibleIds(child, ids)
  }
  return ids
}

function toggleCollapse(id) {
  const next = new Set(collapsedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsedIds.value = next
}

function expandAll() {
  collapsedIds.value = new Set()
}

function collapseAll() {
  collapsedIds.value = new Set(collectCollapsibleIds(props.tree))
}

function zoomIn() {
  scale.value = Math.min(2, +(scale.value + 0.1).toFixed(2))
}

function zoomOut() {
  scale.value = Math.max(0.4, +(scale.value - 0.1).toFixed(2))
}

function resetView() {
  scale.value = 0.85
  offset.x = 40
  offset.y = 40
}

function onWheel(event) {
  const delta = event.deltaY > 0 ? -0.08 : 0.08
  scale.value = Math.min(2, Math.max(0.4, +(scale.value + delta).toFixed(2)))
}

function onPanStart(event) {
  if (event.button !== 0) return
  if (event.target.closest('.mind-node-card')) return
  isPanning.value = true
  panStart.x = event.clientX
  panStart.y = event.clientY
  panStart.offsetX = offset.x
  panStart.offsetY = offset.y
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', onPanEnd)
}

function onPanMove(event) {
  if (!isPanning.value) return
  offset.x = panStart.offsetX + (event.clientX - panStart.x)
  offset.y = panStart.offsetY + (event.clientY - panStart.y)
}

function onPanEnd() {
  isPanning.value = false
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
}

function handleNodeClick(node) {
  if (node.kind !== 'requirement' || !node.requirement) return
  if (props.selectMode) {
    emit('toggle-select', node.requirement)
    return
  }
  emit('node-click', node.requirement)
}

watch(
  () => props.tree,
  () => {
    collapsedIds.value = new Set()
  },
  { deep: true }
)

onMounted(() => {
  collapseAll()
  const typeNodes = props.tree.children?.filter((item) => item.kind === 'type' || item.kind === 'project') || []
  for (const node of typeNodes.slice(0, 2)) {
    collapsedIds.value.delete(node.id)
  }
})

onUnmounted(() => {
  onPanEnd()
})

defineExpose({
  TYPE_LABELS,
  STATUS_LABELS,
  SOURCE_LABELS,
})
</script>

<style scoped>
.mindmap-shell {
  display: flex;
  flex-direction: column;
  min-height: 620px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: linear-gradient(180deg, #f8fbff 0%, #f5f7fa 100%);
  overflow: hidden;
}

.mindmap-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
  flex-wrap: wrap;
}

.mindmap-hint {
  color: #909399;
  font-size: 12px;
  margin-left: auto;
}

.mindmap-viewport {
  flex: 1;
  min-height: 560px;
  overflow: hidden;
  cursor: grab;
  position: relative;
}

.mindmap-viewport.panning {
  cursor: grabbing;
}

.mindmap-canvas {
  display: inline-block;
  min-width: max-content;
  padding: 24px;
  transition: transform 0.08s ease-out;
}
</style>
