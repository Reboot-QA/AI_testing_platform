# 后端硬约束（backend/）

> 单一事实来源：后端「可执行红线」只在本文维护一份。Claude Code 经 `backend/CLAUDE.md` 按路径加载，Cursor 经 `.cursor/rules/backend.mdc` 按 `globs` 挂载。
> 详细规范（不复制、只链接）：[skills/后端开发规范.md](../../skills/后端开发规范.md) —— 分层、目录、命名、Pydantic、DB、Repository、异常、并发、日志、测试、提交。

技术栈：FastAPI + SQLAlchemy 2.0（`Mapped`/`mapped_column` 声明式）+ Pydantic v2 + MySQL（生产 PyMySQL）/ SQLite（本地测试）。包管理 **pip**（`backend/requirements.txt`，非 uv/poetry）。HTTP 出站用 httpx `AsyncClient`。

## 分层范式（apifox 模块为标准）

```
routers/apifox/       # HTTP 层 + Pydantic schema（*_schemas.py）
services/apifox/      # 业务逻辑：run_engine(SSE 执行引擎)、flow_control、variables、operators
repositories/apifox/  # 数据访问
models/apifox/        # SQLAlchemy 模型，表前缀 apifox_
```

- 两套并存的接口自动化模块（**新旧并存，旧模块不删**）：旧 `api_automation`（`routers/api_automation.py` + `services/api_*.py`，前端 `/api-automation/*`）；新 `apifox`（分层重构，当前重心，前后端 `apifox/` 子目录，API 前缀 `/api/v1/apifox/*`）。

## 硬约束

1. 所有 REST 接口统一前缀 `/api/v1`，路由在 `app/main.py` 注册。
2. **乐观锁**：apifox 六实体带 version 字段，写冲突返回 HTTP 409。
3. 认证 JWT（`app/auth.py`）；权限 = 部门 + 项目隔离 + 菜单权限（`app/constants/menus.py` 对应前端 `src/config/menus.ts`）。
4. 应用启动：`main.py` lifespan → `bootstrap.py`（建表/种子）→ `start_scheduler()`（后台线程定时调度）。
5. LLM：OpenAI 兼容 API（`services/ai_service.py`），未配 key 或 `LLM_MOCK_MODE=true` 走 Mock；系统「全局设置」多 Provider 配置优先于环境变量。
6. 提交前过 `ruff check app`（E/F/W/I，line-length 120，py312）与 `mypy app`（宽松基线，不强制注解）。

## 常用命令（backend/）

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # 启动，Swagger /docs
python -m pytest                                            # 全量（tests/）
python -m pytest tests/services/apifox/test_run_service.py -q   # 单文件
# 旧模块历史测试在 backend 根目录，需显式指定：
python -m pytest test_pre_script.py test_post_script.py test_response_extract.py -q
```
