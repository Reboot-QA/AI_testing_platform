<template>
  <div class="run-config">
    <span class="rc-label">运行数据集</span>
    <el-select
      :model-value="datasetId"
      clearable
      placeholder="不绑定（按循环次数）"
      size="small"
      style="width: 220px"
      @update:model-value="$emit('update:datasetId', $event || null)"
    >
      <el-option v-for="d in datasets" :key="d.id" :label="d.name" :value="d.id" />
    </el-select>
    <span class="rc-label">循环次数</span>
    <el-input-number
      :model-value="loopCount"
      :min="1"
      :max="1000"
      :disabled="!!datasetId"
      size="small"
      controls-position="right"
      style="width: 130px"
      @update:model-value="$emit('update:loopCount', $event || 1)"
    />
    <span class="rc-hint">
      {{ datasetId ? '按数据集每行数据各跑一遍整场景' : '整场景重复跑 N 遍' }}
    </span>
  </div>
</template>

<script setup>
// 绑数据集时按行数据驱动整场景（循环次数忽略）；否则整场景重复跑循环次数遍
defineProps({
  datasets: { type: Array, default: () => [] },
  loopCount: { type: Number, default: 1 },
  datasetId: { type: [Number, String], default: null },
})
defineEmits(['update:loopCount', 'update:datasetId'])
</script>

<style scoped>
.run-config {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--ax-bg-subtle);
  border-radius: 6px;
}

.rc-label {
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.rc-hint {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>
