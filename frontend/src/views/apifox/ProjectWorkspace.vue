<template>
  <div class="ax-workspace workspace">
    <div class="ws-header">
      <el-button link @click="backToWorkbench">
        <el-icon><ArrowLeft /></el-icon> 工作台
      </el-button>
      <el-divider direction="vertical" />
      <el-select
        :model-value="projectId"
        size="small"
        filterable
        class="proj-switch"
        @change="switchProject"
      >
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="String(p.id)" />
      </el-select>

      <div class="spacer" />

      <span class="env-label">环境</span>
      <el-select
        :model-value="store.currentEnvironmentId"
        size="small"
        clearable
        placeholder="选择环境"
        class="env-switch"
        @change="store.setCurrentEnvironment"
      >
        <el-option v-for="e in store.environments" :key="e.id" :label="e.name" :value="e.id" />
      </el-select>
    </div>

    <el-tabs v-model="activeTab" class="ws-tabs" @tab-change="onTabChange">
      <el-tab-pane v-for="s in sections" :key="s.key" :label="s.label" :name="s.key" />
    </el-tabs>

    <div class="ws-content">
      <router-view :key="projectId" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { projectApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'

const route = useRoute()
const router = useRouter()
const store = useWorkspaceStore()

const sections = [
  { key: 'apis', label: '接口管理' },
  { key: 'datamodels', label: '数据模型' },
  { key: 'tests', label: '自动化测试' },
  { key: 'reports', label: '测试报告' },
  { key: 'environments', label: '环境' },
  { key: 'settings', label: '项目设置' },
] as const

const projects = ref<Schemas['ProjectOut'][]>([])
const projectId = useRouteParamId()
const activeTab = computed(() => route.path.split('/').pop())

function currentTab(): string {
  const seg = route.path.split('/').pop()
  return sections.some((s) => s.key === seg) ? (seg as string) : 'apis'
}

function onTabChange(name: string | number) {
  router.push(`/apifox/project/${projectId.value}/${name}`)
}

function switchProject(id: string) {
  if (id && id !== projectId.value) router.push(`/apifox/project/${id}/${currentTab()}`)
}

function backToWorkbench() {
  router.push('/apifox')
}

onMounted(async () => {
  projects.value = await projectApi.list()
})

watch(
  projectId,
  async (id) => {
    if (!id) return
    try {
      await Promise.all([store.loadProject(id), store.loadEnvironments(id)])
    } catch {
      ElMessage.error('项目不存在或无访问权限')
      router.push('/apifox')
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.workspace {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.ws-header {
  display: flex;
  align-items: center;
  gap: var(--ax-gap);
  margin-bottom: var(--ax-gap);
  flex: none;
}

.proj-switch {
  width: 200px;
}

.spacer {
  flex: 1;
}

.env-label {
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
}

.env-switch {
  width: 180px;
}

.ws-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.ws-content > :deep(*) {
  height: 100%;
  min-height: 0;
}
</style>
