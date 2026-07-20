<template>
  <PageCard fill>
    <template #toolbar>
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 添加用户
      </el-button>
    </template>

    <div class="table-fill">
      <el-table v-loading="loading" :data="users" stripe border height="100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="full_name" label="姓名" width="140">
          <template #default="{ row }">{{ row.full_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>
        <el-table-column prop="department_name" label="部门" width="140">
          <template #default="{ row }">{{ row.department_name || '-' }}</template>
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
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '添加用户'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username" required>
          <el-input
            v-model="form.username"
            :disabled="!!editing"
            placeholder="仅支持字母、数字、下划线"
          />
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
        <el-form-item label="部门" prop="department_id">
          <el-select
            v-model="form.department_id"
            placeholder="请选择部门"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
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
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="90px"
      >
        <el-form-item label="用户">
          <el-input :model-value="passwordTarget?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="passwordForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSubmitting" @click="handleResetPassword"
          >确定</el-button
        >
      </template>
    </el-dialog>
  </PageCard>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userApi, departmentApi } from '@/api'
import { formatBeijingTime } from '@/utils/datetime'
import { useUserStore } from '@/stores/user'
import PageCard from '@/components/PageCard.vue'
import type { DateInput, Department, User } from '@/types/common'
import type { FormInstance, FormRuleItem, FormRules } from '@/types/element-plus'

interface UserForm {
  username: string
  password: string
  full_name: string
  email: string
  department_id: number | null
  is_active: boolean
}

interface ResetPasswordForm {
  password: string
}

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

const users = ref<User[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const submitting = ref(false)
const passwordSubmitting = ref(false)
const editing = ref<User | null>(null)
const passwordTarget = ref<User | null>(null)
const formRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()

const USERNAME_PATTERN = /^[A-Za-z0-9_]+$/

const form = reactive<UserForm>({
  username: '',
  password: '',
  full_name: '',
  email: '',
  department_id: null,
  is_active: true,
})

const validateUsername: NonNullable<FormRuleItem['validator']> = (_rule, value, callback) => {
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

const validateEmail: NonNullable<FormRuleItem['validator']> = (_rule, value, callback) => {
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

const passwordForm = reactive<ResetPasswordForm>({
  password: '',
})

const rules: FormRules<UserForm> = {
  username: [{ required: true, validator: validateUsername, trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  email: [{ validator: validateEmail, trigger: 'blur' }],
  department_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
}

const passwordRules: FormRules<ResetPasswordForm> = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

function formatTime(value: DateInput) {
  return formatBeijingTime(value)
}

async function loadDepartments() {
  departments.value = await departmentApi.list()
}

async function loadData() {
  loading.value = true
  try {
    users.value = await userApi.list()
  } finally {
    loading.value = false
  }
}

function openDialog(row: User | null = null) {
  editing.value = row
  form.username = row?.username || ''
  form.password = ''
  form.full_name = row?.full_name || ''
  form.email = row?.email || ''
  form.department_id = row?.department_id ?? null
  form.is_active = row?.is_active ?? true
  dialogVisible.value = true
}

function openPasswordDialog(row: User) {
  passwordTarget.value = row
  passwordForm.password = ''
  passwordDialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value?.validate()
  submitting.value = true
  try {
    if (editing.value) {
      await userApi.update(editing.value.id, {
        full_name: form.full_name,
        email: form.email.trim() || null,
        department_id: form.department_id,
        is_active: form.is_active,
      })
      ElMessage.success('更新成功')
    } else {
      await userApi.create({
        username: form.username,
        password: form.password,
        full_name: form.full_name,
        email: form.email.trim() || undefined,
        department_id: form.department_id,
        role: 'tester',
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
  await passwordFormRef.value?.validate()
  passwordSubmitting.value = true
  try {
    await userApi.resetPassword(passwordTarget.value!.id, passwordForm.password)
    ElMessage.success('密码已重置')
    passwordDialogVisible.value = false
  } finally {
    passwordSubmitting.value = false
  }
}

async function handleDelete(row: User) {
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
  loadData()
})
</script>
