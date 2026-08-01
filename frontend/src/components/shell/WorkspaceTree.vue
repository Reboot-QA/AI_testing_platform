<template>
  <div class="tree-panel">
    <div class="tree-scroll">
      <template v-for="group in groups" :key="group.title || 'root'">
        <button
          v-if="group.title"
          type="button"
          class="tnode tnode--group"
          @click="toggleGroup(group.title)"
        >
          <el-icon v-if="group.icon" class="tn-ic"><component :is="group.icon" /></el-icon>
          <span class="tn-label">{{ group.title }}</span>
          <el-icon class="tn-arrow">
            <ArrowDown v-if="isGroupExpanded(group.title)" />
            <ArrowRight v-else />
          </el-icon>
        </button>
        <div
          v-show="!group.title || isGroupExpanded(group.title)"
          class="grp-items"
          :class="{ 'grp-items--nested': !!group.title }"
        >
          <button
            v-for="page in group.items"
            :key="page.name"
            type="button"
            class="tnode"
            :class="{ active: route.name === page.name }"
            @click="go(page.name)"
          >
            <el-icon class="tn-ic"><component :is="page.icon" /></el-icon>
            <span class="tn-label">{{ page.label }}</span>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { WorkspaceDomain } from '@/types/shell'
import { workspaceMenuGroups } from '@/router/workspace'
import { useUserStore } from '@/stores/user'

const props = defineProps<{
  domain: WorkspaceDomain
  projectId: string
}>()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const groups = computed(() => workspaceMenuGroups(props.domain, userStore.hasPermission))
const expandedGroups = ref<Set<string>>(new Set())

watch(
  [() => props.domain, groups],
  () => {
    expandedGroups.value = new Set(
      groups.value.flatMap((group) => (group.title ? [group.title] : [])),
    )
  },
  { immediate: true },
)

function isGroupExpanded(title: string): boolean {
  return expandedGroups.value.has(title)
}

function toggleGroup(title: string): void {
  const next = new Set(expandedGroups.value)
  if (next.has(title)) next.delete(title)
  else next.add(title)
  expandedGroups.value = next
}

function go(name: string): void {
  void router.push({ name, params: { projectId: props.projectId } })
}
</script>

<style scoped>
.tree-panel {
  width: var(--ax-workspace-nav-width);
  min-width: var(--ax-workspace-nav-width);
  flex: none;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--ax-bg);
  border-right: 1px solid var(--ax-border);
}

.tree-scroll {
  height: 100%;
  overflow-y: auto;
  padding: var(--ax-space-1) var(--ax-space-2) var(--ax-space-3);
}

.grp-items {
  display: flex;
  flex-direction: column;
}

.grp-items--nested {
  padding-left: var(--ax-space-5);
}

.tnode {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  width: 100%;
  height: var(--ax-nav-item-height);
  min-width: 0;
  padding: 0 var(--ax-space-2);
  overflow: hidden;
  border: 0;
  border-radius: var(--ax-radius-sm);
  background: transparent;
  color: var(--ax-text-tertiary);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.tnode:hover {
  background: var(--ax-bg-subtle);
  color: var(--ax-text);
}

.tnode.active {
  background: var(--ax-tag-blue-bg);
  color: var(--ax-rail-active-bg);
  font-weight: 600;
}

.tn-ic,
.tn-arrow {
  flex: none;
  font-size: 14px;
}

.tn-arrow {
  margin-left: auto;
  font-size: 12px;
  color: var(--ax-text-placeholder);
}

.tn-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-nav-secondary-size);
  line-height: var(--ax-nav-secondary-line);
}
</style>
