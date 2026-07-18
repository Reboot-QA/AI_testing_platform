<template>
  <div class="a2-monaco" :style="{ height }">
    <VueMonacoEditor
      v-if="ready"
      :value="value"
      :language="language"
      theme="vs"
      :options="options"
      @update:value="onChange"
    />
    <div v-else class="a2-monaco-loading">加载编辑器…</div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { ensureMonaco } from '@/plugins/monaco'

withDefaults(
  defineProps<{
    value?: string
    language?: string
    height?: string
  }>(),
  { value: '', language: 'json', height: '100%' },
)
const emit = defineEmits<{ change: [string] }>()

const ready = ref(false)

const options = {
  minimap: { enabled: false },
  fontSize: 13,
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 2,
  scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
}

onBeforeMount(async () => {
  await ensureMonaco()
  ready.value = true
})

function onChange(v: string | undefined) {
  emit('change', v ?? '')
}
</script>

<style scoped>
.a2-monaco {
  width: 100%;
}

.a2-monaco-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--a2-color-text-tertiary);
  font-size: 13px;
}
</style>
