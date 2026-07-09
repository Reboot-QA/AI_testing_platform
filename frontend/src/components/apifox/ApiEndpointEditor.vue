<template>
  <div class="editor">
    <template v-if="showMeta">
      <div class="row1">
        <el-select v-model="form.method" style="width: 110px">
          <el-option v-for="m in METHODS" :key="m" :label="m" :value="m" />
        </el-select>
        <el-input v-model="form.path" placeholder="/path/to/api" />
        <el-button type="primary" :loading="saving" @click="$emit('save')">保存</el-button>
      </div>
      <el-input v-model="form.name" placeholder="接口名称" class="name-input" />
    </template>

    <el-tabs v-model="activeTab" class="spec-tabs">
      <el-tab-pane label="Params" name="params">
        <div class="sub-title">Query 参数</div>
        <KvRowsEditor :rows="form.request_spec.query" />
        <div class="sub-title">Path 变量</div>
        <KvRowsEditor :rows="form.request_spec.path_params" />
      </el-tab-pane>
      <el-tab-pane label="Headers" name="headers">
        <KvRowsEditor :rows="form.request_spec.headers" />
      </el-tab-pane>
      <el-tab-pane label="Body" name="body">
        <el-radio-group v-model="form.request_spec.body.type" size="small">
          <el-radio-button v-for="t in BODY_TYPES" :key="t" :value="t">{{ t }}</el-radio-button>
        </el-radio-group>
        <CodeEditor
          v-if="['json', 'raw'].includes(form.request_spec.body.type)"
          v-model="form.request_spec.body.raw"
          :language="form.request_spec.body.type === 'json' ? 'json' : 'plaintext'"
          height="220px"
          class="body-raw"
        />
        <KvRowsEditor
          v-else-if="['form-data', 'urlencoded'].includes(form.request_spec.body.type)"
          :rows="form.request_spec.body.form"
        />
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
          <el-input v-model="form.request_spec.auth.username" placeholder="用户名" class="auth-input" />
          <el-input v-model="form.request_spec.auth.password" placeholder="密码" class="auth-input" />
        </template>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import KvRowsEditor from '@/components/apifox/KvRowsEditor.vue'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'

defineProps({
  form: { type: Object, required: true },
  saving: { type: Boolean, default: false },
  showMeta: { type: Boolean, default: true },
})
defineEmits(['save'])

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
const BODY_TYPES = ['none', 'json', 'form-data', 'urlencoded', 'raw']
const activeTab = ref('params')
</script>

<style scoped>
.row1 {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.name-input {
  margin-bottom: 12px;
}

.sub-title {
  font-size: 13px;
  color: var(--ax-text-secondary);
  margin: 8px 0;
}

.body-raw,
.auth-input {
  margin-top: 10px;
}

.none-tip {
  color: var(--ax-text-placeholder);
  padding: 12px 0;
}
</style>
