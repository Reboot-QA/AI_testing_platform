# Spec: 项目工作台与用例编辑体验优化

> Issue: #15 — http://git.dbsportapixxxutikb.com/tritech/temp/testhub/-/issues/15
> 状态: 已实现，待验收

## 背景

项目工作台、需求文档上传、功能用例库和用户管理存在多处体验断点：

1. 置顶项目卡片呈灰色，容易被误认为禁用状态。
2. 最左侧全局导航宽度和点击反馈区域偏窄。
3. 点击“我的项目”卡片默认进入自动化模块，而不是更常用的需求概览。
4. 创建项目时填写的描述已入库，但工作台接口和项目卡片未展示。
5. AI 分析需求再次选择文件时，上传组件因单文件限制拒绝新文件，无法覆盖旧文件。
6. 功能用例库仅能查看详情，已有的更新能力没有完整编辑入口；AI 生成用例同样无法人工修订。
7. 添加用户时，少于 6 位的密码会提交到后端并触发全局错误提示，缺少字段级校验反馈。

## 目标

- 提升项目工作台的可辨识性、导航可用性和默认访问效率。
- 完整展示项目描述，并支持按描述搜索项目。
- 允许用户直接替换待解析的需求文件，确保文件列表和解析状态一致。
- 为手工及 AI 生成用例提供统一的详情编辑与保存能力。
- 在提交新增用户表单前完成密码长度校验，避免可预防的后端报错。

## 范围

### 本次实现

- 置顶项目卡片保持白色背景，使用高亮置顶标识和边框表达置顶状态。
- 最左侧全局图标导航从 56px 调整为 64px，并同步调整按钮点击、悬浮和选中反馈区域。
- 点击项目卡片默认进入 `需求 → 需求概览`；用户无需求权限时，沿用现有权限回退逻辑进入首个有权限模块。
- 工作台项目响应增加项目描述；卡片最多展示两行，超出省略，悬浮显示全文；搜索同时匹配项目名称、描述和角色。
- AI 分析需求页面再次选择文件时直接覆盖旧文件并清空旧解析结果；解析过程中禁止替换或移除文件。
- 功能用例详情抽屉增加编辑态和保存操作，手工用例与 AI 生成用例共用。
- 可编辑业务字段：标题、用例类型、优先级、关联需求、评审状态、前置条件、测试步骤、预期结果、标签。
- 只读系统字段：来源、所属项目、创建人、创建时间。
- 编辑者可手动选择 `draft`、`pending`、`approved`、`rejected` 评审状态。
- 保存关联需求时，后端校验该需求必须属于用例所在项目。
- 新增用户表单增加密码最少 6 位的字段级校验，校验失败时阻止提交并在密码输入项下提示。

### 本次不实现

- 需求文档解析在切换 Tab、刷新页面或退出登录时的状态保持和离开确认。
- 用例乐观锁及多人并发编辑冲突处理。
- 调整现有菜单权限模型或新增独立的用例编辑、评审权限。
- 修改项目描述的创建、编辑或存储逻辑。
- 修改 AI 生成流程、生成内容和 SSE 契约。

## 交互约束与边界

- 项目描述为空时不显示占位描述区域，避免卡片产生无意义留白。
- 描述两行截断仅影响展示，悬浮提示展示完整原文。
- 替换需求文件后，旧文件名、Element Plus 内部文件列表、前端选中文件和旧解析结果必须同步清除或更新。
- 文件解析请求已发起后，上传、替换和移除入口保持禁用，避免页面文件名与实际请求文件不一致。
- 用例详情进入编辑态后，取消操作恢复保存前内容；保存成功后退出编辑态并刷新列表及详情。
- 用例来源无论是 `manual` 还是 `ai_generated`，编辑字段、校验规则和保存反馈保持一致。
- 所有关联需求选项限制在当前项目内；后端仍需校验，不能只依赖前端筛选。
- 用例编辑权限沿用现有规则：用户需具有用例库入口权限且可访问用例所属项目。

## 接口契约

### 获取工作台概览

- Method/Path：`GET /api/v1/apifox/workbench/overview`
- 鉴权：JWT；仅返回当前用户可访问的项目。
- 请求：无新增参数。
- 响应：`WorkbenchOverviewOut`
  - `stats`：保持现有字段不变。
  - `projects[]`：保持现有字段，并新增：
    - `description: string | null`：项目描述。
- 错误：
  - `401`：未登录或登录状态失效。
- 兼容性：新增可空响应字段，不改变现有字段语义。

### 更新用例

- Method/Path：`PUT /api/v1/testcases/{case_id}`
- 鉴权：JWT；当前用户必须可访问用例所属项目。
- 请求：`TestCaseUpdate`，字段均为可选，至少按实际变更提交：
  - `title: string`
  - `case_type: string`
  - `priority: string`
  - `preconditions: string | null`
  - `steps: string | null`
  - `expected_results: string | null`
  - `tags: string | null`
  - `requirement_id: integer | null`
  - `review_status: "draft" | "pending" | "approved" | "rejected"`
- 响应：`TestCaseOut`，返回更新后的完整用例。
- 后端校验：
  - `review_status` 必须属于允许值。
  - `requirement_id` 非空时，对应需求必须存在且 `Requirement.project_id == TestCase.project_id`。
- 错误：
  - `400`：评审状态不合法。
  - `401`：未登录或登录状态失效。
  - `404`：用例不存在、无用例所属项目访问权限，或关联需求不存在/不属于当前项目。
- 并发：本次不新增 `version` 字段，保持现有后写覆盖行为。

### 其他改动

- 文件覆盖、导航、默认路由和新增用户密码校验均为前端行为，不新增接口。
- 新增用户仍使用现有创建用户接口及后端密码最少 6 位约束。

## 验收标准

### 项目工作台与导航

- [ ] 置顶卡片与普通卡片均为白底，置顶状态可通过高亮标识和边框清晰识别。
- [ ] 全局图标导航宽度为 64px，按钮悬浮、选中和点击区域同步加宽且对齐。
- [ ] 点击项目卡片默认进入该项目的“需求概览”。
- [ ] 无需求权限时不会进入无权限页面，而是进入首个有权限模块。
- [ ] 新建或已有项目的描述能在卡片中展示两行，超出省略并可悬浮查看全文。
- [ ] 项目搜索可以匹配描述内容。

### 需求文件替换

- [ ] 选择第二个文件后，首个文件被直接替换，界面仅显示新文件。
- [ ] 替换文件会清空旧解析结果。
- [ ] 解析进行中不能替换或移除当前文件。
- [ ] 文件类型、大小及后端解析契约保持现状。

### 用例编辑

- [ ] 手工用例和 AI 生成用例的详情均提供编辑入口。
- [ ] 详情可在查看态与编辑态间切换，并提供保存、取消操作。
- [ ] 全部约定业务字段可编辑，系统字段保持只读。
- [ ] 编辑者可以手动选择四种评审状态。
- [ ] 保存成功后列表和详情同步展示最新值。
- [ ] 取消编辑不产生数据变更。
- [ ] 关联当前项目内需求可以保存。
- [ ] 关联其他项目需求时后端拒绝保存，且前端展示明确错误。

### 用户密码校验

- [ ] 新增用户密码不足 6 位时，在密码字段下显示提示并阻止请求。
- [ ] 密码达到 6 位后字段错误消失，可正常提交。
- [ ] 后端密码长度约束保持不变。

### 质量门

- [x] `frontend` 执行 `pnpm typecheck` 为 0 error。
- [x] `frontend` 执行 `pnpm lint` 通过。
- [x] `backend` 执行 `ruff check app` 通过。
- [x] 后端工作台响应和用例更新校验的相关 `pytest` 通过。
- [x] 更新 `backend/openapi.json`，执行 `pnpm gen:api-types`，前端使用生成类型且不手改 `schema.d.ts`。

## 影响面

### 前端

- 项目工作台与卡片：
  - `frontend/src/views/hub/ProjectsView.vue`
  - `frontend/src/components/hub/ProjectCard.vue`
- 全局导航：
  - `frontend/src/components/shell/GlobalRail.vue`
  - `frontend/src/components/shell/RailButton.vue`
  - `frontend/src/styles/tokens.css`
- 项目默认入口与权限回退：
  - `frontend/src/views/hub/ProjectsView.vue`
  - `frontend/src/composables/useWorkspaceHash.ts`
- 需求文件上传：
  - `frontend/src/views/RequirementDocs.vue`
- 用例编辑：
  - `frontend/src/views/TestCases.vue`
  - `frontend/src/api/testcase.ts`
- 新增用户校验：
  - `frontend/src/views/UserManagement.vue`
- 生成类型：
  - `frontend/src/api/schema.d.ts`（仅由生成命令更新）

### 后端

- 工作台响应契约与组装：
  - `backend/app/routers/apifox/workbench_schemas.py`
  - `backend/app/services/apifox/workbench_service.py`
- 用例更新及关联需求校验：
  - `backend/app/routers/testcases.py`
  - `backend/app/schemas.py`
- OpenAPI：
  - `backend/openapi.json`

### 权限、数据与执行引擎

- 沿用部门、项目隔离及现有菜单权限，不新增权限标识。
- 不变更数据库表结构，不新增迁移。
- 不触及 apifox 六实体的乐观锁。
- 不修改 AI 用例生成及需求解析 SSE 协议。
