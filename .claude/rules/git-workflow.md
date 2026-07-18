# Git 工作流（全仓库通用）

> 单一事实来源：分支流 / 提交风格 / 禁提交清单只在本文维护一份。根 `CLAUDE.md` 常驻 `@import` 本文，Cursor 经 `.cursor/rules/git.mdc`（`alwaysApply`）引用本文。

## 分支流

- 本地功能分支 → PR 到 `test` → `test` 合入 `main`。

## 提交风格

- **中文 conventional commits**，如 `feat(apifox): ...`、`fix(apifox): ...`、`chore(frontend): ...`。
- 前端提交前自动过钩子：pre-commit（lint+format，仅 `src/`）、commit-msg（commitlint 校验）、pre-push（`vue-tsc` 类型检查，基线必须 0 error）。

## 禁提交清单（CRITICAL）

- ❌ `node_modules/`、`frontend/dist/` —— node_modules 历史上被纳入 git 跟踪，改动它会出现在 `git status`，**不要提交这些变化**。
- ❌ `vite.config.ts` 里把 `/api/` proxy target 改成 `http://127.0.0.1:8000` 的本地联调改动 —— 只在本地改，**不提交**（改动说明记在 `CLAUDE.local.md`）。
- ❌ `CLAUDE.local.md` 本身（已 gitignore）。

## 单一事实来源文档

- `接口自动化重构_进度与计划.md`（仓库根目录）是接口自动化重构的**单一事实来源**，做相关改动后应同步更新（该文件已 gitignore，仅本地维护）。
