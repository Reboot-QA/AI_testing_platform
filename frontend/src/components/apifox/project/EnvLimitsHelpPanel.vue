<template>
  <div class="limits-help">
    <div class="var-title">输入长度限制说明</div>
    <p class="intro">
      以下上限来自前端
      <code>constants/limits.ts</code
      >，输入框会按此截断；超限无法继续输入。数值随常量变更自动同步，供联调 / 验收对照。
    </p>

    <section class="group">
      <div class="group-title">与后端契约对齐（超限会 422）</div>
      <el-table :data="contractRows" size="small" border>
        <el-table-column prop="name" label="类别" width="120" />
        <el-table-column prop="limit" label="上限" width="90" align="right" />
        <el-table-column prop="scope" label="本页涉及" min-width="220" />
      </el-table>
    </section>

    <section class="group">
      <div class="group-title">前端防护（后端多为 Text / 无长度校验）</div>
      <el-table :data="guardRows" size="small" border>
        <el-table-column prop="name" label="类别" width="120" />
        <el-table-column prop="limit" label="上限" width="90" align="right" />
        <el-table-column prop="scope" label="本页涉及" min-width="220" />
      </el-table>
    </section>

    <p class="note">
      说明：变量名前端拦 {{ KEY_MAX_LEN }}，后端 schema / 库允许 200；变量值前端拦
      {{ VALUE_MAX_LEN }}，库为 Text、接口未做 max_length。
    </p>
  </div>
</template>

<script setup lang="ts">
import {
  DESC_MAX_LEN,
  KEY_MAX_LEN,
  LONG_TEXT_MAX_LEN,
  PASTE_MAX_LEN,
  SEARCH_MAX_LEN,
  SECRET_MAX_LEN,
  TITLE_MAX_LEN,
  URL_MAX_LEN,
  VALUE_MAX_LEN,
} from '@/constants/limits'

interface LimitRow {
  name: string
  limit: string
  scope: string
}

const contractRows: LimitRow[] = [
  {
    name: '标题 / 名称',
    limit: String(TITLE_MAX_LEN),
    scope: '环境名、命名服务名（TITLE_MAX_LEN）',
  },
  {
    name: '描述',
    limit: String(DESC_MAX_LEN),
    scope: '本页较少用；项目描述等（DESC_MAX_LEN）',
  },
]

const guardRows: LimitRow[] = [
  {
    name: 'URL',
    limit: String(URL_MAX_LEN),
    scope: '默认前置 URL、命名服务 URL（URL_MAX_LEN）',
  },
  {
    name: '键名',
    limit: String(KEY_MAX_LEN),
    scope: '环境/全局变量名、全局参数名（KEY_MAX_LEN）',
  },
  {
    name: '短值',
    limit: String(VALUE_MAX_LEN),
    scope: '变量远程值 / 本地值、参数值（VALUE_MAX_LEN）',
  },
  {
    name: '凭据',
    limit: String(SECRET_MAX_LEN),
    scope: '数据库连接密码等（SECRET_MAX_LEN）',
  },
  {
    name: '搜索关键字',
    limit: String(SEARCH_MAX_LEN),
    scope: '全站搜索框（SEARCH_MAX_LEN）',
  },
  {
    name: '长文本',
    limit: String(LONG_TEXT_MAX_LEN),
    scope: '用例步骤、备注等（LONG_TEXT_MAX_LEN）',
  },
  {
    name: '粘贴大文本',
    limit: String(PASTE_MAX_LEN),
    scope: 'cURL / 需求正文 / AI 输入等（PASTE_MAX_LEN）',
  },
]
</script>

<style scoped>
.limits-help {
  max-width: 720px;
}

.var-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: var(--ax-space-3);
}

.intro,
.note {
  margin: 0 0 var(--ax-space-4);
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
  line-height: var(--ax-leading-compact);
}

.intro code {
  font-size: var(--ax-font-xs);
  color: var(--ax-text);
}

.group {
  margin-bottom: var(--ax-drawer-section-gap);
}

.group-title {
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text);
  margin-bottom: var(--ax-space-2);
}

.note {
  margin-bottom: 0;
  padding: var(--ax-space-2) var(--ax-space-3);
  background: var(--ax-bg-subtle);
  border-radius: var(--ax-radius);
}
</style>
