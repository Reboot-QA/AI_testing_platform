# AI测试平台

演示地址：http://38.12.6.230:5173/login


基于 **Python FastAPI + Vue 3** 的智能质量与测试管理平台，覆盖需求管理、功能用例、AI 生成、手工执行与接口自动化测试。

## 功能模块

| 模块 | 说明 |
|------|------|
| **仪表盘** | 项目与用例统计概览 |
| **项目管理** | 多项目隔离与维护 |
| **需求管理** | 需求文档上传解析、需求点维护 |
| **用例管理** | AI 智能生成、用例库、评审与 Excel 导出、手工用例执行 |
| **接口自动化** | 环境配置、套件与用例、测试报告、定时任务 |
| **系统管理** | 全局 LLM 配置、用户管理、菜单权限 |

### 接口自动化能力

- **Apipost 风格调试**：Header / Query / Path / Body / 认证 / Cookie / 参数化
- **预执行 / 后执行操作**：自定义脚本（JavaScript / Python）、断言、变量提取、等待等
- **套件树形目录**：无限层级子目录，支持拖拽排序、复制、批量删除
- **用例拖拽**：从用例列表拖至目标套件/目录（复制到目标，原用例保留）
- **抓包导入**：支持 DevTools cURL、Charles 等格式
- **数据驱动**：多组数据集批量发送与执行
- **套件执行与报告**：一键执行、步骤级报告、通过率统计
- **定时任务**：按天 / 按周 / 间隔调度，支持立即执行

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI、SQLAlchemy、SQLite、JWT、httpx |
| 前端 | Vue 3、Vite、Element Plus、Pinia、Vue Router、Axios |
| AI | OpenAI 兼容 Chat Completions API（可 Mock） |
| 调度 | 内置后台线程定时调度 |

## 项目结构

```
AI质量平台/
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── main.py               # 应用入口、路由注册、生命周期
│   │   ├── config.py             # 配置项
│   │   ├── database.py           # 数据库连接
│   │   ├── models/               # SQLAlchemy 模型
│   │   ├── routers/              # API 路由
│   │   │   ├── auth.py           # 认证
│   │   │   ├── projects.py       # 项目
│   │   │   ├── requirements.py   # 需求
│   │   │   ├── testcases.py      # 功能用例
│   │   │   ├── test_execution.py # 用例执行
│   │   │   ├── api_automation.py # 接口自动化
│   │   │   ├── users.py          # 用户
│   │   │   └── settings.py       # 系统设置
│   │   ├── services/             # 业务逻辑（AI、接口执行、抓包、调度等）
│   │   ├── constants/            # 菜单与常量
│   │   └── schemas.py            # Pydantic 模型
│   ├── requirements.txt
│   ├── .env.example
│   └── test_*.py                   # 接口自动化相关单元测试
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── views/                # 页面（ApiAutomation、TestCases 等）
│   │   ├── components/           # 用例编辑器、操作项列表等组件
│   │   ├── api/                  # API 封装
│   │   ├── router/               # 路由与权限守卫
│   │   ├── stores/               # Pinia 状态
│   │   ├── config/menus.js       # 前端菜单配置
│   │   └── utils/apiCaseConfig.js
│   ├── index.html
│   └── package.json
├── deploy.sh                     # Linux / macOS / Git Bash 部署脚本
├── start-all.bat                 # Windows 一键启动
├── start-backend.bat
├── start-frontend.bat
├── .gitignore
└── README.md
```

> 本地 `文档/` 目录为原型与说明材料，已在 `.gitignore` 中排除，不会提交到 Git。

## 环境要求

- **Python** 3.8+（推荐 3.10 / 3.11）
- **Node.js** 18+（仅前端开发或完整部署时需要）
- **操作系统**：Windows / Linux / macOS

## 快速启动

### 一键启动（推荐）

**Windows：**

```bat
start-all.bat
```

**Linux / macOS / Git Bash / WSL：**

```bash
chmod +x deploy.sh
./deploy.sh          # 安装依赖并启动开发环境
./deploy.sh stop     # 停止服务
./deploy.sh restart  # 重启
./deploy.sh status   # 查看状态
./deploy.sh prod     # 构建前端 + 生产模式后端
```

启动后访问：

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:5173 |
| 后端 API | http://127.0.0.1:8000 |
| Swagger 文档 | http://127.0.0.1:8000/docs |

**演示账号：** `admin` / `admin123`

### 手动启动

**后端：**

```bash
cd backend
pip install -r requirements.txt
# 复制 .env.example 为 .env 并按需修改
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

**生产构建：**

```bash
cd frontend && npm run build
# 后端可使用 deploy.sh prod，或由 Nginx 等托管 frontend/dist
```

## 配置说明

编辑 `backend/.env`（可从 `.env.example` 复制）：

```env
APP_NAME=AI质量平台
SECRET_KEY=change-this-to-a-random-secret-key
DATABASE_URL=sqlite:///./ai_testcase.db

# LLM（OpenAI 兼容 API）
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_MOCK_MODE=true
```

- 未配置 `LLM_API_KEY` 或 `LLM_MOCK_MODE=true` 时，AI 生成走 Mock 模式。
- LLM 也可在系统「全局设置」中配置多 Provider，优先级高于环境变量。
- 数据库默认 SQLite，文件位于 `backend/ai_testcase.db`，可按需改为其他 SQLAlchemy 支持的 URL。

## 主要路由（前端）

| 路径 | 页面 |
|------|------|
| `/dashboard` | 仪表盘 |
| `/projects` | 项目管理 |
| `/requirement-docs` | 需求文档 |
| `/requirements` | 需求点 |
| `/testcases` | 用例库 |
| `/ai-generate` | AI 智能生成 |
| `/test-execution` | 用例执行 |
| `/api-automation/env` | 环境配置 |
| `/api-automation/suites` | 套件与用例 |
| `/api-automation/reports` | 测试报告 |
| `/api-automation/schedule` | 定时任务 |
| `/system/settings` | 全局设置 |
| `/system/users` | 用户管理 |
| `/system/permissions` | 权限管理 |

## API 前缀

所有 REST 接口统一前缀：`/api/v1`

常见分组：

- `/api/v1/auth` — 登录注册
- `/api/v1/projects` — 项目
- `/api/v1/requirements` — 需求
- `/api/v1/testcases` — 功能用例
- `/api/v1/test-execution` — 用例执行
- `/api/v1/api-automation` — 接口自动化（环境、套件、用例、报告、调度、抓包、脚本调试等）

## 开发与测试

```bash
# 接口自动化相关后端测试（在 backend 目录下）
python -m pytest test_pre_script.py test_post_script.py test_response_extract.py -q
```

前端开发时 Vite 将 `/api` 代理至后端，详见 `frontend/vite.config.js`。

## 许可证

内部项目，按需自行维护与部署。
