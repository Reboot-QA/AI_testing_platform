<template>
  <div>
    <div class="provider-row">
      <span class="provider-label">大模型</span>
      <el-select
        :model-value="modelValue"
        size="small"
        :loading="providersLoading"
        :disabled="!providers.length"
        placeholder="选择大模型"
        style="flex: 1"
        @update:model-value="onProviderChange"
      >
        <el-option
          v-for="p in providers"
          :key="p.id"
          :label="formatProviderLabel(p)"
          :value="p.id"
        />
      </el-select>
    </div>
    <div v-if="mockMode" class="tip mock-tip">
      当前为 Mock 模式，将返回样例用例（不调用真实模型）。
    </div>
    <div v-for="c in categories" :key="c.value" class="cat-row">
      <el-checkbox v-model="c.checked" class="cat-check">{{ c.label }}</el-checkbox>
      <el-checkbox v-model="c.limit" :disabled="!c.checked" size="small">限量</el-checkbox>
      <el-input-number
        v-if="c.limit"
        v-model="c.count"
        :disabled="!c.checked"
        :min="1"
        :max="20"
        size="small"
        controls-position="right"
        style="width: 100px"
      />
      <span v-else class="auto-hint">自动</span>
      <span class="cat-desc">{{ c.desc }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@/api/types'
import type { CategoryRow } from '@/composables/useAiGenConfig'

type ProviderOption = Schemas['LLMProviderOptionOut']

withDefaults(
  defineProps<{
    modelValue: number | null
    providers: ProviderOption[]
    providersLoading?: boolean
    mockMode?: boolean
    categories: CategoryRow[]
  }>(),
  { providersLoading: false, mockMode: false },
)
const emit = defineEmits<{ 'update:modelValue': [number] }>()

function onProviderChange(v: unknown): void {
  emit('update:modelValue', v as number)
}

function formatProviderLabel(item: ProviderOption): string {
  const tags: string[] = []
  if (item.is_default) tags.push('默认')
  if (!item.api_key_configured) tags.push('未配置Key')
  const suffix = tags.length ? ` (${tags.join(' / ')})` : ''
  return `${item.name}${suffix}`
}
</script>

<style scoped>
.provider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.provider-label {
  width: 72px;
  font-size: 14px;
}

.tip {
  color: var(--ax-text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

.mock-tip {
  color: var(--ax-warning, #e6a23c);
}

.cat-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.cat-check {
  width: 72px;
}

.auto-hint {
  width: 100px;
  font-size: 13px;
  color: var(--ax-text-placeholder);
}

.cat-desc {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>
