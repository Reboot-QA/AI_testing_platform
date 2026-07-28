<template>
  <div class="progress">
    <div v-if="task && !compact" class="task-info">
      <div class="ti-row">
        <span class="ti-k">目标</span><span class="ti-v">{{ targetText }}</span>
      </div>
      <div class="ti-row">
        <span class="ti-k">类别</span><span class="ti-v">{{ categoryConfig }}</span>
      </div>
      <div class="ti-row">
        <span class="ti-k">模型</span><span class="ti-v">{{ modeText }}</span>
      </div>
      <div class="ti-row">
        <span class="ti-k">创建</span>
        <span class="ti-v">{{ task.creator_name || '-' }} · {{ formatTime(task.created_at) }}</span>
      </div>
      <div class="ti-row">
        <span class="ti-k">完成</span>
        <span class="ti-v"
          >{{ task.finished_at ? formatTime(task.finished_at) : '--'
          }}<span v-if="durationText"> · 耗时 {{ durationText }}</span></span
        >
      </div>
    </div>

    <div class="overall">
      <el-progress
        :percentage="percent"
        :status="barStatus"
        :indeterminate="running"
        :stroke-width="6"
      />
      <div class="overall-text">{{ overallText }}</div>
    </div>

    <div v-if="genLogs.length && !compact" class="gen-logs">
      <div class="gen-logs-title">生成日志</div>
      <div v-for="(line, i) in genLogs" :key="i" class="gen-log-line">{{ line }}</div>
    </div>

    <!-- 批量入库（多接口任务中心）；单接口 AI 页用下方用例级「入库」即可 -->
    <div v-if="applicableItems.length && props.view !== 'done' && !compact" class="batch-bar">
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

    <el-collapse v-if="items.length" v-model="expanded">
      <el-collapse-item v-for="it in items" :key="it.id" :name="it.id">
        <template #title>
          <template v-if="!compact">
            <el-checkbox
              v-if="canSelectEp(it)"
              :model-value="!!epChecked[it.id]"
              class="ep-check"
              @click.stop
              @change="(v: boolean) => (epChecked[it.id] = v)"
            />
            <MethodTag :method="it.endpoint_method" />
            <span class="ep-name">{{ it.endpoint_name }}</span>
            <el-tag size="small" :type="statusType(it.status)" class="st-tag">{{
              statusText(it)
            }}</el-tag>
          </template>
          <span v-else class="ep-name compact-title">生成结果</span>
        </template>

        <div v-if="casesBlockVisible(it)" class="cases">
          <p v-if="it.status === 'running'" class="gen-running-hint">
            <el-icon class="is-loading"><Loading /></el-icon>
            已生成 {{ it.cases.length }} 条，继续生成中…
          </p>
          <div v-if="props.view === 'pending' && it.status === 'succeeded'" class="case-bar">
            <el-checkbox
              :model-value="allSel(it)"
              :indeterminate="someSel(it)"
              @change="() => toggleAll(it, !allSel(it))"
              >全选</el-checkbox
            >
            <div class="case-bar-actions">
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
          <p v-else-if="props.view === 'done'" class="applied-hint">
            已入库 {{ it.applied_count }} 条用例
          </p>
          <p v-else-if="props.view === 'discarded'" class="applied-hint">
            已废弃 {{ it.discarded_cases?.length ?? 0 }} 条预览用例（未入库）
          </p>
          <template v-if="selected[it.id] || props.view === 'done' || props.view === 'discarded'">
            <div
              v-for="(g, i) in itemCaseList(it)"
              :key="i"
              class="gen-item"
              :class="{ 'gen-item--open': isCaseOpen(it.id, i) }"
            >
              <div class="gen-row">
                <el-checkbox v-if="props.view === 'pending'" v-model="selected[it.id][i]" />
                <el-tag size="small" :type="tagType(g.category)">{{
                  categoryLabel(g.category)
                }}</el-tag>
                <div class="gen-body">
                  <button type="button" class="gen-name-btn" @click.stop="toggleCase(it.id, i)">
                    <el-icon class="gen-chev" :class="{ 'gen-chev--open': isCaseOpen(it.id, i) }">
                      <ArrowRight />
                    </el-icon>
                    <span class="gen-name">{{ g.name }}</span>
                  </button>
                  <div v-if="!isCaseOpen(it.id, i)" class="gen-sum">
                    {{ summarizeAssertions(g) }}
                  </div>
                </div>
                <div
                  v-if="props.view === 'pending' && it.cases.length"
                  class="gen-row-actions"
                  @click.stop
                >
                  <span class="gen-more" aria-hidden="true">
                    <el-icon><MoreFilled /></el-icon>
                  </span>
                  <div class="gen-row-actions-pop">
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
              </div>
              <AiGenCaseDebugExpand
                v-if="isCaseOpen(it.id, i) && props.view !== 'discarded'"
                v-model="it.cases[i]"
                :endpoint-id="it.endpoint_id"
                :project-id="projectId"
              />
              <AiGenCaseDebugExpand
                v-else-if="isCaseOpen(it.id, i)"
                v-model="it.discarded_cases![i]"
                :endpoint-id="it.endpoint_id"
                :project-id="projectId"
              />
            </div>
          </template>
        </div>
        <div v-else-if="it.status === 'running'" class="item-msg">
          <el-icon class="is-loading"><Loading /></el-icon>
          正在调用模型生成用例…
        </div>
        <div v-else-if="it.status === 'failed'" class="item-fail">
          <span class="item-msg err">{{ it.error || '生成失败' }}</span>
          <el-button size="small" :loading="retrying[it.id]" @click="retry(it)">重试</el-button>
        </div>
        <div v-else class="item-msg">{{ statusText(it) }}…</div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ArrowRight, Loading, MoreFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { categoryLabel } from '@/utils/caseCategory'
import { formatTime } from '@/utils/runFormat'
import { summarizeAssertions } from '@/utils/apifoxCaseSummary'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import AiGenCaseDebugExpand from '@/components/apifox/ai/AiGenCaseDebugExpand.vue'

type Item = Schemas['AiGenTaskItemOut']

const props = withDefaults(
  defineProps<{
    taskId: string | number
    projectId?: Id
    endpointId?: number
    endpointPath?: string
    view?: 'all' | 'pending' | 'done' | 'discarded'
  }>(),
  { view: 'all', endpointPath: '' },
)
const emit = defineEmits<{ applied: [number] }>()

const store = useApifoxAiGenerateStore()
const task = computed(() => store.taskById(Number(props.taskId)))

const projectId = computed(() => {
  const fromProp = props.projectId
  if (fromProp != null && fromProp !== '') return fromProp
  return task.value?.project_id ?? 0
})
const allItems = computed<Item[]>(() => task.value?.items || [])

const items = computed<Item[]>(() => {
  let list = allItems.value
  if (props.endpointId != null) {
    list = list.filter((i) => i.endpoint_id === props.endpointId)
  }
  if (props.view === 'pending') {
    list = list.filter(
      (i) => i.status !== 'succeeded' || (i.status === 'succeeded' && i.cases.length > 0),
    )
  } else if (props.view === 'done') {
    list = list.filter((i) => i.applied_count > 0)
  } else if (props.view === 'discarded') {
    list = list.filter((i) => (i.discarded_cases?.length ?? 0) > 0)
  }
  return list
})

function itemCaseList(it: Item): Schemas['CaseCreate'][] {
  if (props.view === 'discarded') return it.discarded_cases ?? []
  return it.cases
}

function casesBlockVisible(it: Item): boolean {
  if (it.status !== 'succeeded' && it.status !== 'running') return false
  if (props.view === 'discarded') return (it.discarded_cases?.length ?? 0) > 0
  return it.cases.length > 0 || it.status === 'running'
}

const compact = computed(() => props.endpointId != null)
const running = computed(
  () => !!task.value && !['succeeded', 'partial', 'failed', 'canceled'].includes(task.value.status),
)

// ---------- 详情信息区 ----------
const targetText = computed(() => {
  const t = task.value
  if (!t) return ''
  if (t.total_items === 1 && t.items[0])
    return `${t.items[0].endpoint_method} ${t.items[0].endpoint_name}`
  return `批量 · ${t.total_items} 接口`
})
const categoryConfig = computed(
  () =>
    (task.value?.categories || [])
      .map((c) => `${categoryLabel(c.category)}（${c.count ? '限量 ' + c.count : '自动'}）`)
      .join(' · ') || '-',
)
const modeText = computed(() =>
  task.value?.mode === 'mock'
    ? 'Mock'
    : task.value?.mode === 'llm'
      ? task.value?.provider_name || 'LLM'
      : '-',
)
const durationText = computed(() => {
  const t = task.value
  if (!t?.finished_at || !t?.created_at) return ''
  const ms = new Date(t.finished_at).getTime() - new Date(t.created_at).getTime()
  if (ms <= 0) return ''
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s} 秒` : `${Math.floor(s / 60)} 分 ${s % 60} 秒`
})
const expanded = ref<number[]>([])
const selected = reactive<Record<number, boolean[]>>({})
const epChecked = reactive<Record<number, boolean>>({})
const applying = reactive<Record<number, boolean>>({})
const discarding = reactive<Record<number, boolean>>({})
const retrying = reactive<Record<number, boolean>>({})
const batchApplying = ref(false)
const openCaseKeys = ref<Set<string>>(new Set())

function caseKey(itemId: number, index: number) {
  return `${itemId}:${index}`
}

function isCaseOpen(itemId: number, index: number) {
  return openCaseKeys.value.has(caseKey(itemId, index))
}

function toggleCase(itemId: number, index: number) {
  const key = caseKey(itemId, index)
  const next = new Set(openCaseKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  openCaseKeys.value = next
}

const percent = computed(() => {
  const t = task.value
  if (!t || !t.total_items) return 0
  if (t.total_items === 1 && items.value.length === 1) {
    const it = items.value[0]
    if (it.status === 'succeeded') return 100
    if (it.status === 'running') {
      const n = it.cases.length
      const catN = Math.max(t.categories?.length || 1, 1)
      if (n > 0) return Math.min(92, Math.round((n / (catN * 3)) * 100))
      return 8
    }
    if (it.status === 'pending') return 0
  }
  return Math.round((t.done_items / t.total_items) * 100)
})
const barStatus = computed<'' | 'success' | 'warning' | 'exception'>(() => {
  const s = task.value?.status
  if (s === 'succeeded') return 'success'
  if (s === 'failed') return 'exception'
  if (s === 'partial') return 'warning'
  return ''
})
const STATUS_LABELS: Record<string, string> = {
  pending: '排队中',
  running: '生成中',
  succeeded: '全部完成',
  partial: '部分完成',
  failed: '生成失败',
  canceled: '已取消',
}
const overallText = computed(() => {
  const t = task.value
  if (!t) return ''
  const base = `${STATUS_LABELS[t.status] || t.status} · ${t.done_items}/${t.total_items} 个接口`
  if (t.total_items === 1 && items.value[0]?.status === 'running') {
    const n = items.value[0].cases.length
    return n ? `${base} · 已生成 ${n} 条用例` : `${base} · 等待模型响应…`
  }
  return base
})

const genLogs = computed(() => {
  const t = task.value
  if (!t) return []
  const lines: string[] = [`任务 #${t.id} · ${STATUS_LABELS[t.status] || t.status}`]
  if (t.error) lines.push(`任务错误：${t.error}`)
  for (const it of items.value) {
    const ep = `${it.endpoint_method} ${it.endpoint_name}`
    if (it.status === 'pending') lines.push(`${ep}：排队中`)
    else if (it.status === 'running')
      lines.push(`${ep}：生成中${it.cases.length ? `，已产出 ${it.cases.length} 条` : '…'}`)
    else if (it.status === 'succeeded') lines.push(`${ep}：完成，生成 ${it.cases.length} 条用例`)
    else if (it.status === 'failed') lines.push(`${ep}：失败 · ${it.error || '未知错误'}`)
    else if (it.status === 'canceled') lines.push(`${ep}：已取消`)
    if (it.applied_count > 0) lines.push(`${ep}：已入库 ${it.applied_count} 条`)
  }
  return lines
})

const tagType = (cat: string): string =>
  ({ positive: 'success', negative: 'warning', boundary: '', security: 'danger' })[cat] || 'info'

function statusText(it: Item): string {
  if (it.status === 'succeeded') return `${it.cases.length} 条`
  if (it.status === 'running') return it.cases.length ? `${it.cases.length} 条…` : '生成中'
  const map: Record<string, string> = {
    pending: '排队中',
    running: '生成中',
    failed: '失败',
    canceled: '已取消',
  }
  return map[it.status] || it.status
}
function statusType(status: string): string {
  const map: Record<string, string> = {
    succeeded: 'success',
    failed: 'danger',
    running: 'primary',
    canceled: 'info',
  }
  return map[status] || 'info'
}

// 生成成功、拿到用例后为该接口初始化默认全选（用例级 + 接口级默认勾选）
watch(
  items,
  (list) => {
    list.forEach((it) => {
      if (
        (it.status === 'succeeded' || it.status === 'running') &&
        it.cases.length &&
        !selected[it.id]
      ) {
        selected[it.id] = it.cases.map(() => true)
        if (it.applied_count === 0 && it.status === 'succeeded') epChecked[it.id] = true
      } else if (it.cases.length && selected[it.id]) {
        const sel = selected[it.id]
        while (sel.length < it.cases.length) sel.push(true)
        if (sel.length > it.cases.length) {
          selected[it.id] = sel.slice(0, it.cases.length)
        }
      } else if (!it.cases.length) {
        delete selected[it.id]
      }
    })
    if (compact.value && list.length && expanded.value.length === 0) {
      expanded.value = list.map((it) => it.id)
    }
  },
  { deep: true, immediate: true },
)

// 可批量入库的接口：生成成功、有用例、尚未入库
const canSelectEp = (it: Item): boolean => it.status === 'succeeded' && it.cases.length > 0
const applicableItems = computed(() => items.value.filter(canSelectEp))
const epCheckedCount = computed(() => applicableItems.value.filter((it) => epChecked[it.id]).length)
const allEpSel = computed(
  () => applicableItems.value.length > 0 && epCheckedCount.value === applicableItems.value.length,
)
const someEpSel = computed(() => epCheckedCount.value > 0 && !allEpSel.value)
function toggleAllEp(val: unknown): void {
  applicableItems.value.forEach((it) => (epChecked[it.id] = !!val))
}

async function batchApply(): Promise<void> {
  const targets = applicableItems.value.filter((it) => epChecked[it.id] && selCount(it) > 0)
  if (!targets.length) return
  batchApplying.value = true
  try {
    // 一次请求入库全部所选接口项（服务端聚合），避免逐项串行往返
    const items = targets.map((it) => ({
      item_id: it.id,
      indexes: it.cases.map((_, i) => i).filter((i) => selected[it.id]?.[i]),
    }))
    const res = await store.applyItemsBatch(Number(props.taskId), items)
    targets.forEach((it) => {
      const fresh = store.taskById(Number(props.taskId))?.items.find((x) => x.id === it.id)
      if (fresh && selected[it.id]) {
        selected[it.id] = selected[it.id].slice(0, fresh.cases.length)
        while (selected[it.id].length < fresh.cases.length) selected[it.id].push(true)
      }
    })
    targets.forEach((it) => emit('applied', it.endpoint_id))
    const failed = res.failed?.length || 0
    const tail = res.skipped ? `，跳过 ${res.skipped} 条已存在` : ''
    if (failed)
      ElMessage.warning(
        `批量入库：${res.applied_items} 个接口共创建 ${res.created} 条，${failed} 条失败${tail}`,
      )
    else
      ElMessage.success(
        `批量入库完成：${res.applied_items} 个接口共创建 ${res.created} 条用例${tail}`,
      )
  } catch {
    ElMessage.error('批量入库失败，请重试')
  } finally {
    batchApplying.value = false
  }
}

const selCount = (it: Item): number => (selected[it.id] || []).filter(Boolean).length
const allSel = (it: Item): boolean => it.cases.length > 0 && selCount(it) === it.cases.length
const someSel = (it: Item): boolean => selCount(it) > 0 && !allSel(it)
function toggleAll(it: Item, val: unknown): void {
  selected[it.id] = it.cases.map(() => !!val)
}

/** 从预览移除用例后，同步勾选与展开态（不整页刷新） */
function syncAfterCasesRemoved(it: Item, removedIndexes: number[]): void {
  const drop = new Set(removedIndexes)
  if (selected[it.id]) {
    selected[it.id] = selected[it.id].filter((_, i) => !drop.has(i))
  }
  const prefix = `${it.id}:`
  const next = new Set<string>()
  for (const k of openCaseKeys.value) {
    if (!k.startsWith(prefix)) {
      next.add(k)
      continue
    }
    const idx = Number(k.slice(prefix.length))
    if (drop.has(idx)) continue
    const shift = removedIndexes.filter((r) => r < idx).length
    next.add(`${it.id}:${idx - shift}`)
  }
  openCaseKeys.value = next
}

function indexesRemovedByApply(
  snapshots: { i: number; name: string }[],
  failed: string[],
): number[] {
  const failedSet = new Set(failed)
  return snapshots.filter((s) => s.name && !failedSet.has(s.name)).map((s) => s.i)
}

async function apply(it: Item): Promise<void> {
  const indexes = it.cases.map((_, i) => i).filter((i) => selected[it.id]?.[i])
  const snapshots = indexes.map((i) => ({ i, name: it.cases[i]?.name ?? '' }))
  applying[it.id] = true
  try {
    const res = await store.applyItem(Number(props.taskId), it.id, indexes)
    syncAfterCasesRemoved(it, indexesRemovedByApply(snapshots, res.failed))
    const tail = res.skipped ? `，跳过 ${res.skipped} 条已存在` : ''
    if (res.failed?.length) {
      ElMessage.warning(
        `${it.endpoint_name}：已创建 ${res.created} 条，${res.failed.length} 条失败${tail}`,
      )
    } else {
      ElMessage.success(`${it.endpoint_name}：已创建 ${res.created} 条用例${tail}`)
    }
    emit('applied', it.endpoint_id)
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '入库失败')
  } finally {
    applying[it.id] = false
  }
}

async function discard(it: Item): Promise<void> {
  const indexes = it.cases.map((_, i) => i).filter((i) => selected[it.id]?.[i])
  if (!indexes.length) return
  await discardIndexes(it, indexes)
}

async function applyOne(it: Item, index: number): Promise<void> {
  const snapshots = [{ i: index, name: it.cases[index]?.name ?? '' }]
  applying[it.id] = true
  try {
    const res = await store.applyItem(Number(props.taskId), it.id, [index])
    syncAfterCasesRemoved(it, indexesRemovedByApply(snapshots, res.failed))
    const tail = res.skipped ? `，跳过 ${res.skipped} 条已存在` : ''
    if (res.failed?.length) {
      ElMessage.warning(`入库失败：${res.failed.join('、')}${tail}`)
    } else if (res.created) {
      ElMessage.success('已入库 1 条用例' + tail)
      emit('applied', it.endpoint_id)
    } else {
      ElMessage.info('未新建用例' + tail)
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '入库失败')
  } finally {
    applying[it.id] = false
  }
}

async function discardOne(it: Item, index: number): Promise<void> {
  await discardIndexes(it, [index])
}

async function discardIndexes(it: Item, indexes: number[]): Promise<void> {
  if (!indexes.length) return
  discarding[it.id] = true
  try {
    const res = await store.discardItem(Number(props.taskId), it.id, indexes)
    syncAfterCasesRemoved(it, indexes)
    ElMessage.success(`已废弃 ${res.discarded} 条预览用例`)
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '废弃失败')
  } finally {
    discarding[it.id] = false
  }
}

async function retry(it: Item): Promise<void> {
  retrying[it.id] = true
  try {
    await store.retryItem(Number(props.taskId), it.id)
    ElMessage.info(`${it.endpoint_name}：已重新排队生成`)
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '重试失败')
  } finally {
    retrying[it.id] = false
  }
}
</script>

<style scoped>
.task-info {
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  padding: var(--ax-space-2) var(--ax-space-3);
  margin-bottom: var(--ax-space-3);
  background: var(--ax-bg-subtle);
}

.ti-row {
  display: flex;
  gap: var(--ax-space-2);
  font-size: var(--ax-text-body-sm-size);
  line-height: var(--ax-leading-prose);
}

.ti-k {
  width: 40px;
  flex-shrink: 0;
  color: var(--ax-text-secondary);
}

.ti-v {
  color: var(--ax-text);
  min-width: 0;
}

.overall {
  margin-bottom: var(--ax-space-3);
}

.overall-text {
  margin-top: var(--ax-space-1-5);
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
}

.gen-logs {
  margin-bottom: var(--ax-space-3);
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  background: var(--ax-bg);
  padding: var(--ax-space-2) var(--ax-space-3);
  max-height: 160px;
  overflow: auto;
}

.gen-logs-title {
  font-size: var(--ax-font-xs);
  font-weight: 600;
  color: var(--ax-text-secondary);
  margin-bottom: var(--ax-space-1-5);
}

.gen-log-line {
  font-family: Consolas, Monaco, monospace;
  font-size: var(--ax-font-xs);
  color: var(--ax-text);
  line-height: 1.6;
  word-break: break-word;
}

.ep-name {
  margin: 0 var(--ax-space-2);
  font-size: var(--ax-text-body-size);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}

.st-tag {
  margin-left: auto;
}

.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  padding: var(--ax-space-2) var(--ax-space-3);
  margin-bottom: var(--ax-space-2);
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  background: var(--ax-bg-subtle);
}

.ep-check {
  margin-right: var(--ax-space-2);
}

.case-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-space-2);
}

.case-bar-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.gen-item {
  padding: var(--ax-space-1-5) var(--ax-space-2);
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  margin-bottom: var(--ax-space-1-5);
}

.gen-item--open {
  border-color: color-mix(in srgb, var(--color-blue-6) 35%, var(--ax-border));
}

.gen-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.gen-row-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 28px;
  margin-left: auto;
}

.gen-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--ax-text-tertiary);
  cursor: default;
}

.gen-row-actions-pop {
  display: none;
  align-items: center;
  gap: var(--ax-space-1);
}

.gen-row-actions:hover .gen-more,
.gen-row-actions:focus-within .gen-more {
  display: none;
}

.gen-row-actions:hover .gen-row-actions-pop,
.gen-row-actions:focus-within .gen-row-actions-pop {
  display: flex;
}

.gen-body {
  min-width: 0;
  flex: 1;
}

.gen-name-btn {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: var(--ax-text);
}

.gen-name-btn:hover .gen-name {
  color: var(--color-blue-6);
}

.gen-chev {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--ax-text-placeholder);
  transition: transform 0.15s ease;
}

.gen-chev--open {
  transform: rotate(90deg);
}

.gen-name {
  font-size: var(--ax-text-body-size);
  line-height: 1.4;
  word-break: break-word;
}

.gen-sum {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
  margin-top: var(--ax-space-0-5);
}

.gen-running-hint {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  margin: 0 0 var(--ax-space-2);
  font-size: var(--ax-text-body-sm-size);
  color: var(--color-blue-6);
}

.item-msg {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
  padding: var(--ax-space-1) 0;
}

.item-fail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-3);
  padding: var(--ax-space-1) 0;
}

.compact-title {
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.applied-hint {
  font-size: var(--ax-font-sm);
  color: var(--ax-success);
  margin: 0 0 var(--ax-space-2);
}

.item-msg.err {
  color: var(--ax-danger, #f56c6c);
}
</style>
