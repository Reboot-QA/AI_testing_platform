<template>
  <div class="editor">
    <template v-if="showMeta">
      <div class="row1">
        <el-select v-model="form.method" size="small" class="method-sel">
          <el-option v-for="m in METHODS" :key="m" :label="m" :value="m" />
        </el-select>
        <el-select
          v-model="form.server_name"
          size="small"
          placeholder="默认前置URL"
          clearable
          :value-on-clear="null"
          class="server-sel"
          @clear="form.server_name = null"
        >
          <el-option v-for="n in serverNames" :key="n" :label="n" :value="n" />
        </el-select>
        <VarInput
          v-model="form.path"
          size="small"
          placeholder="/path/to/api"
          class="path-input"
          :maxlength="PATH_MAX_LEN"
        />
        <slot name="actions" />
        <el-button
          v-if="showSave"
          type="primary"
          size="small"
          :loading="saving"
          @click="$emit('save')"
          >保存</el-button
        >
      </div>
      <el-input
        v-model="form.name"
        size="small"
        :maxlength="TITLE_MAX_LEN"
        placeholder="接口名称"
        class="name-input"
      />
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
        <div v-if="form.request_spec.auth.type === 'bearer'" class="auth-row">
          <span class="auth-label">Token</span>
          <VarInput
            v-model="form.request_spec.auth.token"
            size="small"
            placeholder="Bearer Token，支持 {{变量}}"
            class="auth-row-input"
          />
        </div>
        <template v-else-if="form.request_spec.auth.type === 'basic'">
          <VarInput
            v-model="form.request_spec.auth.username"
            size="small"
            placeholder="用户名"
            class="auth-input"
          />
          <VarInput
            v-model="form.request_spec.auth.password"
            size="small"
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
              size="small"
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
            <el-switch v-model="form.request_spec.settings.verify_ssl" size="small" />
            <span class="set-hint">关闭则不校验服务端证书（自签名 / 测试环境）</span>
          </div>
          <div class="set-row">
            <span class="set-label">自动重定向</span>
            <el-switch v-model="form.request_spec.settings.follow_redirects" size="small" />
            <span class="set-hint">关闭则返回 3xx 原始响应，不自动跟随</span>
          </div>
        </div>
      </el-tab-pane>

      <!-- 接口级处理器（与用例级合并叠加）；用例编辑器内不显示（用例有自己的处理器 tab） -->
      <template v-if="showProcessors">
        <el-tab-pane label="前置操作" name="pre">
          <ProcessorsEditor
            :rows="form.pre_processors ?? []"
            phase="pre"
            :scripts="scripts"
            :databases="databases"
            :sql-scripts="sqlScripts"
          />
        </el-tab-pane>
        <el-tab-pane label="后置操作" name="post">
          <ProcessorsEditor
            :rows="form.post_processors ?? []"
            phase="post"
            :scripts="scripts"
            :databases="databases"
            :sql-scripts="sqlScripts"
            :schemas="schemas"
          />
        </el-tab-pane>
      </template>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { PATH_MAX_LEN, TITLE_MAX_LEN } from '@/constants/limits'
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadRawFile } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { CaseEditorForm, RequestSpecHolderForm } from '@/types/apifox'
import { apifoxApi } from '@/api'
import { provideEditorVariables } from '@/composables/useEditorVariables'
import { useEnvDatabases } from '@/composables/useEnvDatabases'
import { useSqlScripts } from '@/composables/useSqlScripts'
import KvRowsEditor from '@/components/apifox/editors/KvRowsEditor.vue'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import ProcessorsEditor from '@/components/apifox/editors/ProcessorsEditor.vue'
import VarInput from '@/components/apifox/common/VarInput.vue'

type ScriptBrief = Schemas['ScriptBrief']
type SchemaBrief = Schemas['SchemaBrief']

const props = withDefaults(
  defineProps<{
    saving?: boolean
    showMeta?: boolean
    showSave?: boolean
    serverNames?: string[]
    showProcessors?: boolean
    scripts?: ScriptBrief[]
    schemas?: SchemaBrief[]
    projectId?: Id
  }>(),
  {
    saving: false,
    showMeta: true,
    showSave: true,
    serverNames: () => [],
    showProcessors: false,
    scripts: () => [],
    schemas: () => [],
    projectId: '',
  },
)
const form = defineModel<RequestSpecHolderForm>('form', { required: true })
defineEmits<{ save: [] }>()

// 数据库操作处理器需按当前环境选连接（环境级）
const { databases } = useEnvDatabases()
const { sqlScripts } = useSqlScripts()

provideEditorVariables(() => ({
  postProcessors: form.value.post_processors ?? [],
  variableRows: (form.value as CaseEditorForm).variables,
}))

// 兼容历史/未归一化 spec：确保 settings 存在，避免「设置」tab 的 v-model 绑定报错
watch(
  () => form.value.request_spec,
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
  const t = form.value.request_spec.body.type
  return t === 'json' ? 'json' : t === 'xml' ? 'xml' : 'plaintext'
})

// binary body：上传文件到项目，spec 只存 file_id + 展示名（发送时后端按 id 取字节）
const uploading = ref(false)
async function onPickFile(file: UploadRawFile) {
  uploading.value = true
  try {
    const res = await apifoxApi.uploadFile(props.projectId, file)
    form.value.request_spec.body.file_id = res.id
    form.value.request_spec.body.file_name = res.filename
    ElMessage.success('已上传')
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '上传失败')
  } finally {
    uploading.value = false
  }
  return false // 阻止 el-upload 默认自动上传（已手动走 api client）
}
function clearFile() {
  form.value.request_spec.body.file_id = null
  form.value.request_spec.body.file_name = ''
}
</script>

<style scoped>
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
  margin-bottom: var(--ax-space-3);
}

.sub-title {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
  margin: var(--ax-space-2) 0;
}

.body-raw,
.auth-input {
  margin-top: var(--ax-space-2);
}

.auth-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-top: var(--ax-space-2);
}

.auth-label {
  flex-shrink: 0;
  min-width: 48px;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.auth-row-input {
  flex: 1;
  min-width: 0;
}

.binary-body {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
  margin-top: var(--ax-space-2);
}

.binary-file {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.none-tip {
  color: var(--ax-text-placeholder);
  padding: var(--ax-space-3) 0;
}

.contract-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-3);
}

.c-label {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.proc-sub-title {
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text-secondary);
  margin: var(--ax-space-1) 0 var(--ax-space-2);
}

.proc-sub-title:not(:first-child) {
  margin-top: var(--ax-space-4);
}

.settings-form {
  padding: var(--ax-space-1) 0;
}

.set-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
  margin-bottom: var(--ax-space-4);
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
