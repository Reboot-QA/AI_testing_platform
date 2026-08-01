<template>
  <div class="ipt">
    <div class="ipt-head">
      <h4 class="ipt-title">预览 &amp; 勾选</h4>
      <span class="ipt-count">已选 {{ selected.length }} / {{ total }}</span>
    </div>

    <el-input
      v-model="filterText"
      :maxlength="SEARCH_MAX_LEN"
      size="small"
      clearable
      placeholder="搜索接口名 / 路径 / 方法"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <div class="ipt-tree">
      <el-tree
        ref="treeRef"
        :data="nodes"
        node-key="key"
        show-checkbox
        :default-expanded-keys="[ROOT_KEY, GROUP_KEY]"
        :expand-on-click-node="false"
        :filter-node-method="filterPreviewNode"
        @check="syncChecked"
      >
        <template #default="{ data }">
          <span class="ipt-node">
            <el-icon v-if="data.type === 'root'" class="ipt-icon ipt-icon--root"><Box /></el-icon>
            <el-icon v-else-if="data.type === 'group'" class="ipt-icon ipt-icon--root">
              <Files />
            </el-icon>
            <el-icon v-else-if="data.type === 'folder'" class="ipt-icon"><Folder /></el-icon>
            <MethodTag v-else :method="data.method" class="ipt-method" />
            <span class="ipt-label">{{ data.label }}</span>
            <span v-if="data.type !== 'endpoint'" class="ipt-num">({{ data.count ?? 0 }})</span>
            <span v-if="data.path" class="ipt-path">{{ data.path }}</span>
            <span v-if="data.changed" class="ipt-badge ipt-badge--changed">有变更</span>
            <span v-else-if="data.exists" class="ipt-badge">已存在</span>
          </span>
        </template>
      </el-tree>
      <el-empty v-if="!total" description="文档里没有可导入的接口" :image-size="48" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { nextTick, ref, watch } from 'vue'
import { Box, Files, Folder, Search } from '@element-plus/icons-vue'
import type { ImportPreviewNode } from '@/types/apifox'
import {
  GROUP_KEY,
  ROOT_KEY,
  collectEndpointKeys,
  filterPreviewNode,
  pickCheckedEndpointKeys,
} from '@/utils/importPreviewTree'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const props = defineProps<{ nodes: ImportPreviewNode[] }>()
const emit = defineEmits<{ 'update:selected': [keys: string[]] }>()

interface TreeExpose {
  filter: (value: string) => void
  getCheckedKeys: (leafOnly?: boolean) => (string | number)[]
  setCheckedKeys: (keys: string[]) => void
}

const treeRef = ref<TreeExpose | null>(null)
const filterText = ref('')
const selected = ref<string[]>([])
const total = ref(0)

function syncChecked() {
  const checked = new Set((treeRef.value?.getCheckedKeys(false) ?? []).map(String))
  selected.value = pickCheckedEndpointKeys(props.nodes, checked)
  emit('update:selected', selected.value)
}

/** 新预览到达：默认全选（用户再自行取消不需要的） */
watch(
  () => props.nodes,
  async (nodes) => {
    const keys = collectEndpointKeys(nodes)
    total.value = keys.length
    await nextTick()
    treeRef.value?.setCheckedKeys(keys)
    syncChecked()
    if (filterText.value) treeRef.value?.filter(filterText.value)
  },
  { immediate: true },
)

watch(filterText, (v) => treeRef.value?.filter(v))
</script>

<style scoped>
.ipt {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
  min-width: 0;
}

.ipt-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--ax-space-2);
}

.ipt-title {
  margin: 0;
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text);
}

.ipt-count {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
}

.ipt-tree {
  flex: 1;
  min-height: 300px;
  max-height: 420px;
  overflow: auto;
  padding: var(--ax-space-2);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
}

.ipt-node {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  min-width: 0;
  font-size: var(--ax-font-sm);
  line-height: var(--ax-leading-compact);
}

.ipt-icon {
  flex-shrink: 0;
  font-size: 15px;
  color: var(--ax-tag-orange-fg);
}

.ipt-icon--root {
  color: var(--color-purple-6);
}

.ipt-method {
  flex-shrink: 0;
}

.ipt-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ipt-num,
.ipt-path {
  flex-shrink: 0;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.ipt-badge {
  flex-shrink: 0;
  padding: 0 var(--ax-space-1);
  border-radius: 3px;
  font-size: 10px;
  color: var(--ax-text-secondary);
  background: var(--ax-bg-subtle);
}

.ipt-badge--changed {
  color: var(--ax-tag-orange-fg);
  background: color-mix(in srgb, var(--ax-tag-orange-fg) 14%, transparent);
}

.ipt-tree :deep(.el-tree-node__content) {
  height: 32px;
}

.ipt-tree :deep(.el-tree-node__content:hover) {
  background: var(--ax-bg-hover);
}
</style>
