# 前端 UI 设计与优化规范

> 适用范围：AI 测试平台前端（Vue 3 + Element Plus + Tailwind v4 + shadcn-vue）
> 目的：统一页面观感、表格显示、组件用法，降低协作成本，让新页面开箱即符合品牌
> 版本：v1.0（2026-07）

---

## 0. TL;DR（最少要记住的 6 条）

1. **颜色/圆角/间距/阴影一律用 `--ax-*` design token，禁止硬编码 hex。**
2. **列表/CRUD 页统一用 `<PageCard>` 容器**，工具栏进 `#toolbar` 槽。
3. **要表格填满一屏、内部滚动**：`<PageCard fill>` + 表格外包 `.table-fill` + `el-table height="100%"`。
4. **Element Plus 管重组件**（表格/表单/弹窗/树），**Tailwind + shadcn 管布局与轻组件**（卡片/磁贴/按钮/门面页）。
5. **Tailwind 工具类不放进 `@layer`**（本项目有全局 `* {margin:0;padding:0}` 重置，放进 layer 会被它盖掉）。
6. **页面标题由顶栏统一展示，页面内不再重复大标题。**

---

## 1. 设计体系总览

平台采用**双轨并存**：

| 轨道 | 负责 | 何时用 |
| --- | --- | --- |
| **Element Plus**（已主题化） | 表格、表单、弹窗、下拉、树、分页等重交互组件 | 存量页面、所有数据密集型 CRUD |
| **Tailwind v4 + shadcn-vue** | 页面布局、卡片、磁贴、按钮、门面页（登录/仪表盘）、新页面高观感区块 | 新页面、需要精细排版处 |

两轨**共享同一套 design token**（`src/styles/tokens.css` 的 `--ax-*`），所以观感一致。

关键文件：
- `src/styles/tokens.css` —— design token 单一来源（`--ax-*`）
- `src/styles/element-theme.css` —— 把 token 映射到 Element Plus 的 `--el-*` 变量
- `src/styles/tailwind.css` —— Tailwind 接入 + shadcn 令牌，全部对齐 `--ax-*`
- `src/components/PageCard.vue` —— 通用页面容器
- `src/components/ui/` —— shadcn-vue 组件（Button、Card…）

---

## 2. Design Token 速查（`--ax-*`）

**改配色/尺寸只改 `tokens.css` 一处，全站生效。业务代码只引用 token，不写死值。**

### 品牌 / 中性 / 文字
```
--ax-brand: #1a365d          品牌主色（藏青）
--ax-brand-hover / -active / -subtle   品牌悬停/按下/极浅底
--ax-text: #1e293b           主文字
--ax-text-secondary: #64748b 次要文字（说明/副标题）
--ax-text-tertiary: #475569  常规正文
--ax-text-placeholder / -disabled
--ax-border: #e2e8f0         边框
--ax-bg / -bg-subtle / -bg-hover / -bg-active   背景层级
```

### 语义状态色
```
--ax-success #16a34a   --ax-warning #d97706   --ax-danger #dc2626   --ax-info #64748b
```

### 圆角 / 间距 / 字号 / 阴影
```
圆角  --ax-radius-sm 4  · --ax-radius 6  · --ax-radius-lg 10  · --ax-radius-xl 14
间距  --ax-gap-xs 4 · --ax-gap 8 · --ax-gap-sm 12 · --ax-gap-lg 16 · --ax-gap-xl 24 · --ax-gap-2xl 32
字号  --ax-font-xs 12 · -sm 13 · (base)14 · -md 16 · -lg 18 · -xl 22 · -2xl 28
阴影  --ax-shadow-sm（卡片）· --ax-shadow（浮层）· --ax-shadow-lg（弹窗/强调）
过渡  --ax-transition: 0.2s ease
```

> Tailwind 侧：token 已注入为工具类（`rounded-lg`、`bg-card`、`text-muted-foreground`、`border-border` 等），直接用即可，无需写 `var(--ax-*)`。

---

## 3. 页面布局标准

### 3.1 页面容器：`<PageCard>`

所有列表/CRUD/内容页用 `PageCard` 承载，得到统一的白卡片（圆角 + 细阴影 + 内边距）+ 工具栏区。

```vue
<template>
  <PageCard>
    <template #toolbar>
      <el-select v-model="projectId" ... />        <!-- 筛选项 -->
      <el-input v-model="keyword" ... />
      <el-button type="primary" @click="openDialog()">新建</el-button>
    </template>

    <el-table :data="rows" stripe border> ... </el-table>
    <div class="pagination-bar"><el-pagination ... /></div>

    <!-- 弹窗/抽屉放这里即可（会 teleport 到 body，不占布局） -->
    <el-dialog v-model="visible"> ... </el-dialog>
  </PageCard>
</template>

<script setup>
import PageCard from '@/components/PageCard.vue'
</script>
```

约定：
- **不在页面里再写大标题**——顶栏（MainLayout）已按路由展示标题。
- 顶部提示 Alert 类横幅放 `PageCard` **外面**作为兄弟节点（见 `DepartmentManagement.vue`）。
- 已经用 `el-card` 自带 header 的页面（如权限管理、测试执行）**不要再套 PageCard**，避免双层卡；若为纯平，去掉 `shadow="never"` 即可获得统一细阴影。

### 3.2 页面根节点高度约定

`el-main` 由布局提供确定高度（flex 链）。默认页面内容自然增高、超出时 `el-main` 整体滚动——适合仪表盘、表单页。
若要**一屏内固定、局部滚动**，见下节 `fill` 模式。

---

## 4. 表格显示标准 ⭐

### 4.1 基础约定
- 一律 `stripe`（斑马纹）+ `border`。
- 操作列 `fixed="right"`，宽度按钮数定（1 个 ~90px，2 个 ~160px）。
- 长文本列加 `show-overflow-tooltip`。
- 状态/类型用 `el-tag` + 语义色，不用纯文字。
- 空值显示 `-`，计数为 0 显示灰色 `0`。

### 4.2 撑满剩余高度、内部滚动（推荐用于主数据表）

**目标**：工具栏、表头、分页固定，只有表格数据区滚动，整页不出现纵向滚动条。

**做法**（示范见 `views/Requirements.vue`）：

```vue
<PageCard fill>
  <template #toolbar> ... </template>

  <div class="table-fill">
    <el-table :data="rows" stripe border height="100%"> ... </el-table>
  </div>

  <div class="pagination-bar"><el-pagination ... /></div>
</PageCard>
```

```css
/* 页面 scoped 样式 */
.table-fill {
  flex: 1;
  min-height: 0;   /* 关键：让 el-table 内部滚动生效 */
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  flex: none;
}
```

原理：`PageCard fill` 让卡片成为撑满高度的纵向 flex，`body` 为 `flex:1; min-height:0`；`.table-fill` 再 `flex:1` 吃掉剩余高度，`el-table height="100%"` 在确定高度的父容器内启用自身滚动（表头 sticky）。

**注意**：`min-height: 0` 必写，否则 flex 子项按内容撑高、表格不会内部滚动。

### 4.3 分页
- 统一 `background`，`layout="total, sizes, prev, pager, next, jumper"`，`:page-sizes="[10,20,50,100]"`。
- 分页栏右对齐（`.pagination-bar`）。

---

## 5. 组件规范

### 5.1 按钮
- **表格内/表单内/弹窗**：用 Element Plus `el-button`（已主题化，`type="primary"` 即品牌色）。
- **门面页/卡片/磁贴**（登录、仪表盘、新页面区块）：用 shadcn `Button`（`@/components/ui/button`），变体 `default / outline / secondary / ghost / destructive`。
- 主操作 `type="primary"`/`default` 变体；次操作 `plain`/`outline`；危险操作 `danger`/`destructive`。

### 5.2 统计卡片（仪表盘范式，见 `Dashboard.vue`）
- 图标用**淡色底 + 同色图标**（`background: color-mix(in srgb, {color} 14%, white)`，图标同色），比纯色块柔和。
- 悬停：整卡 `-translate-y-0.5` + 阴影加深 + 底部彩条/右侧箭头反馈。
- 数值 `text-3xl font-bold`，标签 `text-sm text-muted-foreground`。

### 5.3 快捷入口磁贴
- 用 2×N 网格磁贴（图标 + 标题 + 一句简述）填满卡片，避免一排小按钮留大片空白。

### 5.4 卡片
- 用 shadcn `Card / CardHeader / CardTitle / CardDescription / CardContent`（`@/components/ui/card`），或 `el-card`（默认 shadow，勿 `shadow="never"`）。

---

## 6. 样式与 Tailwind 约定

- **禁止硬编码颜色 hex / 内联像素尺寸**（`style="width:260px"` 之类除输入框定宽外尽量避免），改用 token / 工具类。
- 组件样式一律 `scoped`；穿透用 `:deep()`。
- 复用型基础组件（如 PageCard）优先 **scoped CSS + `var(--ax-*)`**，与 `components/apifox/` 既有约定一致，零 Tailwind 依赖。
- **Tailwind 工具类不放进 `@layer`**（`tailwind.css` 已如此配置）。原因：`App.vue` 有全局无 layer 的 `* { margin:0; padding:0 }` 重置，CSS 中「无 layer」恒压过「有 layer」，工具类若入 layer 会被它盖掉（`p-*`、`m-*` 全失效）。改动 `tailwind.css` 时务必保持工具类无 layer。
- 不引入 Tailwind preflight（避免全局 reset 破坏 Element Plus）。
- 颜色透明度用 Tailwind 的 `/xx` 修饰（如 `bg-primary/90`、`text-white/70`），底层走 `color-mix`。

---

## 7. Do / Don't

| ✅ Do | ❌ Don't |
| --- | --- |
| 颜色/圆角/间距用 `--ax-*` token | 写死 `#1a365d`、`16px` |
| 列表页用 `<PageCard>` | 内容裸置于灰底 `<div>` |
| 主数据表用 `fill` + `height="100%"` 内部滚动 | 让整页随表格无限拉长 |
| 页面标题交给顶栏 | 页面内再写一个大标题 |
| 已卡片化页面去掉 `shadow="never"` | 给已在 el-card 的页面再套 PageCard（双层卡） |
| Tailwind 工具类保持无 layer | 把 utilities 塞进 `@layer utilities` |
| `min-height:0` 配 flex 滚动 | 忘了它导致表格撑高不滚 |

---

## 8. 新页面脚手架（复制即用）

```vue
<template>
  <PageCard fill>
    <template #toolbar>
      <el-input v-model="keyword" placeholder="搜索" style="width: 220px" @keyup.enter="load" />
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新建
      </el-button>
    </template>

    <div class="table-fill">
      <el-table v-loading="loading" :data="rows" stripe border height="100%">
        <el-table-column prop="id" label="ID" width="70" />
        <!-- ... -->
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="load"
        @size-change="load"
      />
    </div>

    <el-dialog v-model="dialogVisible" title="编辑" width="520px"> ... </el-dialog>
  </PageCard>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import PageCard from '@/components/PageCard.vue'
// import { xxxApi } from '@/api'

const loading = ref(false)
const rows = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)

async function load() {
  loading.value = true
  try {
    /* rows.value = await xxxApi.list(...) */
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.table-fill {
  flex: 1;
  min-height: 0;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  flex: none;
}
</style>
```

---

## 9. 参考实现（读代码更快）

| 范式 | 参考文件 |
| --- | --- |
| PageCard 容器 | `src/components/PageCard.vue` |
| 撑满高度表格 | `src/views/Requirements.vue` |
| 统计卡 + 磁贴 | `src/views/Dashboard.vue` |
| 门面页（双栏 + shadcn） | `src/views/Login.vue` |
| token → EP 变量映射 | `src/styles/element-theme.css` |
| Tailwind 接入（无 layer） | `src/styles/tailwind.css` |
| 顶栏/侧边栏 | `src/layouts/MainLayout.vue` |
