<template>
  <div class="data-drive-table">
    <div class="kv-toolbar">
      <el-button size="small" :disabled="!variableNames.length" @click="addRow">添加数据集</el-button>
      <el-button size="small" :disabled="!variableNames.length" @click="csvDialogVisible = true">从 CSV 导入</el-button>
      <el-button size="small" :disabled="!variableNames.length" @click="jsonDialogVisible = true">从 JSON 导入</el-button>
      <el-button size="small" type="danger" plain :disabled="!selectedIndexes.size" @click="batchDelete">
        批量删除
      </el-button>
    </div>

    <div v-if="!variableNames.length" class="form-tip empty-tip">请先在上方定义变量名，再配置数据驱动数据集</div>

    <el-table v-else :data="rows" size="small" border class="kv-table">
      <el-table-column width="44" align="center">
        <template #header>
          <el-checkbox v-model="allSelected" :indeterminate="indeterminate" />
        </template>
        <template #default="{ $index }">
          <el-checkbox :model-value="isSelected($index)" @change="(val) => toggleSelect($index, val)" />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="60" align="center">
        <template #default="{ row }">
          <el-checkbox v-model="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="数据集名称" min-width="120">
        <template #default="{ row, $index }">
          <el-input v-model="row.name" :placeholder="`数据集${$index + 1}`" size="small" />
        </template>
      </el-table-column>
      <el-table-column
        v-for="name in variableNames"
        :key="name"
        :label="name"
        min-width="140"
      >
        <template #default="{ row }">
          <el-input v-model="row.values[name]" :placeholder="defaultValues[name] || ''" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" align="center">
        <template #default="{ $index }">
          <el-button link type="danger" @click="removeRow($index)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="csvDialogVisible" title="从 CSV 导入" width="560px" append-to-body>
      <div class="form-tip">首行可为变量名表头（phone,password），也可直接写数据行</div>
      <el-input v-model="csvText" type="textarea" :rows="10" placeholder="phone,password&#10;13800138000,abc123" />
      <template #footer>
        <el-button @click="csvDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyCsv">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="jsonDialogVisible" title="从 JSON 导入" width="560px" append-to-body>
      <div class="form-tip">JSON 数组，每项为一组变量值</div>
      <el-input
        v-model="jsonText"
        type="textarea"
        :rows="10"
        placeholder='[{"phone":"13800138000","password":"abc123"}]'
      />
      <template #footer>
        <el-button @click="jsonDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyJson">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  defaultValuesFromRows,
  emptyDataDriveRow,
  parseCsvDataSets,
  parseJsonDataSets,
  variableNamesFromRows,
} from '@/utils/apiCaseConfig'

const rows = defineModel('rows', { type: Array, required: true })
const props = defineProps({
  variableRows: { type: Array, default: () => [] },
})

const variableNames = computed(() => variableNamesFromRows(props.variableRows))
const defaultValues = computed(() => defaultValuesFromRows(props.variableRows))

const csvDialogVisible = ref(false)
const jsonDialogVisible = ref(false)
const csvText = ref('')
const jsonText = ref('')
const selectedIndexes = ref(new Set())

watch(variableNames, (names) => {
  rows.value = (rows.value || []).map((row) => ({
    enabled: row.enabled !== false,
    name: row.name || '',
    values: {
      ...Object.fromEntries(names.map((name) => [name, ''])),
      ...(row.values || {}),
    },
  }))
  if (!rows.value.length && names.length) {
    rows.value = [emptyDataDriveRow(names)]
  }
}, { immediate: true })

const allSelected = computed({
  get() {
    return rows.value.length > 0 && selectedIndexes.value.size === rows.value.length
  },
  set(val) {
    selectedIndexes.value = val ? new Set(rows.value.map((_, index) => index)) : new Set()
  },
})

const indeterminate = computed(() => {
  const size = selectedIndexes.value.size
  return size > 0 && size < rows.value.length
})

function isSelected(index) {
  return selectedIndexes.value.has(index)
}

function toggleSelect(index, checked) {
  const next = new Set(selectedIndexes.value)
  if (checked) next.add(index)
  else next.delete(index)
  selectedIndexes.value = next
}

function addRow() {
  rows.value.push(emptyDataDriveRow(variableNames.value))
}

function removeRow(index) {
  rows.value.splice(index, 1)
  if (!rows.value.length) {
    rows.value.push(emptyDataDriveRow(variableNames.value))
  }
}

function batchDelete() {
  rows.value = rows.value.filter((_, index) => !selectedIndexes.value.has(index))
  selectedIndexes.value = new Set()
  if (!rows.value.length) {
    rows.value.push(emptyDataDriveRow(variableNames.value))
  }
}

function applyCsv() {
  try {
    const imported = parseCsvDataSets(csvText.value, variableNames.value)
    rows.value = [...rows.value.filter((row) => row.name?.trim() || Object.values(row.values || {}).some((v) => String(v ?? '').trim())), ...imported]
    csvDialogVisible.value = false
    csvText.value = ''
    ElMessage.success(`已导入 ${imported.length} 组数据`)
  } catch (err) {
    ElMessage.error(err.message || 'CSV 解析失败')
  }
}

function applyJson() {
  try {
    const imported = parseJsonDataSets(jsonText.value, variableNames.value)
    rows.value = [...rows.value.filter((row) => row.name?.trim() || Object.values(row.values || {}).some((v) => String(v ?? '').trim())), ...imported]
    jsonDialogVisible.value = false
    jsonText.value = ''
    ElMessage.success(`已导入 ${imported.length} 组数据`)
  } catch (err) {
    ElMessage.error(err.message || 'JSON 解析失败')
  }
}
</script>

<style scoped>
.kv-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.kv-table {
  width: 100%;
}

.empty-tip {
  margin-top: 4px;
}
</style>
