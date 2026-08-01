<template>
  <div class="code-editor" :style="{ height }">
    <div v-if="!readonly && showToolbar" class="toolbar">
      <el-button v-if="language === 'json'" link size="small" @click="format">格式化</el-button>
      <slot name="toolbar" />
    </div>
    <div class="editor-host">
      <vue-monaco-editor
        v-if="ready"
        :value="modelValue"
        :language="language"
        :theme="theme"
        :options="mergedOptions"
        @update:value="onChange"
        @mount="onMount"
      />
      <div v-else class="loading">加载编辑器…</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, shallowRef, watch } from 'vue'
import type { editor } from 'monaco-editor'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { ensureMonaco } from '@/plugins/monaco'
import { useResolvableVars } from '@/composables/useResolvableVars'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    language?: string
    height?: string
    readonly?: boolean
    theme?: string
    showToolbar?: boolean
  }>(),
  {
    modelValue: '',
    language: 'json',
    height: '240px',
    readonly: false,
    theme: 'vs',
    showToolbar: true,
  },
)
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const ready = ref(false)
const editorRef = shallowRef<editor.IStandaloneCodeEditor | null>(null)
const vars = useResolvableVars()

// {{变量}} 装饰高亮：仅给能联动到的变量上色 + hover 提示（值/来源）；联动不到不装饰（不变色）
let decoIds: string[] = []
function applyVarDecorations() {
  const ed = editorRef.value
  const model = ed?.getModel()
  if (!ed || !model) return
  const text = model.getValue()
  const map = vars.value
  const re = /\{\{([^}]*)\}\}/g
  const decos: editor.IModelDeltaDecoration[] = []
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) {
    const hit = map[m[1].trim()]
    if (!hit) continue
    const s = model.getPositionAt(m.index)
    const e = model.getPositionAt(m.index + m[0].length)
    decos.push({
      range: {
        startLineNumber: s.lineNumber,
        startColumn: s.column,
        endLineNumber: e.lineNumber,
        endColumn: e.column,
      },
      options: {
        inlineClassName: 'mono-var-ok',
        hoverMessage: { value: `\`${m[0]}\` = ${hit.value || '(空)'}（${hit.source}）` },
      },
    })
  }
  decoIds = ed.deltaDecorations(decoIds, decos)
}
watch(vars, applyVarDecorations, { deep: true })

const mergedOptions = computed(() => ({
  readOnly: props.readonly,
  minimap: { enabled: false },
  fontSize: 13,
  fontFamily: 'Consolas, Monaco, monospace',
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 2,
  lineNumbersMinChars: 3,
  overviewRulerLanes: 0,
  scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
}))

onBeforeMount(async () => {
  await ensureMonaco()
  ready.value = true
})

function onChange(value: string | undefined) {
  emit('update:modelValue', value ?? '')
}

function onMount(ed: editor.IStandaloneCodeEditor) {
  editorRef.value = ed
  applyVarDecorations()
  ed.onDidChangeModelContent(applyVarDecorations)
}

function format() {
  editorRef.value?.getAction('editor.action.formatDocument')?.run()
}

/** 在光标处插入一段代码片段：独占一行——当前行已有内容则先换行，末尾补换行，光标落到下一行。 */
function insert(text: string) {
  const ed = editorRef.value
  const model = ed?.getModel()
  const selection = ed?.getSelection()
  if (!ed || !model || !selection) return
  const before = model.getLineContent(selection.startLineNumber).slice(0, selection.startColumn - 1)
  const prefix = before.trim() ? '\n' : '' // 光标前本行有内容才补前置换行，避免空行插入多一行
  ed.executeEdits('snippet-insert', [
    { range: selection, text: `${prefix}${text}\n`, forceMoveMarkers: true },
  ])
  ed.focus()
}

defineExpose({ format, insert })
</script>

<style scoped>
.code-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  padding: var(--ax-space-0-5) var(--ax-space-2);
  border-bottom: 1px solid var(--ax-border);
  background: var(--ax-bg-hover);
}

.editor-host {
  flex: 1;
  min-height: 0;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-sm);
}

/* Monaco 行内装饰类由编辑器自建 DOM 渲染，用 :deep 穿透 scoped */
:deep(.mono-var-ok) {
  color: var(--el-color-primary, var(--ax-raw-hex-409eff));
  font-weight: 600;
}
</style>
