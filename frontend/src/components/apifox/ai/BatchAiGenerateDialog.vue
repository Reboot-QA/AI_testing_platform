<template>
  <el-dialog
    v-model="visible"
    title="批量 AI 生成接口测试用例"
    width="640px"
    class="batch-ai-gen-dialog"
    :close-on-click-modal="false"
    @closed="onClosed"
  >
    <div class="config">
      <div class="tip">
        选择接口并勾选类别，AI
        按各接口复杂度批量生成用例；已存在的同名用例不会重复创建。默认勾选「无用例」与「待复核」的接口，也可自行选择任意接口。
      </div>
      <AiGenConfigFields
        v-model="providerId"
        :providers="llmProviders"
        :providers-loading="providersLoading"
        :mock-mode="mockMode"
        :categories="categories"
      />
      <div class="ep-block">
        <div class="ep-head">
          <span>接口（{{ checkedCount }}/{{ endpoints.length }}）</span>
          <div class="ep-head-right">
            <el-checkbox v-model="onlyNeed" @change="onOnlyNeedChange">只看需生成</el-checkbox>
            <el-checkbox
              :model-value="allEpSelected"
              :indeterminate="someEpSelected"
              @change="toggleAllEndpoints"
              >全选</el-checkbox
            >
          </div>
        </div>
        <el-input
          v-model="epKeyword"
          :maxlength="SEARCH_MAX_LEN"
          size="small"
          placeholder="搜索接口名 / 路径 / 文件夹"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <div v-loading="endpointsLoading" class="tree-wrap">
          <el-tree
            ref="treeRef"
            :data="treeData"
            node-key="key"
            show-checkbox
            :props="{ disabled: 'disabled' }"
            :default-expanded-keys="['root']"
            :expand-on-click-node="false"
            :filter-node-method="filterNode"
            @check="syncChecked"
          >
            <template #default="{ data }">
              <span class="tree-node">
                <el-icon v-if="data.type === 'root'" class="node-icon node-icon--root"
                  ><Box
                /></el-icon>
                <el-icon v-else-if="data.type === 'folder'" class="node-icon"><Folder /></el-icon>
                <MethodTag
                  v-else-if="data.type === 'endpoint'"
                  :method="data.method"
                  class="tree-method"
                />
                <span class="node-label">{{ data.label }}</span>
                <span v-if="data.type === 'folder' || data.type === 'root'" class="node-count"
                  >({{ data.endpointCount ?? 0 }})</span
                >
                <span v-if="data.type === 'endpoint' && data.path" class="node-path">{{
                  data.path
                }}</span>
                <el-tag
                  v-if="data.type === 'endpoint' && caseCount(data.id) === 0"
                  size="small"
                  type="info"
                  class="ep-flag"
                  >无用例</el-tag
                >
                <el-tag
                  v-else-if="data.type === 'endpoint' && endpointById.get(data.id)?.cases_stale"
                  size="small"
                  type="warning"
                  class="ep-flag"
                  >待复核</el-tag
                >
              </span>
            </template>
          </el-tree>
          <el-empty
            v-if="!endpointsLoading && !treeData.length"
            description="无接口"
            :image-size="40"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="!anyChecked || checkedCount === 0"
        @click="generate"
        >生成（{{ checkedCount }} 个接口）</el-button
      >
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, nextTick, ref, watch } from 'vue'
import { Box, Folder, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { buildApiTree } from '@/composables/useApiTree'
import {
  applyImportTreeDisabled,
  filterImportTreeNode,
  type ImportTreeNode,
} from '@/composables/useImportCaseTree'
import { useAiGenConfig } from '@/composables/useAiGenConfig'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { useWorkspaceStore } from '@/stores/workspace'
import AiGenConfigFields from '@/components/apifox/ai/AiGenConfigFields.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const props = defineProps<{ projectId: string | number }>()
const emit = defineEmits<{ created: [] }>()

type Endpoint = Schemas['EndpointBrief']

type TreeExpose = {
  filter: (value: string) => void
  getCheckedKeys: (leafOnly?: boolean) => (string | number)[]
  setCheckedKeys: (keys: string[]) => void
}

const workspace = useWorkspaceStore()
const store = useApifoxAiGenerateStore()
const {
  categories,
  llmProviders,
  providersLoading,
  providerId,
  mockMode,
  anyChecked,
  resetCategories,
  loadProviders,
  buildCategoriesPayload,
} = useAiGenConfig()

const visible = ref(false)
const submitting = ref(false)
const endpoints = ref<Endpoint[]>([])
const endpointById = ref(new Map<number, Endpoint>())
const endpointsLoading = ref(false)
const epKeyword = ref('')
const treeData = ref<ImportTreeNode[]>([])
const treeRef = ref<TreeExpose | null>(null)
const checkedCount = ref(0)
const caseCounts = ref<Record<number, number>>({})
const onlyNeed = ref(false)
const autoSelectNeed = ref(false)

const caseCount = (id: number) => caseCounts.value[id] ?? 0
const needsGen = (ep: Endpoint) => caseCount(ep.id) === 0 || !!ep.cases_stale

function filterNode(value: string, data: ImportTreeNode): boolean {
  if (onlyNeed.value && data.type === 'endpoint') {
    const ep = endpointById.value.get(data.id)
    if (ep && !needsGen(ep)) return false
  }
  return filterImportTreeNode(value, data)
}

watch([epKeyword, onlyNeed], () => {
  treeRef.value?.filter(epKeyword.value)
  syncChecked()
})

function pickedEndpointIds(): number[] {
  const keys = new Set(treeRef.value?.getCheckedKeys(false) ?? [])
  const out: number[] = []
  const walk = (nodes: ImportTreeNode[], inherited: boolean) => {
    for (const node of nodes) {
      const checked = inherited || keys.has(node.key)
      if (node.children?.length) walk(node.children, checked)
      else if (checked && node.type === 'endpoint') out.push(node.id)
    }
  }
  walk(treeData.value, false)
  return out
}

function syncChecked() {
  checkedCount.value = pickedEndpointIds().length
}

function eligibleEndpointIds(): number[] {
  const kw = epKeyword.value.trim().toLowerCase()
  return endpoints.value
    .filter((ep) => {
      if (onlyNeed.value && !needsGen(ep)) return false
      if (kw && !ep.name.toLowerCase().includes(kw) && !ep.path.toLowerCase().includes(kw))
        return false
      return true
    })
    .map((e) => e.id)
}

const allEpSelected = computed(() => {
  const eligible = eligibleEndpointIds()
  if (!eligible.length) return false
  const picked = new Set(pickedEndpointIds())
  return eligible.every((id) => picked.has(id))
})

const someEpSelected = computed(() => {
  const n = checkedCount.value
  return n > 0 && !allEpSelected.value
})

function onOnlyNeedChange() {
  treeRef.value?.filter(epKeyword.value)
  if (onlyNeed.value) {
    const visible = new Set(eligibleEndpointIds())
    const keys = pickedEndpointIds()
      .filter((id) => visible.has(id))
      .map((id) => `e-${id}`)
    treeRef.value?.setCheckedKeys(keys)
  }
  syncChecked()
}

function toggleAllEndpoints(val: unknown) {
  const eligible = eligibleEndpointIds()
  const keys = eligible.map((id) => `e-${id}`)
  if (val) {
    const merged = new Set([...(treeRef.value?.getCheckedKeys(false) ?? []).map(String), ...keys])
    treeRef.value?.setCheckedKeys([...merged])
  } else {
    const remove = new Set(keys)
    const kept = (treeRef.value?.getCheckedKeys(false) ?? [])
      .map(String)
      .filter((k) => !remove.has(k))
    treeRef.value?.setCheckedKeys(kept)
  }
  syncChecked()
}

async function loadEndpoints() {
  endpointsLoading.value = true
  try {
    const [folders, eps, cases] = await Promise.all([
      apifoxApi.listFolders(props.projectId),
      apifoxApi.listEndpoints(props.projectId),
      apifoxApi.listProjectCases(props.projectId),
    ])
    endpoints.value = eps
    endpointById.value = new Map(eps.map((e) => [e.id, e]))
    const counts: Record<number, number> = {}
    for (const c of cases) counts[c.endpoint_id] = (counts[c.endpoint_id] ?? 0) + 1
    caseCounts.value = counts

    treeData.value = [
      {
        key: 'root',
        id: 0,
        type: 'root',
        label: workspace.currentProjectName || '当前项目',
        endpointCount: eps.length,
        children: buildApiTree(folders, eps) as ImportTreeNode[],
      },
    ]
    applyImportTreeDisabled(treeData.value, 'endpoint')

    await nextTick()
    if (autoSelectNeed.value) {
      treeRef.value?.setCheckedKeys(eps.filter(needsGen).map((e) => `e-${e.id}`))
    }
    if (epKeyword.value) treeRef.value?.filter(epKeyword.value)
    syncChecked()
  } finally {
    endpointsLoading.value = false
  }
}

function onClosed() {
  epKeyword.value = ''
  onlyNeed.value = false
  treeData.value = []
  checkedCount.value = 0
  endpoints.value = []
  endpointById.value = new Map()
}

function open(preselect?: number[]) {
  resetCategories()
  const hasPreselect = !!preselect && preselect.length > 0
  autoSelectNeed.value = !hasPreselect
  epKeyword.value = ''
  onlyNeed.value = false
  submitting.value = false
  loadProviders()
  visible.value = true
  void loadEndpoints().then(async () => {
    if (hasPreselect) {
      await nextTick()
      treeRef.value?.setCheckedKeys(preselect!.map((id) => `e-${id}`))
      syncChecked()
    }
  })
}
defineExpose({ open })

async function generate() {
  const ids = pickedEndpointIds()
  if (!ids.length) return
  submitting.value = true
  try {
    await store.start(Number(props.projectId), ids, buildCategoriesPayload(), providerId.value)
    ElMessage.success('已提交批量生成，请到「AI 任务中心」查看进度与结果')
    emit('created')
    visible.value = false
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || 'AI 任务创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.tip {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
  margin-bottom: var(--ax-space-3);
}

.ep-block {
  margin-top: var(--ax-space-2);
}

.ep-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
  margin-bottom: var(--ax-space-1-5);
}

.ep-head-right {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
}

.ep-flag {
  margin-left: var(--ax-space-1);
}

.tree-wrap {
  min-height: 280px;
  max-height: 360px;
  overflow: auto;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  padding: var(--ax-space-2);
  margin-top: var(--ax-space-1-5);
}

.tree-node {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  min-width: 0;
  font-size: var(--ax-font-sm);
  line-height: var(--ax-leading-compact);
}

.node-icon {
  flex-shrink: 0;
  font-size: 15px;
  color: var(--ax-tag-orange-fg);
}

.node-icon--root {
  color: var(--color-purple-6);
}

.tree-method {
  flex-shrink: 0;
}

.node-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-count {
  flex-shrink: 0;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.node-path {
  flex-shrink: 0;
  margin-left: var(--ax-space-1);
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.tree-wrap :deep(.el-tree-node__content) {
  height: 32px;
}

.tree-wrap :deep(.el-tree-node__content:hover) {
  background: var(--ax-bg-hover);
}
</style>

<style>
.batch-ai-gen-dialog .el-dialog__body {
  padding-top: var(--ax-space-2);
}
</style>
