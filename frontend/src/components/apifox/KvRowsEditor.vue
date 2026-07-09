<template>
  <div class="kv-editor">
    <div v-for="(row, i) in rows" :key="i" class="kv-row">
      <el-checkbox v-model="row.enabled" />
      <el-input v-model="row.key" placeholder="键" size="small" />
      <el-input v-model="row.value" placeholder="值" size="small" />
      <el-button link type="danger" size="small" @click="rows.splice(i, 1)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <el-button link type="primary" size="small" @click="rows.push(emptyKvRow())">
      + 添加一行
    </el-button>
  </div>
</template>

<script setup>
import { emptyKvRow } from '@/utils/apiCaseConfig'

// rows 为父级 reactive 数组（按引用传入），子组件就地增删改，父级自动响应。
defineProps({ rows: { type: Array, required: true } })
</script>

<style scoped>
.kv-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
</style>
