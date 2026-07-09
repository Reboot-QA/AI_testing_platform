<template>
  <div>
    <div v-for="(row, i) in rows" :key="i" class="a-row">
      <el-checkbox v-model="row.enabled" />
      <el-select v-model="row.type" size="small" style="width: 130px">
        <el-option v-for="t in TYPES" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-input
        v-model="row.path"
        size="small"
        :disabled="!needsPath(row.type)"
        :placeholder="pathPlaceholder(row.type)"
        style="width: 180px"
      />
      <el-input v-model="row.expected" size="small" placeholder="期望值" />
      <el-button link type="danger" size="small" @click="rows.splice(i, 1)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <el-button link type="primary" size="small" @click="rows.push(emptyRow())">+ 添加断言</el-button>
  </div>
</template>

<script setup>
defineProps({ rows: { type: Array, required: true } })

const TYPES = [
  { value: 'status_code', label: '状态码' },
  { value: 'json_path', label: 'JSON 字段' },
  { value: 'header', label: '响应头' },
  { value: 'contains', label: '包含文本' },
  { value: 'response_time', label: '响应时间(ms)' },
]

function needsPath(type) {
  return type === 'json_path' || type === 'header'
}

function pathPlaceholder(type) {
  if (type === 'json_path') return '$.code'
  if (type === 'header') return 'Header 名'
  return '（无需）'
}

function emptyRow() {
  return { type: 'status_code', path: '', expected: '200', enabled: true }
}
</script>

<style scoped>
.a-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
</style>
