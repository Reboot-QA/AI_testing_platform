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
        <template #label>
          <LlmProviderLabel
            v-if="selectedProvider"
            :text="formatLlmProviderLabel(selectedProvider)"
          />
        </template>
        <el-option
          v-for="p in providers"
          :key="p.id"
          :label="formatLlmProviderLabel(p)"
          :value="p.id"
        >
          <LlmProviderLabel :text="formatLlmProviderLabel(p)" />
        </el-option>
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
import { computed } from 'vue'
import type { Schemas } from '@/api/types'
import type { CategoryRow } from '@/composables/useAiGenConfig'
import LlmProviderLabel from '@/components/LlmProviderLabel.vue'
import { formatLlmProviderLabel } from '@/utils/llmProviderLabel'

type ProviderOption = Schemas['LLMProviderOptionOut']

const props = withDefaults(
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

const selectedProvider = computed(
  () => props.providers.find((item) => item.id === props.modelValue) ?? null,
)

function onProviderChange(v: unknown): void {
  emit('update:modelValue', v as number)
}
</script>

<style scoped>
.provider-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
  margin-bottom: var(--ax-space-3);
}

.provider-label {
  width: 72px;
  font-size: var(--ax-text-body-size);
}

.tip {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
  margin-bottom: var(--ax-space-3);
}

.mock-tip {
  color: var(--ax-warning, var(--ax-raw-hex-e6a23c));
}

.cat-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
  margin-bottom: var(--ax-space-3);
}

.cat-check {
  width: 72px;
}

.auto-hint {
  width: 100px;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-placeholder);
}

.cat-desc {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
}
</style>
