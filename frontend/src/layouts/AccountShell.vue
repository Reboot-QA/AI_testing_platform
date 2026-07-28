<template>
  <div class="account-shell">
    <GlobalRail
      mode="home"
      :user-name="userName"
      @nav-view="onNavView"
      @nav-home="goHome"
      @nav-projects="goProjects"
      @nav-profile="onNavProfile"
      @nav-logout="onNavLogout"
    />
    <main class="account-main">
      <UserProfile />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import GlobalRail from '@/components/shell/GlobalRail.vue'
import UserProfile from '@/views/UserProfile.vue'
import type { HomeView } from '@/types/shell'

const router = useRouter()
const userStore = useUserStore()
const userName = computed(() => userStore.user?.username ?? '')

function goHome() {
  router.push({ path: '/hub', hash: '#view=home' })
}

function goProjects() {
  router.push({ path: '/hub', hash: '#view=projects' })
}

function onNavView(view: HomeView) {
  router.push({ path: '/hub', hash: `#view=${view}` })
}

function onNavProfile() {
  if (router.currentRoute.value.path !== '/account') {
    router.push('/account')
  }
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
</script>

<style scoped>
.account-shell {
  display: flex;
  height: 100vh;
  background: var(--ax-bg-subtle);
}

.account-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: 14px 16px;
  overflow: auto;
}
</style>
