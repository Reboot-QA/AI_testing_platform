<template>
  <div
    class="projcard"
    :class="{ pinned: project.pinned }"
    :style="{ '--pc': color }"
    @click="emit('enter', project.id, 'requirements')"
  >
    <div class="head">
      <div class="avatar" aria-hidden="true">{{ initial }}</div>
      <div class="head-main">
        <div class="row">
          <el-tooltip
            :content="project.name"
            placement="top"
            :disabled="!nameOverflow"
            :show-after="300"
          >
            <div ref="pnRef" class="pn" @mouseenter="checkNameOverflow">
              <span class="pname">{{ project.name }}</span>
            </div>
          </el-tooltip>
          <span v-if="project.pinned" class="pin-badge">
            <el-tooltip content="已置顶" placement="top" :show-after="300">
              <span class="pin-icon" aria-label="已置顶">
                <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"
                  />
                </svg>
              </span>
            </el-tooltip>
          </span>
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
                <el-dropdown-item command="edit">编辑基本信息</el-dropdown-item>
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
      </div>
    </div>

    <p class="description" :title="project.description || undefined">
      {{ project.description || '暂无描述' }}
    </p>

    <div class="quick">
      <span class="role" :class="roleClass">{{ project.role }}</span>
      <div class="links">
        <a @click.stop="emit('enter', project.id, 'requirements')">需求</a>
        <a @click.stop="emit('enter', project.id, 'functional')">功能</a>
        <a @click.stop="emit('enter', project.id, 'automation')">自动化</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Schemas } from '@/api/types'
import type { WorkspaceDomain } from '@/types/shell'

type WorkbenchProject = Schemas['WorkbenchProject']

const props = defineProps<{ project: WorkbenchProject }>()
const emit = defineEmits<{
  enter: [id: number, domain?: WorkspaceDomain]
  rename: [project: WorkbenchProject]
  edit: [project: WorkbenchProject]
  delete: [project: WorkbenchProject]
  pin: [project: WorkbenchProject]
}>()

/** 用 token 色板派生，避免硬编码饱和 hex */
const PALETTE = [
  'var(--ax-brand)',
  'var(--color-blue-6)',
  'var(--color-geekblue-6)',
  'var(--color-purple-6)',
  'var(--color-pink-6)',
  'var(--color-orange-6)',
  'var(--color-green-6)',
]
const color = computed(() => PALETTE[props.project.id % PALETTE.length])
const initial = computed(() => {
  const name = props.project.name?.trim() || '?'
  return name.slice(0, 1).toUpperCase()
})
const roleClass = computed(
  () =>
    ({
      管理员: 'r-admin',
      负责人: 'r-owner',
    })[props.project.role] || 'r-member',
)

const canDelete = computed(() => ['管理员', '负责人'].includes(props.project.role))

const pnRef = ref<HTMLElement | null>(null)
const nameOverflow = ref(false)
function checkNameOverflow() {
  const el = pnRef.value?.querySelector('.pname') as HTMLElement | null
  nameOverflow.value = !!el && el.scrollWidth > el.clientWidth
}

function onCommand(cmd: 'pin' | 'rename' | 'edit' | 'delete') {
  if (cmd === 'pin') emit('pin', props.project)
  else if (cmd === 'rename') emit('rename', props.project)
  else if (cmd === 'edit') emit('edit', props.project)
  else emit('delete', props.project)
}
</script>

<style scoped>
.projcard {
  position: relative;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  padding: var(--ax-space-3) var(--ax-space-3-5);
  height: 132px;
  cursor: pointer;
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  transition:
    border-color var(--ax-transition),
    box-shadow var(--ax-transition),
    transform var(--ax-transition);
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.projcard:hover {
  border-color: color-mix(in srgb, var(--ax-brand) 28%, var(--ax-border));
  box-shadow: var(--ax-shadow);
  transform: translateY(-1px);
}

.projcard.pinned {
  border-color: color-mix(in srgb, var(--ax-brand) 22%, var(--ax-border));
  background: color-mix(in srgb, var(--ax-brand) 3%, var(--ax-bg));
}

.head {
  display: flex;
  align-items: flex-start;
  gap: var(--ax-space-2-5);
  min-width: 0;
}

.avatar {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: var(--ax-radius);
  display: grid;
  place-items: center;
  font-size: var(--ax-text-body-sm-size);
  font-weight: 700;
  color: var(--pc);
  background: color-mix(in srgb, var(--pc) 12%, white);
  letter-spacing: 0;
}

.head-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-0-5);
}

.row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  min-width: 0;
}

.pn {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  font-weight: 600;
  font-size: var(--ax-text-body-size);
  color: var(--ax-text);
}

.pname {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pin-badge {
  flex: none;
  line-height: 0;
}

.pin-icon {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  color: var(--ax-brand);
  transform: rotate(35deg);
  transform-origin: center 70%;
  cursor: default;
  opacity: 0.85;
}

.more {
  flex: none;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: var(--ax-radius-sm);
  color: var(--ax-text-placeholder);
  cursor: pointer;
  outline: none;
  opacity: 0;
  transition:
    opacity var(--ax-transition),
    background var(--ax-transition),
    color var(--ax-transition);
}

.projcard:hover .more,
.projcard:focus-within .more {
  opacity: 1;
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
  gap: var(--ax-space-1);
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-text-caption-line);
}

.pmeta .sep {
  color: var(--ax-text-placeholder);
}

.description {
  margin: 0;
  min-height: calc(var(--ax-text-caption-size) * var(--ax-text-caption-line));
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-text-caption-line);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.description:not([title]) {
  color: var(--ax-text-placeholder);
}

.quick {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  margin-top: auto;
  min-width: 0;
}

.role {
  flex: none;
  font-size: var(--ax-text-caption-size);
  font-weight: 500;
  padding: var(--ax-space-0-5) var(--ax-space-1-5);
  border-radius: var(--ax-radius-sm);
}

.r-admin {
  color: var(--ax-tag-blue-fg);
  background: var(--ax-tag-blue-bg);
}

.r-owner {
  color: var(--ax-tag-green-fg);
  background: var(--ax-tag-green-bg);
}

.r-member {
  color: var(--ax-text-secondary);
  background: var(--ax-bg-subtle);
}

.links {
  display: flex;
  gap: var(--ax-space-0-5);
  min-width: 0;
  opacity: 0.72;
  transition: opacity var(--ax-transition);
}

.projcard:hover .links {
  opacity: 1;
}

.links a {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
  cursor: pointer;
  padding: var(--ax-space-0-5) var(--ax-space-1);
  border-radius: var(--ax-radius-sm);
  transition:
    color var(--ax-transition),
    background var(--ax-transition);
}

.links a:hover {
  color: var(--ax-brand);
  background: var(--ax-brand-subtle);
  text-decoration: none;
}
</style>
