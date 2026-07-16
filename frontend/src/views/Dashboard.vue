<template>
  <div v-loading="loading" class="space-y-5">
    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-4">
      <button
        v-for="item in statCards"
        :key="item.label"
        type="button"
        class="group relative overflow-hidden rounded-lg border border-border bg-card p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-transparent hover:shadow-md"
        @click="goToPage(item.path)"
      >
        <div class="flex items-center gap-4 cursor-pointer">
          <div
            class="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl"
            :style="{ backgroundColor: tint(item.color), color: item.color }"
          >
            <el-icon :size="26"><component :is="item.icon" /></el-icon>
          </div>
          <div>
            <div class="text-3xl font-bold leading-none text-foreground">{{ item.value }}</div>
            <div class="mt-2 text-sm text-muted-foreground">{{ item.label }}</div>
          </div>
        </div>
        <el-icon
          class="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100"
          :size="18"
        >
          <ArrowRight />
        </el-icon>
        <span
          class="absolute inset-x-0 bottom-0 h-1 origin-left scale-x-0 transition-transform group-hover:scale-x-100"
          :style="{ backgroundColor: item.color }"
        />
      </button>
    </div>

    <!-- 快捷操作 + 平台能力 -->
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card class="lg:col-span-2">
        <CardHeader>
          <CardTitle>快捷操作</CardTitle>
          <CardDescription>常用功能一键直达</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              v-for="action in quickActions"
              :key="action.label"
              type="button"
              class="group flex cursor-pointer items-start gap-3 rounded-lg border border-border p-4 text-left transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:bg-accent hover:shadow-sm"
              @click="router.push(action.path)"
            >
              <div
                class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg transition-transform group-hover:scale-105"
                :style="{ backgroundColor: tint(action.color), color: action.color }"
              >
                <el-icon :size="20"><component :is="action.icon" /></el-icon>
              </div>
              <div class="min-w-0">
                <div class="font-medium text-foreground">{{ action.label }}</div>
                <div class="mt-0.5 text-xs text-muted-foreground">{{ action.desc }}</div>
              </div>
            </button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>平台能力</CardTitle>
          <CardDescription>覆盖测试全生命周期</CardDescription>
        </CardHeader>
        <CardContent>
          <ul class="space-y-3 text-sm text-foreground">
            <li v-for="feat in features" :key="feat" class="flex items-start gap-2.5">
              <el-icon class="mt-0.5 shrink-0" :size="16" color="var(--ax-success)">
                <CircleCheck />
              </el-icon>
              <span>{{ feat }}</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { projectApi } from '@/api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'

const router = useRouter()

const loading = ref(false)
const stats = ref({
  project_count: 0,
  requirement_count: 0,
  testcase_count: 0,
  ai_generated_count: 0,
  pending_review_count: 0,
})

// 图标底色：品牌/状态色的 14% 淡色调，配同色图标，观感比纯色块更柔和
const tint = (color) => `color-mix(in srgb, ${color} 14%, white)`

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
    label: '待评审',
    value: stats.value.pending_review_count,
    icon: 'Clock',
    color: '#dd6b20',
    path: '/testcases?review_status=pending',
  },
])

const quickActions = [
  {
    label: 'AI 生成用例',
    desc: '从需求智能生成测试用例',
    icon: 'MagicStick',
    color: '#1a365d',
    path: '/ai-generate',
  },
  {
    label: '新建项目',
    desc: '创建一个新的测试项目',
    icon: 'FolderAdd',
    color: '#3182ce',
    path: '/projects',
  },
  {
    label: '添加需求',
    desc: '录入或导入需求点',
    icon: 'Document',
    color: '#38a169',
    path: '/requirements',
  },
  {
    label: '查看用例',
    desc: '浏览与管理用例库',
    icon: 'List',
    color: '#805ad5',
    path: '/testcases',
  },
]

const features = [
  '基于 LLM 的智能用例生成',
  '需求-用例全生命周期管理',
  '用例评审与状态流转',
  'Excel 批量导出',
  'OpenAI 兼容 API 接入',
]

function goToPage(path) {
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
