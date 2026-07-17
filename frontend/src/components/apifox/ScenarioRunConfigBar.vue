<template>
  <div class="run-config">
    <span class="rc-label">运行数据集</span>
    <el-select
      :model-value="datasetId"
      clearable
      placeholder="不绑定（按循环次数）"
      size="small"
      style="width: 220px"
      @update:model-value="$emit('update:datasetId', $event || null)"
    >
      <el-option v-for="d in datasets" :key="d.id" :label="d.name" :value="d.id" />
    </el-select>
    <span class="rc-label">循环次数</span>
    <el-input-number
      :model-value="loopCount"
      :min="1"
      :max="1000"
      :disabled="!!datasetId"
      size="small"
      controls-position="right"
      style="width: 130px"
      @update:model-value="$emit('update:loopCount', $event || 1)"
    />
    <span class="rc-hint">
      {{ datasetId ? '按数据集每行数据各跑一遍整场景' : '整场景重复跑 N 遍' }}
    </span>
    <el-checkbox
      :model-value="propagateAuth"
      size="small"
      class="rc-auth"
      @update:model-value="$emit('update:propagateAuth', $event)"
    >
      自动传递 token/cookie
      <el-tooltip
        content="开启后：登录/refresh 响应的 Set-Cookie 与 token 自动跨步骤透传，无需手动提取；某步手动写了 Authorization 则以手动为准。关闭则保持逐步手动提取。"
        placement="top"
      >
        <el-icon class="rc-help"><QuestionFilled /></el-icon>
      </el-tooltip>
    </el-checkbox>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@/api/types'

type DatasetBrief = Schemas['DatasetBrief']

withDefaults(
  defineProps<{
    datasets?: DatasetBrief[]
    loopCount?: number
    datasetId?: number | string | null
    propagateAuth?: boolean
  }>(),
  {
    datasets: () => [],
    loopCount: 1,
    datasetId: null,
    propagateAuth: true,
  },
)
defineEmits<{
  'update:loopCount': [value: number]
  'update:datasetId': [value: number | null]
  'update:propagateAuth': [value: boolean]
}>()
</script>

<style scoped>
.run-config {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--ax-bg-subtle);
  border-radius: 6px;
}

.rc-label {
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.rc-hint {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>
