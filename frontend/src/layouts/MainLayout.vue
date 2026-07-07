<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="24"><Cpu /></el-icon>
        <span>AI 质量平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="defaultOpeneds"
        router
        background-color="#1a365d"
        text-color="#cbd5e0"
        active-text-color="#ffffff"
      >
        <el-menu-item v-if="userStore.hasPermission('dashboard')" index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.hasPermission('projects')" index="/projects" data-assistant="menu.projects">
          <el-icon><Folder /></el-icon>
          <span>项目管理</span>
        </el-menu-item>

        <el-sub-menu v-if="showRequirementMenu" index="requirement_mgmt">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>需求管理</span>
          </template>
          <el-menu-item v-if="userStore.hasPermission('requirement_docs')" index="/requirement-docs">
            <el-icon><Upload /></el-icon>
            <span>需求文档</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('requirements')" index="/requirements">
            <el-icon><Tickets /></el-icon>
            <span>需求点</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showTestcaseMenu" index="testcase_mgmt">
          <template #title>
            <el-icon><List /></el-icon>
            <span>用例管理</span>
          </template>
          <el-menu-item v-if="userStore.hasPermission('ai_generate')" index="/ai-generate">
            <el-icon><MagicStick /></el-icon>
            <span>AI 生成</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('testcases')" index="/testcases">
            <el-icon><Collection /></el-icon>
            <span>用例库</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('test_execution')" index="/test-execution">
            <el-icon><VideoPlay /></el-icon>
            <span>用例执行</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showAutomationMenu" index="api_automation_mgmt">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>接口自动化</span>
          </template>
          <el-menu-item v-if="userStore.hasPermission('api_automation_env')" index="/api-automation/env">
            环境配置
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('api_automation_suites')" index="/api-automation/suites">
            套件与用例
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('api_automation_reports')" index="/api-automation/reports">
            测试报告
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('api_automation_schedule')" index="/api-automation/schedule">
            定时任务
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showSystemMenu" index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item v-if="userStore.hasPermission('system_settings')" index="/system/settings">
            全局设置
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('system_users')" index="/system/users">
            用户管理
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('system_departments')" index="/system/departments">
            部门权限
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('system_permissions')" index="/system/permissions">
            权限管理
          </el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('system_logs')" index="/system/logs">
            日志监控
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ pageTitle }}</span>
        <div class="user-area">
          <el-tag type="info" size="small">{{ userStore.user?.full_name || userStore.user?.username }}</el-tag>
          <el-button link type="danger" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-alert
        v-if="aiStore.generating && route.path !== '/ai-generate'"
        class="leave-warning"
        type="warning"
        show-icon
        :closable="false"
      >
        <template #title>
          AI 正在生成用例，请在 {{ aiStore.leaveCountdown }} 秒内返回
          <el-button type="primary" link @click="router.push('/ai-generate')">AI 生成</el-button>
          页面，否则将自动停止
        </template>
      </el-alert>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
    <AssistantPanel />
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAiGenerateStore } from '@/stores/aiGenerate'
import { PAGE_TITLES, SUBMENU_INDEX_BY_PATH } from '@/config/menus'
import AssistantPanel from '@/components/AssistantPanel.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const aiStore = useAiGenerateStore()

const showRequirementMenu = computed(
  () =>
    userStore.hasPermission('requirement_docs') || userStore.hasPermission('requirements')
)

const showTestcaseMenu = computed(
  () =>
    userStore.hasPermission('testcases') ||
    userStore.hasPermission('ai_generate') ||
    userStore.hasPermission('test_execution')
)

const showAutomationMenu = computed(
  () =>
    userStore.hasPermission('api_automation_env') ||
    userStore.hasPermission('api_automation_suites') ||
    userStore.hasPermission('api_automation_reports') ||
    userStore.hasPermission('api_automation_schedule')
)

const showSystemMenu = computed(
  () =>
    userStore.hasPermission('system_settings') ||
    userStore.hasPermission('system_users') ||
    userStore.hasPermission('system_departments') ||
    userStore.hasPermission('system_permissions') ||
    userStore.hasPermission('system_logs')
)

const activeMenu = computed(() => {
  if (route.path.startsWith('/system/')) {
    return route.path
  }
  return route.path
})

const defaultOpeneds = computed(() => {
  const open = []
  if (route.path.startsWith('/system')) {
    open.push('system')
  }
  const submenu = SUBMENU_INDEX_BY_PATH[route.path]
  if (submenu) {
    open.push(submenu)
  }
  return open
})

const pageTitle = computed(() => PAGE_TITLES[route.path] || 'AI 质量平台')

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  background: #1a365d;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 60px;
  padding: 0 20px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.el-menu {
  border-right: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a365d;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main {
  background: #f7fafc;
  padding: 20px;
}

.leave-warning {
  margin: 0;
  border-radius: 0;
}
</style>
