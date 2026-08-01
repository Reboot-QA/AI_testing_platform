<template>
  <RunReportDetail
    v-if="detail"
    :detail="detail"
    :environment-name="environmentName"
    :running="detail.status === 'running'"
  >
    <template #actions>
      <el-button v-if="parentDetail" link type="primary" @click="emit('backToParent')">
        ← {{ backLabel }}
      </el-button>
      <el-dropdown
        v-if="showExport"
        split-button
        size="small"
        type="primary"
        :button-props="{ loading: exporting }"
        @click="emit('export', 'excel')"
        @command="(cmd: string) => emit('export', cmd)"
      >
        导出报告
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="excel">Excel (.xlsx)</el-dropdown-item>
            <el-dropdown-item command="word">Word (.docx)</el-dropdown-item>
            <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
            <el-dropdown-item command="json">JSON (.json)</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </template>

    <RunChildRunsList
      v-if="aggregateChildren && detail.children?.length"
      :children="detail.children"
      :search-placeholder="childSearchPlaceholder"
      :expand-inline="detail.target_type === 'endpoint'"
      @open-child="(row) => emit('openChild', row)"
    />
    <el-empty v-else-if="aggregateChildren" description="暂无用例" :image-size="64" />

    <RunStepGroups v-else :detail="detail" />
  </RunReportDetail>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Schemas } from '@/api/types'
import RunChildRunsList from '@/components/apifox/run/RunChildRunsList.vue'
import RunReportDetail from '@/components/apifox/run/RunReportDetail.vue'
import { RUN_LIST_SEARCH_CASE } from '@/utils/runReportList'
import RunStepGroups from '@/components/apifox/run/RunStepGroups.vue'

const props = withDefaults(
  defineProps<{
    detail: Schemas['RunOut'] | null
    parentDetail: Schemas['RunOut'] | null
    environmentName: string
    exporting: boolean
    isSuite?: boolean
    showChildren?: boolean
    childSearchPlaceholder?: string
    backLabel?: string
    showExport?: boolean
  }>(),
  {
    isSuite: false,
    showChildren: undefined,
    childSearchPlaceholder: RUN_LIST_SEARCH_CASE,
    backLabel: '返回套件报告',
    showExport: true,
  },
)

const emit = defineEmits<{
  backToParent: []
  export: [format: string]
  openChild: [row: Schemas['RunBrief']]
}>()

const aggregateChildren = computed(() => {
  if (props.showChildren != null) return props.showChildren
  if (props.isSuite) return true
  const t = props.detail?.target_type
  return t === 'suite' || t === 'endpoint'
})
</script>
