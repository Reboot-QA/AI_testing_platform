<template>
  <div class="global-params">
    <div class="var-title">全局参数（项目级，执行时自动附加到请求 · header/query/cookie）</div>
    <el-table :data="params" size="small" border>
      <el-table-column label="位置" width="120">
        <template #default="{ row }">
          <el-select v-model="row.location" size="small" @change="updateParam(row)">
            <el-option v-for="l in LOCATIONS" :key="l" :label="l" :value="l" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="参数名" min-width="140">
        <template #default="{ row }">
          <el-input v-model="row.key" size="small" @change="updateParam(row)" />
        </template>
      </el-table-column>
      <el-table-column label="值" min-width="180">
        <template #default="{ row }">
          <el-input v-model="row.value" size="small" @change="updateParam(row)" />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="70" align="center">
        <template #default="{ row }">
          <el-switch v-model="row.enabled" size="small" @change="updateParam(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" align="center">
        <template #default="{ row }">
          <el-button link type="danger" size="small" @click="delParam(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="add-row">
      <el-select v-model="newParam.location" size="small" style="width: 110px">
        <el-option v-for="l in LOCATIONS" :key="l" :label="l" :value="l" />
      </el-select>
      <el-input v-model="newParam.key" size="small" placeholder="参数名" style="width: 160px" />
      <el-input v-model="newParam.value" size="small" placeholder="值" style="width: 200px" />
      <el-button size="small" type="primary" :disabled="!newParam.key.trim()" @click="addParam">
        + 新增参数
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'

const props = defineProps<{ projectId: Id }>()

const LOCATIONS = ['header', 'query', 'cookie', 'body']
const params = ref<Schemas['GlobalParamOut'][]>([])
const newParam = reactive({ location: 'header', key: '', value: '' })

async function loadParams() {
  params.value = await apifoxApi.listGlobalParams(props.projectId)
}

async function addParam() {
  await apifoxApi.createGlobalParam(props.projectId, {
    location: newParam.location,
    key: newParam.key.trim(),
    value: newParam.value,
    enabled: true,
  })
  newParam.key = ''
  newParam.value = ''
  await loadParams()
}

async function updateParam(row: Schemas['GlobalParamOut']) {
  await apifoxApi.updateGlobalParam(row.id, {
    location: row.location,
    key: row.key,
    value: row.value,
    enabled: row.enabled,
  })
  await loadParams()
}

async function delParam(row: Schemas['GlobalParamOut']) {
  await apifoxApi.deleteGlobalParam(row.id)
  await loadParams()
}

onMounted(loadParams)
</script>

<style scoped>
.var-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 12px;
}

.add-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
