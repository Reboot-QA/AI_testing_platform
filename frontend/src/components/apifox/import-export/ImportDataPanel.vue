<template>
  <div class="io-page">
    <header class="io-head">
      <div>
        <h2 class="io-title">导入数据</h2>
        <p class="io-desc">选择数据源格式，在下方直接完成导入</p>
      </div>
      <div class="io-head-actions">
        <el-button @click="scheduleOpen = true">定时导入</el-button>
        <el-button @click="apiAccessOpen = true">
          通过 API 导入
          <el-icon class="io-ext"><Link /></el-icon>
        </el-button>
      </div>
      <ImportScheduleDialog v-model="scheduleOpen" />
      <ApiAccessDialog v-model="apiAccessOpen" mode="import" />
    </header>

    <section class="io-section">
      <h3 class="io-section-title">选择格式</h3>
      <div class="io-cards">
        <button
          v-for="item in IMPORT_FORMATS"
          :key="item.key"
          type="button"
          class="io-card"
          :class="{ active: format === item.key }"
          @click="format = item.key"
        >
          <span class="io-card-logo" :class="`tone-${item.tone}`">{{ item.abbr }}</span>
          <span class="io-card-name">{{ item.label }}</span>
        </button>
      </div>
    </section>

    <section class="io-section io-panel">
      <!-- 输入态 -->
      <template v-if="!diff">
        <div class="io-panel-head">
          <h3 class="io-section-title">{{ current.label }}</h3>
          <p v-if="current.hint" class="io-hint">
            {{ current.hint }}
            <button type="button" class="io-link" @click="comingSoon">查看详细说明</button>
          </p>
          <p v-if="isUpdate" class="io-hint io-hint--update">
            该项目已有接口，将作为「更新同步」：先预览变更（新增/变更/移除）再应用，不会盲目新建。
          </p>
        </div>

        <ImportDialogContent
          ref="contentRef"
          :format="format"
          :url="url"
          :basic-auth="basicAuth"
          :basic-auth-user="basicAuthUser"
          :basic-auth-pwd="basicAuthPwd"
          :curl-text="curlText"
          @update:url="url = $event"
          @update:basic-auth="basicAuth = $event"
          @update:basic-auth-user="basicAuthUser = $event"
          @update:basic-auth-pwd="basicAuthPwd = $event"
          @update:curl-text="curlText = $event"
          @update:mode="mode = $event"
          @file="onFile"
        />

        <div v-if="showContinue" class="io-footer">
          <el-button
            type="primary"
            :loading="busy"
            :disabled="!canContinue"
            @click="handleContinue"
          >
            {{ continueLabel }}
          </el-button>
        </div>
      </template>

      <!-- 更新预览态（同源识别） -->
      <template v-else>
        <div class="io-panel-head">
          <h3 class="io-section-title">更新预览</h3>
          <p class="io-hint">与上次导入同源，已识别为「更新同步」；确认变更后应用。</p>
        </div>
        <ImportDiffPreview :diff="diff" />
        <el-checkbox v-model="deleteUnreferenced" class="io-del-opt">
          同时删除「新 Swagger 已移除且无用例引用」的接口（连同其用例）
        </el-checkbox>
        <div class="io-footer">
          <el-button @click="resetDiff">返回</el-button>
          <el-button type="primary" :loading="busy" @click="handleApply">应用更新</el-button>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ImportSourceFormat } from '@/types/apifox'
import { IMPORT_FORMATS, findImportFormat } from '@/utils/importFormats'
import { useImportWorkspace } from '@/composables/useImportWorkspace'
import ImportDialogContent from '@/components/apifox/import-export/ImportDialogContent.vue'
import ImportDiffPreview from '@/components/apifox/import-export/ImportDiffPreview.vue'
import ImportScheduleDialog from '@/components/apifox/import-export/ImportScheduleDialog.vue'
import ApiAccessDialog from '@/components/apifox/endpoint/ApiAccessDialog.vue'

const format = ref<ImportSourceFormat>('openapi')
const current = computed(() => findImportFormat(format.value))
const contentRef = ref<InstanceType<typeof ImportDialogContent> | null>(null)
const scheduleOpen = ref(false)
const apiAccessOpen = ref(false)

const {
  url,
  basicAuth,
  basicAuthUser,
  basicAuthPwd,
  curlText,
  busy,
  mode,
  showContinue,
  canContinue,
  isUpdate,
  continueLabel,
  diff,
  deleteUnreferenced,
  comingSoon,
  onFile,
  onContinue,
  applySync,
  resetDiff,
} = useImportWorkspace(format)

async function handleContinue() {
  const ok = await onContinue()
  if (ok) contentRef.value?.reset()
}

async function handleApply() {
  const ok = await applySync()
  if (ok) contentRef.value?.reset()
}
</script>

<style scoped>
.io-page {
  max-width: 880px;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-5);
}
.io-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ax-space-3);
}
.io-title {
  margin: 0 0 var(--ax-space-1);
  font-size: var(--ax-text-title-size);
  font-weight: 600;
  line-height: var(--ax-leading-tight);
  color: var(--ax-text);
}
.io-desc {
  margin: 0;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
}
.io-head-actions {
  display: flex;
  gap: var(--ax-space-2);
  flex: none;
}
.io-ext {
  margin-left: var(--ax-space-1);
}
.io-section-title {
  margin: 0 0 var(--ax-space-3);
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text);
}
.io-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--ax-space-2-5);
}
.io-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ax-space-2);
  padding: var(--ax-space-3) var(--ax-space-2);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg);
  cursor: pointer;
  transition:
    border-color var(--ax-transition),
    background var(--ax-transition);
}
.io-card:hover {
  border-color: var(--ax-brand);
}
.io-card.active {
  border-color: var(--ax-brand);
  background: var(--ax-tag-blue-bg);
}
.io-card-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--ax-radius-sm);
  font-size: var(--ax-font-xs);
  font-weight: 700;
  color: var(--ax-bg);
}
.tone-green {
  background: var(--ax-success);
}
.tone-orange {
  background: var(--ax-warning);
}
.tone-blue {
  background: var(--ax-info);
}
.tone-brand {
  background: var(--ax-brand);
}
.tone-red {
  background: var(--ax-danger);
}
.io-card-name {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text);
  text-align: center;
}
.io-panel {
  padding: var(--ax-space-4);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
}
.io-panel-head {
  margin-bottom: var(--ax-space-3);
}
.io-panel-head .io-section-title {
  margin-bottom: var(--ax-space-1);
}
.io-hint {
  margin: 0;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
  line-height: var(--ax-leading-compact);
}
.io-link {
  padding: 0;
  border: none;
  background: none;
  color: var(--ax-brand);
  cursor: pointer;
  font-size: inherit;
  text-decoration: underline;
}
.io-hint--update {
  margin-top: var(--ax-space-1);
  color: var(--ax-brand);
}
.io-del-opt {
  margin-top: var(--ax-space-3);
}
.io-footer {
  margin-top: var(--ax-space-4);
  display: flex;
  justify-content: flex-end;
  gap: var(--ax-space-2);
}
</style>
