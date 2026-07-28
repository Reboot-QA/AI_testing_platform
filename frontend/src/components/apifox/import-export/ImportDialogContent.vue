<template>
  <div class="idd-content">
    <!-- OpenAPI -->
    <template v-if="format === 'openapi'">
      <div class="idd-tabs">
        <button
          v-for="t in OPENAPI_TABS"
          :key="t.key"
          type="button"
          class="idd-tab"
          :class="{ active: openapiTab === t.key }"
          @click="openapiTab = t.key"
        >
          {{ t.label }}
        </button>
      </div>
      <ImportDropZone
        v-if="openapiTab === 'file'"
        ref="dropRef"
        accept=".json,.yaml,.yml,.txt"
        @file="emitFile"
      />
      <div v-else-if="openapiTab === 'url'" class="idd-url">
        <label class="idd-req">URL *</label>
        <el-input
          :maxlength="URL_MAX_LEN"
          :model-value="url"
          placeholder="输入 OpenAPI/Swagger 数据 URL"
          @update:model-value="emit('update:url', $event)"
        />
        <div class="idd-auth">
          <span>Basic Auth</span>
          <el-switch :model-value="basicAuth" @update:model-value="onBasicAuth" />
        </div>
        <div v-if="basicAuth" class="idd-auth-fields">
          <el-input
            :maxlength="VALUE_MAX_LEN"
            :model-value="basicAuthUser"
            placeholder="用户名"
            size="small"
            @update:model-value="emit('update:basicAuthUser', String($event))"
          />
          <el-input
            :maxlength="SECRET_MAX_LEN"
            :model-value="basicAuthPwd"
            type="password"
            placeholder="密码"
            size="small"
            show-password
            @update:model-value="emit('update:basicAuthPwd', String($event))"
          />
        </div>
      </div>
      <ImportGitConnectList v-else />
    </template>

    <!-- Postman -->
    <ImportDropZone
      v-else-if="format === 'postman'"
      ref="dropRef"
      variant="postman"
      accept=".json"
      @file="emitFile"
      @folder="comingSoon"
    />

    <!-- cURL：页内粘贴 -->
    <div v-else-if="format === 'curl'" class="idd-curl">
      <label class="idd-req">cURL *</label>
      <el-input
        :maxlength="PASTE_MAX_LEN"
        :model-value="curlText"
        type="textarea"
        :rows="10"
        placeholder="粘贴 cURL 命令，例如：curl -X POST 'https://api.example.com/v1/login' -H 'Content-Type: application/json' -d '{...}'"
        @update:model-value="emit('update:curlText', String($event))"
      />
    </div>

    <!-- Apifox -->
    <template v-else-if="format === 'apifox'">
      <div class="idd-tabs">
        <button
          type="button"
          class="idd-tab"
          :class="{ active: apifoxTab === 'file' }"
          @click="apifoxTab = 'file'"
        >
          上传文件
        </button>
        <button
          type="button"
          class="idd-tab"
          :class="{ active: apifoxTab === 'git' }"
          @click="apifoxTab = 'git'"
        >
          Git 仓库
        </button>
      </div>
      <ImportDropZone v-if="apifoxTab === 'file'" ref="dropRef" accept=".json" @file="emitFile" />
      <ImportGitConnectList v-else />
    </template>

    <!-- JMeter -->
    <ImportDropZone
      v-else-if="format === 'jmeter'"
      ref="dropRef"
      accept=".jmx,.xml"
      @file="emitFile"
    />
  </div>
</template>

<script setup lang="ts">
import { PASTE_MAX_LEN, SECRET_MAX_LEN, URL_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { ImportSourceFormat } from '@/types/apifox'
import ImportDropZone from '@/components/apifox/import-export/ImportDropZone.vue'
import ImportGitConnectList from '@/components/apifox/import-export/ImportGitConnectList.vue'

const props = defineProps<{
  format: ImportSourceFormat
  url: string
  basicAuth: boolean
  basicAuthUser: string
  basicAuthPwd: string
  curlText: string
}>()

const emit = defineEmits<{
  'update:url': [v: string]
  'update:basicAuth': [v: boolean]
  'update:basicAuthUser': [v: string]
  'update:basicAuthPwd': [v: string]
  'update:curlText': [v: string]
  'update:mode': [m: 'file' | 'url' | 'git' | 'paste' | 'stub']
  file: [file: File]
}>()

const OPENAPI_TABS = [
  { key: 'file' as const, label: '上传文件' },
  { key: 'url' as const, label: 'URL 导入' },
  { key: 'git' as const, label: 'Git 仓库' },
]

const openapiTab = ref<'file' | 'url' | 'git'>('file')
const apifoxTab = ref<'file' | 'git'>('file')
const dropRef = ref<InstanceType<typeof ImportDropZone> | null>(null)

function comingSoon() {
  ElMessage.info('敬请期待')
}

function onBasicAuth(on: boolean) {
  emit('update:basicAuth', on)
}

function emitFile(file: File) {
  emit('file', file)
}

function syncMode() {
  if (props.format === 'openapi') {
    emit('update:mode', openapiTab.value)
  } else if (props.format === 'postman') {
    emit('update:mode', 'file')
  } else if (props.format === 'curl') {
    emit('update:mode', 'paste')
  } else if (props.format === 'apifox') {
    emit('update:mode', apifoxTab.value === 'git' ? 'git' : 'file')
  } else {
    // jmeter：文件上传
    emit('update:mode', 'file')
  }
}

watch(openapiTab, syncMode)
watch(apifoxTab, syncMode)
watch(
  () => props.format,
  () => {
    openapiTab.value = 'file'
    apifoxTab.value = 'file'
    dropRef.value?.clear()
    syncMode()
  },
  { immediate: true },
)

function reset() {
  openapiTab.value = 'file'
  apifoxTab.value = 'file'
  dropRef.value?.clear()
  syncMode()
}

defineExpose({ reset })
</script>

<style scoped>
.idd-content {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.idd-tabs {
  display: flex;
  padding: var(--ax-space-1);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  gap: var(--ax-space-1);
}

.idd-tab {
  flex: 1;
  height: 32px;
  border: none;
  border-radius: var(--ax-radius-sm);
  background: transparent;
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
  cursor: pointer;
}

.idd-tab.active {
  background: var(--ax-bg);
  color: var(--ax-text);
  font-weight: 600;
}

.idd-url {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.idd-req {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-danger);
}

.idd-auth {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.idd-auth-fields {
  display: flex;
  gap: var(--ax-space-2);
  margin-top: var(--ax-space-2);
}

.idd-curl {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}
</style>
