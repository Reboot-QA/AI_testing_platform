<template>
  <div class="system-settings">
    <el-card shadow="never" class="global-card">
      <template #header>
        <div class="card-header">
          <span>全局设置</span>
          <el-tag :type="settings.mock_mode ? 'info' : 'success'" size="small">
            {{ settings.mock_mode ? 'Mock 模式' : 'LLM 模式' }}
          </el-tag>
        </div>
      </template>
      <div class="global-row">
        <span>Mock 模式</span>
        <el-switch
          v-model="settings.mock_mode"
          active-text="开启"
          inactive-text="关闭"
          :loading="mockSaving"
          @change="handleMockChange"
        />
        <span class="form-tip">开启后所有 AI 生成使用本地模板，不调用大模型</span>
      </div>
    </el-card>

    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>大模型配置</span>
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon> 添加模型
          </el-button>
        </div>
      </template>

      <el-table :data="providers" stripe border empty-text="暂无模型配置，请点击添加模型">
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="model" label="模型" min-width="140" show-overflow-tooltip />
        <el-table-column prop="api_base" label="API Base URL" min-width="220" show-overflow-tooltip />
        <el-table-column label="API Key" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.api_key_configured" type="success" size="small">已配置</el-tag>
            <el-tag v-else type="warning" size="small">未配置</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="primary" size="small">当前使用</el-tag>
            <el-tag v-else-if="row.enabled" type="info" size="small">可用</el-tag>
            <el-tag v-else type="danger" size="small">已禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="row.is_default" @click="handleActivate(row.id)">
              设为当前
            </el-button>
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="primary" :loading="testingId === row.id" @click="handleTest(row)">
              测试
            </el-button>
            <el-popconfirm title="确认删除该模型配置？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-alert
        class="preset-alert"
        title="常用免费模型：智谱 glm-4-flash、硅基流动 Qwen/Qwen2.5-7B-Instruct"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑模型' : '添加模型'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：智谱 GLM-4-Flash" />
        </el-form-item>
        <el-form-item label="API Base URL" prop="api_base">
          <el-input v-model="form.api_base" placeholder="https://open.bigmodel.cn/api/paas/v4" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="editing?.api_key_configured ? `已配置 (${editing.api_key_masked})，留空则不修改` : '请输入 API Key'"
          />
        </el-form-item>
        <el-form-item label="模型名称" prop="model">
          <el-input v-model="form.model" placeholder="glm-4-flash" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="设为当前">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
        <el-button :loading="dialogTesting" @click="handleDialogTest">测试连接</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { settingsApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const mockSaving = ref(false)
const testingId = ref(null)
const dialogTesting = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)
const formRef = ref()

const settings = reactive({
  mock_mode: true,
  active_provider_id: null,
})

const providers = ref([])

const form = reactive({
  name: '',
  api_base: '',
  api_key: '',
  model: '',
  enabled: true,
  is_default: false,
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  api_base: [{ required: true, message: '请输入 API Base URL', trigger: 'blur' }],
  model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

async function loadSettings() {
  loading.value = true
  try {
    const data = await settingsApi.getLLM()
    settings.mock_mode = data.mock_mode
    settings.active_provider_id = data.active_provider_id
    providers.value = data.providers || []
  } finally {
    loading.value = false
  }
}

async function handleMockChange(value) {
  mockSaving.value = true
  try {
    const data = await settingsApi.updateMockMode(value)
    settings.mock_mode = data.mock_mode
    settings.active_provider_id = data.active_provider_id
    providers.value = data.providers || []
    ElMessage.success(value ? '已开启 Mock 模式' : '已关闭 Mock 模式')
  } catch {
    settings.mock_mode = !value
  } finally {
    mockSaving.value = false
  }
}

function openDialog(row = null) {
  editing.value = row
  if (row) {
    Object.assign(form, {
      name: row.name,
      api_base: row.api_base,
      api_key: '',
      model: row.model,
      enabled: row.enabled,
      is_default: row.is_default,
    })
  } else {
    Object.assign(form, {
      name: '',
      api_base: 'https://open.bigmodel.cn/api/paas/v4',
      api_key: '',
      model: 'glm-4-flash',
      enabled: true,
      is_default: providers.value.length === 0,
    })
  }
  dialogVisible.value = true
}

function buildPayload() {
  const payload = {
    name: form.name,
    api_base: form.api_base,
    model: form.model,
    enabled: form.enabled,
    is_default: form.is_default,
  }
  if (form.api_key.trim()) {
    payload.api_key = form.api_key.trim()
  }
  return payload
}

async function handleSubmit() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editing.value) {
      await settingsApi.updateProvider(editing.value.id, buildPayload())
      ElMessage.success('模型配置已更新')
    } else {
      await settingsApi.createProvider(buildPayload())
      ElMessage.success('模型配置已添加')
    }
    dialogVisible.value = false
    await loadSettings()
  } finally {
    saving.value = false
  }
}

async function handleActivate(id) {
  await settingsApi.activateProvider(id)
  ElMessage.success('已切换当前使用模型')
  await loadSettings()
}

async function handleDelete(id) {
  await settingsApi.deleteProvider(id)
  ElMessage.success('已删除')
  await loadSettings()
}

async function handleTest(row) {
  testingId.value = row.id
  try {
    const result = await settingsApi.testLLM({ provider_id: row.id })
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.warning(result.message)
    }
  } finally {
    testingId.value = null
  }
}

async function handleDialogTest() {
  await formRef.value.validate()
  dialogTesting.value = true
  try {
    const payload = {
      api_base: form.api_base,
      model: form.model,
      mock_mode: settings.mock_mode,
    }
    if (form.api_key.trim()) {
      payload.api_key = form.api_key.trim()
    } else if (editing.value) {
      payload.provider_id = editing.value.id
    }
    const result = await settingsApi.testLLM(payload)
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.warning(result.message)
    }
  } finally {
    dialogTesting.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.system-settings {
  max-width: 1100px;
}

.global-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.global-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-tip {
  color: #909399;
  font-size: 13px;
}

.preset-alert {
  margin-top: 16px;
}
</style>
