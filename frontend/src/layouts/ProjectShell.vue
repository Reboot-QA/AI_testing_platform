<template>
  <div class="project-shell">
    <GlobalRail
      mode="project"
      :active-domain="state.domain"
      :user-name="userName"
      @nav-domain="switchDomain"
      @nav-home="goHome"
      @nav-projects="goProjects"
      @nav-profile="onNavProfile"
      @nav-logout="onNavLogout"
    />

    <div class="ws-col">
      <header v-if="store.currentProject" class="ws-project-bar">
        <span class="ws-project-name" :title="store.currentProject.name">
          {{ store.currentProject.name }}
        </span>
        <div class="ws-env">
          <el-select
            :model-value="store.currentEnvironmentId ?? undefined"
            filterable
            clearable
            size="small"
            placeholder="选择环境"
            class="ws-env-select"
            @change="onEnvChange"
          >
            <template #prefix>
              <el-icon class="ws-env-icon"><Connection /></el-icon>
            </template>
            <el-option v-for="e in store.environments" :key="e.id" :label="e.name" :value="e.id">
              <span class="env-option">
                <span class="env-option-badge">{{ envBadge(e.name) }}</span>
                <span class="env-option-name">{{ e.name }}</span>
              </span>
            </el-option>
          </el-select>
          <el-button
            size="small"
            class="env-manage-btn"
            title="环境管理"
            @click="envDrawerVisible = true"
          >
            <el-icon><Operation /></el-icon>
          </el-button>
        </div>
      </header>
      <div class="ws-inner">
        <WorkspaceTree
          v-if="state.domain !== 'settings'"
          :key="`tree-${projectId}`"
          :domain="state.domain"
          :biz="state.biz"
          :section="state.section"
          :project-id="String(projectId)"
          @nav-auto="({ biz, section }) => switchBiz(biz, section)"
          @nav-section="setSection"
        />
        <div class="ws-body">
          <WorkspaceMain
            :key="`main-${projectId}`"
            :domain="state.domain"
            :biz="state.biz"
            :section="state.section"
            :open="state.open"
            :project-id="projectId"
            @nav-settings="setSettings"
            @nav-section="setSection"
          />
        </div>
      </div>
    </div>

    <el-drawer
      v-model="envDrawerVisible"
      title="环境管理"
      direction="rtl"
      :size="envDrawerSize"
      destroy-on-close
      class="env-manage-drawer"
      @close="onEnvDrawerClose"
    >
      <div class="env-drawer-body ax-workspace">
        <EnvManage
          show-close-action
          :initial-env-id="store.currentEnvironmentId"
          @close="envDrawerVisible = false"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { useUserStore } from '@/stores/user'
import { useWorkspaceStore } from '@/stores/workspace'
import { useWorkspaceHash } from '@/composables/useWorkspaceHash'
import { provideResolvableVars } from '@/composables/useResolvableVars'
import GlobalRail from '@/components/shell/GlobalRail.vue'
import WorkspaceTree from '@/components/shell/WorkspaceTree.vue'
import WorkspaceMain from '@/components/shell/WorkspaceMain.vue'
import EnvManage from '@/views/apifox/sections/EnvManage.vue'

const router = useRouter()
const userStore = useUserStore()
const store = useWorkspaceStore()
const userName = computed(() => userStore.user?.username ?? '')

const projectId = useRouteParamId()
const { state, switchDomain, switchBiz, setSection, setSettings } = useWorkspaceHash()

// {{变量}} 可解析集合（供 VarInput 按联动性上色 + hover 提示）：随项目/当前环境变化重取
provideResolvableVars(
  projectId,
  computed(() => store.currentEnvironmentId ?? null),
)

// 环境管理抽屉（复用 EnvManage 全套编辑）：关闭后刷新环境，让顶部下拉/调试前置URL拿到最新
const envDrawerVisible = ref(false)
const envDrawerSize = 'var(--ax-drawer-width-xl)'
function onEnvDrawerClose() {
  if (projectId.value) store.loadEnvironments(projectId.value)
}

function onEnvChange(value: number | undefined) {
  store.setCurrentEnvironment(value ?? null)
}

function envBadge(name: string) {
  return (name.trim().charAt(0) || '环').toUpperCase()
}

function goHome() {
  router.push({ path: '/hub', hash: '#view=home' })
}

function goProjects() {
  router.push({ path: '/hub', hash: '#view=projects' })
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

watch(
  projectId,
  async (id) => {
    if (!id) {
      router.push('/hub')
      return
    }
    try {
      await Promise.all([store.loadProject(id), store.loadEnvironments(id)])
    } catch {
      ElMessage.error('项目不存在或无访问权限')
      router.push('/hub')
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.project-shell {
  display: flex;
  height: 100vh;
  background: var(--ax-bg-subtle);
}

/* EnvManage 是 height:100% 两栏布局，抽屉 body 需撑满 */
.env-drawer-body {
  height: 100%;
  min-height: 0;
}

:deep(.env-manage-drawer .el-drawer__body) {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--ax-space-4);
  overflow: hidden;
}

.ws-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.ws-project-bar {
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  padding: var(--ax-space-1-5) var(--ax-space-3);
  background: var(--ax-bg);
  border-bottom: 1px solid var(--ax-border);
}

.ws-project-name {
  flex: 1;
  min-width: 0;
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ws-env {
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
}

.ws-env-select {
  width: 170px;
}

.ws-env-icon {
  color: var(--ax-text-tertiary);
}

.env-manage-btn {
  flex: none;
}

.env-option {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.env-option-badge {
  width: 22px;
  height: 22px;
  border-radius: var(--ax-radius);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--ax-tag-blue-bg);
  color: var(--ax-rail-active-bg);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.env-option-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ws-inner {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.ws-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: var(--ax-page-padding-y) var(--ax-page-padding-x);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ws-body > :deep(.ws-main) {
  flex: 1;
  min-height: 0;
}
</style>
