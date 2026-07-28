<template>
  <div class="db-op">
    <div class="row conn-row">
      <span class="lbl">数据库连接</span>
      <el-select
        v-model="op.connection_id"
        size="small"
        filterable
        placeholder="选择连接（当前环境内）"
        class="conn-select"
      >
        <el-option
          v-for="d in databases"
          :key="d.id"
          :label="`${d.name}（${d.host}/${d.database}）`"
          :value="d.id"
        />
      </el-select>
      <el-button link type="primary" size="small" @click="openManage">管理连接</el-button>
    </div>
    <div v-if="databases.length === 0" class="hint db-hint">
      当前环境暂无连接，点击「管理连接」新建（Host / 端口 / 库名 / 账号密码）。
    </div>

    <div v-if="op.kind === 'database_script'" class="row">
      <span class="lbl">SQL 脚本</span>
      <el-select
        v-model="op.sql_script_id"
        size="small"
        filterable
        placeholder="选择 SQL 脚本（项目资源 · SQL 脚本）"
        style="flex: 1"
      >
        <el-option v-for="s in sqlScripts" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
    </div>
    <div v-else class="field-top">
      <span class="lbl">SQL</span>
      <div class="sql-wrap">
        <CodeEditor v-model="op.sql" language="sql" height="140px" />
        <span class="hint">{{ sqlHint }}</span>
      </div>
    </div>

    <div class="field-top">
      <span class="lbl">提取变量</span>
      <div class="extracts">
        <div v-for="(ex, i) in extracts" :key="i" class="ex-row">
          <el-input
            v-model="ex.var_name"
            :maxlength="KEY_MAX_LEN"
            size="small"
            placeholder="变量名"
            style="width: 120px"
          />
          <span class="arrow">← 列</span>
          <el-input
            v-model="ex.column"
            :maxlength="KEY_MAX_LEN"
            size="small"
            placeholder="结果列名"
            style="width: 120px"
          />
          <el-select v-model="ex.scope" size="small" style="width: 96px">
            <el-option label="临时" value="temporary" />
            <el-option label="环境" value="environment" />
            <el-option label="全局" value="global" />
          </el-select>
          <el-button link type="danger" size="small" @click="extracts.splice(i, 1)">删</el-button>
        </div>
        <el-button link type="primary" size="small" @click="addExtract">
          + 提取（取查询结果首行的列）
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { KEY_MAX_LEN } from '@/constants/limits'
import { computed } from 'vue'
import type { Schemas } from '@/api/types'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import { useDatabaseManageDrawer } from '@/composables/useDatabaseManageDrawer'
import { useWorkspaceStore } from '@/stores/workspace'

const props = withDefaults(
  defineProps<{
    op: Schemas['ProcessorRow']
    databases?: Schemas['DatabaseOut'][]
    sqlScripts?: Schemas['SqlScriptBrief'][]
  }>(),
  { databases: () => [], sqlScripts: () => [] },
)

// SQL 支持 {{变量}} 插值——用常量承载，避免模板里嵌套 mustache 触发解析错误
const sqlHint = '支持 {{变量}} 插值；按当前环境执行。'

// op.db_extracts 后端默认 []，旧数据可能缺失：只读兜底，不在 computed 里改 prop
const extracts = computed<Schemas['DbExtractRow'][]>(() => props.op.db_extracts ?? [])

function addExtract() {
  if (!props.op.db_extracts) props.op.db_extracts = []
  props.op.db_extracts.push({ var_name: '', column: '', scope: 'temporary' })
}

const { open: openDatabaseManage } = useDatabaseManageDrawer()
const workspace = useWorkspaceStore()

function openManage() {
  openDatabaseManage(workspace.currentEnvironmentId, { create: props.databases.length === 0 })
}
</script>

<style scoped>
.db-op {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.conn-row {
  flex-wrap: wrap;
}

.conn-select {
  flex: 1;
  min-width: 160px;
}

.field-top {
  display: flex;
  gap: var(--ax-space-2);
}

.lbl {
  flex-shrink: 0;
  width: 72px;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
  padding-top: var(--ax-space-1);
}

.sql-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-1);
}

.extracts {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-1-5);
}

.ex-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.arrow {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.hint {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-placeholder);
}

.db-hint {
  padding-left: 72px;
}
</style>
