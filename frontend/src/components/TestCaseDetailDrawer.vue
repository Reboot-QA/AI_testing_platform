<template>
  <el-drawer v-model="visible" size="560px" @closed="handleClosed">
    <template #header>
      <div class="drawer-header">
        <span>用例详情</span>
        <el-button v-if="testcase && !editing" type="primary" plain @click="startEdit">
          编辑
        </el-button>
      </div>
    </template>

    <template v-if="testcase">
      <el-form v-if="editing" ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="form.title"
            :maxlength="REQ_CASE_TITLE_MAX_LEN"
            show-word-limit
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
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option v-for="item in priorities" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联需求">
          <el-select
            v-model="form.requirement_id"
            clearable
            filterable
            :loading="requirementsLoading"
            placeholder="不关联需求"
            style="width: 100%"
          >
            <el-option
              v-for="item in requirements"
              :key="item.id"
              :label="item.title"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="评审状态">
          <el-select v-model="form.review_status" style="width: 100%">
            <el-option
              v-for="item in reviewOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="前置条件">
          <el-input
            v-model="form.preconditions"
            :maxlength="LONG_TEXT_MAX_LEN"
            type="textarea"
            :rows="2"
          />
        </el-form-item>
        <el-form-item label="测试步骤">
          <el-input v-model="form.steps" :maxlength="LONG_TEXT_MAX_LEN" type="textarea" :rows="5" />
        </el-form-item>
        <el-form-item label="预期结果">
          <el-input
            v-model="form.expected_results"
            :maxlength="LONG_TEXT_MAX_LEN"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" :maxlength="VALUE_MAX_LEN" placeholder="逗号分隔" />
        </el-form-item>

        <div class="edit-actions">
          <el-button @click="cancelEdit">取消</el-button>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </div>
      </el-form>

      <el-descriptions v-else :column="1" border>
        <el-descriptions-item label="标题">{{ testcase.title }}</el-descriptions-item>
        <el-descriptions-item label="所属项目">{{
          testcase.project_name || '-'
        }}</el-descriptions-item>
        <el-descriptions-item label="需求点">
          {{ testcase.requirement_title || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="优先级">{{ testcase.priority }}</el-descriptions-item>
        <el-descriptions-item label="类型">
          {{ formatCaseTypeLabel(testcase.case_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="来源">
          {{ testcase.source === 'ai_generated' ? 'AI生成' : '手动' }}
        </el-descriptions-item>
        <el-descriptions-item label="评审状态">
          {{ reviewLabels[testcase.review_status as ReviewStatus] || testcase.review_status }}
        </el-descriptions-item>
        <el-descriptions-item label="创建人">{{
          testcase.creator_name || '-'
        }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatBeijingTime(testcase.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="前置条件">
          {{ testcase.preconditions || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="测试步骤">
          <pre class="pre-text">{{ testcase.steps || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="预期结果">
          <pre class="pre-text">{{ testcase.expected_results || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="标签">{{ testcase.tags || '-' }}</el-descriptions-item>
      </el-descriptions>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { LONG_TEXT_MAX_LEN, REQ_CASE_TITLE_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from '@/types/element-plus'
import type { Schemas } from '@/api/types'
import { requirementApi, testcaseApi } from '@/api'
import { formatBeijingTime } from '@/utils/datetime'
import { formatCaseTypeLabel } from '@/utils/caseType'
import type { ReviewStatus, TestCase } from '@/types/common'

interface EditableTestCase {
  title: string
  case_type: string
  priority: string
  requirement_id: number | null
  review_status: ReviewStatus
  preconditions: string
  steps: string
  expected_results: string
  tags: string
}

const props = defineProps<{
  modelValue: boolean
  testcase: TestCase | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [testcase: TestCase]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const priorities = ['P0', 'P1', 'P2', 'P3']
const reviewOptions: Array<{ label: string; value: ReviewStatus }> = [
  { label: '草稿', value: 'draft' },
  { label: '待评审', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已驳回', value: 'rejected' },
]
const reviewLabels = Object.fromEntries(
  reviewOptions.map((item) => [item.value, item.label]),
) as Record<ReviewStatus, string>

const editing = ref(false)
const saving = ref(false)
const requirementsLoading = ref(false)
const requirements = ref<Schemas['RequirementOut'][]>([])
const formRef = ref<FormInstance>()
const form = reactive<EditableTestCase>({
  title: '',
  case_type: 'functional',
  priority: 'P1',
  requirement_id: null,
  review_status: 'draft',
  preconditions: '',
  steps: '',
  expected_results: '',
  tags: '',
})
const rules: FormRules<EditableTestCase> = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    {
      max: REQ_CASE_TITLE_MAX_LEN,
      message: `标题不能超过 ${REQ_CASE_TITLE_MAX_LEN} 字`,
      trigger: 'blur',
    },
  ],
}

function fillForm(testcase: TestCase) {
  form.title = testcase.title
  form.case_type = testcase.case_type
  form.priority = testcase.priority
  form.requirement_id = testcase.requirement_id ?? null
  form.review_status = testcase.review_status as ReviewStatus
  form.preconditions = testcase.preconditions || ''
  form.steps = testcase.steps || ''
  form.expected_results = testcase.expected_results || ''
  form.tags = testcase.tags || ''
}

async function loadRequirements() {
  if (!props.testcase) return
  requirementsLoading.value = true
  try {
    requirements.value = await requirementApi.list(props.testcase.project_id)
  } finally {
    requirementsLoading.value = false
  }
}

async function startEdit() {
  if (!props.testcase) return
  fillForm(props.testcase)
  editing.value = true
  await loadRequirements()
}

function cancelEdit() {
  if (props.testcase) fillForm(props.testcase)
  editing.value = false
}

async function save() {
  if (!props.testcase) return
  await formRef.value?.validate()
  saving.value = true
  try {
    const updated = await testcaseApi.update(props.testcase.id, { ...form })
    emit('saved', updated)
    editing.value = false
    ElMessage.success('更新成功')
  } finally {
    saving.value = false
  }
}

function handleClosed() {
  editing.value = false
  requirements.value = []
}

watch(
  () => props.testcase,
  (testcase) => {
    if (testcase) fillForm(testcase)
    editing.value = false
  },
)
</script>

<style scoped>
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  color: var(--ax-text);
  font-weight: 600;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--ax-space-2);
  padding-top: var(--ax-space-2);
}

.pre-text {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: var(--ax-text-body-size);
  line-height: var(--ax-leading-relaxed);
}
</style>
