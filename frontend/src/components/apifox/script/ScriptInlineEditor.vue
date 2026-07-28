<template>
  <div class="inline-script">
    <div class="editor-wrap">
      <CodeEditor
        ref="editorRef"
        :model-value="modelValue"
        :language="lang"
        height="200px"
        @update:model-value="$emit('update:modelValue', $event)"
      />
    </div>
    <div class="snippet-panel">
      <div class="snippet-title">代码片段</div>
      <div v-for="s in snippets" :key="s.label" class="snippet-item" @click="insert(s.code)">
        {{ s.label }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    lang?: string
    phase?: 'pre' | 'post'
  }>(),
  { modelValue: '', lang: 'javascript', phase: 'pre' },
)
defineEmits<{ 'update:modelValue': [value: string] }>()

interface Snippet {
  label: string
  code: string
  postOnly?: boolean // 依赖响应上下文，仅后置可用
}

// 片段严格对齐平台真实运行时 API（JS: script_js_runtime._pmBuild；Python: script_runner）
const JS_SNIPPETS: Snippet[] = [
  { label: '获取环境变量', code: 'pm.environment.get("变量名")' },
  { label: '设置环境变量', code: 'pm.environment.set("变量名", "值")' },
  { label: '获取临时变量', code: 'pm.variables.get("变量名")' },
  { label: '设置临时变量', code: 'pm.variables.set("变量名", "值")' },
  { label: '打印日志', code: 'console.log("信息")' },
  { label: '读取响应 JSON', code: 'const data = pm.response.json();', postOnly: true },
  { label: '读取响应状态码', code: 'pm.response.code', postOnly: true },
  {
    label: '断言状态码为 200',
    code: 'pm.test("状态码为 200", () => pm.expect(pm.response.code).to.equal(200));',
    postOnly: true,
  },
]

const PY_SNIPPETS: Snippet[] = [
  { label: '获取变量', code: 'variables.get("变量名")' },
  { label: '设置变量', code: 'variables["变量名"] = "值"' },
  { label: '打印日志', code: 'print("信息")' },
  { label: '读取响应体', code: 'data = json.loads(response_body)', postOnly: true },
  { label: '读取响应状态码', code: 'response_status', postOnly: true },
  { label: '断言状态码为 200', code: 'assert response_status == 200', postOnly: true },
]

const snippets = computed(() => {
  const list = props.lang === 'python' ? PY_SNIPPETS : JS_SNIPPETS
  return props.phase === 'post' ? list : list.filter((s) => !s.postOnly)
})

const editorRef = ref<{ insert: (text: string) => void } | null>(null)
function insert(code: string) {
  editorRef.value?.insert(code)
}
</script>

<style scoped>
.inline-script {
  display: flex;
  gap: var(--ax-space-2);
  width: 100%;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  overflow: hidden;
}

.editor-wrap {
  flex: 1;
  min-width: 0;
}

/* 内层 CodeEditor 自带边框，这里外层已包一层，去掉内层重复边框 */
.editor-wrap :deep(.code-editor) {
  border: none;
  border-radius: 0;
}

.snippet-panel {
  width: 160px;
  flex-shrink: 0;
  border-left: 1px solid var(--ax-border);
  background: var(--ax-bg-subtle);
  padding: var(--ax-space-2);
  overflow-y: auto;
}

.snippet-title {
  font-size: var(--ax-text-caption-size);
  font-weight: 600;
  color: var(--ax-text-secondary);
  margin-bottom: var(--ax-space-1-5);
}

.snippet-item {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-brand);
  padding: var(--ax-space-1) var(--ax-space-1-5);
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.snippet-item:hover {
  background: var(--ax-bg-hover);
}
</style>
