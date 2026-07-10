<template>
  <div class="debug-panel">
    <div class="send-bar">
      <el-select v-model="envId" placeholder="选择环境" size="small" clearable style="width: 200px">
        <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
      </el-select>
      <el-button type="success" size="small" :loading="sending" @click="send">发送</el-button>
      <span class="hint">直接发一次请求（不建用例、不落报告）</span>
    </div>

    <ApiEndpointEditor :form="form" :saving="saving" @save="$emit('save')" />

    <div v-if="resp" class="resp">
      <div class="resp-head">
        <span class="lbl">响应</span>
        <el-tag size="small" :type="statusType">{{ resp.status_code ?? '—' }}</el-tag>
        <span class="meta">{{ Math.round(resp.duration_ms) }} ms</span>
        <span v-if="resp.error" class="err">{{ resp.error }}</span>
      </div>
      <el-tabs v-model="respTab" class="resp-tabs">
        <el-tab-pane label="Body" name="body">
          <div class="resp-box"><JsonView :data="resp.response_body" :deep="3" /></div>
        </el-tab-pane>
        <el-tab-pane label="Headers" name="headers">
          <div class="resp-box"><JsonView :data="resp.response_headers" :deep="2" /></div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { apifoxApi } from '@/api'
import ApiEndpointEditor from '@/components/apifox/ApiEndpointEditor.vue'
import JsonView from '@/components/apifox/common/JsonView.vue'

const props = defineProps({
  form: { type: Object, required: true },
  saving: { type: Boolean, default: false },
  environments: { type: Array, default: () => [] },
  projectId: { type: [String, Number], required: true },
})
defineEmits(['save'])

const envId = ref(null)
const sending = ref(false)
const resp = ref(null)
const respTab = ref('body')

// 默认选中默认环境
watch(
  () => props.environments,
  (list) => {
    if (!envId.value) {
      const def = list.find((e) => e.is_default)
      if (def) envId.value = def.id
    }
  },
  { immediate: true }
)

const statusType = computed(() => {
  const s = resp.value?.status_code
  if (s == null) return 'info'
  return s >= 200 && s < 400 ? 'success' : 'danger'
})

async function send() {
  sending.value = true
  try {
    resp.value = await apifoxApi.debugSend(props.projectId, {
      method: props.form.method,
      path: props.form.path,
      request_spec: props.form.request_spec,
      environment_id: envId.value,
    })
    respTab.value = 'body'
  } catch (e) {
    ElMessage.error(e.message || '发送失败')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.send-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.hint {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}

.resp {
  margin-top: 14px;
  border-top: 1px solid var(--ax-border);
  padding-top: 10px;
}

.resp-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lbl {
  font-weight: 600;
  color: var(--ax-brand);
}

.meta {
  color: var(--ax-text-secondary);
  font-size: 12px;
}

.err {
  color: var(--ax-danger);
  font-size: 12px;
}

.resp-box {
  max-height: 320px;
  overflow: auto;
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  padding: 8px;
}
</style>
