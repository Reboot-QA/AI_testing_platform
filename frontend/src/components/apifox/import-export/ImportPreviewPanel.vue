<template>
  <div class="ipp">
    <ImportPreviewTree :nodes="nodes" class="ipp-left" @update:selected="selectedKeys = $event" />

    <div class="ipp-right">
      <h4 class="ipp-title">{{ preview.title || '导入数据' }}</h4>

      <div class="ipp-field">
        <label class="ipp-label">目标目录</label>
        <el-tree-select
          v-model="targetFolderId"
          :data="folderOptions"
          node-key="value"
          check-strictly
          clearable
          :render-after-expand="false"
          placeholder="根目录"
          class="ipp-select"
        />
        <p class="ipp-tip">文档里的 tag 会作为子目录建在这里；没有 tag 的接口直接放在该目录下。</p>
      </div>

      <div class="ipp-field">
        <label class="ipp-label">
          已存在的接口
          <span v-if="preview.exists_count" class="ipp-inline-num">
            （{{ preview.exists_count }} 个，其中 {{ preview.changed_count }} 个契约有变更）
          </span>
        </label>
        <el-radio-group v-model="onConflict" :disabled="!preview.exists_count">
          <el-radio value="skip">跳过，不动已有接口</el-radio>
          <el-radio value="overwrite">覆盖请求契约（保留本地命名与鉴权设置）</el-radio>
        </el-radio-group>
      </div>

      <div class="ipp-field ipp-field--row">
        <el-switch v-model="withSchemas" :disabled="!preview.schemas_total" />
        <span class="ipp-label">
          同时导入数据模型
          <span v-if="preview.schemas_total" class="ipp-inline-num">
            （共 {{ preview.schemas_total }} 个，新增 {{ preview.schemas_new }} 个）
          </span>
        </span>
      </div>

      <div class="ipp-actions">
        <el-button :disabled="busy" @click="emit('back')">返回</el-button>
        <el-button
          type="primary"
          :loading="busy"
          :disabled="!selectedKeys.length"
          @click="onConfirm"
        >
          确定导入{{ selectedKeys.length ? `（${selectedKeys.length}）` : '' }}
        </el-button>
      </div>

      <button v-if="hasEndpoints" type="button" class="ipp-link" @click="emit('to-sync')">
        需要清理文档里已移除的接口？改用「更新同步」
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Schemas } from '@/api/types'
import type { FolderOptionNode } from '@/types/apifox'
import type { ImportChoice } from '@/composables/useImportWorkspace'
import { apifoxApi } from '@/api'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { buildFolderOptions, buildImportPreviewTree } from '@/utils/importPreviewTree'
import ImportPreviewTree from '@/components/apifox/import-export/ImportPreviewTree.vue'

const props = defineProps<{
  preview: Schemas['ImportPreviewOut']
  busy: boolean
  hasEndpoints: boolean
}>()

const emit = defineEmits<{
  back: []
  'to-sync': []
  confirm: [choice: ImportChoice]
}>()

const pid = useRouteParamId()
const selectedKeys = ref<string[]>([])
const targetFolderId = ref<number | null>(null)
const onConflict = ref<'skip' | 'overwrite'>('skip')
const withSchemas = ref(true)
const folderOptions = ref<FolderOptionNode[]>([])

const nodes = computed(() => buildImportPreviewTree(props.preview))

async function loadFolders() {
  try {
    folderOptions.value = buildFolderOptions(await apifoxApi.listFolders(pid.value))
  } catch {
    folderOptions.value = [] // 拉不到目录时退化为只能导入到根目录
  }
}

watch(
  () => props.preview,
  () => {
    targetFolderId.value = null
    onConflict.value = 'skip'
    withSchemas.value = !!props.preview.schemas_total
    loadFolders()
  },
  { immediate: true },
)

function onConfirm() {
  emit('confirm', {
    selectedKeys: selectedKeys.value,
    targetFolderId: targetFolderId.value,
    onConflict: onConflict.value,
    withSchemas: withSchemas.value,
  })
}
</script>

<style scoped>
.ipp {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: var(--ax-space-4);
}

.ipp-left {
  min-width: 0;
}

.ipp-right {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-4);
  padding-left: var(--ax-space-4);
  border-left: 1px solid var(--ax-border);
}

.ipp-title {
  margin: 0;
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text);
}

.ipp-field {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.ipp-field--row {
  flex-direction: row;
  align-items: center;
  gap: var(--ax-space-2);
}

.ipp-label {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text);
}

.ipp-inline-num {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-caption-size);
}

.ipp-select {
  width: 100%;
}

.ipp-tip {
  margin: 0;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
  line-height: var(--ax-leading-compact);
}

.ipp-right :deep(.el-radio) {
  display: flex;
  height: auto;
  margin-right: 0;
  white-space: normal;
}

.ipp-actions {
  display: flex;
  gap: var(--ax-space-2);
}

.ipp-actions .el-button {
  flex: 1;
}

.ipp-link {
  padding: 0;
  border: none;
  background: none;
  color: var(--ax-brand);
  cursor: pointer;
  font-size: var(--ax-text-caption-size);
  text-align: left;
}
</style>
