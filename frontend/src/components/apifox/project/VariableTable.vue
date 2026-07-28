<template>
  <div class="var-table-wrap scrollbar-visible">
    <el-table :data="displayRows" size="small" border class="var-table" scrollbar-always-on>
      <el-table-column label="变量名" min-width="140">
        <template #default="{ row }">
          <el-input
            v-if="isDraft(row)"
            ref="draftKeyRef"
            v-model="draft.key"
            size="small"
            :maxlength="KEY_MAX_LEN"
            placeholder="在此输入新变量名"
            @blur="onDraftBlur"
            @keyup.enter="commitDraft"
          />
          <el-input
            v-else
            v-model="row.key"
            size="small"
            :maxlength="KEY_MAX_LEN"
            @change="$emit('update', row.id, { key: row.key })"
          />
        </template>
      </el-table-column>
      <el-table-column label="远程值（团队共享）" min-width="160">
        <template #default="{ row }">
          <VarInput
            v-if="isDraft(row)"
            v-model="draft.remote_value"
            placeholder="远程值"
            @change="onDraftBlur"
          />
          <VarInput
            v-else
            v-model="row.remote_value"
            placeholder="团队共享"
            @change="onRemoteChange(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="我的本地值（个人覆盖）" min-width="160">
        <template #default="{ row }">
          <span v-if="isDraft(row)" class="draft-placeholder">—</span>
          <VarInput
            v-else
            v-model="row.local_value"
            placeholder="留空=用远程值"
            @change="onLocalChange(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="有效值" min-width="120">
        <template #default="{ row }">
          <span v-if="isDraft(row)" class="draft-placeholder">—</span>
          <el-popover
            v-else
            placement="top"
            trigger="hover"
            :width="'auto'"
            :show-after="300"
            :disabled="!row.effective_value"
            popper-class="var-value-popover"
          >
            <template #reference>
              <span class="eff">{{ row.effective_value ?? '-' }}</span>
            </template>
            <div class="var-value-popover__body">{{ row.effective_value ?? '-' }}</div>
          </el-popover>
        </template>
      </el-table-column>
      <el-table-column label="密文" width="70" align="center" fixed="right">
        <template #default="{ row }">
          <el-switch v-if="isDraft(row)" v-model="draft.is_secret" size="small" />
          <el-switch
            v-else
            v-model="row.is_secret"
            size="small"
            @change="$emit('update', row.id, { is_secret: row.is_secret })"
          />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="70" align="center" fixed="right">
        <template #default="{ row }">
          <el-switch v-if="isDraft(row)" v-model="draft.enabled" size="small" />
          <el-switch
            v-else
            v-model="row.enabled"
            size="small"
            @change="$emit('update', row.id, { enabled: row.enabled })"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="72" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="isDraft(row)"
            link
            type="primary"
            size="small"
            :disabled="!draft.key.trim()"
            @mousedown.prevent
            @click="commitDraft"
          >
            新增
          </el-button>
          <el-button v-else link type="danger" size="small" @click="$emit('delete', row.id)">
            删
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="add-hint">
      <el-button link type="primary" size="small" @click="focusDraft">
        <el-icon><Plus /></el-icon> 新增变量
      </el-button>
      <span class="hint-text">在表格末行填写后点「新增」，或回车 / 离开该行自动保存</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import type { Schemas } from '@/api/types'
import type { InputInstance } from 'element-plus'
import { KEY_MAX_LEN } from '@/constants/limits'
import VarInput from '@/components/apifox/common/VarInput.vue'

type VariableOut = Schemas['VariableOut']
type VariableCreate = Schemas['VariableCreate']

/** 表内末行草稿哨兵 id，对齐 Apifox：在列表里直接输入新建 */
const DRAFT_ID = -1

/** 密文变量对外脱敏占位（与后端 variable_service.SECRET_MASK 一致）：
 *  行值仍是掩码（未改动）时不回写，避免仅聚焦掠过密文框就用掩码覆盖真值。 */
const SECRET_MASK = '••••••'

const props = withDefaults(defineProps<{ variables?: VariableOut[] }>(), {
  variables: () => [],
})
const emit = defineEmits<{
  create: [payload: VariableCreate]
  update: [id: number, payload: Partial<VariableOut>]
  delete: [id: number]
  'set-local': [id: number, value: string | null]
}>()

const draftKeyRef = ref<InputInstance>()
const draft = reactive({
  key: '',
  remote_value: '',
  is_secret: false,
  enabled: true,
})
const committing = ref(false)

const displayRows = computed(() => [
  ...props.variables,
  {
    id: DRAFT_ID,
    key: '',
    remote_value: '',
    local_value: null,
    effective_value: null,
    is_secret: false,
    enabled: true,
    sort_order: 0,
  } as VariableOut,
])

function isDraft(row: VariableOut) {
  return row.id === DRAFT_ID
}

/** 密文行的值仍为掩码 = 用户没改，跳过回写；否则按用户新输入的真值保存 */
function onRemoteChange(row: VariableOut) {
  if (row.is_secret && row.remote_value === SECRET_MASK) return
  emit('update', row.id, { remote_value: row.remote_value })
}

function onLocalChange(row: VariableOut) {
  if (row.is_secret && row.local_value === SECRET_MASK) return
  emit('set-local', row.id, row.local_value ? row.local_value : null)
}

function resetDraft() {
  draft.key = ''
  draft.remote_value = ''
  draft.is_secret = false
  draft.enabled = true
}

function focusDraft() {
  nextTick(() => draftKeyRef.value?.focus())
}

function commitDraft() {
  const key = draft.key.trim()
  if (!key || committing.value) return
  committing.value = true
  emit('create', {
    key,
    remote_value: draft.remote_value,
    is_secret: draft.is_secret,
    enabled: draft.enabled,
  })
  resetDraft()
  committing.value = false
  focusDraft()
}

/** 焦点仍在末行草稿内（如 Tab 到远程值）则不提交，避免只填了名就被创建 */
function onDraftBlur() {
  nextTick(() => {
    const active = document.activeElement as HTMLElement | null
    if (active?.closest?.('.var-table .el-table__body tr:last-child')) return
    commitDraft()
  })
}
</script>

<style scoped>
.var-table-wrap {
  width: 100%;
  min-width: 0;
  /* 横滑交给表格内部；避免外层再叠一层横滚导致 Windows 拖不动 */
  overflow-x: hidden;
}

.var-table {
  width: 100%;
}

.eff {
  color: var(--ax-success);
  font-size: var(--ax-text-body-sm-size);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  word-break: break-word;
  white-space: normal;
  line-height: var(--ax-leading-compact);
  max-width: 100%;
}

.draft-placeholder {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-body-sm-size);
}

.add-hint {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-top: var(--ax-space-2);
}

.hint-text {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}
</style>

<!-- popover 挂到 body，需非 scoped -->
<style>
.var-value-popover.el-popper {
  max-width: var(--ax-dialog-width-md) !important;
  width: max-content !important;
}

.var-value-popover .var-value-popover__body {
  max-width: var(--ax-dialog-width-md);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: var(--ax-leading-compact);
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
  max-height: 240px;
  overflow: auto;
}
</style>
