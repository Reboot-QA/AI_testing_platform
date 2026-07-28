<template>
  <el-dialog
    :model-value="modelValue"
    :title="mode === 'import' ? '通过 API 导入' : '通过 API 导出'"
    width="720px"
    @update:model-value="emit('update:modelValue', $event)"
    @open="load"
  >
    <div class="aad">
      <p class="aad-tip">
        为外部系统（CI、脚本）生成项目级 API Token，携带
        <code>X-API-Token</code> 头调用下方端点，无需登录。Token 仅项目内可见、可随时吊销。
      </p>

      <section class="aad-tokens">
        <div class="aad-new">
          <el-input
            v-model="newName"
            :maxlength="TITLE_MAX_LEN"
            placeholder="Token 名称，如 CI-流水线"
            class="aad-name"
          />
          <el-button type="primary" :loading="creating" @click="create">生成 Token</el-button>
        </div>
        <div v-for="t in tokens" :key="t.id" class="aad-token">
          <div class="aad-token-main">
            <div class="aad-token-name">{{ t.name }}</div>
            <code class="aad-token-val">{{ t.token }}</code>
          </div>
          <div class="aad-token-ops">
            <el-button size="small" @click="copy(t.token)">复制</el-button>
            <el-button size="small" type="danger" text @click="revoke(t)">吊销</el-button>
          </div>
        </div>
        <el-empty v-if="!tokens.length" description="暂无 Token" :image-size="60" />
      </section>

      <section class="aad-example">
        <h4 class="aad-example-title">调用示例</h4>
        <pre class="aad-code">{{ example }}</pre>
      </section>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { TITLE_MAX_LEN } from '@/constants/limits'
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { copyText } from '@/utils/clipboard'
import { useRouteParamId } from '@/composables/useRouteParamId'

const props = defineProps<{ modelValue: boolean; mode: 'import' | 'export' }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const pid = useRouteParamId()
const tokens = ref<Schemas['ApiTokenOut'][]>([])
const newName = ref('')
const creating = ref(false)

async function load() {
  try {
    tokens.value = await apifoxApi.listApiTokens(pid.value)
  } catch {
    /* 忽略 */
  }
}

async function create() {
  creating.value = true
  try {
    await apifoxApi.createApiToken(pid.value, { name: newName.value.trim() || 'API Token' })
    newName.value = ''
    await load()
    ElMessage.success('已生成 Token')
  } catch {
    ElMessage.error('生成失败')
  } finally {
    creating.value = false
  }
}

async function revoke(t: Schemas['ApiTokenOut']) {
  try {
    await ElMessageBox.confirm(`吊销 Token「${t.name}」后调用将失效，确认？`, '吊销确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await apifoxApi.revokeApiToken(t.id)
    await load()
  } catch {
    ElMessage.error('吊销失败')
  }
}

async function copy(text: string) {
  if (await copyText(text)) ElMessage.success('已复制')
  else ElMessage.warning('复制失败，请手动选择')
}

const example = computed(() => {
  const token = tokens.value[0]?.token || '<YOUR_TOKEN>'
  const base = `${window.location.origin}/api/v1/apifox/api`
  if (props.mode === 'import') {
    return (
      `curl -X POST '${base}/import' \\\n` +
      `  -H 'X-API-Token: ${token}' \\\n` +
      `  -H 'Content-Type: application/json' \\\n` +
      `  -d '{"url": "https://example.com/openapi.json"}'`
    )
  }
  return `curl '${base}/export/openapi?spec_version=3.0&file_format=json' \\\n  -H 'X-API-Token: ${token}' -OJ`
})
</script>

<style scoped>
.aad {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-4);
}

.aad-tip {
  margin: 0;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
  line-height: var(--ax-leading-normal);
}

.aad-tip code,
.aad-token-val {
  padding: 0 var(--ax-space-1);
  background: var(--ax-bg-subtle);
  border-radius: var(--ax-radius-sm);
}

.aad-tokens {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.aad-new {
  display: flex;
  gap: var(--ax-space-2);
}

.aad-name {
  flex: 1;
}

.aad-token {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-3);
  padding: var(--ax-space-2) var(--ax-space-3);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
}

.aad-token-main {
  min-width: 0;
  flex: 1;
}

.aad-token-name {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text);
}

.aad-token-val {
  display: inline-block;
  max-width: 100%;
  margin-top: var(--ax-space-1);
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aad-token-ops {
  display: flex;
  gap: var(--ax-space-1);
  flex: none;
}

.aad-example-title {
  margin: 0 0 var(--ax-space-2);
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text);
}

.aad-code {
  margin: 0;
  padding: var(--ax-space-3);
  background: var(--ax-bg-subtle);
  border-radius: var(--ax-radius);
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
