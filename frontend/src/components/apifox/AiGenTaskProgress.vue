<template>
  <div class="progress">
    <div class="overall">
      <el-progress
        :percentage="percent"
        :status="barStatus"
        :indeterminate="running"
        :stroke-width="6"
      />
      <div class="overall-text">{{ overallText }}</div>
    </div>

    <el-collapse v-if="items.length" v-model="expanded">
      <el-collapse-item v-for="it in items" :key="it.id" :name="it.id">
        <template #title>
          <MethodTag :method="it.endpoint_method" />
          <span class="ep-name">{{ it.endpoint_name }}</span>
          <el-tag size="small" :type="statusType(it.status)" class="st-tag">{{
            statusText(it)
          }}</el-tag>
        </template>

        <div v-if="it.status === 'succeeded'" class="cases">
          <div class="case-bar">
            <el-checkbox
              :model-value="allSel(it)"
              :indeterminate="someSel(it)"
              @change="() => toggleAll(it, !allSel(it))"
              >全选</el-checkbox
            >
            <el-button
              type="primary"
              size="small"
              :loading="applying[it.id]"
              :disabled="!selCount(it) || it.applied_count > 0"
              @click="apply(it)"
              >{{ it.applied_count > 0 ? '已入库' : `入库（${selCount(it)}）` }}</el-button
            >
          </div>
          <template v-if="selected[it.id]">
            <div v-for="(g, i) in it.cases" :key="i" class="gen-item">
              <el-checkbox v-model="selected[it.id][i]" :disabled="it.applied_count > 0" />
              <el-tag size="small" :type="tagType(g.category)">{{
                categoryLabel(g.category)
              }}</el-tag>
              <div class="gen-body">
                <div class="gen-name">{{ g.name }}</div>
                <div class="gen-sum">{{ summarizeAssertions(g) }}</div>
              </div>
            </div>
          </template>
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
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { categoryLabel } from '@/utils/caseCategory'
import { summarizeAssertions } from '@/utils/apifoxCaseSummary'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

type Item = Schemas['AiGenTaskItemOut']

const props = defineProps<{ taskId: string | number }>()
const emit = defineEmits<{ applied: [number] }>()

const store = useApifoxAiGenerateStore()
const task = computed(() => store.taskById(Number(props.taskId)))
const items = computed<Item[]>(() => task.value?.items || [])
const running = computed(
  () => !!task.value && !['succeeded', 'partial', 'failed', 'canceled'].includes(task.value.status),
)

const expanded = ref<number[]>([])
const selected = reactive<Record<number, boolean[]>>({})
const applying = reactive<Record<number, boolean>>({})
const retrying = reactive<Record<number, boolean>>({})

const percent = computed(() => {
  const t = task.value
  if (!t || !t.total_items) return 0
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
  return `${STATUS_LABELS[t.status] || t.status} · ${t.done_items}/${t.total_items} 个接口`
})

const tagType = (cat: string): string =>
  ({ positive: 'success', negative: 'warning', boundary: '', security: 'danger' })[cat] || 'info'

function statusText(it: Item): string {
  if (it.status === 'succeeded') return `${it.cases.length} 条`
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

// 生成成功、拿到用例后为该接口初始化默认全选
watch(
  items,
  (list) => {
    list.forEach((it) => {
      if (it.status === 'succeeded' && it.cases.length && !selected[it.id]) {
        selected[it.id] = it.cases.map(() => true)
      }
    })
  },
  { deep: true, immediate: true },
)

const selCount = (it: Item): number => (selected[it.id] || []).filter(Boolean).length
const allSel = (it: Item): boolean => it.cases.length > 0 && selCount(it) === it.cases.length
const someSel = (it: Item): boolean => selCount(it) > 0 && !allSel(it)
function toggleAll(it: Item, val: unknown): void {
  selected[it.id] = it.cases.map(() => !!val)
}

async function apply(it: Item): Promise<void> {
  const indexes = it.cases.map((_, i) => i).filter((i) => selected[it.id]?.[i])
  applying[it.id] = true
  try {
    const res = await store.applyItem(Number(props.taskId), it.id, indexes)
    if (res.failed?.length) {
      ElMessage.warning(
        `${it.endpoint_name}：已创建 ${res.created} 条，${res.failed.length} 条失败`,
      )
    } else {
      ElMessage.success(`${it.endpoint_name}：已创建 ${res.created} 条用例`)
    }
    emit('applied', it.endpoint_id)
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '入库失败')
  } finally {
    applying[it.id] = false
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
.overall {
  margin-bottom: 12px;
}

.overall-text {
  margin-top: 6px;
  color: var(--ax-text-secondary);
  font-size: 13px;
}

.ep-name {
  margin: 0 8px;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}

.st-tag {
  margin-left: auto;
}

.case-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.gen-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  margin-bottom: 6px;
}

.gen-body {
  min-width: 0;
  flex: 1;
}

.gen-name {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gen-sum {
  color: var(--ax-text-placeholder);
  font-size: 12px;
  margin-top: 2px;
}

.item-msg {
  color: var(--ax-text-secondary);
  font-size: 13px;
  padding: 4px 0;
}

.item-fail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0;
}

.item-msg.err {
  color: var(--ax-danger, #f56c6c);
}
</style>
