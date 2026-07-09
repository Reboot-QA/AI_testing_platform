<template>
  <div>
    <el-switch v-model="model.enabled" active-text="启用数据驱动" />
    <p class="tip">列 = 用例变量；每行一组值，执行时按行跑多次（执行引擎 P4 接入）。</p>

    <el-table v-if="model.enabled" :data="model.rows" size="small" border>
      <el-table-column label="数据集名" width="140">
        <template #default="{ row }">
          <el-input v-model="row.name" size="small" />
        </template>
      </el-table-column>
      <el-table-column v-for="name in varNames" :key="name" :label="name" min-width="120">
        <template #default="{ row }">
          <el-input v-model="row.values[name]" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="60" align="center">
        <template #default="{ row }">
          <el-switch v-model="row.enabled" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" align="center">
        <template #default="{ $index }">
          <el-button link type="danger" size="small" @click="model.rows.splice($index, 1)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-button v-if="model.enabled" link type="primary" size="small" class="add" @click="addRow">
      + 添加数据集
    </el-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { variableNamesFromRows } from '@/utils/apiCaseConfig'

const props = defineProps({
  model: { type: Object, required: true },
  varRows: { type: Array, default: () => [] },
})

const varNames = computed(() => variableNamesFromRows(props.varRows))

function addRow() {
  const values = {}
  varNames.value.forEach((n) => {
    values[n] = ''
  })
  props.model.rows.push({ name: `数据集${props.model.rows.length + 1}`, enabled: true, values })
}
</script>

<style scoped>
.tip {
  color: #94a3b8;
  font-size: 12px;
  margin: 8px 0;
}

.add {
  margin-top: 8px;
}
</style>
