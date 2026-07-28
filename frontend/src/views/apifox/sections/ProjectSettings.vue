<template>
  <div class="proj-basic">
    <div class="basic-form">
      <div class="field">
        <span class="lbl">项目名称</span>
        <el-input
          v-model="basicForm.name"
          :disabled="!isManager"
          :maxlength="TITLE_MAX_LEN"
          placeholder="项目名称"
          style="max-width: 360px"
        />
      </div>
      <div class="field">
        <span class="lbl">描述</span>
        <el-input
          v-model="basicForm.description"
          type="textarea"
          :rows="3"
          :maxlength="DESC_MAX_LEN"
          show-word-limit
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
</template>

<script setup lang="ts">
import { TITLE_MAX_LEN, DESC_MAX_LEN } from '@/constants/limits'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { projectApi, userApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useWorkspaceStore } from '@/stores/workspace'

const router = useRouter()
const pid = useRouteParamId()
const workspace = useWorkspaceStore()

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const users = ref<Schemas['UserOut'][]>([])
// 项目负责人/系统管理员：可改项目名、删项目（与后端 is_project_manager 一致）
const isManager = computed(() => isAdmin.value || basicForm.owner_id === userStore.user?.id)
const canDelete = isManager

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
    const payload: Schemas['ProjectUpdate'] = {
      name: basicForm.name,
      description: basicForm.description || null,
    }
    if (isAdmin.value) payload.owner_id = basicForm.owner_id
    const updated = await projectApi.update(pid.value, payload)
    workspace.currentProject = updated
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
.proj-basic {
  height: 100%;
  min-height: 0;
  overflow: auto;
}

.basic-form {
  max-width: 480px;
}

.field {
  display: flex;
  align-items: flex-start;
  gap: var(--ax-space-3);
  margin-bottom: var(--ax-space-3-5);
}

.lbl {
  flex-shrink: 0;
  width: 72px;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
  padding-top: var(--ax-space-1-5);
}

.danger-zone {
  max-width: 620px;
  margin-top: var(--ax-space-7);
  border: 1px solid var(--ax-danger);
  border-radius: var(--ax-radius-lg);
  padding: var(--ax-space-4);
}

.dz-title {
  font-weight: 600;
  color: var(--ax-danger);
  margin-bottom: var(--ax-space-3);
}

.dz-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-4);
}

.dz-h {
  font-weight: 600;
}

.dz-desc {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  margin-top: var(--ax-space-0-5);
}
</style>
