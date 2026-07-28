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
            :key="m.key"
            class="menu-item"
            :class="{ active: open === m.key }"
            @click="emit('nav', m.key)"
          >
            <span>{{ m.label }}</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="settings-body">
      <ProjectSettings v-if="open === 'basic'" />
      <ProjectScriptsPanel v-else-if="open === 'scripts'" :project-id="projectId" />
      <ProjectSqlScriptsPanel v-else-if="open === 'sql-scripts'" :project-id="projectId" />
      <DatasetPanel v-else-if="open === 'datasets'" />
      <ProjectDatabasesPanel v-else-if="open === 'databases'" />
      <NotifyConfigPanel v-else-if="open === 'notify'" :project-id="projectId" />
      <EnvManage v-else-if="open === 'envs'" />
      <ImportDataPanel v-else-if="open === 'import'" />
      <ExportDataPanel v-else-if="open === 'export'" />
      <ProjectMembersPanel v-else-if="open === 'members' && isManager" :project-id="projectId" />
      <el-empty v-else description="无权限访问该设置页" :image-size="64" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { SettingsSection } from '@/types/shell'
import { useUserStore } from '@/stores/user'
import { useWorkspaceStore } from '@/stores/workspace'
import ProjectSettings from '@/views/apifox/sections/ProjectSettings.vue'
import EnvManage from '@/views/apifox/sections/EnvManage.vue'
import ImportDataPanel from '@/components/apifox/import-export/ImportDataPanel.vue'
import ExportDataPanel from '@/components/apifox/import-export/ExportDataPanel.vue'
import ProjectScriptsPanel from '@/components/apifox/script/ProjectScriptsPanel.vue'
import ProjectSqlScriptsPanel from '@/components/apifox/script/ProjectSqlScriptsPanel.vue'
import DatasetPanel from '@/views/apifox/sections/DatasetPanel.vue'
import ProjectDatabasesPanel from '@/components/apifox/project/ProjectDatabasesPanel.vue'
import NotifyConfigPanel from '@/components/apifox/project/NotifyConfigPanel.vue'
import ProjectMembersPanel from '@/components/apifox/project/ProjectMembersPanel.vue'

const props = defineProps<{ open: SettingsSection; projectId: number }>()
const emit = defineEmits<{ nav: [open: SettingsSection] }>()

const userStore = useUserStore()
const workspace = useWorkspaceStore()

// 与 ProjectSettings / 后端 is_project_manager 一致：管理员或项目负责人可见「成员管理」
const isManager = computed(
  () => userStore.isAdmin || workspace.currentProject?.owner_id === userStore.user?.id,
)

interface MenuLeaf {
  key: SettingsSection
  label: string
}
interface MenuGroup {
  title: string
  icon: string
  items: MenuLeaf[]
}

const MENU_GROUPS: MenuGroup[] = [
  {
    title: '系统设置',
    icon: 'Setting',
    items: [
      { key: 'basic', label: '基本信息' },
      { key: 'notify', label: '失败通知' },
      { key: 'members', label: '成员管理' },
      { key: 'envs', label: '环境管理' },
    ],
  },
  {
    title: '数据管理',
    icon: 'Coin',
    items: [
      { key: 'import', label: '导入数据' },
      { key: 'export', label: '导出数据' },
    ],
  },
  {
    title: '项目资源',
    icon: 'FolderOpened',
    items: [
      { key: 'scripts', label: '脚本库' },
      { key: 'sql-scripts', label: 'SQL 脚本' },
      { key: 'datasets', label: '数据集' },
      { key: 'databases', label: '数据库' },
    ],
  },
]

const menuGroups = computed(() =>
  MENU_GROUPS.map((grp) => ({
    ...grp,
    items: grp.items.filter((m) => m.key !== 'members' || isManager.value),
  })).filter((grp) => grp.items.length > 0),
)

// 项目已加载且无权限却深链到 members 时回退到基本信息（避免 currentProject 未就绪时误踢负责人）
watch(
  () => [props.open, isManager.value, workspace.currentProject] as const,
  ([open, manager, project]) => {
    if (open === 'members' && project && !manager) emit('nav', 'basic')
  },
  { immediate: true },
)
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
