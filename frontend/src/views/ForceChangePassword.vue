<template>
  <div class="force-change-page">
    <div class="force-change-card">
      <div class="header">
        <el-icon :size="36" color="#1a365d"><Lock /></el-icon>
        <h1>修改密码</h1>
        <p>管理员已重置您的密码，请先设置新密码后再继续使用系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="form.old_password"
            :maxlength="SECRET_MAX_LEN"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="form.new_password"
            :maxlength="SECRET_MAX_LEN"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="至少 6 位"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            :maxlength="SECRET_MAX_LEN"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="再次输入新密码"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          class="submit-btn"
          @click="handleSubmit"
        >
          确认修改
        </el-button>
      </el-form>

      <div class="footer">
        <el-button link type="danger" @click="handleLogout">退出登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SECRET_MAX_LEN } from '@/constants/limits'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'
import type { FormInstance, FormRuleItem, FormRules } from '@/types/element-plus'

interface PasswordForm {
  old_password: string
  new_password: string
  confirm_password: string
}

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive<PasswordForm>({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const validateConfirmPassword: NonNullable<FormRuleItem['validator']> = (
  _rule,
  value,
  callback,
) => {
  if (!value) {
    callback(new Error('请再次输入新密码'))
    return
  }
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const rules: FormRules<PasswordForm> = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
}

async function handleSubmit() {
  await formRef.value?.validate()
  submitting.value = true
  try {
    await authApi.changePassword({
      old_password: form.old_password,
      new_password: form.new_password,
    })
    await userStore.fetchUser()
    ElMessage.success('密码已修改')
    router.push('/dashboard')
  } finally {
    submitting.value = false
  }
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.force-change-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    var(--ax-brand-active) 0%,
    var(--ax-brand) 50%,
    var(--ax-brand-hover) 100%
  );
}

.force-change-card {
  width: 420px;
  padding: var(--ax-space-10);
  background: var(--ax-bg);
  border-radius: var(--ax-radius-xl);
  box-shadow: var(--ax-shadow-lg);
}

.header {
  text-align: center;
  margin-bottom: var(--ax-space-6);
}

.header h1 {
  margin: var(--ax-space-3) 0 var(--ax-space-2);
  font-size: var(--ax-text-heading-size);
  color: var(--ax-text);
}

.header p {
  margin: 0;
  font-size: var(--ax-text-body-size);
  color: var(--ax-text-secondary);
  line-height: var(--ax-text-body-line);
}

.submit-btn {
  width: 100%;
  margin-top: var(--ax-space-2);
}

.footer {
  margin-top: var(--ax-space-4);
  text-align: center;
}
</style>
