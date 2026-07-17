<template>
  <div>
    <div v-for="(row, i) in rows" :key="i" class="e-row">
      <el-checkbox v-model="row.enabled" />
      <el-input v-model="row.var_name" size="small" placeholder="变量名" style="width: 130px" />
      <el-select v-model="row.source" size="small" style="width: 150px">
        <el-option v-for="s in EXTRACT_SOURCE_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-input v-model="row.path" size="small" placeholder="路径/表达式" style="width: 160px" />
      <el-select v-model="row.scope" size="small" style="width: 110px">
        <el-option v-for="sc in VARIABLE_SCOPE_OPTIONS" :key="sc.value" :label="sc.label" :value="sc.value" />
      </el-select>
      <el-button link type="danger" size="small" @click="rows.splice(i, 1)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <el-button link type="primary" size="small" @click="rows.push(emptyRow())">+ 添加提取</el-button>
  </div>
</template>

<script setup lang="ts">
import type { Schemas } from '@/api/types'
import { EXTRACT_SOURCE_OPTIONS, VARIABLE_SCOPE_OPTIONS } from '@/utils/apiCaseConfig'

type ExtractRow = Schemas['ExtractRow']

defineProps<{ rows: ExtractRow[] }>()

function emptyRow(): ExtractRow {
  return { var_name: '', source: 'response_json', path: '$.data', scope: 'environment', enabled: true }
}
</script>

<style scoped>
.e-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
</style>
