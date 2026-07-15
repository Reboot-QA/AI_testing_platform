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
        <el-menu-item
          v-if="userStore.hasPermission('projects')"
          index="/projects"
          data-assistant="menu.projects"
        >
          <el-icon><Folder /></el-icon>
          <span>项目管理</span>
        </el-menu-item>

        <el-sub-menu v-if="showRequirementMenu" index="requirement_mgmt">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>需求管理</span>
          </template>
          <el-menu-item
            v-if="userStore.hasPermission('requirement_docs')"
            index="/requirement-docs"
          >
            <el-icon><Upload /></el-icon>
            <span>AI分析需求</span>
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('requirements')"
            index="/requirements"
            data-assistant="menu.requirements"
          >
            <el-icon><Tickets /></el-icon>
            <span>需求点</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showTestcaseMenu" index="testcase_mgmt">
          <template #title>
            <el-icon><List /></el-icon>
            <span>用例管理</span>
          </template>
          <el-menu-item
            v-if="userStore.hasPermission('ai_generate')"
            index="/ai-generate"
            data-assistant="menu.ai_generate"
          >
            <el-icon><MagicStick /></el-icon>
            <span>AI生成用例</span>
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('testcases')"
            index="/testcases"
            data-assistant="menu.testcases"
          >
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
          <el-menu-item v-if="userStore.hasPermission('apifox_workbench')" index="/apifox">
            工作台
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('api_automation_env')"
            index="/api-automation/env"
            data-assistant="menu.api_automation_env"
          >
            环境配置
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('api_automation_suites')"
            index="/api-automation/suites"
            data-assistant="menu.api_automation_suites"
          >
            套件与用例
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('api_automation_reports')"
            index="/api-automation/reports"
          >
            测试报告
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('api_automation_schedule')"
            index="/api-automation/schedule"
          >
            定时任务
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showLogMenu" index="log_mgmt">
          <template #title>
            <el-icon><DocumentCopy /></el-icon>
            <span>日志管理</span>
          </template>
          <el-menu-item v-if="userStore.hasPermission('system_logs')" index="/system/logs">
            日志监控
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('system_error_logs')"
            index="/system/error-logs"
          >
            错误日志
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
          <el-menu-item
            v-if="userStore.hasPermission('system_departments')"
            index="/system/departments"
          >
            部门权限
          </el-menu-item>
          <el-menu-item
            v-if="userStore.hasPermission('system_permissions')"
            index="/system/permissions"
          >
            权限管理
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ pageTitle }}</span>
        <div class="user-area">
          <el-tag type="info" size="small">{{
            userStore.user?.full_name || userStore.user?.username
          }}</el-tag>
          <el-button link type="primary" @click="passwordDialogVisible = true">修改密码</el-button>
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
          <el-button type="primary" link @click="router.push('/ai-generate')">AI生成用例</el-button>
          页面，否则将自动停止
        </template>
      </el-alert>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
    <AssistantPanel :key="assistantPanelKey" />

    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="420px"
      @closed="resetPasswordForm"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="90px"
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSubmitting" @click="handleChangePassword"
          >确定</el-button
        >
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useAiGenerateStore } from '@/stores/aiGenerate'
import { PAGE_TITLES, SUBMENU_INDEX_BY_PATH } from '@/config/menus'
import AssistantPanel from '@/components/AssistantPanel.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const aiStore = useAiGenerateStore()

const showRequirementMenu = computed(
  () => userStore.hasPermission('requirement_docs') || userStore.hasPermission('requirements'),
)

const showTestcaseMenu = computed(
  () =>
    userStore.hasPermission('testcases') ||
    userStore.hasPermission('ai_generate') ||
    userStore.hasPermission('test_execution'),
)

const showAutomationMenu = computed(
  () =>
    userStore.hasPermission('apifox_workbench') ||
    userStore.hasPermission('api_automation_env') ||
    userStore.hasPermission('api_automation_suites') ||
    userStore.hasPermission('api_automation_reports') ||
    userStore.hasPermission('api_automation_schedule'),
)

const showLogMenu = computed(
  () => userStore.hasPermission('system_logs') || userStore.hasPermission('system_error_logs'),
)

const showSystemMenu = computed(
  () =>
    userStore.hasPermission('system_settings') ||
    userStore.hasPermission('system_users') ||
    userStore.hasPermission('system_departments') ||
    userStore.hasPermission('system_permissions'),
)

const activeMenu = computed(() => {
  if (route.path.startsWith('/apifox')) {
    return '/apifox'
  }
  return route.path
})

const defaultOpeneds = computed(() => {
  const open = []
  if (
    route.path.startsWith('/system/settings') ||
    route.path.startsWith('/system/users') ||
    route.path.startsWith('/system/departments') ||
    route.path.startsWith('/system/permissions')
  ) {
    open.push('system')
  }
  if (route.path.startsWith('/apifox')) {
    open.push('api_automation_mgmt')
  }
  const submenu = SUBMENU_INDEX_BY_PATH[route.path]
  if (submenu) {
    open.push(submenu)
  }
  return open
})

const pageTitle = computed(() => PAGE_TITLES[route.path] || 'AI 质量平台')

const assistantPanelKey = computed(() => userStore.user?.id || userStore.token || 'guest')

const passwordDialogVisible = ref(false)
const passwordSubmitting = ref(false)
const passwordFormRef = ref()

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const validateConfirmPassword = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入新密码'))
    return
  }
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
}

function resetPasswordForm() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordFormRef.value?.clearValidate()
}

async function handleChangePassword() {
  await passwordFormRef.value.validate()
  passwordSubmitting.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码已修改，请重新登录')
    passwordDialogVisible.value = false
    userStore.logout()
    router.push('/login')
  } finally {
    passwordSubmitting.value = false
  }
}

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
  background: linear-gradient(180deg, #1a365d 0%, #12294a 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.aside :deep(.el-menu) {
  flex: 1;
  overflow-y: auto;
  border-right: none;
  padding: 8px 10px;
  background: transparent !important;
}

/* 菜单项圆角化 + 悬停/选中态更清晰 */
.aside :deep(.el-menu-item),
.aside :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  border-radius: var(--ax-radius);
  margin-bottom: 2px;
}

.aside :deep(.el-menu-item:hover),
.aside :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #fff !important;
}

.aside :deep(.el-menu-item.is-active) {
  background: rgba(66, 153, 225, 0.22) !important;
  color: #fff !important;
  font-weight: 600;
  position: relative;
}

/* 选中项左侧高亮条 */
.aside :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: #63b3ed;
}

.aside :deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
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
  letter-spacing: 0.5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--ax-bg);
  border-bottom: 1px solid var(--ax-border);
  box-shadow: var(--ax-shadow-sm);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--ax-text);
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main {
  background: var(--ax-bg-subtle);
  padding: 20px;
}

.leave-warning {
  margin: 0;
  border-radius: 0;
}
</style>
