<template>
  <div>
    <div class="toolbar">
      <span class="title">测试报告</span>
      <el-button size="small" @click="loadRuns">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <el-table :data="runs" size="small" border @row-click="openDetail">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="目标" min-width="180">
        <template #default="{ row }">
          <el-tag size="small" :type="targetTag(row.target_type)">
            {{ targetTypeLabel(row.target_type) }}
          </el-tag>
          {{ row.target_name }}
        </template>
      </el-table-column>
      <el-table-column label="环境" width="120">
        <template #default="{ row }">{{ envName(row.environment_id) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="通过率" width="110">
        <template #default="{ row }">
          {{ row.pass_rate != null ? row.pass_rate + '%' : '-' }}
          <span class="sub">({{ row.passed_count }}/{{ row.total_count }})</span>
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="90">
        <template #default="{ row }">
          {{ row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="triggered_by" label="触发人" width="100" />
      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
      </el-table-column>
    </el-table>
    <el-empty v-if="runs.length === 0" description="暂无运行记录（在自动化测试里运行用例/场景）" />

    <el-drawer
      v-model="drawerVisible"
      :title="`运行 #${detail?.id} · ${detail?.target_name || ''}`"
      size="60%"
    >
      <template v-if="detail">
        <div class="drawer-actions">
          <el-button v-if="parentDetail" link type="primary" class="back-btn" @click="backToParent">
            ← 返回套件报告
          </el-button>
          <el-dropdown
            split-button
            size="small"
            type="primary"
            :button-props="{ loading: exporting }"
            @click="doExport('excel')"
            @command="doExport"
          >
            导出 Excel
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="excel">Excel (.xlsx)</el-dropdown-item>
                <el-dropdown-item command="word">Word (.docx)</el-dropdown-item>
                <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
                <el-dropdown-item command="json">JSON (.json)</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-descriptions :column="4" size="small" border class="summary">
          <el-descriptions-item label="状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
          <el-descriptions-item label="通过率">{{ detail.pass_rate }}%</el-descriptions-item>
          <el-descriptions-item :label="isSuite ? '通过/失败(项)' : '通过/失败'"
            >{{ detail.passed_count }}/{{ detail.failed_count }}</el-descriptions-item
          >
          <el-descriptions-item label="耗时"
            >{{ Math.round(detail.duration_ms || 0) }}ms</el-descriptions-item
          >
        </el-descriptions>

        <el-table v-if="isSuite" :data="detail.children" size="small" border @row-click="openChild">
          <el-table-column label="套件项" min-width="200">
            <template #default="{ row }">
              <el-tag size="small" :type="targetTag(row.target_type)">{{
                targetTypeLabel(row.target_type)
              }}</el-tag>
              {{ row.target_name }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="statusTag(row.status)">{{
                statusLabel(row.status)
              }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="通过率" width="110">
            <template #default="{ row }">
              {{ row.pass_rate != null ? row.pass_rate + '%' : '-' }}
              <span class="sub">({{ row.passed_count }}/{{ row.total_count }})</span>
            </template>
          </el-table-column>
          <el-table-column label="耗时" width="90">
            <template #default="{ row }">{{
              row.duration_ms != null ? Math.round(row.duration_ms) + 'ms' : '-'
            }}</template>
          </el-table-column>
        </el-table>

        <template v-else>
          <div v-for="(g, gi) in stepGroups" :key="gi" class="step-group">
            <div v-if="g.label" class="group-title">{{ g.label }}</div>
            <el-collapse>
              <el-collapse-item v-for="s in g.steps" :key="s.id" :name="s.id">
                <template #title>
                  <el-icon v-if="s.status === 'passed'" color="var(--ax-success)"
                    ><CircleCheck
                  /></el-icon>
                  <el-icon v-else color="var(--ax-danger)"><CircleClose /></el-icon>
                  <span class="step-title">
                    {{ s.case_name }}
                    <span v-if="s.method" class="sub"
                      ><MethodTag :method="s.method" /> {{ s.url }}</span
                    >
                    <span v-if="s.response_status" class="sub"
                      >{{ s.response_status }} · {{ Math.round(s.duration_ms || 0) }}ms</span
                    >
                  </span>
                </template>

                <div v-if="s.error_message" class="err">{{ s.error_message }}</div>

                <el-alert
                  v-for="(w, i) in s.warnings || []"
                  :key="'w' + i"
                  :title="w"
                  type="warning"
                  :closable="false"
                  show-icon
                  class="step-warn"
                />

                <template v-if="s.url">
                  <div class="sec-title">实际请求</div>
                  <ActualRequestView
                    :method="s.method"
                    :url="s.url"
                    :headers="s.request_headers"
                    :body="s.request_body"
                  />
                </template>

                <template v-if="s.assertion_results.length">
                  <div class="sec-title">断言</div>
                  <div v-for="(a, i) in s.assertion_results" :key="'a' + i" class="line">
                    <el-tag size="small" :type="a.passed ? 'success' : 'danger'">{{
                      a.passed ? '过' : '败'
                    }}</el-tag>
                    {{ a.message }}
                  </div>
                </template>

                <template v-if="s.contract_result">
                  <div class="sec-title">契约校验</div>
                  <div class="line">
                    <el-tag size="small" :type="s.contract_result.passed ? 'success' : 'danger'">
                      {{ s.contract_result.passed ? '符合' : '不符' }}
                    </el-tag>
                    {{ s.contract_result.schema_name }} · {{ s.contract_result.message }}
                  </div>
                  <div
                    v-for="(err, i) in s.contract_result.errors"
                    :key="'c' + i"
                    class="line mono"
                  >
                    {{ err }}
                  </div>
                </template>

                <template v-if="s.extract_results.length">
                  <div class="sec-title">提取</div>
                  <div v-for="(e, i) in s.extract_results" :key="'e' + i" class="line">
                    <el-tag size="small" :type="e.passed ? 'success' : 'danger'">{{
                      e.passed ? '成' : '败'
                    }}</el-tag>
                    {{ e.var_name }} = {{ e.value || e.message }}（{{ e.scope }}）
                  </div>
                </template>

                <template v-if="s.script_logs.length">
                  <div class="sec-title">脚本日志</div>
                  <div v-for="(l, i) in s.script_logs" :key="'l' + i" class="line mono">
                    {{ l }}
                  </div>
                </template>

                <template v-if="s.response_body">
                  <div class="sec-title">响应体</div>
                  <div class="body-box">
                    <JsonView :data="s.response_body" :deep="3" />
                  </div>
                </template>
              </el-collapse-item>
            </el-collapse>
          </div>
        </template>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import JsonView from '@/components/apifox/common/JsonView.vue'
import ActualRequestView from '@/components/apifox/ActualRequestView.vue'
import { iterationLabel } from '@/utils/iterationLabel'
import { formatTime, statusLabel, statusTag } from '@/utils/runFormat'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()

const envName = (id) =>
  id == null ? '-' : store.environments.find((e) => e.id === id)?.name || '-'

const runs = ref([])
const detail = ref(null)
const parentDetail = ref(null)
const drawerVisible = ref(false)
const exporting = ref(false)

const isSuite = computed(() => detail.value?.target_type === 'suite')

const EXPORT_EXT = { excel: 'xlsx', word: 'docx', pdf: 'pdf', json: 'json' }

async function doExport(format) {
  if (!detail.value) return
  exporting.value = true
  try {
    // 拦截器返回 blob；文件名前端拼（响应头拿不到），交由浏览器下载
    const blob = await apifoxApi.exportRun(detail.value.id, format)
    const name = `测试报告_${detail.value.target_name || 'report'}_${detail.value.id}.${EXPORT_EXT[format] || 'bin'}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // 全局响应拦截器已提示错误，这里仅避免未捕获 rejection
  } finally {
    exporting.value = false
  }
}

// 数据驱动/循环多轮：按轮次分组展示步骤；单轮为一组无标题（零视觉变化）
const stepGroups = computed(() => {
  const steps = detail.value?.steps || []
  const iters = detail.value?.iterations || []
  if (iters.length <= 1) return [{ label: '', steps }]
  return iters.map((data, i) => ({
    label: iterationLabel(i, data),
    steps: steps.filter((s) => s.iteration === i),
  }))
})

const targetTypeLabel = (t) => (t === 'scenario' ? '场景' : t === 'suite' ? '套件' : '用例')
const targetTag = (t) => (t === 'scenario' ? 'info' : t === 'suite' ? 'primary' : 'success')

async function loadRuns() {
  runs.value = await apifoxApi.listRuns(pid.value)
}

async function openDetail(row) {
  parentDetail.value = null
  detail.value = await apifoxApi.getRun(row.id)
  drawerVisible.value = true
}

async function openChild(row) {
  parentDetail.value = detail.value
  detail.value = await apifoxApi.getRun(row.id)
}

function backToParent() {
  detail.value = parentDetail.value
  parentDetail.value = null
}

onMounted(async () => {
  await loadRuns()
  // 从运行进度「查看测试报告」跳转而来：自动打开对应 run 的报告
  const runId = route.query.run
  if (runId) await openDetail({ id: Number(runId) })
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.title {
  font-weight: 600;
  color: var(--ax-brand);
}

.sub {
  color: var(--ax-text-placeholder);
  font-size: 12px;
  margin-left: 6px;
}

.back-btn {
  margin-bottom: 10px;
}

.drawer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.summary {
  margin-bottom: 14px;
}

.step-title {
  margin-left: 6px;
}

.step-group {
  margin-bottom: 10px;
}

.group-title {
  font-weight: 600;
  color: var(--ax-brand);
  font-size: 13px;
  margin: 6px 0 4px;
  padding: 4px 8px;
  background: var(--ax-bg-subtle);
  border-radius: 4px;
}

.sec-title {
  font-weight: 600;
  color: var(--ax-text-tertiary);
  margin: 10px 0 4px;
  font-size: 13px;
}

.line {
  font-size: 13px;
  padding: 2px 0;
}

.mono {
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text-secondary);
}

.err {
  color: var(--ax-danger);
  font-size: 13px;
  margin-bottom: 6px;
}

.step-warn {
  margin-bottom: 6px;
}

.body-box {
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  padding: 8px;
  font-size: 12px;
  max-height: 320px;
  overflow: auto;
}
</style>
