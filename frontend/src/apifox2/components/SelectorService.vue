<template>
  <el-select
    :model-value="modelValue"
    style="width: 100%"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-option-group label="默认设置">
      <el-option value="" label="继承父级">
        <span class="a2-service-opt">
          <span>继承父级</span>
          <span class="a2-service-hint">跟随父级目录设置（推荐）</span>
        </span>
      </el-option>
    </el-option-group>
    <el-option-group label="手动指定">
      <el-option value="default" label="默认服务" />
    </el-option-group>
  </el-select>
</template>

<script setup lang="ts">
defineProps<{ modelValue?: string }>()
const emit = defineEmits<{ 'update:modelValue': [string | undefined] }>()
</script>

<style scoped>
.a2-service-opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: normal;
}

.a2-service-hint {
  margin-left: 40px;
  opacity: 0.5;
}
</style>
