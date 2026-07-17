<template>
  <div class="loop-editor">
    <div class="le-field">
      <span class="le-label">模式</span>
      <el-select v-model="config.mode" size="small" style="width: 140px" @change="onModeChange">
        <el-option label="固定次数" value="count" />
        <el-option label="遍历列表" value="list" />
        <el-option label="条件循环 while" value="while" />
      </el-select>
    </div>

    <div v-if="config.mode === 'count'" class="le-field">
      <span class="le-label">次数</span>
      <el-input-number v-model="config.count" :min="1" :max="1000" size="small" />
    </div>

    <template v-else-if="config.mode === 'list'">
      <div class="le-field">
        <span class="le-label">列表变量</span>
        <el-input v-model="config.list_var" size="small" placeholder="存 JSON 数组的变量名" />
      </div>
      <div class="le-field">
        <span class="le-label">元素变量</span>
        <el-input v-model="config.item_var" size="small" placeholder="item" />
      </div>
      <div class="le-field">
        <span class="le-label">下标变量</span>
        <el-input v-model="config.index_var" size="small" placeholder="index" />
      </div>
    </template>

    <template v-else-if="config.mode === 'while'">
      <div class="le-field">
        <span class="le-label">条件</span>
        <ConditionEditor :condition="config.condition" />
      </div>
      <div class="le-field">
        <span class="le-label">最大次数</span>
        <el-input-number v-model="config.max_iterations" :min="1" :max="1000" size="small" />
        <span class="le-hint">硬上限防死循环</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import ConditionEditor from '@/components/apifox/ConditionEditor.vue'
import type { ConditionConfig } from '@/components/apifox/ConditionEditor.vue'

export interface LoopConfig {
  mode: string
  count?: number | null
  list_var?: string
  item_var?: string
  index_var?: string
  max_iterations?: number | null
  condition?: ConditionConfig
}

const props = defineProps<{ config: LoopConfig }>()

function onModeChange(mode: string) {
  const c = props.config
  if (mode === 'count' && c.count == null) c.count = 1
  if (mode === 'list') {
    if (!c.item_var) c.item_var = 'item'
    if (!c.index_var) c.index_var = 'index'
  }
  if (mode === 'while') {
    if (!c.condition) c.condition = { left: '', operator: 'eq', right: '' }
    if (c.max_iterations == null) c.max_iterations = 10
  }
}
</script>

<style scoped>
.loop-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.le-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.le-label {
  flex-shrink: 0;
  width: 68px;
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.le-hint {
  font-size: 12px;
  color: var(--ax-text-placeholder);
}
</style>
