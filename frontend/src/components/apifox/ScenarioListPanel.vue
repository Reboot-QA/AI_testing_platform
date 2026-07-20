<template>
  <div class="w-60 border-r border-[var(--ax-border)] overflow-auto pr-2 shrink-0">
    <!-- 头部工具栏 -->
    <div class="panel-head">
      <span class="panel-title">场景</span>
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
      <div class="group-head" :class="grp.folder ? 'group-head--folder' : 'group-head--ungrouped'">
        <el-icon class="group-head-icon"
          ><component :is="grp.folder ? 'Folder' : 'Files'"
        /></el-icon>
        <span class="group-head-name">
          {{ grp.folder ? grp.folder.name : '未分组' }}
        </span>
        <span class="group-head-count">{{ grp.scenarios.length }}</span>
        <el-dropdown
          v-if="grp.folder"
          trigger="click"
          @command="(c: 'rename' | 'delete') => onFolderCmd(c, grp.folder!)"
        >
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
        :key="`drag-${grp.key}`"
        v-model="grp.scenarios"
        :data-gkey="grp.key"
        :group="{ name: 'scenarios', pull: true, put: true }"
        handle=".drag-handle"
        :animation="150"
        ghost-class="scenario-ghost"
        :class="grp.scenarios.length === 0 ? 'scenario-drop-empty' : 'scenario-drop'"
        @end="onDragEnd"
      >
        <div
          v-for="s in grp.scenarios"
          :key="s.id"
          :data-scenario-id="s.id"
          class="scenario-row group"
          :class="s.id === activeId ? 'scenario-row--active' : ''"
          @click="$emit('select', s.id)"
        >
          <!-- 拖拽手柄：按住可拖到其他分组 -->
          <span class="drag-handle" title="按住拖动到其他分组" @click.stop>
            <el-icon><Rank /></el-icon>
          </span>

          <!-- 名称（截断 + tooltip 全称） -->
          <el-tooltip :content="s.name" placement="right" :show-after="600">
            <span class="scenario-name">{{ s.name }}</span>
          </el-tooltip>

          <!-- 步数 -->
          <span class="scenario-meta">{{ s.step_count }} 步</span>

          <!-- 优先级：文字 + 语义色（高=红 / 中=橙 / 低=灰） -->
          <el-tooltip
            :content="`优先级：${priorityMeta(s.priority).label}`"
            placement="right"
            :show-after="300"
          >
            <span
              class="priority-label shrink-0"
              :style="{ color: `var(--el-color-${priorityMeta(s.priority).type})` }"
            >
              {{ priorityMeta(s.priority).label }}
            </span>
          </el-tooltip>

          <!-- 删除：常驻 icon，hover 变红 -->
          <el-icon class="scenario-del" title="删除场景" @click.stop="$emit('del', s)">
            <Delete />
          </el-icon>
        </div>
      </VueDraggable>

      <div v-if="grp.scenarios.length === 0" class="empty-hint">拖动场景到此分组</div>
    </div>

    <el-empty v-if="scenarios.length === 0" description="暂无场景" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import type { Schemas } from '@/api/types'
import {
  PRIORITY_OPTIONS,
  priorityMeta,
  useScenarioPriorityFilter,
} from '@/composables/useScenarioPriority'

type ScenarioBrief = Schemas['ScenarioBrief']
type ScenarioFolderOut = Schemas['ScenarioFolderOut']

interface ScenarioGroup {
  key: string
  folder: ScenarioFolderOut | null
  scenarios: ScenarioBrief[]
}

const props = withDefaults(
  defineProps<{
    scenarios?: ScenarioBrief[]
    folders?: ScenarioFolderOut[]
    activeId?: number | string | null
  }>(),
  {
    scenarios: () => [],
    folders: () => [],
    activeId: null,
  },
)
const emit = defineEmits<{
  select: [id: number]
  del: [scenario: ScenarioBrief]
  reorder: [items: Schemas['ScenarioReorderRequest']['items']]
  'new-scenario': []
  'new-folder': []
  'rename-folder': [folder: ScenarioFolderOut]
  'delete-folder': [folder: ScenarioFolderOut]
}>()

const { priorityFilter, visibleScenarios } = useScenarioPriorityFilter(toRef(props, 'scenarios'))

// 按 folder_id 分组：所有文件夹（含空）在前，未分组始终置底作为拖放目标
const groups = computed((): ScenarioGroup[] => {
  const bucket = new Map<number, ScenarioBrief[]>(
    props.folders.map((f) => [f.id, [] as ScenarioBrief[]]),
  )
  const ungrouped: ScenarioBrief[] = []
  for (const s of visibleScenarios.value) {
    const list = s.folder_id != null ? bucket.get(s.folder_id) : undefined
    if (list) list.push(s)
    else ungrouped.push(s)
  }
  const result: ScenarioGroup[] = props.folders.map((f) => ({
    key: `f${f.id}`,
    folder: f,
    scenarios: bucket.get(f.id) ?? [],
  }))
  // 始终保留「未分组」作为跨组拖放目标（即使当前为空）
  result.push({ key: 'ungrouped', folder: null, scenarios: ungrouped })
  return result
})

// 拖拽需要可变数组：从 groups 派生本地可变副本，props 变化时重建
const localGroups = ref<ScenarioGroup[]>([])
watch(
  groups,
  (g) => {
    localGroups.value = g.map((grp) => ({ ...grp, scenarios: [...grp.scenarios] }))
  },
  { immediate: true },
)

// 拖放结束：快照重编号受影响的组（组内=源=目标 1 组；跨组=源+目标 2 组），交后端批量落库
interface ScenarioDragEndEvent {
  from?: HTMLElement & { dataset?: { gkey?: string } }
  to?: HTMLElement & { dataset?: { gkey?: string } }
}

// 组内 index 即 sort_order（组内相对序，前端按 folder 分组，跨组重叠无妨）
function groupSnapshot(grp: ScenarioGroup): Schemas['ScenarioReorderRequest']['items'] {
  return grp.scenarios.map((s, i) => ({
    id: s.id,
    folder_id: grp.folder ? grp.folder.id : null,
    sort_order: i,
  }))
}

function onDragEnd(evt: ScenarioDragEndEvent) {
  const fromKey = evt.from?.dataset?.gkey
  const toKey = evt.to?.dataset?.gkey
  // 能识别到源/目标组就只发这两组；否则全量兜底（仍正确，只是多发几条）
  const affected =
    fromKey && toKey
      ? localGroups.value.filter((g) => g.key === fromKey || g.key === toKey)
      : localGroups.value
  const items = affected.flatMap(groupSnapshot)
  if (items.length) emit('reorder', items)
}

function onFolderCmd(cmd: 'rename' | 'delete', folder: ScenarioFolderOut) {
  if (cmd === 'rename') emit('rename-folder', folder)
  else emit('delete-folder', folder)
}
</script>

<style scoped>
/* 字号阶梯：面板标题 14 > 分组标题 12 > 场景名 12 > 元信息 11 */
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.panel-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: 1.25;
  color: var(--ax-brand);
}

.group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  margin-top: 6px;
  font-size: var(--ax-font-xs);
  font-weight: 600;
  line-height: 1.25;
}

.group-head--folder {
  color: var(--ax-text-secondary);
}

.group-head--ungrouped {
  color: var(--ax-text-tertiary);
}

.group-head-icon {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
}

.group-head-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-head-count {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  font-weight: 400;
  color: var(--ax-text-tertiary);
}

.scenario-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.scenario-row:hover {
  background: var(--ax-bg-hover);
}

.scenario-row--active {
  background: var(--ax-bg-active);
}

.scenario-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
  font-weight: 400;
  line-height: 1.35;
  color: var(--ax-text);
}

.scenario-meta {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: 1;
  color: var(--ax-text-placeholder);
  font-variant-numeric: tabular-nums;
}

.drag-handle {
  display: inline-flex;
  align-items: center;
  cursor: grab;
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-sm);
  opacity: 0.4;
  transition:
    opacity 0.15s,
    color 0.15s;
}

.group:hover .drag-handle {
  opacity: 1;
}

.drag-handle:hover {
  color: var(--ax-brand);
}

.drag-handle:active {
  cursor: grabbing;
}

.priority-label {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: 1;
}

.scenario-del {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  cursor: pointer;
  color: var(--ax-text-placeholder);
  transition: color 0.15s;
}

.scenario-del:hover {
  color: var(--el-color-danger);
}

.empty-hint {
  pointer-events: none;
  padding: 2px 0 2px 28px;
  font-size: var(--ax-font-xs);
  line-height: 1.35;
  color: var(--ax-text-placeholder);
}

.scenario-drop {
  min-height: 8px;
}

.scenario-drop-empty {
  min-height: 28px;
}

:global(.scenario-ghost) {
  opacity: 0.45;
  background: var(--ax-bg-hover);
  border-radius: 4px;
}
</style>
