<template>
  <div class="global-params">
    <div class="var-title">全局参数（项目级，执行时自动附加到请求 · header/query/cookie）</div>
    <el-table :data="displayRows" size="small" border class="param-table">
      <el-table-column label="位置" width="120">
        <template #default="{ row }">
          <el-select v-if="isDraft(row)" v-model="draft.location" size="small">
            <el-option v-for="l in LOCATIONS" :key="l" :label="l" :value="l" />
          </el-select>
          <el-select v-else v-model="row.location" size="small" @change="updateParam(row)">
            <el-option v-for="l in LOCATIONS" :key="l" :label="l" :value="l" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="参数名" min-width="140">
        <template #default="{ row }">
          <el-input
            v-if="isDraft(row)"
            ref="draftKeyRef"
            v-model="draft.key"
            :maxlength="KEY_MAX_LEN"
            size="small"
            placeholder="在此输入新参数名"
            @blur="onDraftBlur"
            @keyup.enter="commitDraft"
          />
          <el-input
            v-else
            v-model="row.key"
            :maxlength="KEY_MAX_LEN"
            size="small"
            @change="updateParam(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="值" min-width="180">
        <template #default="{ row }">
          <VarInput
            v-if="isDraft(row)"
            v-model="draft.value"
            placeholder="值"
            @change="onDraftBlur"
          />
          <VarInput v-else v-model="row.value" @change="updateParam(row)" />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="70" align="center">
        <template #default="{ row }">
          <el-switch v-if="isDraft(row)" v-model="draft.enabled" size="small" />
          <el-switch v-else v-model="row.enabled" size="small" @change="updateParam(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="72" align="center">
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
          <el-button v-else link type="danger" size="small" @click="delParam(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="add-hint">
      <el-button link type="primary" size="small" @click="focusDraft">
        <el-icon><Plus /></el-icon> 新增参数
      </el-button>
      <span class="hint-text">在表格末行填写后点「新增」，或回车 / 离开该行自动保存</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { KEY_MAX_LEN } from '@/constants/limits'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { InputInstance } from 'element-plus'
import { apifoxApi } from '@/api'
import { useResolvableVarsReload } from '@/composables/useResolvableVars'
import VarInput from '@/components/apifox/common/VarInput.vue'

const props = defineProps<{ projectId: Id }>()
const reloadResolvableVars = useResolvableVarsReload()

const LOCATIONS = ['header', 'query', 'cookie', 'body'] as const
type Location = (typeof LOCATIONS)[number]

/** 表内末行草稿哨兵 id，对齐 Apifox：在列表里直接输入新建 */
const DRAFT_ID = -1

const params = ref<Schemas['GlobalParamOut'][]>([])
const draftKeyRef = ref<InputInstance>()
const draft = reactive({
  location: 'header' as Location,
  key: '',
  value: '',
  enabled: true,
})
const committing = ref(false)

const displayRows = computed(() => [
  ...params.value,
  {
    id: DRAFT_ID,
    project_id: Number(props.projectId) || 0,
    location: draft.location,
    key: '',
    value: '',
    enabled: true,
    sort_order: 0,
  } as Schemas['GlobalParamOut'],
])

function isDraft(row: Schemas['GlobalParamOut']) {
  return row.id === DRAFT_ID
}

function resetDraft() {
  draft.location = 'header'
  draft.key = ''
  draft.value = ''
  draft.enabled = true
}

function focusDraft() {
  nextTick(() => draftKeyRef.value?.focus())
}

async function loadParams() {
  params.value = await apifoxApi.listGlobalParams(props.projectId)
}

async function commitDraft() {
  const key = draft.key.trim()
  if (!key || committing.value) return
  committing.value = true
  try {
    await apifoxApi.createGlobalParam(props.projectId, {
      location: draft.location,
      key,
      value: draft.value,
      enabled: draft.enabled,
    })
    resetDraft()
    await loadParams()
    await reloadResolvableVars()
    focusDraft()
  } finally {
    committing.value = false
  }
}

/** 焦点仍在末行草稿内则不提交 */
function onDraftBlur() {
  nextTick(() => {
    const active = document.activeElement as HTMLElement | null
    if (active?.closest?.('.param-table .el-table__body tr:last-child')) return
    void commitDraft()
  })
}

async function updateParam(row: Schemas['GlobalParamOut']) {
  await apifoxApi.updateGlobalParam(row.id, {
    location: row.location,
    key: row.key,
    value: row.value,
    enabled: row.enabled,
  })
  await loadParams()
  await reloadResolvableVars()
}

async function delParam(row: Schemas['GlobalParamOut']) {
  await apifoxApi.deleteGlobalParam(row.id)
  await loadParams()
  await reloadResolvableVars()
}

onMounted(loadParams)
</script>

<style scoped>
.var-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: var(--ax-space-3);
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
