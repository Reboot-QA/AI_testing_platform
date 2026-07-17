<template>
  <div class="proj-settings">
    <div class="side-panel">
      <div
        v-for="s in SECTIONS"
        :key="s.key"
        class="side-item"
        :class="{ active: section === s.key }"
        @click="section = s.key"
      >
        <el-icon><component :is="s.icon" /></el-icon>
        <span>{{ s.label }}</span>
      </div>
    </div>

    <!-- 基本信息 -->
    <div v-if="section === 'basic'" class="editor-panel">
      <div class="basic-form">
        <div class="field">
          <span class="lbl">项目名称</span>
          <el-input v-model="basicForm.name" placeholder="项目名称" style="max-width: 360px" />
        </div>
        <div class="field">
          <span class="lbl">描述</span>
          <el-input
            v-model="basicForm.description"
            type="textarea"
            :rows="3"
            placeholder="选填"
            style="max-width: 360px"
          />
        </div>
        <div v-if="isAdmin" class="field">
          <span class="lbl">负责人</span>
          <el-select
            v-model="basicForm.owner_id"
            filterable
            placeholder="选择负责人"
            style="max-width: 360px"
          >
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="u.full_name ? `${u.username}（${u.full_name}）` : u.username"
              :value="u.id"
            />
          </el-select>
        </div>
        <el-button type="primary" :loading="savingBasic" @click="saveBasic">保存</el-button>
      </div>

      <div class="danger-zone">
        <div class="dz-title">危险区域</div>
        <div class="dz-row">
          <div>
            <div class="dz-h">删除项目</div>
            <div class="dz-desc">
              永久删除该项目及其全部接口 / 用例 / 场景 / 环境 / 数据模型 / 脚本 / 定时任务 /
              运行记录等数据，不可恢复。
            </div>
          </div>
          <el-button v-if="canDelete" type="danger" @click="delProject">删除项目</el-button>
          <el-tag v-else type="info" size="small">仅项目负责人或系统管理员可删除</el-tag>
        </div>
      </div>
    </div>

    <!-- 脚本库 -->
    <ProjectScriptsPanel v-else-if="section === 'scripts'" :project-id="pid" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { projectApi, userApi } from '@/api'
import { useUserStore } from '@/stores/user'
import ProjectScriptsPanel from '@/components/apifox/ProjectScriptsPanel.vue'

const router = useRouter()
const pid = useRouteParamId()

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const users = ref<Schemas['UserOut'][]>([])
// 硬删除仅项目负责人/系统管理员可见（与工作台卡片、后端校验一致）
const canDelete = computed(() => isAdmin.value || basicForm.owner_id === userStore.user?.id)

const SECTIONS = [
  { key: 'basic', label: '基本信息', icon: 'Setting' },
  { key: 'scripts', label: '脚本库', icon: 'Tickets' },
]

const section = ref<'basic' | 'scripts'>('basic')
const savingBasic = ref(false)
const basicForm = reactive({ name: '', description: '', owner_id: null as number | null })

async function loadBasic() {
  const p = await projectApi.get(pid.value)
  basicForm.name = p.name
  basicForm.description = p.description || ''
  basicForm.owner_id = p.owner_id ?? null
}

async function loadUsers() {
  // 用户列表接口仅管理员可访问，非管理员不请求（选择器也不显示）
  if (isAdmin.value) users.value = await userApi.list()
}

async function saveBasic() {
  savingBasic.value = true
  try {
    const payload = { name: basicForm.name, description: basicForm.description || null }
    if (isAdmin.value) payload.owner_id = basicForm.owner_id // 仅管理员可变更负责人
    await projectApi.update(pid.value, payload)
    ElMessage.success('已保存')
  } finally {
    savingBasic.value = false
  }
}

async function delProject() {
  // 硬删除不可逆：要求输入项目名完全一致二次确认（与工作台一致）
  await ElMessageBox.prompt(
    `此操作将永久删除项目「${basicForm.name}」及其全部数据（接口/用例/场景/环境/数据模型/脚本/定时任务/运行报告/需求等），不可恢复！\n请输入项目名称以确认：`,
    '硬删除项目',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      confirmButtonClass: 'el-button--danger',
      inputValidator: (v) => (v || '').trim() === basicForm.name || '项目名称不一致',
    },
  )
  await projectApi.delete(pid.value)
  ElMessage.success('项目已删除')
  router.push('/apifox')
}

onMounted(() => {
  loadBasic()
  loadUsers()
})
</script>

<style scoped>
.proj-settings {
  display: flex;
  gap: var(--ax-gap-lg);
  height: 100%;
  min-height: 0;
}

.side-panel {
  width: 140px;
  border-right: 1px solid var(--ax-border);
  padding-right: 8px;
}

.side-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--ax-text-tertiary);
}

.side-item:hover {
  background: var(--ax-bg-hover);
}

.side-item.active {
  background: var(--ax-bg-active);
  color: var(--ax-brand);
  font-weight: 600;
}

.editor-panel {
  flex: 1;
  overflow: auto;
}

.basic-form {
  max-width: 480px;
}

.field {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.lbl {
  flex-shrink: 0;
  width: 72px;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
  padding-top: 6px;
}

.danger-zone {
  max-width: 620px;
  margin-top: 28px;
  border: 1px solid var(--ax-danger);
  border-radius: var(--ax-radius-lg);
  padding: 16px;
}

.dz-title {
  font-weight: 600;
  color: var(--ax-danger);
  margin-bottom: 12px;
}

.dz-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.dz-h {
  font-weight: 600;
}

.dz-desc {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  margin-top: 2px;
}
</style>
