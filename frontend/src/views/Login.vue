<template>
  <div class="min-h-screen w-full lg:grid lg:grid-cols-2">
    <!-- 左：品牌区（大屏可见） -->
    <div
      class="relative hidden flex-col justify-between overflow-hidden p-12 text-white lg:flex"
      style="background: linear-gradient(150deg, #0f2544 0%, #1a365d 45%, #2c5282 100%)"
    >
      <div class="flex items-center gap-3">
        <el-icon :size="30"><Cpu /></el-icon>
        <span class="text-lg font-semibold tracking-wide">AI 质量平台</span>
      </div>

      <div class="max-w-md">
        <h2 class="text-3xl font-bold leading-snug">基于大语言模型的<br />智能测试管理平台</h2>
        <p class="mt-4 text-sm leading-relaxed text-white/70">
          需求分析、用例生成、手工执行到接口自动化，一站式覆盖测试全生命周期。
        </p>
        <ul class="mt-8 space-y-3 text-sm text-white/85">
          <li class="flex items-center gap-2">
            <el-icon color="#7fd1ae"><CircleCheck /></el-icon> LLM 智能用例生成
          </li>
          <li class="flex items-center gap-2">
            <el-icon color="#7fd1ae"><CircleCheck /></el-icon> 需求-用例全生命周期管理
          </li>
          <li class="flex items-center gap-2">
            <el-icon color="#7fd1ae"><CircleCheck /></el-icon> Apifox 式接口自动化编排
          </li>
        </ul>
      </div>

      <p class="text-xs text-white/50">© {{ year }} AI 质量平台</p>
    </div>

    <!-- 右：登录表单 -->
    <div class="flex min-h-screen items-center justify-center bg-muted/40 p-6 lg:min-h-full">
      <div class="w-full max-w-sm">
        <div class="mb-8 text-center lg:hidden">
          <el-icon :size="40" color="#1a365d"><Cpu /></el-icon>
          <h1 class="mt-2 text-xl font-bold text-foreground">AI 质量平台</h1>
        </div>

        <div class="rounded-xl border border-border bg-card p-8 shadow-lg">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-foreground">欢迎回来</h1>
            <p class="mt-1 text-sm text-muted-foreground">请登录以继续使用平台</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                prefix-icon="User"
                size="large"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                prefix-icon="Lock"
                size="large"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <Button
              type="button"
              class="mt-2 h-11 w-full text-base cursor-pointer"
              :disabled="loading"
              @click="handleLogin"
            >
              <el-icon v-if="loading" class="is-loading"><Loading /></el-icon>
              {{ loading ? '登录中…' : '登 录' }}
            </Button>
          </el-form>

          <div
            class="mt-6 rounded-md border border-border bg-muted/50 px-3 py-2 text-center text-xs text-muted-foreground"
          >
            演示账号 <span class="font-medium text-foreground">admin</span> / 密码
            <span class="font-medium text-foreground">admin123</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { Button } from '@/components/ui/button'
import type { FormInstance, FormRules } from '@/types/element-plus'

interface LoginForm {
  username: string
  password: string
}

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const year = new Date().getFullYear()

const form = reactive<LoginForm>({
  username: 'admin',
  password: 'admin123',
})

const rules: FormRules<LoginForm> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(() => {
  userStore.logout()
})

async function handleLogin() {
  await formRef.value?.validate()
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    if (userStore.mustChangePassword) {
      router.push('/force-change-password')
    } else {
      router.push('/dashboard')
    }
  } finally {
    loading.value = false
  }
}
</script>
