<template>
  <div v-loading="loading" class="dashboard">
    <div class="stat-tiles">
      <button
        v-for="item in statCards"
        :key="item.label"
        type="button"
        class="stat-tile"
        @click="goToPage(item.path)"
      >
        <div class="ico" :style="{ backgroundColor: tint(item.color), color: item.color }">
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
        </div>
        <div class="meta">
          <div class="n">{{ item.value }}</div>
          <div class="l">{{ item.label }}</div>
        </div>
        <el-icon class="arrow"><ArrowRight /></el-icon>
      </button>
    </div>

    <div class="dash-body">
      <div class="panel quick-panel">
        <div class="panel-h">
          <span class="panel-title"
            ><el-icon><Lightning /></el-icon> 快捷操作</span
          >
          <span class="panel-desc">常用功能一键直达</span>
        </div>
        <div class="quick-list">
          <button
            v-for="action in quickActions"
            :key="action.label"
            type="button"
            class="quick-item"
            @click="router.push(action.path)"
          >
            <div
              class="qi-ico"
              :style="{ backgroundColor: tint(action.color), color: action.color }"
            >
              <el-icon :size="20"><component :is="action.icon" /></el-icon>
            </div>
            <div class="qi-text">
              <div class="qi-label">{{ action.label }}</div>
              <div class="qi-desc">{{ action.desc }}</div>
            </div>
            <el-icon class="qi-arrow"><ArrowRight /></el-icon>
          </button>
        </div>
      </div>

      <div class="panel side-panel">
        <div class="panel-h">
          <span class="panel-title"
            ><el-icon><Cpu /></el-icon> 平台能力</span
          >
          <span class="panel-desc">覆盖测试全生命周期</span>
        </div>
        <div class="side-body">
          <div class="flow">
            <div v-for="(step, i) in flowSteps" :key="step.label" class="flow-step">
              <div class="flow-node" :style="{ color: step.color, background: tint(step.color) }">
                <el-icon :size="16"><component :is="step.icon" /></el-icon>
              </div>
              <div class="flow-label">{{ step.label }}</div>
              <el-icon v-if="i < flowSteps.length - 1" class="flow-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
          <ul class="features">
            <li v-for="feat in features" :key="feat">
              <el-icon :size="14" color="var(--ax-success)"><CircleCheck /></el-icon>
              <span>{{ feat }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { projectApi } from '@/api'
import { useUserStore } from '@/stores/user'
import type { DashboardStats } from '@/types/common'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const stats = ref<DashboardStats>({
  project_count: 0,
  requirement_count: 0,
  testcase_count: 0,
  ai_generated_count: 0,
  pending_review_count: 0,
})

const tint = (color: string) => `color-mix(in srgb, ${color} 14%, white)`

const statCards = computed(() => [
  {
    label: '项目数',
    value: stats.value.project_count,
    icon: 'Folder',
    color: '#3182ce',
    path: '/projects',
  },
  {
    label: '需求数',
    value: stats.value.requirement_count,
    icon: 'Document',
    color: '#38a169',
    path: '/requirements',
  },
  {
    label: '用例总数',
    value: stats.value.testcase_count,
    icon: 'List',
    color: '#805ad5',
    path: '/testcases',
  },
  {
    label: 'AI 生成',
    value: stats.value.ai_generated_count,
    icon: 'MagicStick',
    color: '#1a365d',
    path: '/ai-generate',
  },
  {
    label: '待评审',
    value: stats.value.pending_review_count,
    icon: 'Clock',
    color: '#dd6b20',
    path: '/testcases?review_status=pending',
  },
])

const allQuickActions = [
  {
    label: 'AI 生成用例',
    desc: '从需求智能生成测试用例',
    icon: 'MagicStick',
    color: '#1a365d',
    path: '/ai-generate',
    permission: 'ai_generate',
  },
  {
    label: '接口自动化',
    desc: 'Apifox 式接口编排与执行',
    icon: 'Connection',
    color: '#0d9488',
    path: '/apifox',
    permission: 'apifox_workbench',
  },
  {
    label: '新建项目',
    desc: '创建一个新的测试项目',
    icon: 'FolderAdd',
    color: '#3182ce',
    path: '/projects',
    permission: 'projects',
  },
  {
    label: '添加需求',
    desc: '录入或导入需求点',
    icon: 'Document',
    color: '#38a169',
    path: '/requirements',
    permission: 'requirements',
  },
  {
    label: '查看用例',
    desc: '浏览与管理用例库',
    icon: 'List',
    color: '#805ad5',
    path: '/testcases',
    permission: 'testcases',
  },
  {
    label: '用例执行',
    desc: '手工执行与结果记录',
    icon: 'VideoPlay',
    color: '#16a34a',
    path: '/test-execution',
    permission: 'test_execution',
  },
]

const quickActions = computed(() =>
  allQuickActions.filter((a) => !a.permission || userStore.hasPermission(a.permission)),
)

const flowSteps = [
  { label: '需求', icon: 'Document', color: '#38a169' },
  { label: '用例', icon: 'List', color: '#805ad5' },
  { label: '评审', icon: 'CircleCheck', color: '#dd6b20' },
  { label: '执行', icon: 'VideoPlay', color: '#16a34a' },
  { label: '自动化', icon: 'Connection', color: '#0d9488' },
]

const features = [
  '基于 LLM 的智能用例生成',
  '需求-用例全生命周期管理',
  '用例评审与状态流转',
  'Excel 批量导出',
  'OpenAI 兼容 API 接入',
]

function goToPage(path: string) {
  if (path) router.push(path)
}

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await projectApi.dashboard()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  gap: 12px;
}

/* ── 统计卡片 ── */
.stat-tiles {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  flex: none;
}

.stat-tile {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  cursor: pointer;
  text-align: left;
  transition: all var(--ax-transition);
  overflow: hidden;
}

.stat-tile:hover {
  border-color: color-mix(in srgb, var(--ax-brand) 30%, var(--ax-border));
  box-shadow: var(--ax-shadow);
  transform: translateY(-1px);
}

.stat-tile .ico {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: var(--ax-radius-lg);
  display: grid;
  place-items: center;
}

.stat-tile .meta {
  min-width: 0;
  flex: 1;
}

.stat-tile .n {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--ax-text);
  font-variant-numeric: tabular-nums;
}

.stat-tile .l {
  color: var(--ax-text-secondary);
  font-size: 12px;
  margin-top: 2px;
}

.stat-tile .arrow {
  flex: none;
  color: var(--ax-text-tertiary);
  opacity: 0;
  transition: opacity var(--ax-transition);
}

.stat-tile:hover .arrow {
  opacity: 1;
}

/* ── 主体区域 ── */
.dash-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 12px;
}

.panel {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-h {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--ax-border);
  flex: none;
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--ax-text);
}

.panel-title .el-icon {
  color: var(--ax-brand);
}

.panel-desc {
  font-size: 12px;
  color: var(--ax-text-tertiary);
}

/* ── 快捷操作 ── */
.quick-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  overflow-y: auto;
}

.quick-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  cursor: pointer;
  text-align: left;
  transition: all var(--ax-transition);
  flex: none;
}

.quick-item:hover {
  border-color: color-mix(in srgb, var(--ax-brand) 30%, var(--ax-border));
  background: var(--ax-bg-subtle);
  box-shadow: var(--ax-shadow-sm);
  transform: translateY(-1px);
}

.qi-ico {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: var(--ax-radius-lg);
  display: grid;
  place-items: center;
  transition: transform var(--ax-transition);
}

.quick-item:hover .qi-ico {
  transform: scale(1.05);
}

.qi-text {
  flex: 1;
  min-width: 0;
}

.qi-label {
  font-weight: 600;
  font-size: 14px;
  color: var(--ax-text);
}

.qi-desc {
  margin-top: 3px;
  font-size: 12px;
  color: var(--ax-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qi-arrow {
  flex: none;
  color: var(--ax-text-placeholder);
  opacity: 0;
  transition: opacity var(--ax-transition);
}

.quick-item:hover .qi-arrow {
  opacity: 1;
}

/* ── 右侧平台能力 ── */
.side-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 16px;
  gap: 16px;
  overflow-y: auto;
}

.flow {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 4px;
  padding: 12px;
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg-subtle);
}

.flow-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  position: relative;
  min-width: 0;
}

.flow-node {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: grid;
  place-items: center;
}

.flow-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--ax-text-secondary);
  text-align: center;
}

.flow-arrow {
  position: absolute;
  right: -8px;
  top: 10px;
  color: var(--ax-text-placeholder);
  font-size: 12px;
}

.features {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.features li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: var(--ax-text);
  line-height: 1.5;
}

.features li .el-icon {
  margin-top: 3px;
  flex: none;
}

@media (max-width: 1100px) {
  .stat-tiles {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dash-body {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .dashboard {
    overflow: auto;
  }
}

@media (max-width: 640px) {
  .stat-tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
