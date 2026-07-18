<template>
  <div class="condition-editor">
    <VarInput v-model="condition.left" placeholder="左值，支持 {{变量}}" class="cond-left" />
    <el-select v-model="condition.operator" size="small" class="cond-op">
      <el-option v-for="op in OPERATORS" :key="op.value" :label="op.label" :value="op.value" />
    </el-select>
    <VarInput
      v-if="condition.operator !== 'exists'"
      v-model="condition.right"
      placeholder="右值，支持 {{变量}}"
      class="cond-right"
    />
  </div>
</template>

<script setup lang="ts">
import type { ConditionConfig } from '@/types/apifox'
import VarInput from '@/components/apifox/common/VarInput.vue'

export type { ConditionConfig } from '@/types/apifox'

const OPERATORS = [
  { value: 'eq', label: '等于' },
  { value: 'neq', label: '不等于' },
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'gt', label: '大于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lt', label: '小于' },
  { value: 'lte', label: '小于等于' },
  { value: 'regex', label: '正则匹配' },
  { value: 'exists', label: '存在' },
]

defineProps<{ condition: ConditionConfig }>()
</script>

<style scoped>
.condition-editor {
  display: flex;
  gap: 6px;
  flex: 1;
}

.cond-left,
.cond-right {
  flex: 1;
}

.cond-op {
  width: 110px;
  flex-shrink: 0;
}
</style>
