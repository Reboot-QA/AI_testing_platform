---
name: apifox-usecase-gen
description: 为 apifox 模块的某个接口/场景生成结构化测试用例（正常/边界/异常/权限），产出贴合本仓库 apifox 分层与数据契约。用户说「生成 apifox 用例 / 给这个接口出用例 / apifox 用例」时触发。仅本仓库适用。
---

# apifox 接口用例生成（骨架）

> 状态：占位骨架，待按实际 run_engine / schema 补全。核心原则：用例贴合 `.claude/rules/backend.md` 的分层与数据契约，字段名对齐 `routers/apifox/*_schemas.py`。

## 流程（待细化）

### 1. 定位目标接口
- 确认接口所在：`backend/app/routers/apifox/` 下路由 + 对应 `*_schemas.py` 的请求/响应模型。
- 记录：路径（`/api/v1/apifox/...`）、方法、鉴权要求、涉及的乐观锁 version 字段。

### 2. 按维度枚举用例
- **正常**：合法入参、典型业务路径。
- **边界**：空值/极值/长度上限、分页边界。
- **异常**：缺字段、类型错误、非法枚举 → 期望 4xx。
- **并发/乐观锁**：version 冲突 → 期望 HTTP 409。
- **权限**：跨部门/跨项目访问 → 期望拒绝。

### 3. 产出格式
- 每条用例：名称、前置条件、请求（method + path + body）、期望（status + 关键响应字段）。
- 对齐 apifox 执行引擎可消费的结构（后续接 `services/apifox/run_engine`）。

## TODO
- [ ] 对接实际 schema 字段自动读取
- [ ] 补真实断言模板
- [ ] 与 run_engine 用例格式对齐
