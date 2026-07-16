# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于 **FastAPI + Vue 3** 的 AI 测试平台（需求管理 / 功能用例 / AI 生成 / 手工执行 / 接口自动化）。文档、注释、commit message 均使用中文。

## 常用命令

### 前端（frontend/，Vue 3 + Vite + Element Plus + Pinia）

```bash
cd frontend
pnpm install     # 包管理器统一为 pnpm（corepack enable pnpm 激活；npm/yarn 会被 only-allow 拦截）
pnpm dev         # 开发服务器，端口 5173
pnpm build       # 生产构建到 dist/
```

- 前端无 lint / 测试脚本。
- Vite 将 `/api` 代理到 `vite.config.js` 中的 target（当前指向演示服务器 `43.160.226.39`）；本地联调后端时需改为 `http://127.0.0.1:8000`，但**不要把这个改动提交**。

### 后端（backend/，FastAPI + SQLAlchemy + MySQL）

```bash
cd backend
pip install -r requirements.txt        # 复制 .env.example 为 .env 并配置 MySQL
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

测试（pytest，`testpaths = ["tests"]`，配置见 `backend/pyproject.toml`）：

```bash
cd backend
python -m pytest                                        # 全量（tests/ 目录）
python -m pytest tests/services/apifox/test_run_service.py -q   # 单文件
python -m pytest tests/services/apifox/test_operators.py::test_xxx  # 单用例
# 旧模块的历史测试在 backend 根目录，需显式指定：
python -m pytest test_pre_script.py test_post_script.py test_response_extract.py -q
```

Lint / 类型检查（配置在 `backend/pyproject.toml`，项目用 pip + requirements.txt，非 uv/poetry）：

```bash
ruff check app    # E/F/W/I，line-length 120，py312
mypy app          # 宽松基线：不强制注解
```

### 全栈

`./deploy.sh`（Linux/macOS/WSL 本地开发）、`./linux-deploy.sh`（Docker 生产部署）。Swagger 文档在 `http://127.0.0.1:8000/docs`，演示账号 `admin / admin123`。

## Git 工作流

- 分支流：本地功能分支 → PR 到 `test` → `test` 合入 `main`。
- **前端 PR 只提交源码 + package.json，不含 node_modules / dist**（node_modules 历史上被纳入了 git 跟踪，改动它会出现在 git status 里——不要提交这些变化）。
- Commit 风格：中文 conventional commits，如 `feat(apifox): ...`、`fix(apifox): ...`。
- `接口自动化重构_进度与计划.md`（仓库根目录）是接口自动化重构的**单一事实来源**，做相关改动后应同步更新该文档。

## 架构

### 两套并存的接口自动化模块（重要）

按用户决策**新旧并存，旧模块不删除**：

1. **旧模块 `api_automation`**：`backend/app/routers/api_automation.py` + `services/api_*.py`（单文件为主）；前端 `views/ApiAutomation.vue` + `components/Api*.vue`，路由 `/api-automation/*`。
2. **新模块 `apifox`**（Apifox 式分层重构，当前开发重心）：前后端均放在 `apifox/` 子目录，路由 `/apifox`（工作台）与 `/apifox/project/:projectId`（项目工作区），API 前缀 `/api/v1/apifox/*`。

### 后端分层（apifox 模块为标准范式）

```
routers/apifox/    # HTTP 层 + Pydantic schema（*_schemas.py）
services/apifox/   # 业务逻辑：run_engine(SSE 执行引擎)、flow_control、variables、operators 等
repositories/apifox/  # 数据访问
models/apifox/     # SQLAlchemy 模型，表前缀 apifox_
```

- 所有 REST 接口统一前缀 `/api/v1`，路由在 `app/main.py` 注册。
- 认证：JWT（`app/auth.py`）；权限：部门 + 项目隔离 + 菜单权限（`app/constants/menus.py` 与前端 `src/config/menus.ts` 对应）。
- 应用启动：`main.py` lifespan → `bootstrap.py`（建表/种子数据）→ `start_scheduler()`（后台线程定时调度）。
- **乐观锁**：apifox 六实体带 version 字段，冲突返回 HTTP 409。
- 执行引擎通过 **SSE** 推送套件/场景运行进度。
- LLM：OpenAI 兼容 API（`services/ai_service.py`），未配 key 或 `LLM_MOCK_MODE=true` 走 Mock；系统「全局设置」中的多 Provider 配置优先于环境变量。

### 前端结构

- **API 层集中在 `src/api/index.ts`**（axios 单实例，baseURL `/api/v1`，自动带 token，401 跳登录，响应拦截器直接返回 `response.data`）。注意：`/apifox/` 路径的 409 不弹全局错误，由调用方配合 `composables/useSaveConflict.ts` 处理保存冲突。
- 路由守卫：`src/router/index.ts`，每个路由 `meta.permission` 对应后端菜单权限。
- **`src/` 业务代码统一 TypeScript**（`.ts`）；禁止新增 `.js` 源文件。Vue SFC 的 `<script setup lang="ts">` 为后续阶段。
- apifox 前端：`views/apifox/ProjectWorkspace.vue` 是项目工作区外壳（顶部 tab 切 `views/apifox/sections/` 下各面板），可复用组件在 `components/apifox/`。
- 代码编辑器统一用 Monaco（`@guolao/vue-monaco-editor`，本地 worker 无 CDN）；design token / Apifox 配色在 `src/styles/`。
- Pinia stores：`user`（登录态/权限）、`workspace`（当前项目）、`apiTabs`、`aiGenerate`。
