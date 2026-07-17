<template>
  <div class="projcard" :style="{ '--pc': color }" @click="$emit('enter', project.id)">
    <div class="row">
      <el-tooltip
        :content="project.name"
        placement="top"
        :disabled="!nameOverflow"
        :show-after="300"
      >
        <div ref="pnRef" class="pn" @mouseenter="checkNameOverflow">{{ project.name }}</div>
      </el-tooltip>
      <span v-if="project.pinned" class="pin-flag">置顶</span>
      <el-dropdown trigger="click" @command="onCommand">
        <span class="more" @click.stop>
          <el-icon><MoreFilled /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="pin">
              {{ project.pinned ? '取消置顶' : '置顶' }}
            </el-dropdown-item>
            <el-dropdown-item command="rename">改名</el-dropdown-item>
            <el-dropdown-item v-if="canDelete" command="delete" divided>
              <span class="del">删除项目</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div class="pmeta">
      <span>{{ project.endpoint_count }} 接口</span>
      <span class="sep">·</span>
      <span>{{ project.scenario_count }} 场景</span>
    </div>

    <div>
      <span class="role" :class="roleClass">{{ project.role }}</span>
    </div>

    <el-icon class="drag-handle" title="拖拽排序" @click.stop><Rank /></el-icon>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Schemas } from '@/api/types'

type WorkbenchProject = Schemas['WorkbenchProject']

const props = defineProps<{ project: WorkbenchProject }>()
const emit = defineEmits<{
  enter: [id: number]
  rename: [project: WorkbenchProject]
  delete: [project: WorkbenchProject]
  pin: [project: WorkbenchProject]
}>()

// 从项目 id 稳定取色，作为卡片左侧标签色条（替代原头像图标）
const PALETTE = ['#2c5282', '#2b6cb0', '#2c7a7b', '#6b46c1', '#b83280', '#c05621', '#2f855a']
const color = computed(() => PALETTE[props.project.id % PALETTE.length])
const roleClass = computed(
  () =>
    ({
      管理员: 'r-admin',
      负责人: 'r-owner',
    })[props.project.role] || 'r-member',
)

// 硬删除仅项目负责人/系统管理员可见（后端同样校验），成员只能改名
const canDelete = computed(() => ['管理员', '负责人'].includes(props.project.role))

// 标题溢出时才启用 tooltip：进入前实测宽度，避免未截断也弹提示
const pnRef = ref<HTMLElement | null>(null)
const nameOverflow = ref(false)
function checkNameOverflow() {
  const el = pnRef.value
  nameOverflow.value = !!el && el.scrollWidth > el.clientWidth
}

function onCommand(cmd: 'pin' | 'rename' | 'delete') {
  emit(cmd, props.project)
}
</script>

<style scoped>
/* 标签式卡片：左侧项目色条替代头像图标，整体扁平、克制 */
.projcard {
  position: relative;
  border: 1px solid var(--ax-border);
  border-left: 3px solid var(--pc);
  border-radius: var(--ax-radius-lg);
  padding: 14px 16px;
  min-height: 116px;
  cursor: pointer;
  background: var(--ax-bg);
  transition:
    border-color var(--ax-transition),
    box-shadow var(--ax-transition);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.projcard:hover {
  border-color: color-mix(in srgb, var(--ax-brand) 35%, var(--ax-border));
  border-left-color: var(--pc);
  box-shadow: var(--ax-shadow);
}

.row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pn {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  font-size: 15px;
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pin-flag {
  flex: none;
  font-size: 11px;
  font-weight: 600;
  color: var(--ax-text-secondary);
  background: var(--ax-bg-hover);
  border-radius: 10px;
  padding: 1px 8px;
}

.more {
  flex: none;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  color: var(--ax-text-tertiary);
  cursor: pointer;
  outline: none;
}

.more:hover {
  background: var(--ax-bg-subtle);
  color: var(--ax-text);
}

.del {
  color: var(--ax-danger);
}

.pmeta {
  display: flex;
  gap: 8px;
  color: var(--ax-text-tertiary);
  font-size: 12.5px;
}

.pmeta .sep {
  color: var(--ax-text-placeholder);
}

.role {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 20px;
}

.r-admin {
  color: var(--color-blue-6);
  background: color-mix(in srgb, var(--color-blue-6) 12%, transparent);
}

.r-owner {
  color: var(--color-green-6);
  background: color-mix(in srgb, var(--color-green-6) 12%, transparent);
}

.r-member {
  color: var(--ax-text-secondary);
  background: var(--ax-bg-subtle);
}

/* 拖拽手柄常显于卡片右下角，不挤占标题宽度 */
.drag-handle {
  position: absolute;
  right: 12px;
  bottom: 14px;
  color: var(--ax-text-placeholder);
  cursor: grab;
  transition: color var(--ax-transition);
}

.drag-handle:hover {
  color: var(--ax-text-secondary);
}

.drag-handle:active {
  cursor: grabbing;
}
</style>
