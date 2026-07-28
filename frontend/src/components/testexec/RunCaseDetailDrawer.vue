<template>
  <el-drawer
    :model-value="modelValue"
    title="用例执行详情"
    size="560px"
    append-to-body
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <template v-if="caseItem">
      <div class="case-detail-head">
        <h4 class="case-title">{{ caseItem.case_title }}</h4>
        <div class="case-tags">
          <el-tag v-if="caseItem.case_priority" size="small">{{ caseItem.case_priority }}</el-tag>
          <el-tag size="small" type="info">{{ formatCaseTypeLabel(caseItem.case_type) }}</el-tag>
          <el-tag :type="resultType[caseItem.result]" size="small">
            {{ resultLabel[caseItem.result] || caseItem.result }}
          </el-tag>
        </div>
      </div>

      <el-descriptions :column="1" border class="case-meta">
        <el-descriptions-item label="执行人">{{
          caseItem.executor_name || '-'
        }}</el-descriptions-item>
        <el-descriptions-item label="执行时间">{{
          formatTime(caseItem.executed_at)
        }}</el-descriptions-item>
      </el-descriptions>

      <div class="field-block">
        <div class="field-label">前置条件</div>
        <pre class="text-block">{{ caseItem.preconditions || '无' }}</pre>
      </div>
      <div class="field-block">
        <div class="field-label">测试步骤</div>
        <pre class="text-block">{{ caseItem.steps || '无' }}</pre>
      </div>
      <div class="field-block">
        <div class="field-label">预期结果</div>
        <pre class="text-block">{{ caseItem.expected_results || '无' }}</pre>
      </div>
      <div class="field-block">
        <div class="field-label">实际结果</div>
        <pre class="text-block">{{ caseItem.actual_result || '无' }}</pre>
      </div>
      <div class="field-block">
        <div class="field-label">备注</div>
        <pre class="text-block">{{ caseItem.remark || '无' }}</pre>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import type { Schemas } from '@/api/types'
import { formatBeijingTime } from '@/utils/datetime'
import { formatCaseTypeLabel } from '@/utils/caseType'
import type { DateInput } from '@/types/common'

defineProps<{
  modelValue: boolean
  caseItem: Schemas['ManualTestRunCaseOut'] | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const resultLabel: Record<string, string> = {
  pending: '待测',
  pass: '通过',
  fail: '失败',
  blocked: '阻塞',
  skip: '跳过',
}
const resultType: Record<string, string> = {
  pending: 'info',
  pass: 'success',
  fail: 'danger',
  blocked: 'warning',
  skip: '',
}

function formatTime(value: DateInput) {
  return formatBeijingTime(value)
}
</script>

<style scoped>
.case-detail-head {
  margin-bottom: var(--ax-gap-lg);
}

.case-title {
  margin: 0 0 var(--ax-gap);
  color: var(--ax-text);
  font-size: var(--ax-font-md);
}

.case-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-gap);
}

.case-meta {
  margin-bottom: var(--ax-gap-lg);
}

.field-block {
  margin-bottom: var(--ax-gap-lg);
}

.field-label {
  margin-bottom: var(--ax-gap-xs);
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
  font-weight: 600;
}

.text-block {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: var(--ax-text-body-size);
  line-height: var(--ax-leading-relaxed);
  color: var(--ax-text);
}
</style>
