<template>
  <div>
    <el-switch v-model="model.enabled" active-text="启用数据驱动" />

    <template v-if="model.enabled">
      <el-radio-group v-model="source" size="small" class="src">
        <el-radio-button value="inline">内联数据</el-radio-button>
        <el-radio-button value="dataset">引用数据集</el-radio-button>
      </el-radio-group>

      <div v-if="source === 'dataset'" class="ds-pick">
        <el-select
          v-model="model.dataset_id"
          filterable
          clearable
          placeholder="选择项目数据集"
          size="small"
          class="ds-select"
        >
          <el-option
            v-for="d in datasets"
            :key="d.id"
            :label="`${d.name}（${d.row_count} 行）`"
            :value="d.id"
          />
        </el-select>
        <p class="tip">执行时按所选数据集的每行数据各跑一次；到「数据集」页维护数据。</p>
      </div>
    </template>

    <p v-if="model.enabled && source === 'inline'" class="tip">
      列 = 用例变量；每行一组值，执行时按行跑多次。
    </p>

    <el-table v-if="model.enabled && source === 'inline'" :data="model.rows" size="small" border>
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

    <el-button
      v-if="model.enabled && source === 'inline'"
      link
      type="primary"
      size="small"
      class="add"
      @click="addRow"
    >
      + 添加数据行
    </el-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { variableNamesFromRows } from '@/utils/apiCaseConfig'

const props = defineProps({
  model: { type: Object, required: true },
  varRows: { type: Array, default: () => [] },
  datasets: { type: Array, default: () => [] },
})

const varNames = computed(() => variableNamesFromRows(props.varRows))

// undefined/其它 视为 inline；写回 model.source
const source = computed({
  get: () => (props.model.source === 'dataset' ? 'dataset' : 'inline'),
  set: (v) => {
    props.model.source = v
  },
})

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
  color: var(--ax-text-placeholder);
  font-size: 12px;
  margin: 8px 0;
}

.add {
  margin-top: 8px;
}

.src {
  display: block;
  margin: 10px 0;
}

.ds-select {
  width: 260px;
}
</style>
