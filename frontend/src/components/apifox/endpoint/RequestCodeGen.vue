<template>
  <div class="codegen">
    <!-- 语言 -->
    <div class="cg-langs">
      <button
        v-for="l in CODE_LANGS"
        :key="l.target"
        type="button"
        class="cg-lang"
        :class="{ active: l.target === lang.target }"
        @click="selectLang(l)"
      >
        {{ l.label }}
      </button>
    </div>
    <!-- 客户端（子变体） -->
    <div v-if="lang.clients.length > 1" class="cg-clients">
      <button
        v-for="c in lang.clients"
        :key="c.client"
        type="button"
        class="cg-client"
        :class="{ active: c.client === client }"
        @click="client = c.client"
      >
        {{ c.label }}
      </button>
    </div>
    <!-- 代码 + 复制 -->
    <div class="cg-code">
      <el-button class="cg-copy" link size="small" title="复制" @click="copy">
        <el-icon><CopyDocument /></el-icon>
      </el-button>
      <pre class="cg-pre">{{ code || '（无法生成该语言代码）' }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { copyText } from '@/utils/clipboard'
import { HTTPSnippet, type ClientId, type HarRequest, type TargetId } from 'httpsnippet-lite'

// httpsnippet 的目标语言 id（与其 TargetId 对齐，避免 convert 类型不匹配）
type Target =
  | 'shell'
  | 'javascript'
  | 'java'
  | 'swift'
  | 'go'
  | 'php'
  | 'python'
  | 'http'
  | 'c'
  | 'csharp'
  | 'objc'
  | 'ruby'
  | 'ocaml'
  | 'r'

interface LangClient {
  label: string
  client: string
}
interface Lang {
  label: string
  target: Target
  clients: LangClient[]
}

// 覆盖截图里的语言（httpsnippet 无 Dart，故省略）；每语言给常用客户端
const CODE_LANGS: Lang[] = [
  {
    label: 'Shell',
    target: 'shell',
    clients: [
      { label: 'cURL', client: 'curl' },
      { label: 'Httpie', client: 'httpie' },
      { label: 'wget', client: 'wget' },
      { label: 'PowerShell', client: 'powershell' },
    ],
  },
  {
    label: 'JavaScript',
    target: 'javascript',
    clients: [
      { label: 'Fetch', client: 'fetch' },
      { label: 'Axios', client: 'axios' },
      { label: 'XHR', client: 'xhr' },
      { label: 'jQuery', client: 'jquery' },
    ],
  },
  {
    label: 'Java',
    target: 'java',
    clients: [
      { label: 'OkHttp', client: 'okhttp' },
      { label: 'Unirest', client: 'unirest' },
    ],
  },
  { label: 'Swift', target: 'swift', clients: [{ label: 'URLSession', client: 'nsurlsession' }] },
  { label: 'Go', target: 'go', clients: [{ label: 'Native', client: 'native' }] },
  {
    label: 'PHP',
    target: 'php',
    clients: [
      { label: 'cURL', client: 'curl' },
      { label: 'Guzzle', client: 'guzzle' },
    ],
  },
  {
    label: 'Python',
    target: 'python',
    clients: [
      { label: 'Requests', client: 'requests' },
      { label: 'http.client', client: 'python3' },
    ],
  },
  { label: 'HTTP', target: 'http', clients: [{ label: 'HTTP/1.1', client: 'http1.1' }] },
  { label: 'C', target: 'c', clients: [{ label: 'libcurl', client: 'libcurl' }] },
  {
    label: 'C#',
    target: 'csharp',
    clients: [
      { label: 'RestSharp', client: 'restsharp' },
      { label: 'HttpClient', client: 'httpclient' },
    ],
  },
  {
    label: 'Objective-C',
    target: 'objc',
    clients: [{ label: 'NSURLSession', client: 'nsurlsession' }],
  },
  { label: 'Ruby', target: 'ruby', clients: [{ label: 'Native', client: 'native' }] },
  { label: 'OCaml', target: 'ocaml', clients: [{ label: 'CoHTTP', client: 'cohttp' }] },
  { label: 'R', target: 'r', clients: [{ label: 'httr', client: 'httr' }] },
]

const props = withDefaults(
  defineProps<{
    method?: string
    url?: string
    headers?: Record<string, unknown> | string
    body?: string
  }>(),
  { method: 'GET', url: '', headers: () => ({}), body: '' },
)

const lang = ref<Lang>(CODE_LANGS[0])
const client = ref<string>(CODE_LANGS[0].clients[0].client)

function selectLang(l: Lang) {
  lang.value = l
  client.value = l.clients[0].client
}

function headerRows(): { name: string; value: string }[] {
  const h = props.headers
  if (!h || typeof h === 'string') return []
  return Object.entries(h).map(([name, value]) => ({ name, value: String(value ?? '') }))
}

function mimeType(): string {
  const ct = headerRows().find((r) => r.name.toLowerCase() === 'content-type')
  return ct?.value || 'application/json'
}

const harRequest = computed<HarRequest>(() => {
  // postData 在 HarRequest 类型里为必填，但空 body 时不应带；构造后按需补，用断言绕过必填校验
  const req = {
    method: (props.method || 'GET').toUpperCase(),
    url: props.url || '',
    httpVersion: 'HTTP/1.1',
    headers: headerRows(),
    queryString: [],
    cookies: [],
    headersSize: -1,
    bodySize: -1,
  } as HarRequest
  if (props.body && String(props.body).trim()) {
    req.postData = { mimeType: mimeType(), text: String(props.body) }
  }
  return req
})

// httpsnippet-lite 的 convert 为异步（按需加载目标语言生成器）：随语言/客户端/请求变化重算
const code = ref('')
async function regenerate() {
  try {
    const out = await new HTTPSnippet(harRequest.value).convert(
      lang.value.target as TargetId,
      client.value as ClientId,
    )
    code.value = out == null ? '' : Array.isArray(out) ? out.join('\n') : out
  } catch {
    code.value = ''
  }
}
watch([() => lang.value.target, client, harRequest], regenerate, { immediate: true })

async function copy() {
  if (!code.value) return
  if (await copyText(code.value)) ElMessage.success('已复制')
  else ElMessage.error('复制失败')
}
</script>

<style scoped>
.cg-langs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-space-1) var(--ax-space-3);
  border-bottom: 1px solid var(--ax-border);
  padding-bottom: var(--ax-space-1-5);
}
.cg-lang {
  border: none;
  background: none;
  padding: var(--ax-space-1) 0;
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
  cursor: pointer;
}
.cg-lang.active {
  color: var(--ax-brand);
  font-weight: 600;
}
.cg-clients {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
  margin: var(--ax-space-2) 0;
}
.cg-client {
  border: 1px solid var(--ax-border);
  border-radius: 999px;
  background: var(--ax-bg);
  padding: 2px var(--ax-space-2-5);
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-caption-size);
  cursor: pointer;
}
.cg-client.active {
  border-color: var(--ax-brand);
  color: var(--ax-brand);
}
.cg-code {
  position: relative;
  margin-top: var(--ax-space-2);
}
.cg-copy {
  position: absolute;
  top: var(--ax-space-1);
  right: var(--ax-space-1);
  z-index: 1;
}
.cg-pre {
  margin: 0;
  padding: var(--ax-space-2-5);
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-leading-normal);
  white-space: pre;
  overflow: auto;
  max-height: 320px;
}
</style>
