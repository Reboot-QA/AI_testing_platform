<template>
  <div class="workspace">
    <div class="ws-header">
      <el-button link @click="backToWorkbench">
        <el-icon><ArrowLeft /></el-icon> 工作台
      </el-button>
      <el-divider direction="vertical" />
      <span class="ws-title">{{ store.currentProjectName || '加载中…' }}</span>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane v-for="s in sections" :key="s.key" :label="s.label" :name="s.key" />
    </el-tabs>

    <router-view />
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useWorkspaceStore } from '@/stores/workspace'
import { useRecentProjects } from '@/composables/useRecentProjects'

const route = useRoute()
const router = useRouter()
const store = useWorkspaceStore()
const { record: recordRecent } = useRecentProjects()

const sections = [
  { key: 'apis', label: '接口管理' },
  { key: 'datamodels', label: '数据模型' },
  { key: 'tests', label: '自动化测试' },
  { key: 'reports', label: '测试报告' },
  { key: 'environments', label: '环境' },
  { key: 'settings', label: '项目设置' },
]

const projectId = computed(() => route.params.projectId)
const activeTab = computed(() => route.path.split('/').pop())

function onTabChange(name) {
  router.push(`/apifox/project/${projectId.value}/${name}`)
}

function backToWorkbench() {
  router.push('/apifox')
}

watch(
  projectId,
  async (id) => {
    if (!id) return
    try {
      await store.loadProject(id)
      recordRecent(store.currentProject)
    } catch {
      ElMessage.error('项目不存在或无访问权限')
      router.push('/apifox')
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.ws-header {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
}

.ws-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ax-brand);
}
</style>
