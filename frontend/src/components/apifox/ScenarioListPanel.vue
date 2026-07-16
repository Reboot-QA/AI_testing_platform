<template>
  <div class="w-60 border-r border-[var(--ax-border)] overflow-auto pr-2 shrink-0">
    <!-- 头部工具栏 -->
    <div class="flex items-center justify-between font-semibold text-[var(--ax-brand)] mb-2">
      <div class="flex items-center gap-1">
        <span>场景</span>
        <el-tooltip content="按住场景左侧手柄可拖动到其他分组" placement="right">
          <el-icon class="text-xs text-[var(--ax-text-placeholder)] cursor-default">
            <QuestionFilled />
          </el-icon>
        </el-tooltip>
      </div>
      <div class="flex items-center gap-1.5">
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

    <!-- 分组列表 -->
    <div v-for="grp in localGroups" :key="grp.key" class="mb-0.5">
      <!-- 文件夹 header -->
      <div
        class="flex items-center gap-1.5 px-1.5 py-[5px] mt-1.5 text-[12.5px] font-semibold"
        :class="grp.folder ? 'text-[var(--ax-text-secondary)]' : 'text-[var(--ax-text-tertiary)]'"
      >
        <el-icon><component :is="grp.folder ? 'Folder' : 'Files'" /></el-icon>
        <span class="flex-1 min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">
          {{ grp.folder ? grp.folder.name : '未分组' }}
        </span>
        <span class="text-[11px] text-[var(--ax-text-tertiary)]">{{ grp.scenarios.length }}</span>
        <el-dropdown v-if="grp.folder" trigger="click" @command="(c) => onFolderCmd(c, grp.folder)">
          <el-icon class="cursor-pointer text-[var(--ax-text-tertiary)]" @click.stop>
            <MoreFilled />
          </el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">重命名</el-dropdown-item>
              <el-dropdown-item command="delete">删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 场景行（可拖拽，跨分组移动） -->
      <VueDraggable
        v-model="grp.scenarios"
        :group="{ name: 'scenarios' }"
        handle=".drag-handle"
        :animation="150"
        class="min-h-[8px]"
        @add="(e) => onDrop(grp, e)"
      >
        <div
          v-for="s in grp.scenarios"
          :key="s.id"
          class="group flex items-center gap-2 pl-2 pr-1.5 py-1.5 rounded cursor-pointer"
          :class="s.id === activeId ? 'bg-[var(--ax-bg-active)]' : 'hover:bg-[var(--ax-bg-hover)]'"
          @click="$emit('select', s.id)"
        >
          <!-- 拖拽抓手（默认淡，hover 提亮） -->
          <el-icon
            class="drag-handle shrink-0 cursor-grab text-[var(--ax-text-placeholder)] opacity-40 group-hover:opacity-100 hover:!text-[var(--ax-brand)] transition"
            title="拖动到其他分组"
            @click.stop
          >
            <DCaret />
          </el-icon>

          <!-- 优先级：小圆点（颜色区分高/中/低） -->
          <span
            class="shrink-0 w-2 h-2 rounded-full"
            :style="{ background: `var(--el-color-${priorityMeta(s.priority).type})` }"
            :title="`优先级：${priorityMeta(s.priority).label}`"
          />

          <!-- 名称（截断 + tooltip 全称） -->
          <el-tooltip :content="s.name" placement="right" :show-after="600">
            <span class="flex-1 min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm">
              {{ s.name }}
            </span>
          </el-tooltip>

          <!-- 步数（纯文字） -->
          <span class="shrink-0 text-[11px] text-[var(--ax-text-placeholder)] tabular-nums">
            {{ s.step_count }} 步
          </span>

          <!-- 删除：常驻 icon，hover 变红 -->
          <el-icon
            class="shrink-0 cursor-pointer text-[var(--ax-text-placeholder)] hover:!text-[var(--el-color-danger)] transition-colors"
            title="删除场景"
            @click.stop="$emit('del', s)"
          >
            <Delete />
          </el-icon>
        </div>
      </VueDraggable>

      <!-- 空分组：提示可拖入 -->
      <div
        v-if="grp.scenarios.length === 0"
        class="pl-7 py-1 text-[11px] text-[var(--ax-text-placeholder)]"
      >
        拖动场景到此分组
      </div>
    </div>

    <el-empty v-if="scenarios.length === 0" description="暂无场景" :image-size="60" />
  </div>
</template>

<script setup>
import { computed, ref, toRef, watch } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
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

// 拖拽需要可变数组：从 groups 派生本地可变副本，props 变化时重建
const localGroups = ref([])
watch(
  groups,
  (g) => {
    localGroups.value = g.map((grp) => ({ ...grp, scenarios: [...grp.scenarios] }))
  },
  { immediate: true },
)

// 拖入某分组：仅当跨分组时持久化 folder_id（组内重排后端不支持排序，忽略）
function onDrop(grp, evt) {
  const moved = grp.scenarios[evt.newIndex]
  if (!moved) return
  const targetFolderId = grp.folder ? grp.folder.id : null
  if (moved.folder_id === targetFolderId) return
  emit('move', { id: moved.id, folderId: targetFolderId })
}

function onFolderCmd(cmd, folder) {
  emit(cmd === 'rename' ? 'rename-folder' : 'delete-folder', folder)
}
</script>
