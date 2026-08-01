<template>
  <div class="hub-home">
    <GlobalRail
      mode="home"
      :active-view="view"
      :can-system="canSeeSystem"
      :can-home="userStore.hasPermission('dashboard')"
      :can-projects="userStore.hasPermission('projects')"
      :user-name="userName"
      @nav-view="setView"
      @nav-home="onNavHome"
      @nav-projects="setView('projects')"
      @nav-profile="onNavProfile"
      @nav-logout="onNavLogout"
    />
    <main class="hub-main">
      <HomeView v-if="view === 'home'" @go-projects="onGoProjects" />
      <ProjectsView v-else-if="view === 'projects'" :auto-create="pendingProjectCreate" />
      <ActivityView v-else-if="view === 'activity'" />
      <SystemView v-else-if="view === 'system'" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { SYSTEM_VIEW_PERMS } from '@/config/menus'
import { resolveDefaultHubView } from '@/router/landing'
import { useHomeHash } from '@/composables/useHomeHash'
import GlobalRail from '@/components/shell/GlobalRail.vue'
import HomeView from '@/views/hub/HomeView.vue'
import ProjectsView from '@/views/hub/ProjectsView.vue'
import ActivityView from '@/views/hub/ActivityView.vue'
import SystemView from '@/views/hub/SystemView.vue'

const router = useRouter()
const userStore = useUserStore()
const userName = computed(() => userStore.user?.username ?? '')
// 无任一系统权限时，隐藏左侧「系统」入口；SystemView 自身对 #view=system 深链再做空状态兜底
const canSeeSystem = computed(() => SYSTEM_VIEW_PERMS.some((p) => userStore.hasPermission(p)))
const { view, setView } = useHomeHash()

onMounted(() => {
  if (view.value === 'home' && !userStore.hasPermission('dashboard')) {
    setView(resolveDefaultHubView(userStore.hasPermission, canSeeSystem.value))
  }
})

// 首页快捷入口在无项目时会带 create 意图跳来，项目列表挂载后自动弹「新建项目」
const pendingProjectCreate = ref(false)

function onNavHome() {
  setView(resolveDefaultHubView(userStore.hasPermission, canSeeSystem.value))
}

function onGoProjects(options?: { create?: boolean }) {
  pendingProjectCreate.value = !!options?.create
  setView('projects')
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
.hub-home {
  display: flex;
  height: 100vh;
  background: var(--ax-bg-subtle);
}

.hub-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: var(--ax-page-padding-y) var(--ax-page-padding-x);
  overflow: hidden;
}
</style>
