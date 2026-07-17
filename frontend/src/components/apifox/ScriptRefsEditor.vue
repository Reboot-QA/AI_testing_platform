<template>
  <div>
    <div v-for="(row, i) in rows" :key="i" class="s-row">
      <el-checkbox v-model="row.enabled" />
      <el-tag size="small" :type="row.script_lang === 'python' ? 'warning' : 'success'">
        {{ row.script_lang === 'python' ? 'Py' : 'JS' }}
      </el-tag>
      <span class="s-name">{{ row.script_name || `脚本#${row.script_id}` }}</span>
      <el-button link size="small" :disabled="i === 0" @click="move(i, -1)">↑</el-button>
      <el-button link size="small" :disabled="i === rows.length - 1" @click="move(i, 1)"
        >↓</el-button
      >
      <el-button link type="danger" size="small" @click="rows.splice(i, 1)">移除</el-button>
    </div>

    <div class="add-row">
      <el-select
        v-model="pickedId"
        size="small"
        placeholder="从脚本库选择"
        style="width: 220px"
        filterable
      >
        <el-option
          v-for="s in availableScripts"
          :key="s.id"
          :label="`${s.name} (${s.lang === 'python' ? 'Py' : 'JS'})`"
          :value="s.id"
        />
      </el-select>
      <el-button size="small" type="primary" :disabled="!pickedId" @click="addRef"
        >+ 添加</el-button
      >
      <span class="tip">脚本属于项目脚本库（项目设置里维护），此处仅引用</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Schemas } from '@/api/types'

type CaseScriptOut = Schemas['CaseScriptOut']
type ScriptBrief = Schemas['ScriptBrief']

const props = withDefaults(
  defineProps<{
    rows: CaseScriptOut[]
    scripts?: ScriptBrief[]
  }>(),
  {
    scripts: () => [],
  },
)

const pickedId = ref<number | null>(null)

const availableScripts = computed(() =>
  props.scripts.filter((s) => !props.rows.some((r) => r.script_id === s.id)),
)

function addRef() {
  const s = props.scripts.find((x) => x.id === pickedId.value)
  if (!s) return
  props.rows.push({ script_id: s.id, enabled: true, script_name: s.name, script_lang: s.lang })
  pickedId.value = null
}

function move(i: number, delta: number) {
  const j = i + delta
  const [row] = props.rows.splice(i, 1)
  props.rows.splice(j, 0, row)
}
</script>

<style scoped>
.s-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.s-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.add-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.tip {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>
