<template>
  <div class="diff-preview">
    <div class="summary">
      <el-tag type="success" effect="plain">新增 {{ diff.added.length }}</el-tag>
      <el-tag type="warning" effect="plain">变更 {{ diff.changed.length }}</el-tag>
      <el-tag type="danger" effect="plain">移除 {{ diff.removed.length }}</el-tag>
      <el-tag v-if="diff.schemas_added" type="info" effect="plain">
        新增数据模型 {{ diff.schemas_added }}
      </el-tag>
    </div>

    <el-collapse v-model="active" class="sections">
      <el-collapse-item v-if="diff.added.length" name="added">
        <template #title
          ><span class="sec-title added">新增接口 ({{ diff.added.length }})</span></template
        >
        <div v-for="e in diff.added" :key="`a-${e.method}-${e.path}`" class="row">
          <span class="method">{{ e.method }}</span>
          <span class="path">{{ e.path }}</span>
          <span class="ep-name">{{ e.name }}</span>
        </div>
      </el-collapse-item>

      <el-collapse-item v-if="diff.changed.length" name="changed">
        <template #title
          ><span class="sec-title changed">变更接口 ({{ diff.changed.length }})</span></template
        >
        <div v-for="e in diff.changed" :key="`c-${e.endpoint_id}`" class="row col">
          <div class="row">
            <span class="method">{{ e.method }}</span>
            <span class="path">{{ e.path }}</span>
            <el-tag v-for="c in e.changes" :key="c" size="small" type="warning" effect="plain">
              {{ c }}
            </el-tag>
          </div>
          <div v-if="e.affected_cases.length" class="affected">
            引用该接口的用例（不会自动改动，请自查）：{{ e.affected_cases.join('、') }}
          </div>
        </div>
      </el-collapse-item>

      <el-collapse-item v-if="diff.removed.length" name="removed">
        <template #title
          ><span class="sec-title removed">移除接口 ({{ diff.removed.length }})</span></template
        >
        <div v-for="e in diff.removed" :key="`r-${e.endpoint_id}`" class="row col">
          <div class="row">
            <span class="method">{{ e.method }}</span>
            <span class="path">{{ e.path }}</span>
            <el-tag v-if="e.referenced" size="small" type="danger">被引用，不会删除</el-tag>
            <el-tag v-else size="small" type="info" effect="plain">
              无引用{{ e.case_count ? `（含 ${e.case_count} 个用例）` : '' }}
            </el-tag>
          </div>
          <div v-for="cref in e.references" :key="cref.case_id" class="ref-warn">
            用例「{{ cref.case_name }}」被
            <template v-if="cref.scenarios.length">场景 {{ cref.scenarios.join('、') }}</template>
            <template v-if="cref.scenarios.length && cref.suites.length"> 和 </template>
            <template v-if="cref.suites.length">套件 {{ cref.suites.join('、') }}</template>
            引用，请先处理引用后再手动删除。
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <el-empty v-if="isEmpty" description="无差异，接口已与该 Swagger 一致" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Schemas } from '@/api/types'

type ImportDiffView = Schemas['ImportDiffOut'] & {
  added: NonNullable<Schemas['ImportDiffOut']['added']>
  changed: NonNullable<Schemas['ImportDiffOut']['changed']>
  removed: NonNullable<Schemas['ImportDiffOut']['removed']>
}

export type { ImportDiffView }

const props = defineProps<{ diff: ImportDiffView }>()

const active = ref(['added', 'changed', 'removed'])

const isEmpty = computed(
  () => !props.diff.added.length && !props.diff.changed.length && !props.diff.removed.length,
)
</script>

<style scoped>
.summary {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.sec-title {
  font-weight: 600;
}
.sec-title.added {
  color: var(--ax-success, #67c23a);
}
.sec-title.changed {
  color: var(--ax-warning, #e6a23c);
}
.sec-title.removed {
  color: var(--ax-danger, #f56c6c);
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  flex-wrap: wrap;
}
.row.col {
  flex-direction: column;
  align-items: stretch;
  border-bottom: 1px solid var(--ax-border-lighter, #ebeef5);
  padding: 6px 0;
}

.method {
  font-family: monospace;
  font-weight: 600;
  min-width: 52px;
}
.path {
  font-family: monospace;
  color: var(--ax-text-regular, #606266);
}
.ep-name {
  color: var(--ax-text-secondary, #909399);
  font-size: 12px;
}

.affected,
.ref-warn {
  font-size: 12px;
  padding-left: 60px;
}
.affected {
  color: var(--ax-text-secondary, #909399);
}
.ref-warn {
  color: var(--ax-danger, #f56c6c);
}
</style>
