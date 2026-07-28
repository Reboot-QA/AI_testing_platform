<template>
  <Teleport to="body">
    <div v-if="activeTask" class="ai-leave-banner">
      <el-icon class="banner-icon"><WarningFilled /></el-icon>
      <span class="banner-text">
        {{ activeTask.message }}
        <strong>{{ activeTask.countdown }}s</strong>
        内未返回将停止任务
      </span>
      <el-button type="primary" size="small" @click="goBack">返回继续</el-button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAiGenerateStore } from '@/stores/aiGenerate'
import { useRequirementExtractStore } from '@/stores/requirementExtract'

const router = useRouter()
const aiStore = useAiGenerateStore()
const reqStore = useRequirementExtractStore()
const { leaveCountdown: aiCountdown } = storeToRefs(aiStore)
const { leaveCountdown: reqCountdown } = storeToRefs(reqStore)

const activeTask = computed(() => {
  if (aiStore.shouldShowLeaveWarning && aiStore.taskProjectId) {
    return {
      message: '用例生成过程中，请返回该页面，',
      countdown: aiCountdown.value,
      hash: 'domain=functional&section=ai',
      projectId: aiStore.taskProjectId,
    }
  }
  if (reqStore.shouldShowLeaveWarning && reqStore.taskProjectId) {
    return {
      message: '需求解析过程中，请返回该页面，',
      countdown: reqCountdown.value,
      hash: 'domain=requirements&section=req-docs',
      projectId: reqStore.taskProjectId,
    }
  }
  return null
})

function goBack() {
  const task = activeTask.value
  if (!task) return
  void router.push({
    path: `/hub/workspace/${task.projectId}`,
    hash: `#${task.hash}`,
  })
}
</script>

<style scoped>
.ai-leave-banner {
  position: fixed;
  top: var(--ax-space-3);
  left: 50%;
  z-index: 3000;
  display: flex;
  align-items: center;
  gap: var(--ax-space-2-5);
  width: min(720px, calc(100vw - 32px));
  padding: var(--ax-space-2) var(--ax-space-3-5);
  border-radius: var(--ax-radius);
  background: color-mix(in srgb, var(--el-color-warning) 12%, white);
  border: 1px solid color-mix(in srgb, var(--el-color-warning) 35%, white);
  box-shadow: 0 4px 12px rgb(0 0 0 / 12%);
  color: var(--ax-text);
  font-size: var(--ax-text-body-sm-size);
  transform: translateX(-50%);
}

.banner-icon {
  color: var(--el-color-warning);
  font-size: var(--ax-text-title-size);
  flex-shrink: 0;
}

.banner-text {
  flex: 1;
  min-width: 0;
}

.banner-text strong {
  color: var(--el-color-warning);
  font-weight: 700;
}
</style>
