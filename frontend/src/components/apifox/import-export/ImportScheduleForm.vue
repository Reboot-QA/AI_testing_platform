<template>
  <div class="isf">
    <div class="isf-row">
      <span class="isf-lbl">名称 *</span>
      <el-input v-model="form.name" :maxlength="TITLE_MAX_LEN" placeholder="如：每日同步订单服务" />
    </div>
    <div class="isf-row">
      <span class="isf-lbl">数据 URL *</span>
      <el-input
        v-model="form.url"
        :maxlength="URL_MAX_LEN"
        placeholder="OpenAPI/Swagger/Postman 等的 URL"
      />
    </div>
    <div class="isf-row">
      <span class="isf-lbl">调度</span>
      <el-select v-model="form.schedule_type" class="isf-type">
        <el-option label="每天" value="daily" />
        <el-option label="每周" value="weekly" />
        <el-option label="按间隔" value="interval" />
        <el-option label="Cron" value="cron" />
      </el-select>
      <el-time-picker
        v-if="form.schedule_type === 'daily' || form.schedule_type === 'weekly'"
        v-model="runTime"
        format="HH:mm"
        value-format="HH:mm"
        placeholder="时间"
      />
      <el-select
        v-if="form.schedule_type === 'weekly'"
        v-model="form.week_day"
        class="isf-week"
        placeholder="星期"
      >
        <el-option v-for="(w, i) in WEEKDAYS" :key="i" :label="w" :value="i" />
      </el-select>
      <el-input-number
        v-if="form.schedule_type === 'interval'"
        v-model="form.interval_minutes"
        :min="5"
        :step="5"
      />
      <span v-if="form.schedule_type === 'interval'" class="isf-unit">分钟</span>
      <el-input
        v-if="form.schedule_type === 'cron'"
        v-model="form.cron_expr"
        :maxlength="VALUE_MAX_LEN"
        placeholder="如 0 2 * * *"
      />
    </div>
    <div class="isf-row">
      <span class="isf-lbl">鉴权</span>
      <el-input
        v-model="form.basic_auth_user"
        :maxlength="VALUE_MAX_LEN"
        class="isf-half"
        placeholder="Basic 用户名（可选）"
      />
      <el-input
        v-model="form.basic_auth_pwd"
        :maxlength="SECRET_MAX_LEN"
        class="isf-half"
        type="password"
        show-password
        placeholder="Basic 密码"
      />
    </div>
    <div class="isf-row">
      <span class="isf-lbl">Git Token</span>
      <el-input
        v-model="form.git_token"
        :maxlength="SECRET_MAX_LEN"
        type="password"
        show-password
        placeholder="私有仓库 PAT（可选）"
      />
    </div>
    <div class="isf-row isf-row--opts">
      <el-checkbox v-model="form.delete_unreferenced">同步时删除已移除且无引用的接口</el-checkbox>
      <el-checkbox v-model="form.enabled">启用</el-checkbox>
    </div>
    <div class="isf-actions">
      <el-button type="primary" :loading="busy" :disabled="!canSave" @click="submit">
        添加定时导入
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SECRET_MAX_LEN, TITLE_MAX_LEN, URL_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useRouteParamId } from '@/composables/useRouteParamId'

const emit = defineEmits<{ created: [] }>()

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const pid = useRouteParamId()
const busy = ref(false)
const runTime = ref('09:00')

function blank(): Schemas['ImportScheduleCreate'] {
  return {
    name: '',
    url: '',
    schedule_type: 'daily',
    run_time: '09:00',
    week_day: 0,
    interval_minutes: 30,
    cron_expr: '',
    basic_auth_user: '',
    basic_auth_pwd: '',
    git_token: '',
    delete_unreferenced: false,
    enabled: true,
  }
}

const form = reactive(blank())

const canSave = computed(() => !!form.name.trim() && !!form.url.trim())

async function submit() {
  busy.value = true
  try {
    await apifoxApi.createImportSchedule(pid.value, { ...form, run_time: runTime.value })
    ElMessage.success('已添加定时导入')
    Object.assign(form, blank())
    runTime.value = '09:00'
    emit('created')
  } catch {
    ElMessage.error('添加失败，请检查配置')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.isf {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.isf-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.isf-row--opts {
  gap: var(--ax-space-4);
  padding-left: 96px;
}

.isf-lbl {
  flex: none;
  width: 88px;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.isf-type {
  width: 120px;
}

.isf-week {
  width: 100px;
}

.isf-half {
  flex: 1;
}

.isf-unit {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.isf-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
