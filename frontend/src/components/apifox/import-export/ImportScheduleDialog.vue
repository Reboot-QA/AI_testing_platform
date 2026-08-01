<template>
  <el-dialog
    :model-value="modelValue"
    title="定时导入"
    width="760px"
    @update:model-value="emit('update:modelValue', $event)"
    @open="load"
  >
    <div class="isd">
      <section v-if="schedules.length" class="isd-list">
        <div v-for="s in schedules" :key="s.id" class="isd-item">
          <div class="isd-main">
            <div class="isd-name">
              {{ s.name }}
              <el-tag v-if="!s.enabled" size="small" type="info">已停用</el-tag>
              <el-tag
                v-if="s.last_run_status"
                size="small"
                :type="s.last_run_status === 'success' ? 'success' : 'danger'"
              >
                {{ s.last_run_status === 'success' ? '上次成功' : '上次失败' }}
              </el-tag>
            </div>
            <div class="isd-sub">{{ s.schedule_desc }} · {{ s.url }}</div>
            <ImportManifestView v-if="s.last_run_manifest" :manifest="s.last_run_manifest" />
            <div v-else-if="s.last_run_detail" class="isd-detail">{{ s.last_run_detail }}</div>
          </div>
          <div class="isd-ops">
            <el-switch
              :model-value="s.enabled"
              size="small"
              @update:model-value="toggle(s, $event === true)"
            />
            <el-button size="small" :loading="runningId === s.id" @click="runNow(s)">
              立即执行
            </el-button>
            <el-button size="small" type="danger" text @click="remove(s)">删除</el-button>
          </div>
        </div>
      </section>
      <el-empty v-else description="暂无定时导入任务" :image-size="80" />

      <section class="isd-form">
        <h4 class="isd-form-title">新增定时导入</h4>
        <ImportScheduleForm @created="load" />
      </section>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useRouteParamId } from '@/composables/useRouteParamId'
import ImportScheduleForm from '@/components/apifox/import-export/ImportScheduleForm.vue'
import ImportManifestView from '@/components/apifox/import-export/ImportManifestView.vue'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const pid = useRouteParamId()
const schedules = ref<Schemas['ImportScheduleOut'][]>([])
const runningId = ref<number | null>(null)

async function load() {
  try {
    schedules.value = await apifoxApi.listImportSchedules(pid.value)
  } catch {
    /* 忽略 */
  }
}

async function toggle(s: Schemas['ImportScheduleOut'], enabled: boolean) {
  try {
    await apifoxApi.updateImportSchedule(s.id, { enabled })
    await load()
  } catch {
    ElMessage.error('更新失败')
  }
}

async function runNow(s: Schemas['ImportScheduleOut']) {
  runningId.value = s.id
  try {
    const updated = await apifoxApi.runImportScheduleNow(s.id)
    ElMessage[updated.last_run_status === 'success' ? 'success' : 'warning'](
      updated.last_run_detail || '已执行',
    )
    await load()
  } catch {
    ElMessage.error('执行失败')
  } finally {
    runningId.value = null
  }
}

async function remove(s: Schemas['ImportScheduleOut']) {
  try {
    await ElMessageBox.confirm(`确定删除定时导入「${s.name}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await apifoxApi.deleteImportSchedule(s.id)
    await load()
  } catch {
    ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.isd {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-4);
}

.isd-list {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
  max-height: 280px;
  overflow-y: auto;
}

.isd-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-3);
  padding: var(--ax-space-3);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
}

.isd-main {
  min-width: 0;
  flex: 1;
}

.isd-name {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  font-size: var(--ax-text-body-size);
  color: var(--ax-text);
}

.isd-sub,
.isd-detail {
  margin-top: var(--ax-space-1);
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.isd-detail {
  color: var(--ax-text-placeholder);
}

.isd-ops {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  flex: none;
}

.isd-form {
  border-top: 1px solid var(--ax-border);
  padding-top: var(--ax-space-4);
}

.isd-form-title {
  margin: 0 0 var(--ax-space-3);
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text);
}
</style>
