<template>
  <div v-if="task && !compact" class="mb-3 rounded border border-border bg-muted px-3 py-2">
    <div class="flex gap-2 text-sm leading-6">
      <span class="w-10 shrink-0 text-muted-foreground">目标</span>
      <span class="min-w-0 text-foreground">{{ targetText }}</span>
    </div>
    <div class="flex gap-2 text-sm leading-6">
      <span class="w-10 shrink-0 text-muted-foreground">类别</span>
      <span class="min-w-0 text-foreground">{{ categoryConfig }}</span>
    </div>
    <div class="flex gap-2 text-sm leading-6">
      <span class="w-10 shrink-0 text-muted-foreground">模型</span>
      <span class="min-w-0 text-foreground">{{ modeText }}</span>
    </div>
    <div class="flex gap-2 text-sm leading-6">
      <span class="w-10 shrink-0 text-muted-foreground">创建</span>
      <span class="min-w-0 text-foreground">
        {{ task.creator_name || '-' }} · {{ formatTime(task.created_at) }}
      </span>
    </div>
    <div class="flex gap-2 text-sm leading-6">
      <span class="w-10 shrink-0 text-muted-foreground">完成</span>
      <span class="min-w-0 text-foreground">
        {{ task.finished_at ? formatTime(task.finished_at) : '--' }}
        <template v-if="durationText"> · 耗时 {{ durationText }}</template>
      </span>
    </div>
  </div>

  <div class="mb-3">
    <el-progress
      :percentage="percent"
      :status="barStatus"
      :indeterminate="running"
      :stroke-width="6"
    />
    <div class="mt-1.5 text-sm text-muted-foreground">{{ overallText }}</div>
  </div>

  <div
    v-if="genLogs.length && !compact"
    class="mb-3 max-h-40 overflow-auto rounded border border-border bg-background px-3 py-2"
  >
    <div class="mb-1.5 text-xs font-semibold text-muted-foreground">生成日志</div>
    <div
      v-for="(line, index) in genLogs"
      :key="index"
      class="break-words font-mono text-xs leading-relaxed text-foreground"
    >
      {{ line }}
    </div>
  </div>

  <div v-if="showRecordTabs" class="mb-2.5">
    <el-radio-group v-model="recordView" size="small">
      <el-radio-button value="pending"
        >待入库{{ pendingTabCount ? ` (${pendingTabCount})` : '' }}</el-radio-button
      >
      <el-radio-button value="done"
        >已入库{{ doneTabCount ? ` (${doneTabCount})` : '' }}</el-radio-button
      >
      <el-radio-button value="discarded"
        >废弃{{ discardedTabCount ? ` (${discardedTabCount})` : '' }}</el-radio-button
      >
    </el-radio-group>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AiGenTaskProgressController } from '@/composables/useAiGenTaskProgress'
import { formatTime } from '@/utils/runFormat'

const props = defineProps<{ controller: AiGenTaskProgressController }>()
const emit = defineEmits<{ 'update:recordView': ['pending' | 'done' | 'discarded'] }>()
const {
  task,
  compact,
  targetText,
  categoryConfig,
  modeText,
  durationText,
  percent,
  barStatus,
  running,
  overallText,
  genLogs,
  showRecordTabs,
  pendingTabCount,
  doneTabCount,
  discardedTabCount,
} = props.controller
const recordView = computed({
  get: () => props.controller.recordView.value,
  set: (value) => emit('update:recordView', value),
})
</script>
