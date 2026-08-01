<template>
  <div class="user-profile">
    <PageCard>
      <div class="profile-header">
        <div class="profile-avatar">{{ avatarText }}</div>
        <div>
          <h1 class="profile-title">个人资料</h1>
          <p class="profile-subtitle">管理您的基本信息与登录密码</p>
        </div>
      </div>

      <el-divider />

      <section class="profile-section">
        <h2 class="section-title">基本信息</h2>
        <el-form
          ref="profileFormRef"
          :model="profileForm"
          :rules="profileRules"
          label-width="88px"
          class="profile-form"
        >
          <el-form-item label="用户名">
            <el-input :maxlength="TITLE_MAX_LEN" :model-value="userStore.user?.username" disabled />
          </el-form-item>
          <el-form-item label="姓名" prop="full_name">
            <el-input
              v-model="profileForm.full_name"
              :maxlength="TITLE_MAX_LEN"
              placeholder="选填"
            />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="profileForm.email" :maxlength="TITLE_MAX_LEN" placeholder="选填" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input
              :maxlength="VALUE_MAX_LEN"
              :model-value="userStore.user?.department_name || '-'"
              disabled
            />
          </el-form-item>
          <el-form-item label="角色">
            <el-input :maxlength="VALUE_MAX_LEN" :model-value="roleLabel" disabled />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="profileSaving" @click="saveProfile">
              保存资料
            </el-button>
          </el-form-item>
        </el-form>
      </section>

      <el-divider />

      <section class="profile-section">
        <h2 class="section-title">修改密码</h2>
        <el-form
          ref="passwordFormRef"
          :model="passwordForm"
          :rules="passwordRules"
          label-width="88px"
          class="profile-form"
          @submit.prevent="changePassword"
        >
          <el-form-item label="原密码" prop="old_password">
            <el-input
              v-model="passwordForm.old_password"
              :maxlength="SECRET_MAX_LEN"
              type="password"
              show-password
              autocomplete="current-password"
              placeholder="请输入当前密码"
            />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input
              v-model="passwordForm.new_password"
              :maxlength="SECRET_MAX_LEN"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="至少 6 位"
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input
              v-model="passwordForm.confirm_password"
              :maxlength="SECRET_MAX_LEN"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="再次输入新密码"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="passwordSaving" @click="changePassword">
              修改密码
            </el-button>
          </el-form-item>
        </el-form>
      </section>
    </PageCard>
  </div>
</template>

<script setup lang="ts">
import { SECRET_MAX_LEN, TITLE_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import PageCard from '@/components/PageCard.vue'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'
import type { FormInstance, FormRuleItem, FormRules } from '@/types/element-plus'

interface ProfileForm {
  full_name: string
  email: string
}

interface PasswordForm {
  old_password: string
  new_password: string
  confirm_password: string
}

const userStore = useUserStore()
const profileFormRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()
const profileSaving = ref(false)
const passwordSaving = ref(false)

const profileForm = reactive<ProfileForm>({
  full_name: '',
  email: '',
})

const passwordForm = reactive<PasswordForm>({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const avatarText = computed(() => (userStore.user?.username || 'A').charAt(0).toUpperCase())

const roleLabel = computed(() => {
  if (userStore.user?.role === 'admin') return '管理员'
  return '测试人员'
})

watch(
  () => userStore.user,
  (user) => {
    profileForm.full_name = user?.full_name || ''
    profileForm.email = user?.email || ''
  },
  { immediate: true },
)

const profileRules: FormRules<ProfileForm> = {
  email: [
    {
      type: 'email',
      message: '请输入有效邮箱',
      trigger: 'blur',
    },
  ],
}

const validateConfirmPassword: NonNullable<FormRuleItem['validator']> = (
  _rule,
  value,
  callback,
) => {
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

const passwordRules: FormRules<PasswordForm> = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
}

async function saveProfile() {
  await profileFormRef.value?.validate()
  profileSaving.value = true
  try {
    await userStore.updateProfile({
      full_name: profileForm.full_name.trim() || null,
      email: profileForm.email.trim() || null,
    })
    ElMessage.success('资料已保存')
  } finally {
    profileSaving.value = false
  }
}

async function changePassword() {
  await passwordFormRef.value?.validate()
  passwordSaving.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    await userStore.fetchUser()
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    passwordFormRef.value?.clearValidate()
    ElMessage.success('密码已修改')
  } finally {
    passwordSaving.value = false
  }
}
</script>

<style scoped>
.user-profile {
  height: 100%;
  overflow: auto;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.profile-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--ax-raw-hex-2b6cff), var(--ax-raw-hex-722ed1));
  color: var(--ax-raw-hex-fff);
  font-size: 22px;
  font-weight: 600;
  flex-shrink: 0;
}

.profile-title {
  margin: 0 0 4px;
  font-size: 20px;
  color: var(--ax-text);
}

.profile-subtitle {
  margin: 0;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-muted);
}

.profile-section {
  max-width: 520px;
}

.section-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--ax-text);
}

.profile-form {
  margin-top: 4px;
}
</style>
