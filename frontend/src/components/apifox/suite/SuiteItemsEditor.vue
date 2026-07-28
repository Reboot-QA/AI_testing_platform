<template>
  <div class="suite-items">
    <div class="items-head">
      <span class="items-title">套件项（按接口分组 · 组内拖拽调整顺序）</span>
      <span class="items-total">共 {{ items.length }} 项</span>
      <el-tooltip
        v-if="orderPending"
        content="该套件里用例与场景是交错保存的，上面按接口分组后顺序有变化；下次保存会按当前展示顺序写回。"
        placement="top"
      >
        <span class="order-hint">
          <el-icon><WarningFilled /></el-icon>
          展示顺序与已保存顺序不同
        </span>
      </el-tooltip>
      <el-button type="primary" size="small" plain class="push-right" @click="openPickCase">
        <el-icon><Plus /></el-icon>
        添加接口用例
      </el-button>
      <el-button type="primary" size="small" plain @click="openPickScenario">
        <el-icon><Plus /></el-icon>
        添加测试场景
      </el-button>
    </div>

    <div class="items-body">
      <SuiteItemGroup
        v-for="g in groups"
        :key="g.key"
        :group="g"
        :start-index="startIndexOf(g.key)"
        @sort="(sorted) => onGroupSort(g.key, sorted)"
        @remove="onRemove"
      />
      <el-empty
        v-if="items.length === 0"
        description="点击上方「添加接口用例」或「添加测试场景」"
        :image-size="50"
      />
    </div>

    <ImportEndpointTreeDialog ref="pickerRef" :project-id="projectId" @confirm="onPick" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, WarningFilled } from '@element-plus/icons-vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { ImportConfirmPayload } from '@/composables/useImportCaseTree'
import type { SuiteEditorItem } from '@/types/apifox'
import {
  buildSuiteItemGroups,
  flattenSuiteItemGroups,
  sameOrder,
} from '@/composables/useSuiteItemGroups'
import ImportEndpointTreeDialog from '@/components/apifox/import-export/ImportEndpointTreeDialog.vue'
import SuiteItemGroup from '@/components/apifox/suite/SuiteItemGroup.vue'

const props = withDefaults(
  defineProps<{ projectId: Id; cases?: Schemas['ProjectCaseBrief'][] }>(),
  { cases: () => [] },
)

const items = defineModel<SuiteEditorItem[]>({ required: true })

const pickerRef = ref<InstanceType<typeof ImportEndpointTreeDialog> | null>(null)

const groups = computed(() => buildSuiteItemGroups(items.value, props.cases))

/** 组内首项在整体执行序列中的下标，用于行号连续 */
function startIndexOf(key: string): number {
  let n = 0
  for (const g of groups.value) {
    if (g.key === key) break
    n += g.items.length
  }
  return n
}

/**
 * 存量套件的用例/场景可能是交错排列的，分组视图会把它们聚到一起——
 * 于是「看到的顺序」和「服务端将执行的顺序」不一致。
 * 这里只做提示、**不自动写回**：打开套件不该凭空变成未保存态。
 * 真正的规范化发生在用户主动改动时（添加/拖拽），那时转脏是合理的。
 */
const orderPending = computed(() => !sameOrder(flattenSuiteItemGroups(groups.value), items.value))

function onGroupSort(key: string, sorted: SuiteEditorItem[]) {
  items.value = groups.value.flatMap((g) => (g.key === key ? sorted : g.items))
}

function onRemove(item: SuiteEditorItem) {
  items.value = items.value.filter((it) => it !== item)
}

function openPickCase() {
  pickerRef.value?.open('pick-suite-case')
}

function openPickScenario() {
  pickerRef.value?.open('pick-suite-scenario')
}

let uid = 0
const nextUid = (): string => `si-add-${uid++}`

/** 批量回填：按 target_type+target_id 去重，重复项跳过并提示 */
function onPick(payload: ImportConfirmPayload) {
  if (payload.mode !== 'pick-suite-item') return

  const seen = new Set(items.value.map((it) => `${it.target_type}:${it.target_id}`))
  const added: SuiteEditorItem[] = []
  let skipped = 0

  const push = (item: SuiteEditorItem) => {
    const key = `${item.target_type}:${item.target_id}`
    if (seen.has(key)) {
      skipped++
      return
    }
    seen.add(key)
    added.push(item)
  }

  for (const c of payload.cases) {
    push({
      _uid: nextUid(),
      target_type: 'case',
      target_id: c.id,
      target_name: c.name,
      endpoint_method: c.endpoint_method,
      endpoint_path: c.endpoint_path,
      enabled: true,
    })
  }
  for (const s of payload.scenarios) {
    push({
      _uid: nextUid(),
      target_type: 'scenario',
      target_id: s.id,
      target_name: s.name,
      endpoint_method: '',
      endpoint_path: '',
      enabled: true,
    })
  }

  // 新项先追加到末尾，再按分组规范化（同接口的新用例会归入已有分组）
  if (added.length) {
    items.value = flattenSuiteItemGroups(
      buildSuiteItemGroups([...items.value, ...added], props.cases),
    )
  }

  if (added.length && skipped) {
    ElMessage.success(`已添加 ${added.length} 项，跳过 ${skipped} 项重复`)
  } else if (added.length) {
    ElMessage.success(`已添加 ${added.length} 项`)
  } else {
    ElMessage.info(`所选 ${skipped} 项已在套件中`)
  }
}
</script>

<style scoped>
.suite-items {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.items-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.items-title {
  font-size: var(--ax-font);
  font-weight: 600;
  line-height: var(--ax-leading-compact);
  color: var(--ax-brand);
}

.items-total {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
  font-variant-numeric: tabular-nums;
}

.order-hint {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1);
  font-size: var(--ax-font-xs);
  color: var(--ax-warning);
  cursor: help;
}

/* 按钮组始终靠右，无论中间的提示是否出现 */
.items-head .push-right {
  margin-left: auto;
}

/* 套件项多时不再把下方运行进度顶走：本区独立滚动 */
.items-body {
  min-height: 96px;
  max-height: 44vh;
  overflow-y: auto;
  padding-right: var(--ax-space-1);
}

.items-body :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}
</style>
