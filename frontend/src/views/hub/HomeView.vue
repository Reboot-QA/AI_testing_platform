<template>
  <div class="home-view">
    <div class="home-content">
      <header class="hero">
        <span class="hero-kicker"
          ><el-icon><MagicStick /></el-icon> AI 质量平台</span
        >
        <h1>
          用 <span class="keyword-ai">AI</span> 打通「<span class="keyword-flow"
            >需求 → 用例 → 执行 → 接口自动化</span
          >」全链路
        </h1>
        <p>
          一个平台覆盖测试全流程，在最耗人力的
          <strong class="keyword-ai">需求拆解与用例设计</strong> 两个环节用 AI 提效；接口自动化通过
          <strong class="keyword-automation">接口、场景、套件分层编排</strong>
          沉淀复用能力——让测试团队少写重复、多做验证。
        </p>
        <div class="hero-actions">
          <Button class="cursor-pointer" size="lg" @click="emit('goProjects')">
            进入项目
            <ArrowRight class="button-icon" />
          </Button>
          <span>从一份需求开始，最终形成可持续回归的质量闭环</span>
        </div>
      </header>

      <section class="journey" aria-labelledby="journey-title">
        <div class="journey-heading">
          <span>HOW IT WORKS</span>
          <h2 id="journey-title">从需求输入，到场景回归</h2>
          <p>每一步都承接上一步的产物，测试资产持续沉淀，而不是散落在不同工具中。</p>
        </div>

        <div class="journey-track">
          <article
            v-for="(stage, index) in visibleStages"
            :key="stage.key"
            class="journey-stage"
            :class="{ 'ai-stage': stage.ai }"
          >
            <div class="stage-marker">
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
              <el-icon><component :is="stage.icon" /></el-icon>
            </div>
            <div class="stage-copy">
              <div class="stage-title">
                <h3>{{ stage.title }}</h3>
                <span v-if="stage.ai">AI 重点提效</span>
              </div>
              <p>{{ stage.desc }}</p>
              <div class="stage-output">
                <small>产出</small>
                <strong>{{ stage.output }}</strong>
              </div>
              <div class="stage-links">
                <button
                  v-for="action in stage.actions"
                  :key="action.label"
                  class="cursor-pointer"
                  type="button"
                  :disabled="entering"
                  @click="openCapability(action.routeName)"
                >
                  {{ action.label }}
                  <el-icon><ArrowRight /></el-icon>
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <footer class="closing-note">
        <el-icon><CircleCheckFilled /></el-icon>
        <p>
          <strong>完整闭环：</strong>
          需求点驱动用例，用例形成执行结果；接口、场景与套件沉淀为自动化资产，再通过定时任务与报告持续验证质量。
        </p>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Button } from '@/components/ui/button'
import { useUserStore } from '@/stores/user'
import { useWorkspaceStore } from '@/stores/workspace'

interface JourneyAction {
  label: string
  perm: string
  routeName: string
}

interface JourneyStage {
  key: string
  title: string
  desc: string
  output: string
  icon: string
  ai?: boolean
  actions: JourneyAction[]
}

const emit = defineEmits<{ goProjects: [options?: { create?: boolean }] }>()
const router = useRouter()
const userStore = useUserStore()
const workspaceStore = useWorkspaceStore()

const STAGES: JourneyStage[] = [
  {
    key: 'requirements',
    title: '需求分析',
    desc: '上传需求文档，AI 完成结构化拆解，沉淀可评审、可追踪的需求点。',
    output: '结构化需求点',
    icon: 'Document',
    ai: true,
    actions: [
      {
        label: 'AI 分析需求',
        perm: 'requirement_docs',
        routeName: 'WorkspaceRequirementDocuments',
      },
      {
        label: '需求点',
        perm: 'requirements',
        routeName: 'WorkspaceRequirementPoints',
      },
    ],
  },
  {
    key: 'cases',
    title: '用例设计',
    desc: 'AI 根据需求上下文生成正常、边界和异常场景，团队聚焦补充与评审。',
    output: '可复用功能用例',
    icon: 'List',
    ai: true,
    actions: [
      {
        label: 'AI 生成用例',
        perm: 'ai_generate',
        routeName: 'WorkspaceFunctionalAi',
      },
      {
        label: '功能用例库',
        perm: 'testcases',
        routeName: 'WorkspaceFunctionalCases',
      },
    ],
  },
  {
    key: 'execution',
    title: '测试执行',
    desc: '将用例组成测试单，手工执行过程实时留痕，结果回流到测试资产。',
    output: '执行记录与结果',
    icon: 'VideoPlay',
    actions: [
      {
        label: '手工执行',
        perm: 'test_execution',
        routeName: 'WorkspaceFunctionalRuns',
      },
    ],
  },
  {
    key: 'automation',
    title: '接口自动化',
    desc: '接口、场景、套件分层组织、灵活编排，把重复验证沉淀为自动化资产。',
    output: '接口、场景与套件',
    icon: 'Connection',
    ai: true,
    actions: [
      {
        label: '接口目录',
        perm: 'apifox_workbench',
        routeName: 'WorkspaceAutomationApis',
      },
      {
        label: '场景编排',
        perm: 'apifox_workbench',
        routeName: 'WorkspaceAutomationScenarios',
      },
      {
        label: '测试套件',
        perm: 'apifox_workbench',
        routeName: 'WorkspaceAutomationSuites',
      },
    ],
  },
  {
    key: 'regression',
    title: '场景回归',
    desc: '定时触发持续回归，SSE 实时反馈运行进度，最终以报告完成质量闭环。',
    output: '回归结果与报告',
    icon: 'RefreshRight',
    actions: [
      {
        label: '定时任务',
        perm: 'apifox_workbench',
        routeName: 'WorkspaceAutomationSchedules',
      },
      {
        label: '测试报告',
        perm: 'apifox_workbench',
        routeName: 'WorkspaceAutomationReports',
      },
    ],
  },
]

const visibleStages = computed(() =>
  STAGES.map((stage) => ({
    ...stage,
    actions: stage.actions.filter((action) => userStore.hasPermission(action.perm)),
  })).filter((stage) => stage.actions.length > 0),
)

// 快捷入口不再要求先选项目：直接进默认项目（置顶优先，其次工作台首个）；无项目时引导创建
const entering = ref(false)

async function openCapability(routeName: string) {
  if (entering.value) return
  entering.value = true
  try {
    const projectId = await workspaceStore.resolveDefaultProjectId()
    if (!projectId) {
      ElMessage.info('还没有项目，先创建一个项目再开始吧')
      emit('goProjects', { create: true })
      return
    }
    router.push({ name: routeName, params: { projectId } })
  } catch {
    // 全局拦截器已提示
  } finally {
    entering.value = false
  }
}
</script>

<style scoped src="@/views/hub/HomeView.css"></style>
