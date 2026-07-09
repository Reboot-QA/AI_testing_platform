<template>
  <div class="force-change-page">
    <div class="force-change-card">
      <div class="header">
        <el-icon :size="36" color="#1a365d"><Lock /></el-icon>
        <h1>修改密码</h1>
        <p>管理员已重置您的密码，请先设置新密码后再继续使用系统</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" @submit.prevent="handleSubmit">
        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="form.old_password"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="至少 6 位"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="再次输入新密码"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="submitting" class="submit-btn" @click="handleSubmit">
          确认修改
        </el-button>
      </el-form>

      <div class="footer">
        <el-button link type="danger" @click="handleLogout">退出登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const submitting = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const validateConfirmPassword = (_rule, value, callback) => {
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

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
}

async function handleSubmit() {
  await formRef.value.validate()
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
  background: linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #4299e1 100%);
}

.force-change-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.header {
  text-align: center;
  margin-bottom: 28px;
}

.header h1 {
  margin: 12px 0 8px;
  font-size: 22px;
  color: #1a365d;
}

.header p {
  margin: 0;
  font-size: 14px;
  color: #718096;
  line-height: 1.5;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.footer {
  margin-top: 16px;
  text-align: center;
}
</style>
