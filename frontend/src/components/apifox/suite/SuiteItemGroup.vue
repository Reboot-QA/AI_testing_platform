<template>
  <div class="si-group">
    <div class="group-head" @click="collapsed = !collapsed">
      <el-icon class="group-caret" :class="{ 'group-caret--collapsed': collapsed }">
        <ArrowDown />
      </el-icon>
      <template v-if="group.kind === 'case'">
        <span class="group-name" :title="group.name">{{ group.name }}</span>
        <MethodTag :method="group.method" class="group-method" />
        <span class="group-path" :title="group.path">{{ group.path }}</span>
      </template>
      <template v-else>
        <span class="group-name">测试场景</span>
      </template>
      <span class="group-count" :title="`已启用 ${enabledCount} / 共 ${group.items.length}`">
        {{ enabledCount }}<span class="group-count-sep">/</span>{{ group.items.length }}
      </span>
    </div>

    <VueDraggable
      v-show="!collapsed"
      :model-value="group.items"
      handle=".drag-handle"
      :animation="150"
      ghost-class="suite-item-ghost"
      @update:model-value="(v: SuiteEditorItem[]) => $emit('sort', v)"
    >
      <div v-for="(it, i) in group.items" :key="it._uid" class="suite-item">
        <span class="si-index">{{ startIndex + i + 1 }}</span>
        <span class="drag-handle" title="拖拽调整组内顺序" @click.stop>
          <el-icon><Rank /></el-icon>
        </span>
        <el-switch v-model="it.enabled" size="small" />
        <span class="si-name" :class="{ 'si-gone': !it.target_name }">
          {{ it.target_name || '(目标已删除，建议移除)' }}
        </span>
        <el-button link type="danger" size="small" class="si-remove" @click="$emit('remove', it)">
          移除
        </el-button>
      </div>
    </VueDraggable>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDown, Rank } from '@element-plus/icons-vue'
import { VueDraggable } from 'vue-draggable-plus'
import type { SuiteEditorItem } from '@/types/apifox'
import type { SuiteItemGroup } from '@/composables/useSuiteItemGroups'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const props = defineProps<{ group: SuiteItemGroup; startIndex: number }>()

defineEmits<{ sort: [items: SuiteEditorItem[]]; remove: [item: SuiteEditorItem] }>()

const collapsed = ref(false)

const enabledCount = computed(() => props.group.items.filter((it) => it.enabled !== false).length)
</script>

<style scoped>
.si-group {
  margin-bottom: var(--ax-space-1);
}

.group-head {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  padding: var(--ax-space-1) var(--ax-space-2);
  border-radius: 4px;
  cursor: pointer;
  background: var(--ax-bg-subtle);
}

.group-head:hover {
  background: var(--ax-bg-hover);
}

.group-caret {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-tertiary);
  transition: transform 0.15s;
}

.group-caret--collapsed {
  transform: rotate(-90deg);
}

.group-name {
  flex-shrink: 0;
  max-width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text);
}

.group-method {
  flex-shrink: 0;
}

.group-path {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: Consolas, Monaco, monospace;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-tertiary);
}

.group-count {
  flex-shrink: 0;
  margin-left: auto;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  font-variant-numeric: tabular-nums;
}

.group-count-sep {
  margin: 0 1px;
  color: var(--ax-text-placeholder);
}

.suite-item {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  padding: var(--ax-space-1) var(--ax-space-2) var(--ax-space-1) var(--ax-space-4);
  border-radius: 4px;
  font-size: var(--ax-font-xs);
  line-height: var(--ax-leading-compact);
}

.suite-item:hover {
  background: var(--ax-bg-hover);
}

.si-index {
  flex-shrink: 0;
  width: 18px;
  text-align: right;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
  font-variant-numeric: tabular-nums;
}

.drag-handle {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  font-size: var(--ax-font-sm);
  cursor: grab;
  color: var(--ax-text-placeholder);
}

.drag-handle:active {
  cursor: grabbing;
}

.suite-item :deep(.el-switch) {
  height: auto;
}

.si-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
  font-weight: 400;
  color: var(--ax-text);
}

.si-gone {
  color: var(--ax-danger);
}

.suite-item :deep(.si-remove.el-button.is-link) {
  flex-shrink: 0;
  padding: 0 var(--ax-space-1);
  font-size: var(--ax-font-xs);
  height: auto;
}

:global(.suite-item-ghost) {
  opacity: 0.45;
  background: var(--ax-bg-hover);
  border-radius: 4px;
}
</style>
