<template>
  <div class="dataset-panel">
    <div class="list-panel">
      <div class="panel-head">
        <span class="panel-title">数据集</span>
        <el-button type="primary" size="small" title="新建数据集" @click="addDataset">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="d in datasets"
        :key="d.id"
        class="dataset-row"
        :class="{ 'dataset-row--active': form.id === d.id }"
        @click="onSelectDataset(d.id)"
      >
        <el-icon class="dataset-row-icon"><Grid /></el-icon>
        <el-tooltip :content="d.name" placement="right" :show-after="600">
          <span class="dataset-name">{{ d.name }}</span>
        </el-tooltip>
        <span class="dataset-meta">{{ d.row_count }} 行</span>
        <el-tooltip v-if="d.ref_count" content="被用例引用数" placement="right" :show-after="300">
          <span class="dataset-ref">{{ d.ref_count }} 引用</span>
        </el-tooltip>
        <el-icon class="dataset-del" title="删除数据集" @click.stop="delDataset(d)">
          <Delete />
        </el-icon>
      </div>
      <el-empty v-if="datasets.length === 0" description="暂无数据集" :image-size="60" />
    </div>

    <div class="editor-panel">
      <template v-if="isDraft || form.id">
        <div class="row1">
          <el-input
            v-model="form.name"
            placeholder="数据集名称（保存前填写）"
            :maxlength="TITLE_MAX_LEN"
            style="width: 240px"
          />
          <el-button type="primary" :loading="saving" @click="saveDataset">保存</el-button>
          <el-tag v-if="isDraft" size="small" type="info">未保存草稿</el-tag>
        </div>
        <el-input
          v-model="form.description"
          placeholder="描述（选填）"
          :maxlength="DESC_MAX_LEN"
          show-word-limit
          class="desc-input"
        />

        <div class="section-title">列定义</div>
        <div class="cols-bar">
          <el-tag
            v-for="(c, i) in form.columns"
            :key="c"
            size="small"
            closable
            class="col-tag"
            @close="removeColumn(i)"
          >
            {{ c }}
          </el-tag>
          <el-input
            v-model="newCol"
            :maxlength="KEY_MAX_LEN"
            size="small"
            placeholder="输入列名后回车 / 点添加"
            class="col-input"
            @keyup.enter="addColumn"
            @blur="addColumn"
          />
          <el-button size="small" :disabled="!newCol.trim()" @click="addColumn">添加列</el-button>
        </div>

        <div class="section-title">数据行</div>
        <el-alert
          v-if="form.columns.length === 0"
          type="info"
          :closable="false"
          show-icon
          title="尚未定义列：请先在上方「列定义」输入列名并回车（或点「添加列」），数据行才会出现对应的列。"
          class="rows-empty-tip"
        />
        <!-- 未定义列时不渲染数据行表格：空列的行没有意义，只留上方提示 -->
        <template v-if="form.columns.length > 0">
          <el-table :data="form.rows" size="small" border class="rows-table">
            <el-table-column type="index" label="#" width="46" />
            <el-table-column v-for="c in form.columns" :key="c" :label="c" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.values[c]" :maxlength="VALUE_MAX_LEN" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="启用" width="60" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button
                  link
                  type="danger"
                  size="small"
                  class="row-del"
                  @click="form.rows.splice($index, 1)"
                >
                  删
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button link type="primary" size="small" class="add-row-btn" @click="addRow">
            + 添加数据行
          </el-button>
        </template>
      </template>
      <el-empty v-else description="选择或新建一个数据集（可被用例数据驱动引用）" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { DESC_MAX_LEN, KEY_MAX_LEN, TITLE_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'

const pid = useRouteParamId()

const datasets = ref<Schemas['DatasetBrief'][]>([])
const saving = ref(false)
const newCol = ref('')
const isDraft = ref(false) // 草稿态：新建先填列/行/名称，保存时才落库
const form = reactive({
  id: null as number | null,
  name: '',
  description: '',
  columns: [] as string[],
  rows: [] as Array<{ values: Record<string, string>; enabled: boolean }>,
  version: 1,
})

async function loadDatasets() {
  datasets.value = await apifoxApi.listDatasets(pid.value)
}

const guard = useUnsavedGuard({
  serialize: () =>
    JSON.stringify({
      id: form.id,
      name: form.name,
      description: form.description,
      columns: form.columns,
      rows: form.rows,
    }),
  save: () => saveDataset(),
  name: () => form.name,
})

async function selectDataset(did: number) {
  const d = await apifoxApi.getDataset(did)
  isDraft.value = false
  form.id = d.id
  form.name = d.name
  form.description = d.description || ''
  form.columns = d.columns || []
  form.rows = (d.rows || []).map((r) => ({ values: { ...r.values }, enabled: r.enabled !== false }))
  form.version = d.version ?? 1
  newCol.value = '' // 切数据集清空未确认的列名，避免残留文本经 blur 混进另一个数据集
  guard.markSaved()
}

async function onSelectDataset(id: number) {
  if (id === form.id) return
  if (!(await guard.confirmLeave())) return
  await selectDataset(id)
}

defineExpose({ create: () => addDataset() })

async function addDataset() {
  if (!(await guard.confirmLeave())) return
  // 进入草稿态：先填列/行，最后再填名称一起保存（此时才落库）
  form.id = null
  form.name = ''
  form.description = ''
  form.columns = []
  form.rows = []
  form.version = 1
  newCol.value = ''
  isDraft.value = true
  guard.markSaved()
}

function addColumn() {
  const name = newCol.value.trim()
  if (!name) return
  if (form.columns.includes(name)) {
    ElMessage.warning('列名已存在')
    return
  }
  form.columns.push(name)
  // 已有数据行补齐新列的空值：否则这些行存回后端时 values 缺该 key（表现为「没有 key 和 value」）
  form.rows.forEach((r) => {
    if (r.values[name] === undefined) r.values[name] = ''
  })
  newCol.value = ''
}

function removeColumn(i: number) {
  const name = form.columns[i]
  form.columns.splice(i, 1)
  form.rows.forEach((r) => delete r.values[name])
}

function addRow() {
  const values: Record<string, string> = {}
  form.columns.forEach((c) => {
    values[c] = ''
  })
  form.rows.push({ values, enabled: true })
}

async function doSaveDataset() {
  if (isDraft.value) {
    const created = await apifoxApi.createDataset(pid.value, {
      name: form.name.trim(),
      description: form.description || null,
      columns: form.columns,
      rows: form.rows.map((r) => ({ values: r.values, enabled: r.enabled })),
    })
    await loadDatasets()
    await selectDataset(created.id)
    return
  }
  if (form.id == null) return
  const updated = await apifoxApi.updateDataset(form.id, {
    name: form.name,
    description: form.description || null,
    columns: form.columns,
    rows: form.rows.map((r) => ({ values: r.values, enabled: r.enabled })),
    expected_version: form.version,
  })
  form.version = updated.version
  await loadDatasets()
}

async function saveDataset() {
  // 先落定列名输入框里尚未确认的列：否则「输了列名直接点保存」会被静默丢弃，存成 0 列数据集
  addColumn()
  if (!form.name.trim()) {
    ElMessage.warning('请先填写数据集名称')
    return false
  }
  const datasetId = form.id
  saving.value = true
  try {
    await doSaveDataset()
    guard.markSaved()
    ElMessage.success('已保存')
    return true
  } catch (e) {
    if (!isConflict(e)) return false // 非冲突错误已由 api 拦截器提示
    if (datasetId == null) return false
    let resolved = false
    await resolveSaveConflict({
      reload: async () => {
        await selectDataset(datasetId)
        resolved = true
      },
      overwrite: async () => {
        const latest = await apifoxApi.getDataset(datasetId)
        form.version = latest.version
        await doSaveDataset()
        guard.markSaved()
        resolved = true
      },
    })
    return resolved
  } finally {
    saving.value = false
  }
}

async function delDataset(d: Schemas['DatasetBrief']) {
  await ElMessageBox.confirm(`确认删除数据集「${d.name}」？被用例引用时会被拦截。`, '提示', {
    type: 'warning',
  })
  await apifoxApi.deleteDataset(d.id)
  if (form.id === d.id) {
    form.id = null
    isDraft.value = false
  }
  ElMessage.success('已删除')
  await loadDatasets()
}

onMounted(loadDatasets)
</script>

<style scoped>
.dataset-panel {
  display: flex;
  gap: var(--ax-space-4);
  height: 100%;
}

/* 字号阶梯：面板标题 14 > 数据集名 12 > 元信息 11；list-panel/panel-head 见 apifox-workspace.css */
.dataset-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  padding: var(--ax-space-1-5) var(--ax-space-1-5) var(--ax-space-1-5) var(--ax-space-2);
  border-radius: 4px;
  cursor: pointer;
}

.dataset-row:hover {
  background: var(--ax-bg-hover);
}

.dataset-row--active {
  background: var(--ax-bg-active);
}

.dataset-row-icon {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-tertiary);
}

.dataset-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
  font-weight: 400;
  line-height: var(--ax-leading-compact);
  color: var(--ax-text);
}

.dataset-meta {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: var(--ax-leading-tight);
  color: var(--ax-text-placeholder);
  font-variant-numeric: tabular-nums;
}

.dataset-ref {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: var(--ax-leading-tight);
  color: var(--el-color-warning);
  font-variant-numeric: tabular-nums;
}

.dataset-del {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  cursor: pointer;
  color: var(--ax-text-placeholder);
  transition: color 0.15s;
}

.dataset-del:hover {
  color: var(--el-color-danger);
}

.list-panel :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}

.editor-panel {
  flex: 1;
  overflow: auto;
  min-width: 0;
}

.desc-input {
  margin-bottom: var(--ax-space-3);
}

.section-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: var(--ax-leading-compact);
  color: var(--ax-brand);
  margin-bottom: var(--ax-space-2);
}

.section-title + .rows-table {
  margin-top: 0;
}

.cols-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ax-space-1-5);
  margin-bottom: var(--ax-space-3-5);
}

.cols-bar :deep(.el-tag) {
  height: 22px;
  padding: 0 var(--ax-space-2);
  font-size: var(--ax-font-xs);
  line-height: 20px;
}

.col-input {
  width: 120px;
}

.rows-empty-tip {
  margin-bottom: var(--ax-space-2);
}

.rows-table {
  margin-bottom: var(--ax-space-1-5);
}

.rows-table :deep(.el-table__header th) {
  font-size: var(--ax-font-xs);
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.rows-table :deep(.el-table__body td) {
  font-size: var(--ax-font-xs);
}

.rows-table :deep(.row-del.el-button.is-link) {
  padding: 0 var(--ax-space-1);
  font-size: var(--ax-font-xs);
  height: auto;
}

.add-row-btn {
  font-size: var(--ax-font-xs);
  padding: 0;
}

.editor-panel :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}
</style>
