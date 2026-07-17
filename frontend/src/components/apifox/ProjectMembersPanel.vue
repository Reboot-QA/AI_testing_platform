<template>
  <div v-loading="loading" class="members-panel">
    <p class="hint">
      项目成员可跨部门授权：被加入者仅获得本项目权限（可读写，等同管理员），但不能删除项目 /
      改项目名 / 管理成员。仅项目负责人或系统管理员可增删成员。
    </p>

    <div class="add-row">
      <el-select
        v-model="pick"
        filterable
        remote
        clearable
        :remote-method="searchCandidates"
        :loading="searching"
        placeholder="搜索用户名 / 姓名后选择添加"
        style="width: 320px"
        @change="onPick"
      >
        <el-option
          v-for="c in candidates"
          :key="c.id"
          :label="c.full_name ? `${c.username}（${c.full_name}）` : c.username"
          :value="c.id"
        />
      </el-select>
    </div>

    <el-table :data="members" size="small" style="margin-top: 12px">
      <el-table-column label="用户名" prop="username" min-width="140" />
      <el-table-column label="姓名" min-width="120">
        <template #default="{ row }">{{ row.full_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="部门" min-width="120">
        <template #default="{ row }">{{ row.department_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" size="small" @click="remove(row)">移除</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无成员（可通过上方搜索添加）</template>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { projectApi } from '@/api'

const props = defineProps<{ projectId: Id }>()

const loading = ref(false)
const searching = ref(false)
const members = ref<Schemas['ProjectMemberOut'][]>([])
const candidates = ref<Schemas['ProjectMemberCandidateOut'][]>([])
const pick = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    members.value = await projectApi.listMembers(props.projectId)
  } finally {
    loading.value = false
  }
}

async function searchCandidates(keyword: string) {
  searching.value = true
  try {
    candidates.value = await projectApi.memberCandidates(props.projectId, keyword || undefined)
  } finally {
    searching.value = false
  }
}

async function onPick(userId: number | null) {
  if (userId == null) return
  await projectApi.addMember(props.projectId, userId)
  ElMessage.success('已添加成员')
  pick.value = null
  candidates.value = []
  await load()
}

async function remove(row: Schemas['ProjectMemberOut']) {
  await ElMessageBox.confirm(
    `确认移除成员「${row.username}」？移除后其将无法访问本项目。`,
    '提示',
    {
      type: 'warning',
    },
  )
  await projectApi.removeMember(props.projectId, row.user_id)
  ElMessage.success('已移除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.members-panel {
  max-width: 680px;
}

.hint {
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
  margin-bottom: 16px;
}
</style>
