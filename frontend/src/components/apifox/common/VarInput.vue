<template>
  <div class="var-input" :class="[`is-${size}`, { 'is-focus': focused, 'is-disabled': disabled }]">
    <div ref="mirrorEl" class="vi-mirror" v-html="highlighted" />
    <input
      ref="inputEl"
      class="vi-field"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      spellcheck="false"
      @input="onInput"
      @scroll="syncScroll"
      @focus="focused = true"
      @blur="focused = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    placeholder?: string
    size?: 'small' | 'default'
    disabled?: boolean
  }>(),
  { modelValue: '', placeholder: '', size: 'small', disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [v: string] }>()

const inputEl = ref<HTMLInputElement>()
const mirrorEl = ref<HTMLElement>()
const focused = ref(false)

function esc(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
// 把 {{变量}} 上色；末尾零宽空格保证空串也占位、对齐稳定
const highlighted = computed(
  () =>
    esc(props.modelValue ?? '').replace(/(\{\{[^}]*\}\})/g, '<span class="vi-token">$1</span>') +
    '​',
)

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
  syncScroll()
}
function syncScroll() {
  if (mirrorEl.value && inputEl.value) mirrorEl.value.scrollLeft = inputEl.value.scrollLeft
}
</script>

<style scoped>
/* 透明输入框叠在高亮镜像层之上：镜像显示上色文字，输入框只留光标 */
.var-input {
  position: relative;
  display: block;
  width: 100%;
  height: 24px;
  background: var(--el-fill-color-blank, #fff);
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: var(--el-border-radius-base, 4px);
  box-sizing: border-box;
  overflow: hidden;
}
.var-input.is-default {
  height: 32px;
}
.var-input.is-focus {
  border-color: var(--el-color-primary, #409eff);
}
.var-input.is-disabled {
  background: var(--el-fill-color-light, #f5f7fa);
  cursor: not-allowed;
}

.vi-mirror,
.vi-field {
  position: absolute;
  inset: 0;
  padding: 0 11px;
  line-height: 22px;
  font-size: 13px;
  font-family: inherit;
  white-space: pre;
  box-sizing: border-box;
}
.is-default .vi-mirror,
.is-default .vi-field {
  line-height: 30px;
}

.vi-mirror {
  color: var(--el-text-color-regular, #606266);
  pointer-events: none;
  overflow: hidden;
}
.vi-field {
  width: 100%;
  background: transparent;
  color: transparent;
  caret-color: var(--el-text-color-primary, #303133);
  border: none;
  outline: none;
  overflow-x: auto;
}
.vi-field::placeholder {
  color: var(--el-text-color-placeholder, #a8abb2);
}
.vi-field::-webkit-scrollbar {
  display: none;
}

:deep(.vi-token) {
  color: var(--el-color-primary, #409eff);
  font-weight: 600;
}
</style>
