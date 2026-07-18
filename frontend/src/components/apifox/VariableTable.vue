<template>
  <div>
    <el-table :data="variables" size="small" border>
      <el-table-column label="变量名" min-width="140">
        <template #default="{ row }">
          <el-input
            v-model="row.key"
            size="small"
            @change="$emit('update', row.id, { key: row.key })"
          />
        </template>
      </el-table-column>
      <el-table-column label="远程值（团队共享）" min-width="160">
        <template #default="{ row }">
          <VarInput
            v-model="row.remote_value"
            placeholder="团队共享"
            @change="$emit('update', row.id, { remote_value: row.remote_value })"
          />
        </template>
      </el-table-column>
      <el-table-column label="我的本地值（个人覆盖）" min-width="160">
        <template #default="{ row }">
          <VarInput
            v-model="row.local_value"
            placeholder="留空=用远程值"
            @change="$emit('set-local', row.id, row.local_value === '' ? null : row.local_value)"
          />
        </template>
      </el-table-column>
      <el-table-column label="有效值" min-width="120">
        <template #default="{ row }">
          <span class="eff">{{ row.effective_value ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="密文" width="70" align="center">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_secret"
            size="small"
            @change="$emit('update', row.id, { is_secret: row.is_secret })"
          />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="70" align="center">
        <template #default="{ row }">
          <el-switch
            v-model="row.enabled"
            size="small"
            @change="$emit('update', row.id, { enabled: row.enabled })"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" align="center">
        <template #default="{ row }">
          <el-button link type="danger" size="small" @click="$emit('delete', row.id)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="add-row">
      <el-input v-model="newKey" size="small" placeholder="新变量名" style="width: 160px" />
      <el-input v-model="newVal" size="small" placeholder="远程值" style="width: 200px" />
      <el-button size="small" type="primary" :disabled="!newKey.trim()" @click="addVar"
        >+ 新增变量</el-button
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Schemas } from '@/api/types'
import VarInput from '@/components/apifox/common/VarInput.vue'

type VariableOut = Schemas['VariableOut']
type VariableCreate = Schemas['VariableCreate']

withDefaults(defineProps<{ variables?: VariableOut[] }>(), {
  variables: () => [],
})
const emit = defineEmits<{
  create: [payload: VariableCreate]
  update: [id: number, payload: Partial<VariableOut>]
  delete: [id: number]
  'set-local': [id: number, value: string | null]
}>()

const newKey = ref('')
const newVal = ref('')

function addVar() {
  emit('create', {
    key: newKey.value.trim(),
    remote_value: newVal.value,
    is_secret: false,
    enabled: true,
  })
  newKey.value = ''
  newVal.value = ''
}
</script>

<style scoped>
.eff {
  color: var(--ax-success);
  font-size: 13px;
}

.add-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
