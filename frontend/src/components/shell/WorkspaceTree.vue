<template>
  <div class="tree-panel">
    <!-- <div class="tools">
      <el-input
        v-model="keyword"
        clearable
        :placeholder="searchPlaceholder"
        class="search"
      >
        <template #prefix
          ><el-icon><Search /></el-icon
        ></template>
      </el-input>
    </div> -->

    <div class="tree-scroll">
      <template v-for="grp in groups" :key="grp.title || 'root'">
        <button
          v-if="grp.title"
          type="button"
          class="tnode tnode--group"
          @click="toggleGroup(grp.title)"
        >
          <el-icon v-if="grp.icon" class="tn-ic"><component :is="grp.icon" /></el-icon>
          <span class="tn-label">{{ grp.title }}</span>
          <el-icon class="tn-arrow">
            <ArrowDown v-if="isGroupExpanded(grp.title)" />
            <ArrowRight v-else />
          </el-icon>
        </button>
        <div
          v-show="!grp.title || isGroupExpanded(grp.title)"
          class="grp-items"
          :class="{ 'grp-items--nested': !!grp.title }"
        >
          <div
            v-for="leaf in grp.items"
            :key="leaf.key"
            class="tnode"
            :class="{ active: isActive(leaf) }"
            @click="onLeaf(leaf)"
          >
            <el-icon class="tn-ic"><component :is="leaf.icon" /></el-icon>
            <span class="tn-label">{{ leaf.label }}</span>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AutomationBiz, WorkspaceDomain } from '@/types/shell'

interface Leaf {
  key: string
  label: string
  icon: string
  biz?: AutomationBiz
  section: string
}
interface Group {
  title?: string
  icon?: string
  items: Leaf[]
}

const props = defineProps<{
  domain: WorkspaceDomain
  biz: AutomationBiz
  section: string
  projectId: string
}>()

const emit = defineEmits<{
  navAuto: [payload: { biz: AutomationBiz; section: string }]
  navSection: [section: string]
}>()

const keyword = ref('')

const AUTOMATION: Group[] = [
  {
    items: [
      {
        key: 'overview',
        label: '自动化概览',
        icon: 'HomeFilled',
        biz: 'autotest',
        section: 'overview',
      },
    ],
  },
  {
    title: '接口管理',
    icon: 'FolderOpened',
    items: [
      { key: 'apis', label: '接口目录', icon: 'Connection', biz: 'apis', section: 'apis' },
      {
        key: 'datamodels',
        label: '数据模型',
        icon: 'Grid',
        biz: 'autotest',
        section: 'datamodels',
      },
    ],
  },
  {
    title: '自动化测试',
    icon: 'Cpu',
    items: [
      { key: 'cases', label: '接口用例', icon: 'Files', biz: 'autotest', section: 'cases' },
      {
        key: 'scenarios',
        label: '测试场景',
        icon: 'Share',
        biz: 'autotest',
        section: 'scenarios',
      },
      {
        key: 'suites',
        label: '测试套件',
        icon: 'Collection',
        biz: 'autotest',
        section: 'suites',
      },
      {
        key: 'schedules',
        label: '定时任务',
        icon: 'Clock',
        biz: 'autotest',
        section: 'schedules',
      },
    ],
  },
  {
    title: '报告 / AI',
    icon: 'DataAnalysis',
    items: [
      { key: 'reports', label: '测试报告', icon: 'Histogram', biz: 'reports', section: 'reports' },
      { key: 'ai', label: 'AI 任务中心', icon: 'MagicStick', biz: 'ai', section: 'ai' },
    ],
  },
  {
    items: [{ key: 'trash', label: '回收站', icon: 'Delete', biz: 'autotest', section: 'trash' }],
  },
]

const REQUIREMENTS: Group[] = [
  {
    items: [
      { key: 'req-overview', label: '需求概览', icon: 'HomeFilled', section: 'req-overview' },
    ],
  },
  {
    title: '需求资产',
    icon: 'Folder',
    items: [
      { key: 'req-docs', label: 'AI 分析需求', icon: 'MagicStick', section: 'req-docs' },
      { key: 'req-points', label: '需求点', icon: 'Document', section: 'req-points' },
    ],
  },
]

const FUNCTIONAL: Group[] = [
  {
    items: [
      { key: 'func-overview', label: '功能测试概览', icon: 'HomeFilled', section: 'func-overview' },
    ],
  },
  {
    title: '功能用例资产',
    icon: 'Briefcase',
    items: [
      { key: 'func-ai', label: 'AI 生成功能用例', icon: 'MagicStick', section: 'ai' },
      { key: 'func-cases', label: '功能用例库', icon: 'Files', section: 'func-cases' },
      { key: 'func-runs', label: '手工执行', icon: 'VideoPlay', section: 'func-runs' },
    ],
  },
]

const rawGroups = computed<Group[]>(() => {
  if (props.domain === 'requirements') return REQUIREMENTS
  if (props.domain === 'functional') return FUNCTIONAL
  return AUTOMATION
})

const groups = computed<Group[]>(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return rawGroups.value
  return rawGroups.value
    .map((g) => ({
      title: g.title,
      icon: g.icon,
      items: g.items.filter((l) => l.label.toLowerCase().includes(kw)),
    }))
    .filter((g) => g.items.length)
})

const expandedGroups = ref<Set<string>>(new Set())

function collectGroupTitles(domain: WorkspaceDomain): string[] {
  const source =
    domain === 'requirements' ? REQUIREMENTS : domain === 'functional' ? FUNCTIONAL : AUTOMATION
  return source.filter((g) => g.title).map((g) => g.title!)
}

watch(
  () => props.domain,
  (domain) => {
    expandedGroups.value = new Set(collectGroupTitles(domain))
  },
  { immediate: true },
)

function isGroupExpanded(title: string): boolean {
  return expandedGroups.value.has(title)
}

function toggleGroup(title: string): void {
  const next = new Set(expandedGroups.value)
  if (next.has(title)) {
    next.delete(title)
  } else {
    next.add(title)
  }
  expandedGroups.value = next
}

const searchPlaceholder = computed(() => {
  if (props.domain === 'requirements') return '搜索需求'
  if (props.domain === 'functional') return '搜索功能用例'
  return '搜索接口 / 用例 / 场景'
})

function isActive(leaf: Leaf): boolean {
  if (props.domain === 'automation') return leaf.biz === props.biz && leaf.section === props.section
  return leaf.section === props.section
}

function onLeaf(leaf: Leaf) {
  if (props.domain === 'automation' && leaf.biz) {
    emit('navAuto', { biz: leaf.biz, section: leaf.section })
  } else {
    emit('navSection', leaf.section)
  }
}
</script>

<style scoped>
.tree-panel {
  width: var(--ax-workspace-nav-width);
  min-width: var(--ax-workspace-nav-width);
  flex: none;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: var(--ax-bg);
  border-right: 1px solid var(--ax-border);
}

.tools {
  flex: none;
  padding: var(--ax-space-2) var(--ax-space-2-5) 0;
}

.search {
  width: 100%;
}

.tree-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--ax-space-1) var(--ax-space-2) var(--ax-space-3);
}

.grp-items {
  display: flex;
  flex-direction: column;
}

.grp-items--nested {
  padding-left: var(--ax-space-5);
}

.tnode {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  height: var(--ax-nav-item-height);
  min-width: 0;
  padding: var(--ax-space-0) var(--ax-space-2);
  overflow: hidden;
  border-radius: var(--ax-radius-sm);
  cursor: pointer;
  color: var(--ax-text-tertiary);
  transition:
    background var(--ax-transition),
    color var(--ax-transition);
}

.tnode--group {
  width: 100%;
  margin: 0;
  border: 0;
  background: transparent;
  text-align: left;
  font: inherit;
}

.tnode:hover {
  background: var(--ax-bg-subtle);
  color: var(--ax-text);
}

.tnode.active {
  background: var(--ax-tag-blue-bg);
  color: var(--ax-rail-active-bg);
  font-weight: 600;
}

.tn-ic {
  flex: none;
  font-size: 14px;
}

.tn-arrow {
  flex: none;
  font-size: 12px;
  color: var(--ax-text-placeholder);
}

.tn-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-nav-secondary-size);
  line-height: var(--ax-nav-secondary-line);
}

.tn-count {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-placeholder);
}
</style>
