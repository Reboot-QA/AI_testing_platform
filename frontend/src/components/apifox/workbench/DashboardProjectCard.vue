<template>
  <div class="projcard" @click="$emit('enter', project.id)">
    <div class="row">
      <el-icon class="drag-handle" title="拖拽排序" @click.stop><Rank /></el-icon>
      <div class="pi" :style="{ background: color }">{{ letter }}</div>
      <div class="pn">{{ project.name }}</div>
      <span v-if="project.pinned" class="pin-flag" title="已置顶">置顶</span>
      <el-dropdown trigger="click" @command="onCommand">
        <span class="more" @click.stop>
          <el-icon><MoreFilled /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="pin">
              <el-icon><Top /></el-icon> {{ project.pinned ? '取消置顶' : '置顶' }}
            </el-dropdown-item>
            <el-dropdown-item command="rename"><el-icon><EditPen /></el-icon> 改名</el-dropdown-item>
            <el-dropdown-item v-if="canDelete" command="delete" divided>
              <span class="del"><el-icon><Delete /></el-icon> 删除项目</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <div class="pmeta">
      <span>🔗 {{ project.endpoint_count }} 接口</span>
      <span>◈ {{ project.scenario_count }} 场景</span>
    </div>
    <div>
      <span class="role" :class="roleClass">{{ project.role }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  project: { type: Object, required: true },
})
const emit = defineEmits(['enter', 'rename', 'delete', 'pin'])

// 从项目 id 稳定取色，避免依赖后端配色
const PALETTE = ['#2c5282', '#2b6cb0', '#2c7a7b', '#6b46c1', '#b83280', '#c05621', '#2f855a']
const color = computed(() => PALETTE[props.project.id % PALETTE.length])
const letter = computed(() => (props.project.name || '?').trim().charAt(0).toUpperCase())
const roleClass = computed(() => ({
  管理员: 'r-admin',
  负责人: 'r-owner',
}[props.project.role] || 'r-member'))

// 硬删除仅项目负责人/系统管理员可见（后端同样校验），成员只能改名
const canDelete = computed(() => ['管理员', '负责人'].includes(props.project.role))

function onCommand(cmd) {
  emit(cmd, props.project)
}
</script>

<style scoped>
.projcard {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  padding: 16px;
  cursor: pointer;
  background: var(--ax-bg);
  transition: all 0.15s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.projcard:hover {
  border-color: var(--ax-brand);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pi {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  flex: none;
}

.pn {
  flex: 1;
  font-weight: 600;
  font-size: 15px;
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drag-handle {
  flex: none;
  color: var(--ax-text-placeholder);
  cursor: grab;
}

.drag-handle:active {
  cursor: grabbing;
}

.pin-flag {
  flex: none;
  font-size: 11px;
  font-weight: 600;
  color: var(--ax-brand);
  background: var(--ax-brand-weak, rgba(64, 128, 255, 0.1));
  border-radius: 10px;
  padding: 1px 7px;
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
  gap: 12px;
  color: var(--ax-text-tertiary);
  font-size: 12.5px;
}

.role {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 20px;
}

.r-admin {
  color: var(--color-blue-6);
  background: var(--ax-brand-weak, rgba(64, 128, 255, 0.1));
}

.r-owner {
  color: var(--color-green-6);
  background: rgba(103, 194, 58, 0.12);
}

.r-member {
  color: var(--ax-text-secondary);
  background: var(--ax-bg-subtle);
}
</style>
