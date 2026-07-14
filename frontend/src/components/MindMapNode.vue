<template>
  <div class="mind-node-wrap" :class="[`depth-${depth}`, `kind-${node.kind}`]">
    <div class="mind-node-row">
      <div
        class="mind-node-card"
        :class="{
          clickable: node.kind === 'requirement',
          selected: node.kind === 'requirement' && selectedIds.includes(node.requirement?.id),
          [`status-${node.requirement?.status}`]: node.kind === 'requirement',
        }"
        @click.stop="onCardClick"
      >
        <button
          v-if="hasChildren"
          class="collapse-btn"
          type="button"
          @click.stop="$emit('toggle', node.id)"
        >
          {{ collapsed ? '+' : '−' }}
        </button>

        <div class="node-title" :title="node.label">{{ node.label }}</div>

        <div v-if="node.kind === 'requirement' && node.meta" class="node-meta">
          <span class="meta-tag type">{{ typeLabel(node.meta.req_type) }}</span>
          <span class="meta-tag priority">{{ node.meta.priority }}</span>
          <span class="meta-tag status">{{ statusLabel(node.meta.status) }}</span>
          <span class="meta-tag source">{{ sourceLabel(node.meta.source) }}</span>
          <span v-if="node.meta.testcase_count" class="meta-tag cases">用例 {{ node.meta.testcase_count }}</span>
        </div>

        <div v-else-if="node.meta?.total != null" class="node-sub">共 {{ node.meta.total }} 条需求</div>
      </div>

      <div v-if="hasChildren && !collapsed" class="mind-children">
        <div class="connector" />
        <div class="children-list">
          <MindMapNode
            v-for="child in node.children"
            :key="child.id"
            :node="child"
            :depth="depth + 1"
            :collapsed-ids="collapsedIds"
            :selected-ids="selectedIds"
            :select-mode="selectMode"
            @toggle="$emit('toggle', $event)"
            @node-click="$emit('node-click', $event)"
            @toggle-select="$emit('toggle-select', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { SOURCE_LABELS, STATUS_LABELS, TYPE_LABELS } from '@/utils/requirementMindMap'

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  collapsedIds: { type: Object, required: true },
  selectedIds: { type: Array, default: () => [] },
  selectMode: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle', 'node-click', 'toggle-select'])

const hasChildren = computed(() => (props.node.children?.length || 0) > 0)
const collapsed = computed(() => props.collapsedIds.has(props.node.id))

function typeLabel(value) {
  return TYPE_LABELS[value] || value
}

function statusLabel(value) {
  return STATUS_LABELS[value] || value
}

function sourceLabel(value) {
  return SOURCE_LABELS[value] || value
}

function onCardClick() {
  if (props.node.kind !== 'requirement') return
  emit('node-click', props.node)
}
</script>

<style scoped>
.mind-node-wrap {
  display: flex;
  align-items: center;
}

.mind-node-row {
  display: flex;
  align-items: center;
}

.mind-node-card {
  position: relative;
  min-width: 120px;
  max-width: 280px;
  padding: 10px 14px 10px 16px;
  border-radius: 10px;
  border: 2px solid transparent;
  background: #fff;
  box-shadow: 0 2px 10px rgba(31, 45, 61, 0.08);
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
}

.mind-node-card.clickable {
  cursor: pointer;
}

.mind-node-card.clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(64, 158, 255, 0.18);
}

.mind-node-card.selected {
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}

.kind-root > .mind-node-row > .mind-node-card {
  min-width: 160px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  font-weight: 600;
  font-size: 16px;
  border: none;
}

.kind-project > .mind-node-row > .mind-node-card {
  background: linear-gradient(135deg, #67c23a, #529b2e);
  color: #fff;
  font-weight: 600;
  border: none;
}

.kind-type > .mind-node-row > .mind-node-card {
  background: #ecf5ff;
  border-color: #b3d8ff;
  color: #409eff;
  font-weight: 600;
}

.kind-priority > .mind-node-row > .mind-node-card {
  background: #fdf6ec;
  border-color: #f5dab1;
  color: #e6a23c;
  font-weight: 600;
}

.kind-requirement > .mind-node-row > .mind-node-card {
  border-left: 4px solid #909399;
}

.mind-node-card.status-draft {
  border-left-color: #909399;
}

.mind-node-card.status-approved {
  border-left-color: #67c23a;
}

.mind-node-card.status-closed {
  border-left-color: #e6a23c;
}

.collapse-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.node-title {
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.kind-root .node-title,
.kind-project .node-title {
  font-size: 15px;
}

.node-sub {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.85;
}

.node-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.meta-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.6;
  background: #f4f4f5;
  color: #606266;
}

.meta-tag.type {
  background: #ecf5ff;
  color: #409eff;
}

.meta-tag.priority {
  background: #fdf6ec;
  color: #e6a23c;
}

.meta-tag.status {
  background: #f0f9eb;
  color: #67c23a;
}

.meta-tag.source {
  background: #fef0f0;
  color: #f56c6c;
}

.meta-tag.cases {
  background: #f4f4f5;
  color: #303133;
}

.mind-children {
  display: flex;
  align-items: center;
  margin-left: 8px;
}

.connector {
  width: 28px;
  height: 2px;
  background: #c0c4cc;
  flex-shrink: 0;
}

.children-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-left: 4px;
  border-left: 2px solid #dcdfe6;
}

.children-list > .mind-node-wrap {
  position: relative;
}

.children-list > .mind-node-wrap::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 50%;
  width: 6px;
  height: 2px;
  background: #dcdfe6;
}
</style>
