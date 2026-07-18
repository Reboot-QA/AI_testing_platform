<template>
  <div class="a2-baseform">
    <div class="a2-bf-grid">
      <div class="a2-bf-item">
        <label>状态</label>
        <el-select
          :model-value="model.status"
          style="width: 100%"
          @change="emit('update', { status: $event })"
        >
          <el-option v-for="o in statusOptions" :key="o.value" :value="o.value" :label="o.text">
            <span class="a2-bf-status">
              <span class="a2-bf-dot" :style="{ backgroundColor: `var(${o.color})` }" />
              {{ o.text }}
            </span>
          </el-option>
        </el-select>
      </div>

      <div class="a2-bf-item">
        <label>责任人</label>
        <el-select
          :model-value="model.responsibleId"
          style="width: 100%"
          @change="emit('update', { responsibleId: $event })"
        >
          <el-option :value="creator.id" :label="`${creator.name}（@${creator.username}）`" />
        </el-select>
      </div>

      <div class="a2-bf-item">
        <label>标签</label>
        <el-select
          :model-value="model.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="查找或回车创建标签"
          style="width: 100%"
          @change="emit('update', { tags: $event })"
        />
      </div>

      <div class="a2-bf-item">
        <label>服务（前置 URL）</label>
        <SelectorService
          :model-value="model.serverId"
          @update:model-value="emit('update', { serverId: $event })"
        />
      </div>

      <div class="a2-bf-item a2-bf-full">
        <label>说明</label>
        <InputDesc
          :model-value="model.description"
          @update:model-value="emit('update', { description: $event })"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import SelectorService from '@/apifox2/components/SelectorService.vue'
import InputDesc from './InputDesc.vue'
import { statusOptions } from '../options'
import { creator } from '@/apifox2/data/remote'
import type { ApiDetails } from '@/apifox2/types'

defineProps<{ model: Partial<ApiDetails> }>()
const emit = defineEmits<{ update: [Partial<ApiDetails>] }>()
</script>

<style scoped>
.a2-bf-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 900px) {
  .a2-bf-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.a2-bf-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.a2-bf-item label {
  color: var(--a2-color-text-secondary);
  font-size: 13px;
}

.a2-bf-full {
  grid-column: 1 / -1;
}

.a2-bf-status {
  display: flex;
  align-items: center;
}

.a2-bf-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 8px;
  display: inline-block;
}
</style>
