<template>
  <div class="system-shell">
    <GlobalRail
      mode="home"
      active-view="system"
      :user-name="userName"
      @nav-view="onNavView"
      @nav-home="goHome"
      @nav-projects="goProjects"
      @nav-profile="onNavProfile"
      @nav-logout="onNavLogout"
    />
    <div class="sys-col">
      <nav class="sys-menu">
        <div class="sys-title">系统管理</div>
        <div
          v-for="m in menu"
          :key="m.path"
          class="sys-item"
          :class="{ active: route.path === m.path }"
          @click="go(m.path)"
        >
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </div>
      </nav>
      <div class="sys-body">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import GlobalRail from '@/components/shell/GlobalRail.vue'
import type { HomeView } from '@/types/shell'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const userName = computed(() => userStore.user?.username ?? '')

const ALL = [
  { label: '全局设置', path: '/system/settings', icon: 'Setting', perm: 'system_settings' },
  { label: '用户管理', path: '/system/users', icon: 'User', perm: 'system_users' },
  {
    label: '部门权限',
    path: '/system/departments',
    icon: 'OfficeBuilding',
    perm: 'system_departments',
  },
  { label: '权限管理', path: '/system/permissions', icon: 'Key', perm: 'system_permissions' },
  { label: '日志监控', path: '/system/logs', icon: 'Document', perm: 'system_logs' },
  { label: '错误日志', path: '/system/error-logs', icon: 'Warning', perm: 'system_error_logs' },
]
const menu = computed(() => ALL.filter((m) => userStore.hasPermission(m.perm)))

function go(path: string) {
  if (route.path !== path) router.push(path)
}
function goHome() {
  router.push({ path: '/hub', hash: '#view=home' })
}
function goProjects() {
  router.push({ path: '/hub', hash: '#view=projects' })
}
function onNavView(view: HomeView) {
  if (view === 'system') return
  router.push({ path: '/hub', hash: `#view=${view}` })
}
async function onNavLogout() {
  try {
    await ElMessageBox.confirm('确认退出登录？', '账号', {
      confirmButtonText: '退出登录',
      cancelButtonText: '取消',
    })
    userStore.logout()
    router.push('/login')
  } catch {
    // 取消
  }
}

function onNavProfile() {
  router.push('/account')
}
</script>

<style scoped>
.system-shell {
  display: flex;
  height: 100vh;
  background: var(--ax-bg-subtle);
}

.sys-col {
  flex: 1;
  min-width: 0;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.sys-menu {
  width: var(--ax-settings-nav-width);
  min-width: var(--ax-settings-nav-width);
  flex: none;
  background: var(--ax-bg);
  border-right: 1px solid var(--ax-border);
  padding: var(--ax-space-2-5) var(--ax-space-2);
  overflow-x: hidden;
  overflow-y: auto;
}

.sys-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-nav-group-size);
  line-height: var(--ax-nav-group-line);
  color: var(--ax-text-placeholder);
  padding: var(--ax-space-1-5) var(--ax-space-2) var(--ax-space-2);
}

.sys-item {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  height: var(--ax-nav-item-height);
  min-width: 0;
  padding: var(--ax-space-0) var(--ax-space-2-5);
  overflow: hidden;
  border-radius: var(--ax-radius-sm);
  cursor: pointer;
  color: var(--ax-text-secondary);
  font-size: var(--ax-nav-secondary-size);
  line-height: var(--ax-nav-secondary-line);
  transition: background var(--ax-transition);
}

.sys-item .el-icon {
  flex: none;
}

.sys-item span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sys-item:hover {
  background: var(--ax-bg-subtle);
}

.sys-item.active {
  background: var(--ax-tag-blue-bg);
  color: var(--ax-rail-active-bg);
  font-weight: 600;
}

.sys-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: var(--ax-page-padding-y) var(--ax-page-padding-x);
  overflow: auto;
}
</style>
