<template>
  <div class="proj-db h-full flex flex-col">
    <div class="db-toolbar">
      <span class="lbl">环境</span>
      <el-select
        v-model="envId"
        size="small"
        placeholder="选择环境"
        style="width: 220px"
        :teleported="false"
      >
        <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
      </el-select>
      <span class="hint">数据库连接按环境隔离；此处按环境分别管理。</span>
    </div>

    <div class="db-body flex-1 min-h-0">
      <EnvDatabasesPanel v-if="envId != null" :environment-id="envId" />
      <el-empty
        v-else
        description="请先选择一个环境（或到「环境管理」新建环境）"
        :image-size="64"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import EnvDatabasesPanel from '@/components/apifox/project/EnvDatabasesPanel.vue'

const workspace = useWorkspaceStore()
const environments = computed(() => workspace.environments)
// 默认取当前选中环境，便于与顶部环境一致
const envId = ref<number | null>(workspace.currentEnvironmentId)
</script>

<style scoped>
.proj-db {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.db-toolbar {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.lbl {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.hint {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-placeholder);
}

.db-body {
  flex: 1;
  min-height: 0;
}
</style>
