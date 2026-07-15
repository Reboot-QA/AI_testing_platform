<template>
  <div v-loading="loading" class="space-y-5">
    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <button
        v-for="item in statCards"
        :key="item.label"
        type="button"
        class="group rounded-lg border border-border bg-card p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
        @click="goToPage(item.path)"
      >
        <div class="flex items-center gap-4">
          <div
            class="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl text-white"
            :style="{ background: item.color }"
          >
            <el-icon :size="26"><component :is="item.icon" /></el-icon>
          </div>
          <div>
            <div class="text-2xl font-bold text-foreground">{{ item.value }}</div>
            <div class="mt-0.5 text-sm text-muted-foreground">{{ item.label }}</div>
          </div>
        </div>
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
          <div class="flex flex-wrap gap-3">
            <Button @click="router.push('/ai-generate')">
              <el-icon><MagicStick /></el-icon> AI 生成用例
            </Button>
            <Button variant="outline" @click="router.push('/projects')">
              <el-icon><Folder /></el-icon> 新建项目
            </Button>
            <Button variant="outline" @click="router.push('/requirements')">
              <el-icon><Document /></el-icon> 添加需求
            </Button>
            <Button variant="outline" @click="router.push('/testcases')">
              <el-icon><List /></el-icon> 查看用例
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>平台能力</CardTitle>
        </CardHeader>
        <CardContent>
          <ul class="space-y-2.5 text-sm text-foreground">
            <li v-for="feat in features" :key="feat" class="flex items-start gap-2">
              <el-icon class="mt-0.5 shrink-0" color="var(--ax-success)"><CircleCheck /></el-icon>
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
import { Button } from '@/components/ui/button'
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
