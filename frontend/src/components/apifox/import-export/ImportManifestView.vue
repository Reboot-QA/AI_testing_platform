<template>
  <div class="imv">
    <div class="imv-summary">
      <el-tag size="small" type="success" effect="plain">新增 {{ manifest.added }}</el-tag>
      <el-tag size="small" type="warning" effect="plain">更新 {{ manifest.updated }}</el-tag>
      <el-tag size="small" type="danger" effect="plain">删除 {{ manifest.deleted }}</el-tag>
      <el-tag v-if="manifest.kept_referenced" size="small" type="info" effect="plain"
        >保留 {{ manifest.kept_referenced }}</el-tag
      >
      <el-tag size="small" type="info" effect="plain">未变 {{ manifest.skipped }}</el-tag>
      <el-button link size="small" class="imv-toggle" @click="expanded = !expanded">
        {{ expanded ? '收起明细' : '展开明细' }}
      </el-button>
    </div>

    <template v-if="expanded">
      <div class="imv-section">
        <div v-if="!changed.length" class="imv-empty">本次无接口变化</div>
        <div v-for="it in changed" :key="rowKey(it)" class="imv-row">
          <el-tag size="small" :type="STATUS_TAG[it.status]">{{ STATUS_LABEL[it.status] }}</el-tag>
          <MethodTag :method="it.method" />
          <span class="imv-path">{{ it.path }}</span>
          <span v-if="it.folder" class="imv-folder">{{ it.folder }}</span>
        </div>
      </div>

      <div v-if="skipped.length" class="imv-skipped">
        <el-button link size="small" @click="showSkipped = !showSkipped">
          {{ showSkipped ? '收起' : '查看' }}未变接口 ({{ skipped.length }})
        </el-button>
        <div v-if="showSkipped" class="imv-section">
          <div v-for="it in skipped" :key="rowKey(it)" class="imv-row">
            <MethodTag :method="it.method" />
            <span class="imv-path">{{ it.path }}</span>
            <span v-if="it.folder" class="imv-folder">{{ it.folder }}</span>
          </div>
        </div>
      </div>

      <div v-if="manifest.truncated" class="imv-trunc">
        清单过长已截断，仅展示前 {{ manifest.items?.length ?? 0 }} 条
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Schemas } from '@/api/types'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

type ManifestItem = Schemas['ImportRunItem']
const props = defineProps<{ manifest: Schemas['ImportRunManifest'] }>()

const STATUS_LABEL: Record<string, string> = {
  added: '新增',
  updated: '更新',
  deleted: '删除',
  kept: '保留',
}
const STATUS_TAG: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
  added: 'success',
  updated: 'warning',
  deleted: 'danger',
  kept: 'info',
}

const expanded = ref(false)
const showSkipped = ref(false)

const changed = computed(() => (props.manifest.items || []).filter((i) => i.status !== 'skipped'))
const skipped = computed(() => (props.manifest.items || []).filter((i) => i.status === 'skipped'))

function rowKey(it: ManifestItem): string {
  return `${it.status}-${it.method}-${it.path}`
}
</script>

<style scoped>
.imv {
  margin-top: var(--ax-space-1);
}

.imv-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ax-space-1);
}

.imv-toggle {
  margin-left: var(--ax-space-1);
}

.imv-section {
  margin-top: var(--ax-space-1);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  max-height: 220px;
  overflow: auto;
}

.imv-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  padding: var(--ax-space-1) var(--ax-space-2);
  font-size: var(--ax-font-xs);
  border-bottom: 1px solid color-mix(in srgb, var(--ax-border) 60%, transparent);
}

.imv-row:last-child {
  border-bottom: none;
}

.imv-path {
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text);
  word-break: break-all;
}

.imv-folder {
  margin-left: auto;
  color: var(--ax-text-placeholder);
  flex-shrink: 0;
}

.imv-skipped {
  margin-top: var(--ax-space-1);
}

.imv-empty {
  padding: var(--ax-space-2);
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.imv-trunc {
  margin-top: var(--ax-space-1);
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}
</style>
