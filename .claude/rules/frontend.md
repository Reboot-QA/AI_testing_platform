# 前端硬约束（frontend/）

> 单一事实来源：前端「可执行红线」只在本文维护一份。Claude Code 经 `frontend/CLAUDE.md` 按路径加载，Cursor 经 `.cursor/rules/frontend.mdc` 按 `globs` 挂载。
> 详细规范（不复制、只链接）：
> - [frontend/docs/前端开发规范.md](../../frontend/docs/前端开发规范.md) —— 技术栈、目录、命名、SFC/TS/组件/API/提交
> - [frontend/docs/前端UI设计规范.md](../../frontend/docs/前端UI设计规范.md) —— 双轨 UI、`--ax-*` token、`PageCard`、表格 `fill` 一屏化、Tailwind 无 layer
> - [frontend/docs/技术方案选型说明.md](../../frontend/docs/技术方案选型说明.md) —— 为何留在 Vue3+TS 不迁 React

技术栈：Vue 3 `<script setup lang="ts">` + Vite + TypeScript + Element Plus + Pinia + Monaco（本地 worker，无 CDN）。包管理统一 **pnpm**（`only-allow` 拦截 npm/yarn）。

## 高频硬约束（违反会破坏一致性）

1. `src/` 只写 TS，SFC 用 `<script setup lang="ts">`；**不新增 `.js` 源文件**（根构建配置亦已 TS 化为 `vite.config.ts`）。
2. API 实体类型用生成的 `Schemas['XxxOut']`（`@/api/types`），**不手写类型、不用 `any`/`unknown`**；`schema.d.ts` 由 `pnpm gen:api-types` 生成，勿手工维护。
3. API 调用只从 `@/api` 具名导入；样式只用 `--ax-*` token，**禁硬编码 hex/rgba**；Tailwind 工具类不入 `@layer`。
4. 列表页用 `PageCard`，主数据表用 `fill` 撑满一屏内部滚动；路由动态参数用 `useRouteParamId()`（`composables/useRouteParamId.ts`），禁止直接解构 `route.params`。
5. 新组件 ≤ 300 行；`pnpm typecheck`（vue-tsc）必须 0 error（pre-push 强制）。
6. script 中引用 props 必须 `const props = defineProps/withDefaults(...)`；template 可直接用 prop 名。Apifox UI 类型放 `types/apifox.ts`，勿从 `.vue` export type。

## 关键约定

- API 层集中在 `src/api/index.ts`（axios 单实例，baseURL `/api/v1`，自动带 token，401 跳登录，响应拦截器直接返回 `response.data`）。`/apifox/` 路径的 409 不弹全局错误，由调用方配合 `composables/useSaveConflict.ts` 处理保存冲突。
- apifox 前端：`views/apifox/ProjectWorkspace.vue` 是项目工作区外壳（顶部 tab 切 `views/apifox/sections/` 下各面板），可复用组件在 `components/apifox/`。
- Pinia stores：`user`（登录态/权限）、`workspace`（当前项目）、`apiTabs`、`aiGenerate`。

## 常用脚本（frontend/）

```bash
pnpm dev            # 开发服务器 :5173
pnpm build          # 生产构建 dist/
pnpm lint           # eslint src（lint:fix 自动修）
pnpm format         # prettier 格式化 src
pnpm typecheck      # vue-tsc --noEmit，必须 0 error
pnpm gen:api-types  # 从 backend/openapi.json 生成 src/api/schema.d.ts
```
