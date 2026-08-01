<template>
  <span class="node">
    <MethodTag v-if="node.type === 'endpoint'" :method="node.method" class="tree-method" />
    <el-icon v-else><Folder /></el-icon>
    <span class="node-title">
      <span class="node-label">{{ node.label }}</span>
      <span v-if="node.type === 'folder'" class="node-count">({{ node.endpointCount ?? 0 }})</span>
      <span
        v-if="node.type === 'endpoint' && caseCounts"
        class="case-count"
        :class="{ 'case-count--right': readonly }"
        title="该接口的用例数"
        >{{ caseCounts[Number(node.id)] ?? 0 }}</span
      >
      <span
        v-if="node.casesStale"
        class="stale-dot"
        title="接口契约已更新，已有用例可能过时，建议重新生成或复核"
        >●</span
      >
    </span>
    <el-icon v-if="!readonly" class="node-more" title="更多操作" @click.stop="handleMore">
      <MoreFilled />
    </el-icon>
  </span>
</template>

<script setup lang="ts">
import type { ApiTreeNode } from '@/composables/useApiTree'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const props = withDefaults(
  defineProps<{
    node: ApiTreeNode
    caseCounts?: Record<number, number>
    readonly?: boolean
  }>(),
  {
    caseCounts: undefined,
    readonly: false,
  },
)
const emit = defineEmits<{ more: [event: MouseEvent, node: ApiTreeNode] }>()

function handleMore(event: MouseEvent) {
  emit('more', event, props.node)
}
</script>

<style scoped>
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
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  flex: 1;
  min-width: 0;
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
</style>
