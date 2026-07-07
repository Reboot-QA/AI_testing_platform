# AI测试平台

演示地址：http://186.241.126.61:5173

![Snipaste_01](./images/Snipaste_01.png)
![Snipaste_02](./images/Snipaste_02.png)
![Snipaste_03](./images/Snipaste_03.png)
![Snipaste_04](./images/Snipaste_04.png)
![Snipaste_05](./images/Snipaste_05.png)
![Snipaste_06](./images/Snipaste_06.png)
![Snipaste_07](./images/Snipaste_07.png)
![Snipaste_08](./images/Snipaste_08.png)
![Snipaste_09](./images/Snipaste_09.png)
![Snipaste_10](./images/Snipaste_10.png)
![Snipaste_11](./images/Snipaste_11.png)
![Snipaste_12](./images/Snipaste_12.png)
![Snipaste_13](./images/Snipaste_13.png)
![Snipaste_14](./images/Snipaste_14.png)
![Snipaste_15](./images/Snipaste_15.png)
![Snipaste_16](./images/Snipaste_16.png)

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
| 后端 | FastAPI、SQLAlchemy、MySQL、JWT、httpx、Docker |
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
├── linux-deploy.sh               # Linux Docker 一键部署（推荐）
├── update.sh                     # 一键更新（git pull + 重新部署）
├── install-server.sh             # 远程服务器克隆 + 一键部署
├── deploy.sh                     # 传统开发部署 / docker 别名
├── docker-compose.yml            # Docker Compose 编排
├── docker/deploy.sh              # Docker 子命令（兼容保留）
├── .env.docker.example           # Docker 环境变量模板
├── docker/mysql/init.sql         # MySQL 初始化
├── .gitignore
└── README.md
```

> 本地 `文档/` 目录为原型与说明材料，已在 `.gitignore` 中排除，不会提交到 Git。

## 环境要求

**方式一：Docker 部署（推荐，无需本地 Python/Node/MySQL）**

- **Docker** 20.10+
- **Docker Compose** 插件 v2+

**方式二：传统部署（Linux / macOS / WSL 本地开发）**

- **Python** 3.8+（推荐 3.10 / 3.11）
- **Node.js** 18+（仅前端开发或完整部署时需要）
- **MySQL** 8.0+（或配合 Docker 仅启动 MySQL 容器）

## 快速启动

### 本地开发（Linux / macOS / WSL）

```bash
chmod +x deploy.sh
./deploy.sh          # 安装依赖并启动开发环境
./deploy.sh stop     # 停止服务
./deploy.sh restart  # 重启
./deploy.sh status   # 查看状态
./deploy.sh prod     # 构建前端 + 生产模式后端
./deploy.sh docker up   # Docker 全栈（同 linux-deploy.sh）
```

> **生产环境请使用 Docker**：`./linux-deploy.sh`（见下文）。Windows 本机请安装 [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) 后执行 `docker compose --env-file .env.docker up -d --build`。

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

### Linux 一键部署（推荐）

无需手动安装 Python / Node / MySQL，脚本会自动安装 Docker（Ubuntu/Debian）并启动全部服务。

```bash
cd /opt/AI_testing_platform

# 首次：复制环境变量（可选，脚本也会自动生成）
cp .env.docker.example .env.docker
vi .env.docker   # 修改 MYSQL_ROOT_PASSWORD、DB_PASSWORD

# 一键部署
chmod +x linux-deploy.sh
./linux-deploy.sh
```

**远程服务器首次安装：**

```bash
PUBLIC_HOST=你的公网IP INSTALL_DIR=/opt/AI_testing_platform ./install-server.sh
```

**常用命令：**

```bash
./linux-deploy.sh              # 安装并启动
./linux-deploy.sh status       # 查看状态
./linux-deploy.sh logs backend
./linux-deploy.sh restart
./linux-deploy.sh stop
./linux-deploy.sh update              # 从 GitHub 拉代码并重新部署
bash update.sh                        # 同上（推荐，自动处理权限与 git 冲突）
WITH_MONITORING=1 ./linux-deploy.sh up   # 含 Grafana + Loki
RESET_MYSQL=1 ./linux-deploy.sh up       # 清空前自动备份并重建 MySQL
./linux-deploy.sh backup-db              # 手动备份数据库
./linux-deploy.sh restore-db <文件>      # 从备份恢复
```

也可使用：`./deploy.sh docker up`（等价于 `./linux-deploy.sh up`）

### 数据库备份策略

备份文件默认保存在 `.deploy/backups/mysql/`（已加入 `.gitignore`）。

| 命令 | 说明 |
|------|------|
| `./linux-deploy.sh backup-db` | 立即备份（`mysqldump` + gzip，含 `CREATE DATABASE`） |
| `./linux-deploy.sh backup-list` | 查看已有备份 |
| `./linux-deploy.sh backup-prune` | 删除超过 30 天的旧备份（`BACKUP_KEEP_DAYS` 可调） |
| `./linux-deploy.sh restore-db <文件>` | 从 `.sql` / `.sql.gz` 恢复 |

**自动备份时机**：执行 `fix-db`、`RESET_MYSQL=1` 清空数据卷前，脚本会**先自动备份**一份（文件名带 `pre-reset` 标记）。

**推荐定时任务**（每天凌晨 3 点备份并清理旧文件）：

```bash
crontab -e
# 加入：
0 3 * * * cd /opt/AI_testing_platform && ./linux-deploy.sh backup-db && ./linux-deploy.sh backup-prune >> .deploy/logs/backup.log 2>&1
```

**异地备份**（建议同步到对象存储或另一台机器）：

```bash
rsync -avz .deploy/backups/mysql/ user@backup-server:/data/ai-platform/mysql/
```

**恢复示例**：

```bash
./linux-deploy.sh backup-list
RESTORE_CONFIRM=1 ./linux-deploy.sh restore-db .deploy/backups/mysql/ai_testcase_pre-reset_20260703_120000.sql.gz
```

**访问地址（默认端口）：**

| 服务 | 地址 |
|------|------|
| 前端 | http://服务器IP:5173 |
| 后端 API | http://服务器IP:8000 |
| Swagger | http://服务器IP:5173/docs |
| Grafana（monitoring） | http://服务器IP:3000 |

**演示账号：** `admin` / `admin123`

**`.env.docker` 主要配置：**

| 变量 | 说明 |
|------|------|
| `HTTP_PORT` | 前端 Nginx 对外端口（默认 5173） |
| `BACKEND_PORT` | 后端 API 对外端口（默认 8000） |
| `MYSQL_PORT` | MySQL 映射端口（默认 3306） |
| `MYSQL_PUBLISH_HOST` | MySQL 绑定地址（默认 `127.0.0.1`，仅 SSH 隧道；勿设 `0.0.0.0` 对公网） |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码（**必须强密码**） |
| `DB_PASSWORD` | 应用数据库密码（**必须强密码**） |
| `SECRET_KEY` | JWT 签名密钥 |
| `LLM_API_KEY` | LLM API Key（留空则 Mock 模式） |

服务架构：`frontend (Nginx)` → 反代 `/api` → `backend (FastAPI)` → `mysql`

**Navicat 连接 MySQL（推荐 SSH 隧道，不要对公网开放 3306）：**

| 项 | 值 |
|----|-----|
| SSH | 先 SSH 登录服务器 |
| 主机 | `127.0.0.1`（通过隧道，不是公网 IP） |
| 端口 | 3306 |
| 用户名 | `ai_testcase` |
| 密码 | `.env.docker` 中 `DB_PASSWORD` |
| 数据库 | `ai_testcase` |

`.env.docker` 中保持 `MYSQL_PUBLISH_HOST=127.0.0.1`，云安全组**不要**放行 3306。若曾对外开放且使用弱密码（如 `123456`），库可能被扫描脚本删除并留下 `RECOVER_YOUR_DATA` 勒索库。

### MySQL 安全（重要）

若 `SHOW DATABASES` 出现 **`RECOVER_YOUR_DATA`**，说明数据库曾被公网暴力破解，**不是应用删库**：

1. **立即**在云安全组关闭 3306 入站
2. 修改 `.env.docker` 中 `MYSQL_ROOT_PASSWORD`、`DB_PASSWORD` 为强密码
3. 设置 `MYSQL_PUBLISH_HOST=127.0.0.1`
4. 有备份则 `./linux-deploy.sh restore-db <文件>`，否则 `./linux-deploy.sh fix-db` 重建
5. **不要支付赎金**，勒索库无法恢复原始数据

## 配置说明

编辑 `backend/.env`（可从 `.env.example` 复制）：

```env
APP_NAME=AI质量平台
SECRET_KEY=change-this-to-a-random-secret-key

# MySQL 数据库
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password-here
DB_NAME=ai_testcase

# LLM（OpenAI 兼容 API）
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_MOCK_MODE=true
```

- 未配置 `LLM_API_KEY` 或 `LLM_MOCK_MODE=true` 时，AI 生成走 Mock 模式。
- LLM 也可在系统「全局设置」中配置多 Provider，优先级高于环境变量。
- 数据库使用 **MySQL**，启动前请先创建库：`CREATE DATABASE ai_testcase CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
- 也可直接设置 `DATABASE_URL=mysql+pymysql://user:pass@host:3306/ai_testcase?charset=utf8mb4` 覆盖上述 `DB_*` 参数。

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
