<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 添加用户
      </el-button>
    </div>

    <el-table :data="users" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="full_name" label="姓名" width="140">
        <template #default="{ row }">{{ row.full_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="180">
        <template #default="{ row }">{{ row.email || '-' }}</template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
            {{ roleMap[row.role] || row.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="department_name" label="部门" width="120">
        <template #default="{ row }">{{ row.department_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="organization_name" label="组织" width="120">
        <template #default="{ row }">{{ row.organization_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="team_name" label="团队" width="120">
        <template #default="{ row }">{{ row.team_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="warning" @click="openPasswordDialog(row)">重置密码</el-button>
          <el-button
            v-if="row.id !== currentUserId"
            link
            type="danger"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '添加用户'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username" required>
          <el-input v-model="form.username" :disabled="!!editing" placeholder="仅支持字母、数字、下划线" />
        </el-form-item>
        <el-form-item v-if="!editing" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="测试员" value="tester" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-select v-model="form.department_id" placeholder="请选择部门" style="width: 100%" filterable>
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="组织">
          <el-select
            v-model="form.organization_id"
            placeholder="默认组织"
            style="width: 100%"
            clearable
            @change="onOrgChange"
          >
            <el-option v-for="org in organizations" :key="org.id" :label="org.name" :value="org.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="团队">
          <el-select v-model="form.team_id" placeholder="默认团队（归属标签）" style="width: 100%" clearable>
            <el-option v-for="team in teams" :key="team.id" :label="team.name" :value="team.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="组织角色">
          <el-select v-model="form.org_role" placeholder="成员" style="width: 100%">
            <el-option label="组织所有者" value="owner" disabled />
            <el-option label="组织管理员" value="admin" />
            <el-option label="成员" value="member" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editing" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="passwordDialogVisible" title="重置密码" width="420px">
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px">
        <el-form-item label="用户">
          <el-input :model-value="passwordTarget?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="passwordForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSubmitting" @click="handleResetPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userApi, departmentApi, workbenchApi } from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

const users = ref([])
const departments = ref([])
const organizations = ref([])
const teams = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const submitting = ref(false)
const passwordSubmitting = ref(false)
const editing = ref(null)
const passwordTarget = ref(null)
const formRef = ref()
const passwordFormRef = ref()

const roleMap = { admin: '管理员', tester: '测试员' }
const USERNAME_PATTERN = /^[A-Za-z0-9_]+$/

function validateUsername(_rule, value, callback) {
  if (!value) {
    callback(new Error('请输入用户名'))
    return
  }
  if (!USERNAME_PATTERN.test(value)) {
    callback(new Error('用户名只能包含字母、数字和下划线，不能包含中文或特殊符号'))
    return
  }
  callback()
}

function validateEmail(_rule, value, callback) {
  const email = (value || '').trim()
  if (!email) {
    callback()
    return
  }
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailPattern.test(email)) {
    callback(new Error('邮箱格式不正确'))
    return
  }
  callback()
}

const form = reactive({
  username: '',
  password: '',
  full_name: '',
  email: '',
  role: 'tester',
  department_id: null,
  organization_id: null,
  team_id: null,
  org_role: null,
  is_active: true,
})

const passwordForm = reactive({
  password: '',
})

const rules = {
  username: [{ required: true, validator: validateUsername, trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  email: [{ validator: validateEmail, trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  department_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
}

const passwordRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

async function loadDepartments() {
  departments.value = await departmentApi.list()
}

async function loadOrganizations() {
  organizations.value = await workbenchApi.listOrgs()
}

async function loadTeams(orgId) {
  teams.value = orgId ? await workbenchApi.listOrgTeams(orgId) : []
}

async function onOrgChange(orgId) {
  form.team_id = null
  await loadTeams(orgId)
}

async function loadData() {
  loading.value = true
  try {
    users.value = await userApi.list()
  } finally {
    loading.value = false
  }
}

function openDialog(row = null) {
  editing.value = row
  form.username = row?.username || ''
  form.password = ''
  form.full_name = row?.full_name || ''
  form.email = row?.email || ''
  form.role = row?.role || 'tester'
  form.department_id = row?.department_id ?? null
  form.organization_id = row?.organization_id ?? null
  form.team_id = row?.team_id ?? null
  form.org_role = row?.org_role ?? null
  form.is_active = row?.is_active ?? true
  loadTeams(form.organization_id)
  dialogVisible.value = true
}

function openPasswordDialog(row) {
  passwordTarget.value = row
  passwordForm.password = ''
  passwordDialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (editing.value) {
      const payload = {
        full_name: form.full_name,
        email: form.email.trim() || null,
        role: form.role,
        department_id: form.department_id,
        is_active: form.is_active,
        organization_id: form.organization_id,
        team_id: form.team_id,
      }
      // owner 不经表单改动：仅在选了 admin/member 时才回传组织角色，否则后端沿用原角色
      if (form.org_role === 'admin' || form.org_role === 'member') {
        payload.org_role = form.org_role
      }
      await userApi.update(editing.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await userApi.create({
        username: form.username,
        password: form.password,
        full_name: form.full_name,
        email: form.email.trim() || undefined,
        role: form.role,
        department_id: form.department_id,
        organization_id: form.organization_id,
        team_id: form.team_id,
        org_role: form.org_role || undefined,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function handleResetPassword() {
  await passwordFormRef.value.validate()
  passwordSubmitting.value = true
  try {
    await userApi.resetPassword(passwordTarget.value.id, passwordForm.password)
    ElMessage.success('密码已重置')
    passwordDialogVisible.value = false
  } finally {
    passwordSubmitting.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除用户「${row.username}」？此操作不可恢复。`, '提示', {
    type: 'warning',
  })
  await userApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(async () => {
  if (!userStore.user) {
    await userStore.fetchUser()
  }
  await loadDepartments()
  await loadOrganizations()
  loadData()
})
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>
