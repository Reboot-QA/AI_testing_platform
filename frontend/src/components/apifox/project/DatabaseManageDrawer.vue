<template>
  <el-dialog
    v-model="visible"
    title="数据库连接管理"
    width="720px"
    align-center
    destroy-on-close
    append-to-body
    class="db-manage-dialog"
    @opened="onDialogOpened"
  >
    <p class="dialog-tip">
      连接按<strong>环境</strong>隔离，与顶部当前运行环境一致。供接口/用例/场景「数据库」步骤使用。
    </p>
    <div class="env-row">
      <span class="env-lbl">环境</span>
      <el-select v-model="envId" size="small" placeholder="选择环境" style="flex: 1" filterable>
        <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
      </el-select>
    </div>
    <EnvDatabasesPanel
      v-if="envId != null"
      ref="panelRef"
      :environment-id="envId"
      @updated="onPanelUpdated"
    />
    <el-empty v-else description="请先选择环境" :image-size="64" />
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import EnvDatabasesPanel from '@/components/apifox/project/EnvDatabasesPanel.vue'
import { useDatabaseManageDrawer } from '@/composables/useDatabaseManageDrawer'
import { useWorkspaceStore } from '@/stores/workspace'

const drawer = useDatabaseManageDrawer()
const { visible, envId, notifyUpdated } = drawer
const workspace = useWorkspaceStore()
const environments = computed(() => workspace.environments)
const panelRef = ref<InstanceType<typeof EnvDatabasesPanel> | null>(null)

function onPanelUpdated() {
  notifyUpdated()
}

async function onDialogOpened() {
  if (!drawer.openCreateOnShow.value) return
  await nextTick()
  panelRef.value?.openCreateDialog()
  drawer.openCreateOnShow.value = false
}

defineExpose({ close: drawer.close })
</script>

<style scoped>
.dialog-tip {
  margin: 0 0 var(--ax-space-3);
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
  line-height: 1.5;
}

.env-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-3);
}

.env-lbl {
  flex-shrink: 0;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}
</style>

<style>
/* append-to-body：保证表格操作列不被右侧布局裁切 */
.db-manage-dialog .el-dialog__body {
  max-height: min(70vh, 640px);
  overflow: auto;
}
</style>
