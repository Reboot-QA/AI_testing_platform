<template>
  <div class="dataset-panel">
    <div class="list-panel">
      <div class="panel-head">
        <span class="panel-title">数据集</span>
        <el-button size="small" type="primary" title="新建数据集" @click="addDataset">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="d in datasets"
        :key="d.id"
        class="dataset-row"
        :class="{ 'dataset-row--active': form.id === d.id }"
        @click="selectDataset(d.id)"
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
      <template v-if="form.id">
        <div class="row1">
          <el-input v-model="form.name" placeholder="数据集名称" style="width: 240px" />
          <el-button type="primary" :loading="saving" @click="saveDataset">保存</el-button>
        </div>
        <el-input v-model="form.description" placeholder="描述（选填）" class="desc-input" />

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
            size="small"
            placeholder="+ 列名"
            class="col-input"
            @keyup.enter="addColumn"
          />
        </div>

        <div class="section-title">数据行</div>
        <el-table :data="form.rows" size="small" border class="rows-table">
          <el-table-column type="index" label="#" width="46" />
          <el-table-column v-for="c in form.columns" :key="c" :label="c" min-width="120">
            <template #default="{ row }">
              <el-input v-model="row.values[c]" size="small" />
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
      <el-empty v-else description="选择或新建一个数据集（可被用例数据驱动引用）" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const datasets = ref([])
const saving = ref(false)
const newCol = ref('')
const form = reactive({ id: null, name: '', description: '', columns: [], rows: [], version: 1 })

async function loadDatasets() {
  datasets.value = await apifoxApi.listDatasets(pid.value)
}

async function selectDataset(did) {
  const d = await apifoxApi.getDataset(did)
  form.id = d.id
  form.name = d.name
  form.description = d.description || ''
  form.columns = d.columns || []
  form.rows = (d.rows || []).map((r) => ({ values: { ...r.values }, enabled: r.enabled !== false }))
  form.version = d.version ?? 1
}

async function addDataset() {
  const { value } = await ElMessageBox.prompt('数据集名称', '新建数据集', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createDataset(pid.value, { name: value, columns: [], rows: [] })
  ElMessage.success('已创建')
  await loadDatasets()
  await selectDataset(created.id)
}

function addColumn() {
  const name = newCol.value.trim()
  if (!name) return
  if (form.columns.includes(name)) {
    ElMessage.warning('列名已存在')
    return
  }
  form.columns.push(name)
  newCol.value = ''
}

function removeColumn(i) {
  const name = form.columns[i]
  form.columns.splice(i, 1)
  form.rows.forEach((r) => delete r.values[name])
}

function addRow() {
  const values = {}
  form.columns.forEach((c) => {
    values[c] = ''
  })
  form.rows.push({ values, enabled: true })
}

async function doSaveDataset() {
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
  saving.value = true
  try {
    await doSaveDataset()
    ElMessage.success('已保存')
  } catch (e) {
    if (!isConflict(e)) return // 非冲突错误已由 api 拦截器提示
    await resolveSaveConflict({
      reload: async () => {
        await selectDataset(form.id)
      },
      overwrite: async () => {
        const latest = await apifoxApi.getDataset(form.id)
        form.version = latest.version
        await doSaveDataset()
      },
    })
  } finally {
    saving.value = false
  }
}

async function delDataset(d) {
  await ElMessageBox.confirm(`确认删除数据集「${d.name}」？被用例引用时会被拦截。`, '提示', {
    type: 'warning',
  })
  await apifoxApi.deleteDataset(d.id)
  if (form.id === d.id) form.id = null
  ElMessage.success('已删除')
  await loadDatasets()
}

onMounted(loadDatasets)
</script>

<style scoped>
.dataset-panel {
  display: flex;
  gap: 16px;
  height: 100%;
}

.list-panel {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

/* 字号阶梯：面板标题 14 > 数据集名 12 > 元信息 11 */
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.panel-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: 1.25;
  color: var(--ax-brand);
}

.dataset-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 6px 6px 8px;
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
  line-height: 1.35;
  color: var(--ax-text);
}

.dataset-meta {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: 1;
  color: var(--ax-text-placeholder);
  font-variant-numeric: tabular-nums;
}

.dataset-ref {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: 1;
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

.row1 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.desc-input {
  margin-bottom: 12px;
}

.section-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: 1.35;
  color: var(--ax-brand);
  margin-bottom: 8px;
}

.section-title + .rows-table {
  margin-top: 0;
}

.cols-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}

.cols-bar :deep(.el-tag) {
  height: 22px;
  padding: 0 8px;
  font-size: var(--ax-font-xs);
  line-height: 20px;
}

.col-input {
  width: 120px;
}

.rows-table {
  margin-bottom: 6px;
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
  padding: 0 4px;
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
