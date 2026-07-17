<template>
  <div class="editor">
    <template v-if="showMeta">
      <div class="row1">
        <el-select v-model="form.method" class="method-sel">
          <el-option v-for="m in METHODS" :key="m" :label="m" :value="m" />
        </el-select>
        <el-select
          v-model="form.server_name"
          placeholder="默认前置URL"
          clearable
          class="server-sel"
        >
          <el-option v-for="n in serverNames" :key="n" :label="n" :value="n" />
        </el-select>
        <el-input v-model="form.path" placeholder="/path/to/api" class="path-input" />
        <el-button type="primary" :loading="saving" @click="$emit('save')">保存</el-button>
      </div>
      <el-input v-model="form.name" placeholder="接口名称" class="name-input" />
    </template>

    <el-tabs v-model="activeTab" class="spec-tabs">
      <el-tab-pane label="Params" name="params">
        <div class="sub-title">Query 参数</div>
        <KvRowsEditor :rows="form.request_spec.query" show-type />
        <div class="sub-title">Path 变量</div>
        <KvRowsEditor :rows="form.request_spec.path_params" show-type />
      </el-tab-pane>
      <el-tab-pane label="Headers" name="headers">
        <KvRowsEditor :rows="form.request_spec.headers" suggest="header" />
      </el-tab-pane>
      <el-tab-pane label="Cookies" name="cookies">
        <KvRowsEditor :rows="form.request_spec.cookies" />
      </el-tab-pane>
      <el-tab-pane label="Body" name="body">
        <el-radio-group v-model="form.request_spec.body.type" size="small">
          <el-radio-button v-for="t in BODY_TYPES" :key="t" :value="t">{{ t }}</el-radio-button>
        </el-radio-group>
        <CodeEditor
          v-if="['json', 'xml', 'raw'].includes(form.request_spec.body.type)"
          v-model="form.request_spec.body.raw"
          :language="bodyLang"
          height="220px"
          class="body-raw"
        />
        <KvRowsEditor
          v-else-if="['form-data', 'urlencoded'].includes(form.request_spec.body.type)"
          :rows="form.request_spec.body.form"
        />
        <template v-else-if="form.request_spec.body.type === 'graphql'">
          <div class="sub-title">Query</div>
          <CodeEditor
            v-model="form.request_spec.body.graphql_query"
            language="graphql"
            height="180px"
          />
          <div class="sub-title">Variables（JSON）</div>
          <CodeEditor
            v-model="form.request_spec.body.graphql_variables"
            language="json"
            height="120px"
          />
        </template>
        <div v-else-if="form.request_spec.body.type === 'binary'" class="binary-body">
          <el-upload :show-file-list="false" :before-upload="onPickFile" :disabled="uploading">
            <el-button size="small" :loading="uploading">选择文件</el-button>
          </el-upload>
          <span v-if="form.request_spec.body.file_name" class="binary-file">
            {{ form.request_spec.body.file_name }}
            <el-button link type="danger" size="small" @click="clearFile">移除</el-button>
          </span>
          <span v-else class="none-tip">未选择文件（发送时以二进制原样作为 body）</span>
        </div>
        <div v-else class="none-tip">无 Body</div>
      </el-tab-pane>
      <el-tab-pane label="Auth" name="auth">
        <el-radio-group v-model="form.request_spec.auth.type" size="small">
          <el-radio-button value="none">无</el-radio-button>
          <el-radio-button value="bearer">Bearer</el-radio-button>
          <el-radio-button value="basic">Basic</el-radio-button>
        </el-radio-group>
        <el-input
          v-if="form.request_spec.auth.type === 'bearer'"
          v-model="form.request_spec.auth.token"
          placeholder="Token"
          class="auth-input"
        />
        <template v-else-if="form.request_spec.auth.type === 'basic'">
          <el-input
            v-model="form.request_spec.auth.username"
            placeholder="用户名"
            class="auth-input"
          />
          <el-input
            v-model="form.request_spec.auth.password"
            placeholder="密码"
            class="auth-input"
          />
        </template>
      </el-tab-pane>

      <el-tab-pane label="设置" name="settings">
        <div class="settings-form">
          <div class="set-row">
            <span class="set-label">超时（毫秒）</span>
            <el-input-number
              v-model="form.request_spec.settings.timeout_ms"
              :min="0"
              :step="1000"
              :precision="0"
              :controls="false"
              :value-on-clear="null"
              placeholder="默认 30000"
              style="width: 180px"
            />
            <span class="set-hint">留空或 0 用平台默认 30s</span>
          </div>
          <div class="set-row">
            <span class="set-label">SSL 证书校验</span>
            <el-switch v-model="form.request_spec.settings.verify_ssl" />
            <span class="set-hint">关闭则不校验服务端证书（自签名 / 测试环境）</span>
          </div>
          <div class="set-row">
            <span class="set-label">自动重定向</span>
            <el-switch v-model="form.request_spec.settings.follow_redirects" />
            <span class="set-hint">关闭则返回 3xx 原始响应，不自动跟随</span>
          </div>
        </div>
      </el-tab-pane>

      <!-- 接口级处理器（与用例级合并叠加）；用例编辑器内不显示（用例有自己的处理器 tab） -->
      <template v-if="showProcessors">
        <el-tab-pane label="前置操作" name="pre">
          <ScriptRefsEditor :rows="form.pre_scripts" :scripts="scripts" />
        </el-tab-pane>
        <el-tab-pane label="后置操作" name="post">
          <ScriptRefsEditor :rows="form.post_scripts" :scripts="scripts" />
        </el-tab-pane>
        <el-tab-pane label="断言" name="assertions">
          <AssertionsEditor :rows="form.assertions" />
        </el-tab-pane>
        <el-tab-pane label="提取" name="extracts">
          <ExtractsEditor :rows="form.extracts" />
        </el-tab-pane>
        <el-tab-pane label="响应契约" name="contract">
          <div class="contract-row">
            <span class="c-label">响应数据模型</span>
            <el-select
              v-model="form.response_schema_id"
              placeholder="不校验"
              clearable
              filterable
              style="width: 260px"
            >
              <el-option v-for="s in schemas" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </div>
          <el-checkbox v-model="form.contract_strict" :disabled="!form.response_schema_id">
            契约不符则判失败（默认仅提示，不影响通过）
          </el-checkbox>
        </el-tab-pane>
      </template>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadRawFile } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { EndpointEditorForm, RequestSpec } from '@/types/apifox'
import { apifoxApi } from '@/api'
import KvRowsEditor from '@/components/apifox/KvRowsEditor.vue'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import ScriptRefsEditor from '@/components/apifox/ScriptRefsEditor.vue'
import AssertionsEditor from '@/components/apifox/AssertionsEditor.vue'
import ExtractsEditor from '@/components/apifox/ExtractsEditor.vue'

type ScriptBrief = Schemas['ScriptBrief']
type SchemaBrief = Schemas['SchemaBrief']

export type { EndpointEditorForm } from '@/types/apifox'

const props = withDefaults(
  defineProps<{
    form: EndpointEditorForm
    saving?: boolean
    showMeta?: boolean
    serverNames?: string[]
    showProcessors?: boolean
    scripts?: ScriptBrief[]
    schemas?: SchemaBrief[]
    projectId?: Id
  }>(),
  {
    saving: false,
    showMeta: true,
    serverNames: () => [],
    showProcessors: false,
    scripts: () => [],
    schemas: () => [],
    projectId: '',
  },
)
defineEmits<{ save: [] }>()

// 兼容历史/未归一化 spec：确保 settings 存在，避免「设置」tab 的 v-model 绑定报错
watch(
  () => props.form.request_spec,
  (spec) => {
    if (spec && !spec.settings) {
      spec.settings = { timeout_ms: null, verify_ssl: true, follow_redirects: true }
    }
  },
  { immediate: true },
)

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
const BODY_TYPES = ['none', 'json', 'xml', 'form-data', 'urlencoded', 'raw', 'graphql', 'binary']
const activeTab = ref('params')

const bodyLang = computed(() => {
  const t = props.form.request_spec.body.type
  return t === 'json' ? 'json' : t === 'xml' ? 'xml' : 'plaintext'
})

// binary body：上传文件到项目，spec 只存 file_id + 展示名（发送时后端按 id 取字节）
const uploading = ref(false)
async function onPickFile(file: UploadRawFile) {
  uploading.value = true
  try {
    const res = await apifoxApi.uploadFile(props.projectId, file)
    props.form.request_spec.body.file_id = res.id
    props.form.request_spec.body.file_name = res.filename
    ElMessage.success('已上传')
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '上传失败')
  } finally {
    uploading.value = false
  }
  return false // 阻止 el-upload 默认自动上传（已手动走 api client）
}
function clearFile() {
  props.form.request_spec.body.file_id = null
  props.form.request_spec.body.file_name = ''
}
</script>

<style scoped>
.row1 {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

/* 方法框加宽（DELETE/PATCH 不再挤）、环境(前置URL)加宽；URL 占剩余空间自然变短 */
.method-sel {
  width: 120px;
  flex: none;
}

.server-sel {
  width: 200px;
  flex: none;
}

.path-input {
  flex: 1;
  min-width: 0;
}

.name-input {
  margin-bottom: 12px;
}

.sub-title {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
  margin: 8px 0;
}

.body-raw,
.auth-input {
  margin-top: 10px;
}

.binary-body {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.binary-file {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.none-tip {
  color: var(--ax-text-placeholder);
  padding: 12px 0;
}

.contract-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.c-label {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.settings-form {
  padding: 4px 0;
}

.set-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.set-label {
  flex: none;
  width: 96px;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.set-hint {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}
</style>
