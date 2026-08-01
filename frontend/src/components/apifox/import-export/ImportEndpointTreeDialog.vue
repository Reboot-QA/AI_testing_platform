<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="640px"
    class="import-endpoint-dialog"
    :close-on-click-modal="false"
    @closed="onClosed"
  >
    <div class="project-row">
      <span class="project-badge">{{ projectName || '当前项目' }}</span>
      <span class="project-hint">（当前项目）</span>
    </div>

    <el-input
      v-model="filterText"
      :maxlength="SEARCH_MAX_LEN"
      size="small"
      clearable
      :placeholder="searchPlaceholder"
      class="tree-search"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <div v-loading="loading" class="tree-wrap">
      <el-tree
        ref="treeRef"
        :data="treeData"
        node-key="key"
        show-checkbox
        :props="{ disabled: 'disabled' }"
        :default-expanded-keys="['root', SCENARIO_ROOT_KEY, SUITE_ROOT_KEY]"
        :expand-on-click-node="false"
        :filter-node-method="filterNode"
        @check="(node: ImportTreeNode) => onTreeCheck(node)"
      >
        <template #default="{ data }">
          <span class="tree-node">
            <el-icon v-if="data.type === 'root'" class="node-icon node-icon--root"><Box /></el-icon>
            <el-icon v-else-if="data.type === 'scenario-root'" class="node-icon node-icon--root">
              <Connection />
            </el-icon>
            <el-icon v-else-if="data.type === 'suite-root'" class="node-icon node-icon--root">
              <Box />
            </el-icon>
            <el-icon
              v-else-if="data.type === 'folder' || data.type === 'scenario-folder'"
              class="node-icon"
            >
              <Folder />
            </el-icon>
            <span v-else-if="data.type === 'case'" class="case-badge">TC</span>
            <span v-else-if="data.type === 'scenario'" class="scene-badge">场景</span>
            <span v-else-if="data.type === 'suite'" class="scene-badge suite-badge">套件</span>
            <MethodTag
              v-else-if="data.type === 'endpoint'"
              :method="data.method"
              class="tree-method"
            />
            <span class="node-label">{{ data.label }}</span>
            <span v-if="showNodeCount(data)" class="node-count"
              >({{ displayNodeCount(data) }})</span
            >
            <span v-if="data.type === 'endpoint' && data.path" class="node-path">{{
              data.path
            }}</span>
          </span>
        </template>
      </el-tree>
      <el-empty v-if="!loading && !treeData.length" :description="emptyText" :image-size="48" />
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div class="footer-left">
          <span class="picked-count">
            已选 {{ checkedCount }} 个
            <span v-if="noPickableHint" class="picked-hint">（所选节点下暂无可添加项）</span>
          </span>
          <div v-if="importMode === 'import-case'" class="import-as-row">
            <span class="import-as-label">导入方式</span>
            <el-radio-group v-model="importAs" size="small">
              <el-radio value="copy">复制</el-radio>
              <el-radio value="reference">引用</el-radio>
            </el-radio-group>
          </div>
        </div>
        <div class="footer-actions">
          <el-button :disabled="checkedCount === 0" @click="clearChecked">全部移除</el-button>
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" :disabled="checkedCount === 0" @click="confirm">{{
            isSchedulePick ? '确定' : '添加'
          }}</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, toRef } from 'vue'
import { Box, Connection, Folder, Search } from '@element-plus/icons-vue'
import type { Id } from '@/api/request'
import {
  SCENARIO_ROOT_KEY,
  SUITE_ROOT_KEY,
  type ImportConfirmPayload,
  type ImportTreeNode,
} from '@/composables/useImportCaseTree'
import { useImportEndpointDialog } from '@/composables/useImportEndpointDialog'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const props = defineProps<{ projectId: Id }>()
const emit = defineEmits<{ confirm: [ImportConfirmPayload] }>()

const {
  visible,
  importMode,
  importAs,
  loading,
  filterText,
  treeData,
  treeRef,
  checkedCount,
  noPickableHint,
  projectName,
  dialogTitle,
  searchPlaceholder,
  emptyText,
  filterNode,
  onTreeCheck,
  clearChecked,
  open,
  onClosed,
  confirm,
} = useImportEndpointDialog(toRef(props, 'projectId'), (payload) => emit('confirm', payload))

const isSchedulePick = computed(
  () =>
    importMode.value === 'pick-schedule-case' ||
    importMode.value === 'pick-schedule-scenario' ||
    importMode.value === 'pick-schedule-suite',
)

/** 用例模式下各级显示用例数（接口节点也显示），接口模式下只有目录/根显示接口数 */
function showNodeCount(data: { type: string }): boolean {
  if (
    data.type === 'scenario-root' ||
    data.type === 'scenario-folder' ||
    data.type === 'suite-root'
  ) {
    return true
  }
  const withCases =
    importMode.value === 'import-case' ||
    importMode.value === 'pick-suite-item' ||
    importMode.value === 'pick-suite-case' ||
    importMode.value === 'pick-schedule-case'
  if (!withCases) {
    return data.type === 'folder' || data.type === 'root'
  }
  return data.type === 'folder' || data.type === 'root' || data.type === 'endpoint'
}

function displayNodeCount(data: {
  type: string
  caseCount?: number
  endpointCount?: number
  scenarioCount?: number
  suiteCount?: number
}): number {
  if (data.type === 'suite-root') return data.suiteCount ?? 0
  if (data.type === 'scenario-root' || data.type === 'scenario-folder') {
    return data.scenarioCount ?? 0
  }
  if (
    importMode.value === 'import-case' ||
    importMode.value === 'pick-suite-item' ||
    importMode.value === 'pick-suite-case' ||
    importMode.value === 'pick-schedule-case'
  ) {
    return data.caseCount ?? 0
  }
  return data.endpointCount ?? 0
}

defineExpose({ open })
</script>

<style scoped>
.project-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  margin-bottom: var(--ax-space-3);
}

.project-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--ax-space-1) var(--ax-space-2-5);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
}

.project-hint {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.tree-search {
  margin-bottom: var(--ax-space-2);
}

.tree-wrap {
  min-height: 320px;
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  padding: var(--ax-space-2);
}

.tree-node {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  min-width: 0;
  font-size: var(--ax-font-sm);
  line-height: var(--ax-leading-compact);
}

.node-icon {
  flex-shrink: 0;
  font-size: 15px;
  color: var(--ax-tag-orange-fg);
}

.node-icon--root {
  color: var(--color-purple-6);
}

.case-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 18px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  color: var(--ax-text);
  background: color-mix(in srgb, var(--color-yellow-6) 55%, white);
}

.scene-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 18px;
  padding: 0 var(--ax-space-1);
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  color: var(--ax-tag-orange-fg);
  background: color-mix(in srgb, var(--ax-tag-orange-fg) 14%, transparent);
}

.suite-badge {
  color: var(--color-purple-6);
  background: color-mix(in srgb, var(--color-purple-6) 14%, transparent);
}

.tree-method {
  flex-shrink: 0;
}

.node-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-count {
  flex-shrink: 0;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.node-path {
  flex-shrink: 0;
  margin-left: var(--ax-space-1);
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: var(--ax-space-3);
}

.footer-left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--ax-space-2);
  min-width: 0;
}

.picked-count {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.picked-hint {
  color: var(--ax-warning);
}

.import-as-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.import-as-label {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.footer-actions {
  display: flex;
  flex-shrink: 0;
  gap: var(--ax-space-2);
}

.tree-wrap :deep(.el-tree-node__content) {
  height: 32px;
}

.tree-wrap :deep(.el-tree-node__content:hover) {
  background: var(--ax-bg-hover);
}
</style>

<style>
.import-endpoint-dialog .el-dialog__body {
  padding-top: var(--ax-space-2);
}
</style>
