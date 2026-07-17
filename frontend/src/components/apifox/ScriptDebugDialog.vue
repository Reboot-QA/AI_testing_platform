<template>
  <el-dialog
    :model-value="visible"
    title="调试脚本"
    width="640px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="row">
      <span class="lbl">阶段</span>
      <el-radio-group v-model="phase" size="small">
        <el-radio-button value="pre">前置</el-radio-button>
        <el-radio-button value="post">后置</el-radio-button>
      </el-radio-group>
      <span class="hint">语言：{{ lang }}（跟随当前脚本）</span>
    </div>

    <div class="row">
      <span class="lbl">预设</span>
      <el-select
        v-model="selectedPreset"
        size="small"
        placeholder="载入已保存的调试输入"
        clearable
        style="width: 220px"
        @change="applyPreset"
      >
        <el-option v-for="p in presets" :key="p.name" :label="p.name" :value="p.name" />
      </el-select>
      <el-button size="small" @click="savePreset">保存当前输入</el-button>
      <el-button v-if="selectedPreset" size="small" text type="danger" @click="deletePreset"
        >删除</el-button
      >
    </div>

    <div class="block">
      <div class="block-title">输入变量</div>
      <KvRowsEditor :rows="varRows" />
    </div>

    <template v-if="phase === 'post'">
      <div class="block">
        <div class="block-title">响应上下文（后置可读）</div>
        <div class="row">
          <span class="lbl">状态码</span>
          <el-input-number
            v-model="respStatus"
            :min="100"
            :max="599"
            :controls="false"
            style="width: 120px"
          />
        </div>
        <el-input
          v-model="respBody"
          type="textarea"
          :rows="3"
          placeholder="响应体（JSON 文本，选填）"
        />
      </div>
    </template>

    <div class="run-bar">
      <el-button type="success" size="small" :loading="running" @click="run">运行</el-button>
    </div>

    <div v-if="result" class="result">
      <div class="row">
        <el-tag size="small" :type="result.status === 'passed' ? 'success' : 'danger'">
          {{ result.status === 'passed' ? '通过' : '失败' }}
        </el-tag>
        <span v-if="result.error_message" class="err">{{ result.error_message }}</span>
      </div>
      <template v-if="result.logs?.length">
        <div class="block-title">日志</div>
        <div v-for="(l, i) in result.logs" :key="'l' + i" class="log mono">{{ l }}</div>
      </template>
      <div class="block-title">输出变量</div>
      <div class="vars-box"><JsonView :data="result.variables" :deep="2" /></div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import type { KvRow } from '@/types/apifox'
import { apifoxApi } from '@/api'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import KvRowsEditor from '@/components/apifox/KvRowsEditor.vue'
import JsonView from '@/components/apifox/common/JsonView.vue'

const props = withDefaults(
  defineProps<{
    visible?: boolean
    lang?: string
    content?: string
  }>(),
  {
    visible: false,
    lang: 'javascript',
    content: '',
  },
)
defineEmits<{ 'update:visible': [value: boolean] }>()

const phase = ref<'pre' | 'post'>('pre')
const varRows = ref<KvRow[]>(ensureKvRows([]))
const respStatus = ref(200)
const respBody = ref('')
const running = ref(false)
const result = ref<Schemas['ScriptDebugOut'] | null>(null)

// 调试输入预设（本浏览器保存，供下次复用）
interface DebugPreset {
  name: string
  phase: 'pre' | 'post'
  variables: Record<string, string>
  respStatus: number
  respBody: string
}
const PRESET_KEY = 'apifox:scriptDebugPresets'
const presets = ref<DebugPreset[]>([])
const selectedPreset = ref<string | null>(null)

function loadPresets() {
  try {
    const parsed = JSON.parse(localStorage.getItem(PRESET_KEY) || '[]')
    presets.value = Array.isArray(parsed) ? parsed : []
  } catch {
    presets.value = []
  }
}

// localStorage 为唯一事实来源：写成功才更新内存，写失败明确报错，避免"看似已保存实则没落盘"
function writePresets(next: DebugPreset[]): boolean {
  try {
    localStorage.setItem(PRESET_KEY, JSON.stringify(next))
    presets.value = next
    return true
  } catch {
    ElMessage.error('保存预设失败：浏览器本地存储不可用（隐私模式或存储已满）')
    return false
  }
}

function applyPreset(name: string | null) {
  const p = presets.value.find((x) => x.name === name)
  if (!p) return
  phase.value = p.phase
  varRows.value = ensureKvRows(Object.entries(p.variables).map(([key, value]) => ({ key, value })))
  respStatus.value = p.respStatus
  respBody.value = p.respBody
}

async function savePreset() {
  const { value } = await ElMessageBox.prompt(
    '给这组调试输入起个名字（同名覆盖）',
    '保存调试预设',
    {
      inputPattern: /\S/,
      inputErrorMessage: '不能为空',
    },
  )
  const name = value.trim()
  const preset: DebugPreset = {
    name,
    phase: phase.value,
    variables: rowsToObject(varRows.value),
    respStatus: respStatus.value,
    respBody: respBody.value,
  }
  const exists = presets.value.some((x) => x.name === name)
  const next = exists
    ? presets.value.map((x) => (x.name === name ? preset : x))
    : [...presets.value, preset]
  if (!writePresets(next)) return
  selectedPreset.value = name
  ElMessage.success('已保存预设')
}

function deletePreset() {
  if (writePresets(presets.value.filter((x) => x.name !== selectedPreset.value)))
    selectedPreset.value = null
}

onMounted(loadPresets)

// 每次打开重置结果，避免看到上次的输出
watch(
  () => props.visible,
  (v) => {
    if (v) result.value = null
  },
)

function rowsToObject(rows: KvRow[]) {
  return Object.fromEntries(
    rows.filter((r) => r.key && r.enabled !== false).map((r) => [r.key, r.value ?? '']),
  )
}

async function run() {
  running.value = true
  try {
    result.value = await apifoxApi.debugScript({
      phase: phase.value,
      lang: props.lang,
      content: props.content,
      variables: rowsToObject(varRows.value),
      response_body: respBody.value,
      response_status: respStatus.value,
    })
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.lbl {
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.hint {
  font-size: 12px;
  color: var(--ax-text-placeholder);
}

.block {
  margin-bottom: 12px;
}

.block-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ax-brand);
  margin: 8px 0 6px;
}

.run-bar {
  margin: 6px 0 10px;
}

.result {
  border-top: 1px solid var(--ax-border);
  padding-top: 10px;
}

.err {
  color: var(--ax-danger);
  font-size: 12px;
}

.log {
  font-size: 12px;
  color: var(--ax-text-secondary);
  padding: 2px 0;
}

.mono {
  font-family: Consolas, Monaco, monospace;
}

.vars-box {
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  padding: 8px;
  max-height: 200px;
  overflow: auto;
}
</style>
