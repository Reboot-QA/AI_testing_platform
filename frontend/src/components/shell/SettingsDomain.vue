<template>
  <div class="settings-domain">
    <nav class="settings-menu">
      <div v-for="grp in menuGroups" :key="grp.title" class="menu-group">
        <div class="menu-group-title">
          <el-icon><component :is="grp.icon" /></el-icon>
          <span>{{ grp.title }}</span>
        </div>
        <div class="menu-group-items">
          <div
            v-for="m in grp.items"
            :key="m.name"
            class="menu-item"
            :class="{ active: route.name === m.name }"
            @click="go(m.name)"
          >
            <span>{{ m.label }}</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="settings-body">
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useWorkspaceStore } from '@/stores/workspace'
import { workspaceMenuGroups } from '@/router/workspace'
const route = useRoute()
const router = useRouter()

const userStore = useUserStore()
const workspace = useWorkspaceStore()

// 与 ProjectSettings / 后端 is_project_manager 一致：管理员或项目负责人可见「成员管理」
const isManager = computed(
  () => userStore.isAdmin || workspace.currentProject?.owner_id === userStore.user?.id,
)

const menuGroups = computed(() =>
  workspaceMenuGroups('settings', userStore.hasPermission, isManager.value),
)

function go(name: string) {
  void router.push({ name, params: { projectId: route.params.projectId } })
}
</script>

<style scoped>
.settings-domain {
  display: flex;
  height: 100%;
  min-height: 0;
}

.settings-menu {
  width: var(--ax-settings-nav-width);
  min-width: var(--ax-settings-nav-width);
  flex: none;
  border-right: 1px solid var(--ax-border);
  padding: var(--ax-space-2);
  overflow-x: hidden;
  overflow-y: auto;
}

.menu-group + .menu-group {
  margin-top: var(--ax-space-2);
}

.menu-group-title {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  height: var(--ax-nav-item-height);
  min-width: 0;
  padding: var(--ax-space-0) var(--ax-space-2);
  color: var(--ax-text-tertiary);
  font-size: var(--ax-nav-secondary-size);
  line-height: var(--ax-nav-secondary-line);
  font-weight: 600;
  cursor: default;
  user-select: none;
}

.menu-group-title .el-icon {
  flex: none;
  font-size: 14px;
}

.menu-group-title span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-group-items {
  display: flex;
  flex-direction: column;
  padding-left: var(--ax-space-5);
}

.menu-item {
  display: flex;
  align-items: center;
  height: var(--ax-nav-item-height);
  min-width: 0;
  padding: var(--ax-space-0) var(--ax-space-2);
  overflow: hidden;
  border-radius: var(--ax-radius-sm);
  cursor: pointer;
  color: var(--ax-text-secondary);
  font-size: var(--ax-nav-secondary-size);
  line-height: var(--ax-nav-secondary-line);
  transition:
    background var(--ax-transition),
    color var(--ax-transition);
}

.menu-item span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-item:hover {
  background: var(--ax-bg-subtle);
  color: var(--ax-text);
}

.menu-item.active {
  background: var(--ax-tag-blue-bg);
  color: var(--ax-rail-active-bg);
  font-weight: 600;
}

.settings-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: var(--ax-page-padding-y) var(--ax-page-padding-x);
  overflow: auto;
}
</style>
