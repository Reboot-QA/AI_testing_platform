<template>
  <div class="dataset-panel">
    <div class="list-panel">
      <div class="list-toolbar">
        <span>数据集</span>
        <el-button size="small" type="primary" @click="addDataset">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="d in datasets"
        :key="d.id"
        class="item"
        :class="{ active: form.id === d.id }"
        @click="selectDataset(d.id)"
      >
        <el-icon><Grid /></el-icon>
        <span class="item-name">{{ d.name }}</span>
        <el-tag size="small" type="info">{{ d.row_count }} 行</el-tag>
        <el-tag v-if="d.ref_count" size="small" type="warning" title="被用例引用数">
          {{ d.ref_count }}
        </el-tag>
        <el-button link type="danger" size="small" @click.stop="delDataset(d)">删</el-button>
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

        <div class="cols-bar">
          <span class="cols-label">列：</span>
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
              <el-button link type="danger" size="small" @click="form.rows.splice($index, 1)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button link type="primary" size="small" class="add-row" @click="addRow">+ 添加数据行</el-button>
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
  width: 260px;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 8px;
}

.item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.item:hover {
  background: var(--ax-bg-hover);
}

.item.active {
  background: var(--ax-bg-active);
}

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-panel {
  flex: 1;
  overflow: auto;
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

.cols-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.cols-label {
  font-weight: 600;
  color: var(--ax-brand);
}

.col-input {
  width: 120px;
}

.rows-table {
  margin-bottom: 8px;
}
</style>
