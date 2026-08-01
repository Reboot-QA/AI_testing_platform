<template>
  <div class="space-y-3">
    <AiGenTaskOverview
      :controller="controller"
      @update:record-view="(view) => (controller.recordView.value = view)"
    />

    <!-- 批量入库（多接口）；任务中心仅保留各接口内用例级入库，不展示接口级批量条 -->
    <div
      v-if="
        applicableItems.length && effectiveView !== 'done' && !compact && !hideMultiEndpointBatch
      "
      class="mb-2 flex items-center justify-between gap-2 rounded border border-border bg-muted px-3 py-2"
    >
      <el-checkbox :model-value="allEpSel" :indeterminate="someEpSel" @change="toggleAllEp">
        全选接口（{{ epCheckedCount }}/{{ applicableItems.length }}）
      </el-checkbox>
      <el-button
        type="primary"
        size="small"
        :loading="batchApplying"
        :disabled="!epCheckedCount"
        @click="batchApply"
      >
        批量入库（{{ epCheckedCount }} 接口）
      </el-button>
    </div>

    <el-empty
      v-if="controller.showRecordTabs.value && controller.task.value && !items.length"
      class="record-empty"
      :description="recordEmptyText"
      :image-size="56"
    />

    <el-collapse v-if="items.length" v-model="expanded">
      <el-collapse-item v-for="it in pagedItems" :key="it.id" :name="it.id">
        <template #title>
          <template v-if="!compact">
            <el-checkbox
              v-if="canSelectEp(it) && !hideMultiEndpointBatch"
              :model-value="!!epChecked[it.id]"
              class="mr-2"
              @click.stop
              @change="(v: boolean) => (epChecked[it.id] = v)"
            />
            <MethodTag :method="it.endpoint_method" />
            <span class="mx-2 max-w-80 truncate text-base">{{ it.endpoint_name }}</span>
            <el-tag size="small" :type="statusType(it.status)" class="ml-auto">{{
              statusText(it)
            }}</el-tag>
          </template>
          <span v-else class="mx-2 max-w-80 truncate text-base font-semibold text-muted-foreground"
            >生成结果</span
          >
        </template>

        <div v-if="isItemExpanded(it.id) && casesBlockVisible(it)">
          <p
            v-if="it.status === 'running'"
            class="mb-2 flex items-center gap-1 text-sm text-primary"
          >
            <el-icon class="is-loading"><Loading /></el-icon>
            已生成 {{ it.cases.length }} 条，继续生成中…
          </p>
          <div
            v-if="caseActionsEnabled && it.status === 'succeeded'"
            class="mb-2 flex items-center justify-between"
          >
            <el-checkbox
              :model-value="allSel(it)"
              :indeterminate="someSel(it)"
              @change="() => toggleAll(it, !allSel(it))"
              >全选</el-checkbox
            >
            <div class="flex items-center gap-2">
              <el-button
                type="primary"
                size="small"
                :loading="applying[it.id]"
                :disabled="!selCount(it) || !it.cases.length"
                @click="apply(it)"
                >{{
                  it.cases.length ? `批量入库（${selCount(it)}）` : `已入库 ${it.applied_count} 条`
                }}</el-button
              >
              <el-button
                size="small"
                :loading="discarding[it.id]"
                :disabled="!selCount(it) || !it.cases.length || it.applied_count > 0"
                @click="discard(it)"
                >批量废弃（{{ selCount(it) }}）</el-button
              >
            </div>
          </div>
          <p v-else-if="effectiveView === 'done'" class="mb-2 text-xs text-muted-foreground">
            已入库 {{ it.applied_count }} 条用例（以下为入库时快照，只读）
          </p>
          <p v-else-if="effectiveView === 'discarded'" class="mb-2 text-xs text-muted-foreground">
            已废弃 {{ it.discarded_cases?.length ?? 0 }} 条预览用例（未入库）
          </p>
          <p
            v-if="effectiveView === 'done' && !itemCaseList(it).length && it.applied_count > 0"
            class="mb-2 text-xs text-[var(--ax-tag-orange-fg,var(--el-color-warning))]"
          >
            暂无快照内容（多为升级前入库）。请重新打开任务详情刷新，或到该接口「测试用例」查看 AI
            用例。
          </p>
          <template v-if="itemCaseList(it).length">
            <div
              v-for="(g, i) in itemCaseList(it)"
              :key="i"
              class="mb-1.5 rounded border border-border px-2 py-1.5"
              :class="{ 'border-primary/35': isCaseOpen(it.id, i) }"
            >
              <div class="flex items-center gap-2">
                <el-checkbox v-if="caseActionsEnabled" v-model="selected[it.id][i]" />
                <el-tag size="small" :type="tagType(g.category)">{{
                  categoryLabel(g.category)
                }}</el-tag>
                <div class="min-w-0 flex-1">
                  <button
                    type="button"
                    class="flex w-full items-center gap-1 border-0 bg-transparent p-0 text-left text-foreground"
                    @click.stop="toggleCase(it.id, i)"
                  >
                    <el-icon
                      class="shrink-0 text-xs text-muted-foreground transition-transform duration-150"
                      :class="{ 'rotate-90': isCaseOpen(it.id, i) }"
                    >
                      <ArrowRight />
                    </el-icon>
                    <span class="break-words text-base leading-snug">{{ g.name }}</span>
                  </button>
                  <div v-if="!isCaseOpen(it.id, i)" class="mt-0.5 text-xs text-muted-foreground">
                    {{ summarizeAssertions(g) }}
                  </div>
                </div>
                <div
                  v-if="caseActionsEnabled && it.cases.length"
                  class="ml-auto flex shrink-0 items-center gap-1"
                  @click.stop
                >
                  <el-button
                    type="primary"
                    size="small"
                    :loading="applying[it.id]"
                    @click="applyOne(it, i)"
                  >
                    入库
                  </el-button>
                  <el-button size="small" :loading="discarding[it.id]" @click="discardOne(it, i)">
                    废弃
                  </el-button>
                </div>
              </div>
              <AiGenCaseDebugExpand
                v-if="isCaseOpen(it.id, i) && effectiveView === 'discarded'"
                v-model="it.discarded_cases![i]"
                :endpoint-id="it.endpoint_id"
                :project-id="resolvedProjectId"
              />
              <AiGenCaseDebugExpand
                v-else-if="isCaseOpen(it.id, i) && effectiveView === 'done'"
                v-model="it.applied_cases![i]"
                :endpoint-id="it.endpoint_id"
                :project-id="resolvedProjectId"
              />
              <AiGenCaseDebugExpand
                v-else-if="isCaseOpen(it.id, i)"
                v-model="it.cases[i]"
                :endpoint-id="it.endpoint_id"
                :project-id="resolvedProjectId"
              />
            </div>
          </template>
        </div>
        <div v-else-if="it.status === 'running'" class="py-1 text-sm text-muted-foreground">
          <el-icon class="is-loading"><Loading /></el-icon>
          正在调用模型生成用例…
        </div>
        <div
          v-else-if="it.status === 'failed'"
          class="flex items-center justify-between gap-3 py-1"
        >
          <span class="py-1 text-sm text-destructive">{{ it.error || '生成失败' }}</span>
          <el-button size="small" :loading="retrying[it.id]" @click="retry(it)">重试</el-button>
        </div>
        <div v-else class="py-1 text-sm text-muted-foreground">{{ statusText(it) }}…</div>
      </el-collapse-item>
    </el-collapse>

    <el-pagination
      v-if="showEndpointPager"
      small
      class="mt-2 justify-end"
      layout="total, prev, pager, next, sizes"
      :total="items.length"
      :page-size="endpointPageSize"
      :current-page="endpointPage"
      :page-sizes="ENDPOINT_PAGE_SIZES"
      @current-change="onEndpointPageChange"
      @size-change="onEndpointPageSizeChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ArrowRight, Loading } from '@element-plus/icons-vue'
import type { Id } from '@/api/request'
import { useAiGenTaskProgress } from '@/composables/useAiGenTaskProgress'
import { categoryLabel } from '@/utils/caseCategory'
import { summarizeAssertions } from '@/utils/apifoxCaseSummary'
import { getAiGenCategoryTagType as tagType } from '@/utils/aiGenTaskPresentation'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import AiGenCaseDebugExpand from '@/components/apifox/ai/AiGenCaseDebugExpand.vue'
import AiGenTaskOverview from '@/components/apifox/ai/AiGenTaskOverview.vue'

const props = withDefaults(
  defineProps<{
    taskId: string | number
    projectId?: Id
    endpointId?: number
    endpointPath?: string
    view?: 'all' | 'pending' | 'done' | 'discarded'
    hideMultiEndpointBatch?: boolean
  }>(),
  {
    projectId: undefined,
    endpointId: undefined,
    endpointPath: '',
    view: 'all',
    hideMultiEndpointBatch: false,
  },
)
const emit = defineEmits<{ applied: [number] }>()
const controller = useAiGenTaskProgress(props, (endpointId) => emit('applied', endpointId))
const {
  projectId: resolvedProjectId,
  compact,
  items,
  pagedItems,
  effectiveView,
  recordEmptyText,
  expanded,
  selected,
  epChecked,
  applying,
  discarding,
  retrying,
  batchApplying,
  applicableItems,
  epCheckedCount,
  allEpSel,
  someEpSel,
  caseActionsEnabled,
  showEndpointPager,
  endpointPage,
  endpointPageSize,
  endpointPageSizes: ENDPOINT_PAGE_SIZES,
  itemCaseList,
  casesBlockVisible,
  canSelectEp,
  isItemExpanded,
  isCaseOpen,
  toggleCase,
  statusText,
  statusType,
  selCount,
  allSel,
  someSel,
  toggleAll,
  toggleAllEp,
  onEndpointPageChange,
  onEndpointPageSizeChange,
  batchApply,
  apply,
  discard,
  applyOne,
  discardOne,
  retry,
} = controller
</script>
