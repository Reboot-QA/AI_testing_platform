<template>
  <div class="kv-param-table">
    <div class="kv-toolbar">
      <el-button size="small" @click="addRow">添加参数</el-button>
      <slot name="toolbar-extra" />
      <el-button v-if="showBatchDelete" size="small" type="danger" plain @click="batchDelete">
        批量删除
      </el-button>
      <el-button v-if="showBulk" size="small" @click="bulkDialogVisible = true">批量编辑</el-button>
    </div>
    <el-table :data="rows" size="small" border class="kv-table">
      <el-table-column v-if="showBatchDelete" width="44" align="center">
        <template #header>
          <el-checkbox v-model="allSelected" :indeterminate="indeterminate" />
        </template>
        <template #default="{ $index }">
          <el-checkbox :model-value="isSelected($index)" @change="(val) => toggleSelect($index, val)" />
        </template>
      </el-table-column>
      <el-table-column v-if="showEnabled" label="启用" width="60" align="center">
        <template #default="{ row }">
          <el-checkbox v-model="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column :label="keyLabel" min-width="140">
        <template #default="{ row }">
          <el-input v-model="row.key" :placeholder="keyPlaceholder" size="small" />
        </template>
      </el-table-column>
      <el-table-column :label="valueLabel" min-width="180">
        <template #default="{ row }">
          <VariableSuggestInput
            v-if="enableVariableSuggest"
            v-model="row.value"
            :variables="variables"
            :placeholder="row.key?.trim() ? '(空值)' : valuePlaceholder"
          />
          <el-input
            v-else
            v-model="row.value"
            :placeholder="row.key?.trim() ? '(空值)' : valuePlaceholder"
            size="small"
          />
        </template>
      </el-table-column>
      <el-table-column v-if="showDesc" label="说明" min-width="120">
        <template #default="{ row }">
          <el-input v-model="row.desc" placeholder="备注" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" align="center">
        <template #default="{ $index }">
          <el-button link type="danger" @click="removeRow($index)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="bulkDialogVisible" title="批量编辑" width="520px" append-to-body>
      <div class="form-tip">每行一条，格式：参数名:参数值</div>
      <el-input v-model="bulkText" type="textarea" :rows="10" />
      <template #footer>
        <el-button @click="bulkDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyBulk">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { emptyKvRow } from '@/utils/apiCaseConfig'
import VariableSuggestInput from '@/components/VariableSuggestInput.vue'

const rows = defineModel('rows', { type: Array, required: true })
const props = defineProps({
  keyLabel: { type: String, default: '参数名' },
  valueLabel: { type: String, default: '参数值' },
  keyPlaceholder: { type: String, default: 'Key' },
  valuePlaceholder: { type: String, default: 'Value' },
  showEnabled: { type: Boolean, default: true },
  showDesc: { type: Boolean, default: true },
  showBulk: { type: Boolean, default: true },
  showBatchDelete: { type: Boolean, default: false },
  variables: { type: Array, default: () => [] },
})

const enableVariableSuggest = computed(() => (props.variables || []).length > 0)
const bulkDialogVisible = ref(false)
const bulkText = ref('')
const selectedIndexes = ref(new Set())

watch(
  () => rows.value.length,
  () => {
    selectedIndexes.value = new Set(
      [...selectedIndexes.value].filter((index) => index < rows.value.length)
    )
  }
)

const allSelected = computed({
  get() {
    return rows.value.length > 0 && selectedIndexes.value.size === rows.value.length
  },
  set(checked) {
    selectedIndexes.value = checked
      ? new Set(rows.value.map((_, index) => index))
      : new Set()
  },
})

const indeterminate = computed(() => {
  const count = selectedIndexes.value.size
  return count > 0 && count < rows.value.length
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

function batchDelete() {
  if (!selectedIndexes.value.size) {
    ElMessage.warning('请先勾选要删除的参数')
    return
  }
  const removeSet = new Set(selectedIndexes.value)
  const next = rows.value.filter((_, index) => !removeSet.has(index))
  rows.value = next.length ? next : [emptyKvRow()]
  selectedIndexes.value = new Set()
}

function addRow() {
  rows.value = [...rows.value, emptyKvRow()]
}

function removeRow(index) {
  const next = rows.value.filter((_, i) => i !== index)
  rows.value = next.length ? next : [emptyKvRow()]
}

function applyBulk() {
  const parsed = bulkText.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const idx = line.indexOf(':')
      if (idx === -1) return emptyKvRow()
      return {
        key: line.slice(0, idx).trim(),
        value: line.slice(idx + 1).trim(),
        enabled: true,
        desc: '',
      }
    })
    .filter((r) => r.key)
  rows.value = parsed.length ? parsed : [emptyKvRow()]
  bulkDialogVisible.value = false
}
</script>

<style scoped>
.kv-toolbar {
  margin-bottom: 8px;
  display: flex;
  gap: 8px;
}

.kv-table {
  width: 100%;
}

.form-tip {
  margin-bottom: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
