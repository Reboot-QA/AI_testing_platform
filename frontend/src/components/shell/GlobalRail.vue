<template>
  <aside class="global-rail">
    <button
      class="gr-logo cursor-pointer"
      type="button"
      aria-label="返回首页"
      @click="emit('navHome')"
    >
      <img src="/brand-logo.png" alt="" />
    </button>

    <template v-if="mode === 'home'">
      <RailButton label="首页" :active="activeView === 'home'" @click="emit('navView', 'home')">
        <template #icon
          ><el-icon><HomeFilled /></el-icon
        ></template>
      </RailButton>
      <RailButton
        label="项目"
        :active="activeView === 'projects'"
        @click="emit('navView', 'projects')"
      >
        <template #icon
          ><el-icon><Grid /></el-icon
        ></template>
      </RailButton>
      <RailButton
        label="动态"
        :active="activeView === 'activity'"
        :dot="activityDot"
        @click="emit('navView', 'activity')"
      >
        <template #icon
          ><el-icon><Bell /></el-icon
        ></template>
      </RailButton>
      <div class="gr-spacer" />
      <RailButton
        v-if="canSystem"
        label="系统"
        :active="activeView === 'system'"
        @click="emit('navView', 'system')"
      >
        <template #icon
          ><el-icon><Setting /></el-icon
        ></template>
      </RailButton>
    </template>

    <template v-else>
      <RailButton label="项目" @click="emit('navProjects')">
        <template #icon
          ><el-icon><Grid /></el-icon
        ></template>
      </RailButton>
      <div class="gr-divider" />
      <RailButton
        label="需求"
        :active="activeDomain === 'requirements'"
        @click="emit('navDomain', 'requirements')"
      >
        <template #icon
          ><el-icon><Document /></el-icon
        ></template>
      </RailButton>
      <RailButton
        label="功能"
        :active="activeDomain === 'functional'"
        @click="emit('navDomain', 'functional')"
      >
        <template #icon
          ><el-icon><List /></el-icon
        ></template>
      </RailButton>
      <RailButton
        label="自动化"
        :active="activeDomain === 'automation'"
        @click="emit('navDomain', 'automation')"
      >
        <template #icon
          ><el-icon><VideoPlay /></el-icon
        ></template>
      </RailButton>
      <div class="gr-spacer" />
      <RailButton
        label="设置"
        :active="activeDomain === 'settings'"
        @click="emit('navDomain', 'settings')"
      >
        <template #icon
          ><el-icon><Setting /></el-icon
        ></template>
      </RailButton>
    </template>

    <el-dropdown trigger="click" placement="right-end" @command="onUserCommand">
      <RailButton class="gr-user">
        <template #icon
          ><span class="gr-avatar">{{ avatarText }}</span></template
        >
      </RailButton>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="profile">个人资料</el-dropdown-item>
          <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import RailButton from './RailButton.vue'
import type { HomeView, WorkspaceDomain } from '@/types/shell'

const props = withDefaults(
  defineProps<{
    mode: 'home' | 'project'
    activeView?: HomeView
    activeDomain?: WorkspaceDomain
    activityDot?: number | null
    canSystem?: boolean
    userName?: string
  }>(),
  {
    activeView: 'home',
    activeDomain: 'automation',
    activityDot: null,
    canSystem: true,
    userName: '',
  },
)

const emit = defineEmits<{
  navView: [view: HomeView]
  navDomain: [domain: WorkspaceDomain]
  navHome: []
  navProjects: []
  navProfile: []
  navLogout: []
}>()

function onUserCommand(command: string) {
  if (command === 'profile') {
    emit('navProfile')
    return
  }
  if (command === 'logout') {
    emit('navLogout')
  }
}

const avatarText = computed(() => (props.userName || 'A').charAt(0).toUpperCase())
</script>

<style scoped>
.global-rail {
  width: var(--ax-rail-width);
  flex: none;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ax-gap-xs);
  padding: var(--ax-space-2-5) var(--ax-space-0) var(--ax-space-3);
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--ax-rail-bg);
  border-right: 1px solid var(--ax-rail-border);
  z-index: 20;
}

.global-rail > :deep(.gr-btn) {
  flex: none;
}

.gr-logo {
  width: 36px;
  height: 36px;
  flex: none;
  overflow: hidden;
  border: 1px solid var(--ax-rail-border);
  border-radius: 9px;
  margin-bottom: var(--ax-gap-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
}

.gr-logo img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.gr-spacer {
  flex: 1;
  min-height: var(--ax-space-1);
}

.gr-divider {
  width: 24px;
  height: 1px;
  background: var(--ax-rail-border);
  margin: var(--ax-space-1) 0;
}

.gr-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #2b6cff, #722ed1);
  color: #fff;
  font-size: var(--ax-font-xs);
  font-weight: 600;
}

:deep(.gr-user.el-dropdown) {
  display: flex;
}
</style>
