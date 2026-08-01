<template>
  <div class="project-shell">
    <GlobalRail
      mode="project"
      :active-domain="domain"
      :visible-domains="visibleDomains"
      :ai-tasks-dot="aiTasksDot"
      :user-name="userName"
      @nav-domain="navigateDomain"
      @nav-home="goHome"
      @nav-projects="goProjects"
      @nav-profile="onNavProfile"
      @nav-logout="onNavLogout"
    />

    <div class="ws-col">
      <header
        v-if="store.currentProject"
        class="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background px-5 shadow-sm"
      >
        <span
          class="min-w-0 flex-1 truncate text-lg font-semibold leading-none text-foreground"
          :title="store.currentProject.name"
        >
          {{ store.currentProject.name }}
        </span>
        <div class="flex shrink-0 items-center gap-1">
          <el-select
            :model-value="store.currentEnvironmentId ?? undefined"
            filterable
            clearable
            size="small"
            placeholder="选择环境"
            class="w-44"
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
            class="shrink-0"
            title="环境管理"
            @click="envDrawerVisible = true"
          >
            <el-icon><Operation /></el-icon>
          </el-button>
        </div>
      </header>
      <!-- 项目校验通过后才挂子面板：否则每个面板各自发一次项目内请求，会连弹多条「项目不存在」 -->
      <div v-if="projectReady" class="ws-inner">
        <WorkspaceTree
          v-if="domain !== 'settings'"
          :key="`tree-${projectId}`"
          :domain="domain"
          :project-id="String(projectId)"
        />
        <div class="ws-body">
          <!-- 保留工作区样式作用域；路由只负责页面切换，不应丢失 panel-head 等公共规范。 -->
          <div class="ws-main">
            <RouterView v-if="!currentMeta?.managerOnly || isManager" :key="route.fullPath" />
          </div>
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
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { hubAiTasksApi } from '@/api/hubAiTasks'
import { apifoxApi } from '@/api/apifox'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { useAiGenerateStore } from '@/stores/aiGenerate'
import { useRequirementExtractStore } from '@/stores/requirementExtract'
import { useUserStore } from '@/stores/user'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { useWorkspaceStore } from '@/stores/workspace'
import { firstWorkspaceRoute, workspaceDomains, workspaceMeta } from '@/router/workspace'
import { provideResolvableVars } from '@/composables/useResolvableVars'
import GlobalRail from '@/components/shell/GlobalRail.vue'
import WorkspaceTree from '@/components/shell/WorkspaceTree.vue'
import EnvManage from '@/views/apifox/sections/EnvManage.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const functionalAiStore = useAiGenerateStore()
const requirementExtractStore = useRequirementExtractStore()
const aiGenStore = useApifoxAiGenerateStore()
const store = useWorkspaceStore()
const userName = computed(() => userStore.user?.username ?? '')
const remoteHubAiTaskCounts = ref({ requirement: 0, functional: 0 })
const remoteApifoxAiGenCount = ref(0)
// 轮询定时器：仅在“已知有活跃任务”时才转起来，任务收敛为 0 就自行停表，
// 避免不管有没有任务、只要人在工作区就无限轮询（对齐 AiGenJobsPanel / apifoxAiGenerate 的既有约定）。
let hubAiTaskPollTimer: ReturnType<typeof setInterval> | null = null
let hubAiTaskPollProjectId = 0

function localRequirementActiveForProject(projectId: number): boolean {
  return requirementExtractStore.extracting && requirementExtractStore.activeProjectId === projectId
}

function localFunctionalActiveForProject(projectId: number): boolean {
  return functionalAiStore.generating && functionalAiStore.activeProjectId === projectId
}

const aiTasksDot = computed(() => {
  const pid = projectReady.value ? Number(projectId.value) : 0
  if (!pid) return null

  const apifoxActive = Math.max(
    aiGenStore.activeCountForUserInProject(userName.value, pid),
    remoteApifoxAiGenCount.value,
  )
  let count = apifoxActive
  count += localRequirementActiveForProject(pid)
    ? Math.max(1, remoteHubAiTaskCounts.value.requirement)
    : remoteHubAiTaskCounts.value.requirement
  count += localFunctionalActiveForProject(pid)
    ? Math.max(1, remoteHubAiTaskCounts.value.functional)
    : remoteHubAiTaskCounts.value.functional
  return count || null
})

const projectId = useRouteParamId()
const currentMeta = computed(() => workspaceMeta(route))
const domain = computed(() => currentMeta.value?.domain ?? 'automation')
const visibleDomains = computed(() => workspaceDomains(userStore.hasPermission))
const isManager = computed(
  () => userStore.isAdmin || store.currentProject?.owner_id === userStore.user?.id,
)
function navigateDomain(nextDomain: typeof domain.value) {
  const name = firstWorkspaceRoute(userStore.hasPermission, nextDomain)
  if (name && projectId.value) void router.push({ name, params: { projectId: projectId.value } })
}

// 当前 projectId 是否已校验为「存在且当前账号可访问」（切换账号后 URL/内存里可能残留别人的项目）
const projectReady = ref(false)
// 校验通过前传 0，让下面的变量集合先不取数（load 对 falsy pid 直接置空）
const readyProjectId = computed(() => (projectReady.value ? projectId.value : 0))

// {{变量}} 可解析集合（供 VarInput 按联动性上色 + hover 提示）：随项目/当前环境变化重取
provideResolvableVars(
  readyProjectId,
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

// 侧边栏 AI 任务红点：仅统计当前项目（与 AI 任务概述页一致）
async function refreshRemoteHubAiTaskCount(id: number) {
  if (!id || !userName.value) {
    remoteHubAiTaskCounts.value = { requirement: 0, functional: 0 }
    remoteApifoxAiGenCount.value = 0
    stopHubAiTaskPolling()
    return
  }
  try {
    const [reqRunning, reqPending, funcRunning, funcPending, apifoxActive] = await Promise.all([
      hubAiTasksApi.listTasks(id, { task_type: 'requirement', status: 'running', page_size: 50 }),
      hubAiTasksApi.listTasks(id, { task_type: 'requirement', status: 'pending', page_size: 50 }),
      hubAiTasksApi.listTasks(id, { task_type: 'functional', status: 'running', page_size: 50 }),
      hubAiTasksApi.listTasks(id, { task_type: 'functional', status: 'pending', page_size: 50 }),
      apifoxApi.listActiveAiGenTasks(id),
    ])
    const isMine = (task: { creator_name?: string | null }) => task.creator_name === userName.value
    const requirement =
      reqRunning.items.filter(isMine).length + reqPending.items.filter(isMine).length
    const functional =
      funcRunning.items.filter(isMine).length + funcPending.items.filter(isMine).length
    remoteHubAiTaskCounts.value = { requirement, functional }
    remoteApifoxAiGenCount.value = apifoxActive.filter(isMine).length
    const stillActive =
      requirement > 0 ||
      functional > 0 ||
      remoteApifoxAiGenCount.value > 0 ||
      aiGenStore.hasActiveInProject(id) ||
      localFunctionalActiveForProject(id) ||
      localRequirementActiveForProject(id)
    if (stillActive) {
      ensureHubAiTaskPolling(id)
    } else {
      stopHubAiTaskPolling()
    }
  } catch {
    remoteHubAiTaskCounts.value = { requirement: 0, functional: 0 }
    remoteApifoxAiGenCount.value = 0
    stopHubAiTaskPolling()
  }
}

function stopHubAiTaskPolling() {
  if (hubAiTaskPollTimer) {
    clearInterval(hubAiTaskPollTimer)
    hubAiTaskPollTimer = null
  }
  hubAiTaskPollProjectId = 0
}

function ensureHubAiTaskPolling(id: number) {
  if (hubAiTaskPollTimer && hubAiTaskPollProjectId === id) return
  stopHubAiTaskPolling()
  hubAiTaskPollProjectId = id
  hubAiTaskPollTimer = setInterval(() => void refreshRemoteHubAiTaskCount(id), 4000)
}

watch(
  projectId,
  async (id) => {
    projectReady.value = false
    stopHubAiTaskPolling()
    remoteHubAiTaskCounts.value = { requirement: 0, functional: 0 }
    remoteApifoxAiGenCount.value = 0
    if (!id) {
      router.push('/hub')
      return
    }
    // 先单独校验项目（串行，不与环境并发）：不可访问时只弹下面一条提示，不叠多条 404
    try {
      await store.loadProject(id, true)
    } catch {
      store.clearCurrent()
      ElMessage.error('项目不存在或无访问权限')
      router.push('/hub')
      return
    }
    // 环境同样先于子面板就绪（部分面板在挂载时就读当前环境），取不到不阻断工作区
    try {
      await store.loadEnvironments(id)
    } catch {
      // 全局拦截器已提示
    }
    // 期间又切了项目：本次结果作废，交给后一次 watch 回调
    if (projectId.value !== id) return
    projectReady.value = true
    // 只查一次；查到活跃任务时函数内部会自己续上轮询，查不到就此打住，不常驻定时器
    void refreshRemoteHubAiTaskCount(Number(id))
  },
  { immediate: true },
)

watch(userName, () => {
  if (projectReady.value && projectId.value) {
    void refreshRemoteHubAiTaskCount(Number(projectId.value))
  }
})

watch(
  [projectReady, isManager, () => currentMeta.value?.managerOnly],
  ([ready, manager, managerOnly]) => {
    if (ready && managerOnly && !manager && projectId.value) {
      void router.replace({
        name: 'WorkspaceSettingsBasic',
        params: { projectId: projectId.value },
      })
    }
  },
  { immediate: true },
)

// 本地发起流式任务（生成用例/解析需求）时立即探一次远端，尽快让计数与本地状态对齐并续上轮询
watch(
  () =>
    localFunctionalActiveForProject(Number(projectId.value)) ||
    localRequirementActiveForProject(Number(projectId.value)) ||
    aiGenStore.hasActiveInProject(Number(projectId.value)),
  (active) => {
    if (active && projectReady.value && projectId.value) {
      void refreshRemoteHubAiTaskCount(Number(projectId.value))
    }
  },
)

onBeforeUnmount(() => {
  stopHubAiTaskPolling()
})
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

.ws-env-icon {
  color: var(--ax-text-tertiary);
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
