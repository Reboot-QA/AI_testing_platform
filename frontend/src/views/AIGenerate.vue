<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="10">
        <el-card>
          <template #header>
            <span
              ><el-icon><MagicStick /></el-icon> 生成配置</span
            >
          </template>
          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-form-item label="项目" prop="project_id">
              <el-select
                v-model="form.project_id"
                filterable
                placeholder="请选择项目"
                data-assistant="ai_generate.project_select"
                style="width: 100%"
                @change="loadRequirements"
              >
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="大模型" prop="provider_id">
              <el-select
                v-model="form.provider_id"
                style="width: 100%"
                placeholder="请选择大模型"
                :loading="providersLoading"
                :disabled="!llmProviders.length"
              >
                <el-option
                  v-for="item in llmProviders"
                  :key="item.id"
                  :label="formatProviderLabel(item)"
                  :value="item.id"
                />
              </el-select>
              <div v-if="!providersLoading && !llmProviders.length" class="form-tip">
                暂无可用模型，请前往
                <el-button link type="primary" @click="$router.push('/system/settings')"
                  >系统管理</el-button
                >
                添加配置
              </div>
            </el-form-item>
            <el-form-item label="关联需求">
              <el-select
                v-model="form.requirement_ids"
                multiple
                collapse-tags
                collapse-tags-tooltip
                clearable
                placeholder="可多选已评审需求，或下方手动输入"
                style="width: 100%"
              >
                <template v-if="selectableCount" #header>
                  <div class="req-select-header">
                    <el-checkbox
                      :model-value="allSelectableSelected"
                      :indeterminate="selectIndeterminate"
                      @change="handleSelectAllRequirements"
                    >
                      全选已评审需求 ({{ selectableCount }})
                    </el-checkbox>
                  </div>
                </template>
                <el-option
                  v-for="r in approvedRequirements"
                  :key="r.id"
                  :label="r.title"
                  :value="r.id"
                >
                  <div class="req-option">
                    <span class="req-option-title">{{ r.title }}</span>
                    <div class="req-option-tags">
                      <el-tag :type="statusType[r.status]" size="small">
                        {{ statusMap[r.status] || r.status }}
                      </el-tag>
                      <el-tag v-if="r.testcase_count > 0" type="info" size="small">
                        已有 {{ r.testcase_count }} 条用例
                      </el-tag>
                    </div>
                  </div>
                </el-option>
              </el-select>
              <div v-if="selectableCount" class="req-select-actions">
                <el-button link type="primary" @click="selectAllRequirements">全选</el-button>
                <el-button link @click="clearSelectedRequirements">清空</el-button>
                <span class="req-select-count"
                  >已选 {{ selectedSelectableCount }}/{{ selectableCount }}</span
                >
              </div>
              <div v-if="form.project_id && !requirements.length" class="form-tip">
                当前项目暂无需求
              </div>
              <div v-else-if="form.project_id && !approvedCount" class="form-tip">
                当前项目暂无已评审需求，请先在需求点中评审后再关联
              </div>
            </el-form-item>
            <el-form-item label="需求描述" prop="requirement_text">
              <el-input
                v-model="form.requirement_text"
                data-assistant="ai_generate.requirement_text"
                type="textarea"
                :rows="8"
                placeholder="输入需求描述，或选择上方关联需求自动填充"
              />
            </el-form-item>
            <el-form-item label="用例类型">
              <el-select v-model="form.case_type" style="width: 100%">
                <el-option label="功能测试" value="functional" />
                <el-option label="接口测试" value="api" />
                <el-option label="性能测试" value="performance" />
                <el-option label="安全测试" value="security" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                data-assistant="ai_generate.generate_btn"
                :loading="generating"
                @click="handleGenerate"
              >
                <el-icon><MagicStick /></el-icon>
                {{ generating ? '正在生成，请稍候...' : '开始生成' }}
              </el-button>
            </el-form-item>
          </el-form>
          <el-alert
            :title="
              mockMode
                ? '当前为 Mock 模式，将使用本地模板生成'
                : '未配置 API Key 的模型无法生成，请先在系统管理中配置 Key 或开启 Mock 模式'
            "
            type="info"
            :closable="false"
            show-icon
          />
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="result-header">
              <span>生成结果</span>
              <el-tag
                v-if="lastMode"
                :type="lastMode === 'llm' ? 'success' : 'warning'"
                size="small"
              >
                {{ lastMode === 'llm' ? 'LLM 模式' : 'Mock 模式' }}
              </el-tag>
              <el-tag v-if="lastProviderName" type="info" size="small">{{
                lastProviderName
              }}</el-tag>
            </div>
          </template>

          <el-empty
            v-if="!results.length && !generating && !errorMessage"
            description="配置需求后点击「开始生成」"
          />

          <el-alert
            v-if="errorMessage && !generating"
            class="error-alert"
            :title="errorMessage"
            type="error"
            show-icon
            :closable="false"
          />

          <div v-if="generating" class="stream-progress">
            <el-progress :percentage="progressPercent" :stroke-width="10" />
            <p class="progress-text">{{ progressMessage }}</p>
            <p v-if="results.length" class="saved-tip">
              已实时写入用例库 {{ results.length }} 条
              <el-button type="primary" link @click="$router.push('/testcases')"
                >前往用例库查看</el-button
              >
            </p>
          </div>

          <div v-if="results.length" class="result-list">
            <el-collapse v-model="activeNames">
              <el-collapse-item
                v-for="item in results"
                :key="item.id"
                :title="`[${item.priority}] ${item.title}`"
                :name="item.id"
              >
                <el-descriptions :column="1" size="small">
                  <el-descriptions-item label="前置条件">{{
                    item.preconditions
                  }}</el-descriptions-item>
                  <el-descriptions-item label="步骤">
                    <pre class="pre-text">{{ item.steps }}</pre>
                  </el-descriptions-item>
                  <el-descriptions-item label="预期结果">{{
                    item.expected_results
                  }}</el-descriptions-item>
                  <el-descriptions-item label="标签">{{ item.tags }}</el-descriptions-item>
                  <el-descriptions-item label="状态">
                    <el-tag type="warning" size="small">待评审</el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </el-collapse-item>
            </el-collapse>
            <div v-if="!generating" class="result-footer">
              <el-text type="success"
                >共生成 {{ results.length }} 条用例，已实时保存至用例库</el-text
              >
              <el-button type="primary" link @click="$router.push('/testcases')"
                >前往用例库评审 →</el-button
              >
            </div>
            <div v-else class="result-footer">
              <el-text type="info">生成中，用例将实时写入用例库...</el-text>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { projectApi, requirementApi, settingsApi } from '@/api'
import { useAiGenerateStore } from '@/stores/aiGenerate'
import {
  registerAssistantHandler,
  unregisterAssistantHandler,
} from '@/utils/assistantActionRegistry'
import type { LlmProvider, Project, Requirement } from '@/types/common'
import type { FormInstance, FormRules } from '@/types/element-plus'

interface GenerateForm {
  project_id: number | null
  provider_id: number | null
  requirement_ids: number[]
  requirement_text: string
  case_type: string
}

const aiStore = useAiGenerateStore()
const {
  results,
  generating,
  progressMessage,
  progressCurrent,
  progressTotal,
  lastMode,
  lastProviderName,
  errorMessage,
  activeNames,
} = storeToRefs(aiStore)

const projects = ref<Project[]>([])
const requirements = ref<Requirement[]>([])
const llmProviders = ref<LlmProvider[]>([])
const providersLoading = ref(false)
const mockMode = ref(false)
const formRef = ref<FormInstance>()

const form = reactive<GenerateForm>({
  project_id: null,
  provider_id: null,
  requirement_ids: [],
  requirement_text: '',
  case_type: 'functional',
})

const DEFAULT_GENERATE_COUNT = 5
const CASES_PER_REQUIREMENT = 3
const MAX_GENERATE_COUNT = 100

function resolveGenerateCount(requirementIds: number[]) {
  if (!requirementIds.length) return DEFAULT_GENERATE_COUNT
  return Math.min(requirementIds.length * CASES_PER_REQUIREMENT, MAX_GENERATE_COUNT)
}

const rules: FormRules<GenerateForm> = {
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  provider_id: [{ required: true, message: '请选择大模型', trigger: 'change' }],
}

const progressPercent = computed(() => {
  if (!progressTotal.value) return generating.value ? 5 : 0
  return Math.min(100, Math.round((progressCurrent.value / progressTotal.value) * 100))
})

const statusMap: Record<string, string> = { draft: '草稿', approved: '已评审', closed: '已关闭' }
const statusType: Record<string, 'info' | 'success' | 'warning'> = {
  draft: 'info',
  approved: 'success',
  closed: 'warning',
}
const approvedRequirements = computed(() =>
  requirements.value.filter((r) => r.status === 'approved'),
)
const approvedCount = computed(() => approvedRequirements.value.length)
const selectableCount = computed(() => approvedCount.value)
const selectableIds = computed(() => approvedRequirements.value.map((r) => r.id))
const selectedSelectableCount = computed(
  () => selectableIds.value.filter((id) => form.requirement_ids.includes(id)).length,
)
const allSelectableSelected = computed(
  () =>
    selectableIds.value.length > 0 && selectedSelectableCount.value === selectableIds.value.length,
)
const selectIndeterminate = computed(
  () =>
    selectedSelectableCount.value > 0 && selectedSelectableCount.value < selectableIds.value.length,
)

function handleSelectAllRequirements(checked: boolean) {
  if (checked) {
    form.requirement_ids = [...selectableIds.value]
  } else {
    form.requirement_ids = form.requirement_ids.filter((id) => !selectableIds.value.includes(id))
  }
}

function selectAllRequirements() {
  form.requirement_ids = [...selectableIds.value]
}

function clearSelectedRequirements() {
  form.requirement_ids = []
}

watch(
  () => form.requirement_ids,
  () => fillFromRequirement(),
  { deep: true },
)

function fillFromRequirement() {
  if (!form.requirement_ids.length) {
    form.requirement_text = ''
    return
  }
  const texts = form.requirement_ids
    .map((id) => {
      const req = requirements.value.find((r) => r.id === id)
      return req ? `【${req.title}】\n${req.description || ''}` : ''
    })
    .filter(Boolean)
  form.requirement_text = texts.join('\n\n')
}

async function loadProjects() {
  projects.value = await projectApi.list()
  if (projects.value.length) {
    form.project_id = projects.value[0].id
    loadRequirements()
  }
}

async function loadRequirements() {
  if (!form.project_id) return
  requirements.value = await requirementApi.list(form.project_id)
  form.requirement_ids = []
  form.requirement_text = ''
}

function formatProviderLabel(item: LlmProvider) {
  const tags = []
  if (item.is_default) tags.push('默认')
  if (!item.api_key_configured) tags.push('未配置Key')
  const suffix = tags.length ? ` (${tags.join(' / ')})` : ''
  return `${item.name}${suffix}`
}

async function loadProviders() {
  providersLoading.value = true
  try {
    const data = await settingsApi.getLLMOptions()
    llmProviders.value = data.providers || []
    mockMode.value = data.mock_mode
    if (data.active_provider_id) {
      form.provider_id = data.active_provider_id
    } else if (llmProviders.value.length) {
      form.provider_id = llmProviders.value[0].id
    }
  } finally {
    providersLoading.value = false
  }
}

async function handleGenerate() {
  await formRef.value?.validate()
  if (!form.requirement_ids.length && !form.requirement_text.trim()) {
    ElMessage.warning('请选择关联需求或输入需求描述')
    return
  }
  if (form.requirement_ids.length) {
    requirements.value = await requirementApi.list(form.project_id!)
    const blocked = form.requirement_ids
      .map((id) => requirements.value.find((r) => r.id === id))
      .filter((r) => r && r.status !== 'approved')
    if (blocked.length) {
      ElMessage.warning(`需求「${blocked.map((r) => r.title).join('、')}」未评审，不能生成用例`)
      return
    }
  }
  if (!mockMode.value) {
    const provider = llmProviders.value.find((item) => item.id === form.provider_id)
    if (provider && !provider.api_key_configured) {
      ElMessage.warning('当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式')
      return
    }
  }

  const generateCount = resolveGenerateCount(form.requirement_ids)
  await aiStore.startGeneration({
    project_id: form.project_id!,
    provider_id: form.provider_id!,
    requirement_ids: form.requirement_ids,
    requirement_text: form.requirement_text,
    case_type: form.case_type,
    count: generateCount,
  })
}

onMounted(async () => {
  registerAssistantHandler('aiGenerate.prepareDemo', async () => {
    if (!projects.value.length) {
      await loadProjects()
    }
    if (!projects.value.length) {
      throw new Error('请先创建项目')
    }
    form.project_id = projects.value[0].id
    await loadRequirements()
    if (!llmProviders.value.length) {
      await loadProviders()
    }
    if (llmProviders.value.length && !form.provider_id) {
      form.provider_id =
        llmProviders.value.find((item) => item.is_default)?.id || llmProviders.value[0].id
    }
    form.requirement_text = '演示需求：用户可以使用账号密码登录系统，登录成功后进入首页。'
    form.case_type = 'functional'
    await nextTick()
  })

  registerAssistantHandler('aiGenerate.startGenerate', async () => {
    if (generating.value) {
      return
    }
    if (!projects.value.length) {
      await loadProjects()
    }
    if (!form.project_id && projects.value.length) {
      form.project_id = projects.value[0].id
      await loadRequirements()
    }
    if (!llmProviders.value.length) {
      await loadProviders()
    }
    if (!form.provider_id && llmProviders.value.length) {
      form.provider_id =
        llmProviders.value.find((item) => item.is_default)?.id || llmProviders.value[0].id
    }
    if (!form.requirement_text.trim()) {
      throw new Error('请先填写需求描述')
    }
    if (!form.project_id || !form.provider_id) {
      throw new Error('请完善项目与大模型配置')
    }
    await nextTick()
    const btn = document.querySelector('[data-assistant="ai_generate.generate_btn"]')
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
    }
    await handleGenerate()
  })

  await Promise.all([loadProjects(), loadProviders()])
})

onUnmounted(() => {
  unregisterAssistantHandler('aiGenerate.prepareDemo')
  unregisterAssistantHandler('aiGenerate.startGenerate')
})
</script>

<style scoped>
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.result-list {
  max-height: 600px;
  overflow-y: auto;
}

.result-footer {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.pre-text {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
}

.form-tip {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}

.req-select-header {
  padding: 4px 12px 8px;
  border-bottom: 1px solid #ebeef5;
}

.req-select-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.req-select-count {
  color: #909399;
  font-size: 12px;
}

.req-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.req-option-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.req-option-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.stream-progress {
  margin-bottom: 16px;
}

.error-alert {
  margin-bottom: 16px;
}

.progress-text {
  margin: 10px 0 0;
  color: #606266;
  font-size: 13px;
}

.saved-tip {
  margin: 8px 0 0;
  color: #67c23a;
  font-size: 13px;
}
</style>
