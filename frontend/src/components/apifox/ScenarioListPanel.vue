<template>
  <div class="list-panel">
    <div class="list-toolbar">
      <span>场景</span>
      <div class="toolbar-actions">
        <el-select
          v-model="priorityFilter"
          size="small"
          placeholder="优先级"
          clearable
          style="width: 84px"
        >
          <el-option
            v-for="p in PRIORITY_OPTIONS"
            :key="p.value"
            :label="p.label"
            :value="p.value"
          />
        </el-select>
        <el-button size="small" title="新建文件夹" @click="$emit('new-folder')">
          <el-icon><FolderAdd /></el-icon>
        </el-button>
        <el-button size="small" type="primary" title="新建场景" @click="$emit('new-scenario')">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
    </div>

    <div v-for="grp in groups" :key="grp.key" class="folder-group">
      <div class="folder-head" :class="{ ungrouped: !grp.folder }">
        <el-icon><component :is="grp.folder ? 'Folder' : 'Files'" /></el-icon>
        <span class="folder-name">{{ grp.folder ? grp.folder.name : '未分组' }}</span>
        <span class="folder-count">{{ grp.scenarios.length }}</span>
        <el-dropdown v-if="grp.folder" trigger="click" @command="(c) => onFolderCmd(c, grp.folder)">
          <el-icon class="folder-more" @click.stop><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">重命名</el-dropdown-item>
              <el-dropdown-item command="delete">删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div
        v-for="s in grp.scenarios"
        :key="s.id"
        class="item"
        :class="{ active: s.id === activeId }"
        @click="$emit('select', s.id)"
      >
        <el-icon><Share /></el-icon>
        <span class="item-name">{{ s.name }}</span>
        <el-tag size="small" :type="priorityMeta(s.priority).type">{{
          priorityMeta(s.priority).label
        }}</el-tag>
        <el-tag size="small" type="info">{{ s.step_count }} 步</el-tag>
        <el-dropdown trigger="click" @command="(fid) => onMoveCmd(fid, s)">
          <el-icon class="item-more" title="移动到文件夹" @click.stop><Rank /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="__none__" :disabled="s.folder_id == null"
                >移到未分组</el-dropdown-item
              >
              <el-dropdown-item
                v-for="f in folders"
                :key="f.id"
                :command="f.id"
                :disabled="f.id === s.folder_id"
              >
                移到「{{ f.name }}」
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button link type="danger" size="small" @click.stop="$emit('del', s)">删</el-button>
      </div>
    </div>

    <el-empty v-if="scenarios.length === 0" description="暂无场景" :image-size="60" />
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import {
  PRIORITY_OPTIONS,
  priorityMeta,
  useScenarioPriorityFilter,
} from '@/composables/useScenarioPriority'

const props = defineProps({
  scenarios: { type: Array, default: () => [] },
  folders: { type: Array, default: () => [] },
  activeId: { type: [Number, String], default: null },
})
const emit = defineEmits([
  'select',
  'del',
  'move',
  'new-scenario',
  'new-folder',
  'rename-folder',
  'delete-folder',
])

const { priorityFilter, visibleScenarios } = useScenarioPriorityFilter(toRef(props, 'scenarios'))

// 按 folder_id 分组：所有文件夹（含空）在前作为移动目标，未分组置底（无内容则隐藏）
const groups = computed(() => {
  const bucket = new Map(props.folders.map((f) => [f.id, []]))
  const ungrouped = []
  for (const s of visibleScenarios.value) {
    if (s.folder_id != null && bucket.has(s.folder_id)) bucket.get(s.folder_id).push(s)
    else ungrouped.push(s)
  }
  const result = props.folders.map((f) => ({
    key: `f${f.id}`,
    folder: f,
    scenarios: bucket.get(f.id),
  }))
  if (ungrouped.length || props.folders.length === 0) {
    result.push({ key: 'ungrouped', folder: null, scenarios: ungrouped })
  }
  return result
})

function onFolderCmd(cmd, folder) {
  emit(cmd === 'rename' ? 'rename-folder' : 'delete-folder', folder)
}

function onMoveCmd(cmd, scenario) {
  emit('move', { id: scenario.id, folderId: cmd === '__none__' ? null : cmd })
}
</script>

<style scoped>
.list-panel {
  width: 240px;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 8px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.folder-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  margin-top: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.folder-head.ungrouped {
  color: var(--ax-text-tertiary);
}

.folder-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-count {
  font-size: 11px;
  color: var(--ax-text-tertiary);
}

.folder-more {
  cursor: pointer;
  color: var(--ax-text-tertiary);
}

.item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px 6px 18px;
  border-radius: 4px;
  cursor: pointer;
}

.item:hover {
  background: var(--ax-bg-hover);
}

.item.active {
  background: var(--ax-bg-active);
}

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-more {
  cursor: pointer;
  color: var(--ax-text-tertiary);
}
</style>
