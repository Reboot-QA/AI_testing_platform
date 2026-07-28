# Spec 驱动 + Issue/MR 半自主工作流（全仓库通用）

> 单一事实来源：本工作流的平台 / 分支流 / 授权边界 / 质量门只在本文维护一份。根 `CLAUDE.md` 导航登记本文，Cursor 经 `.cursor/rules/spec.mdc`（`alwaysApply`）引用本文。
> 配套四个项目级技能：`.claude/skills/grill-with-docs`（对齐）→ `to-spec`（出规格 + 发 Issue）→ `implement-and-ship`（实施 + 收尾）；跨端 / 跨会话接力走 `handoff`。Cursor 无技能机制，Cursor 用户按本文步骤手动复现。

## 平台

- 自建 GitLab：host `git.dbsportapixxxutikb.com`，project `tritech/temp/testhub`，`origin` 已指向此处。
- 收尾走纯 `glab` 链（无 GitHub 过渡逻辑）。`glab` 需先对该自建 host 认证（`glab auth login --hostname git.dbsportapixxxutikb.com`，protocol 选 HTTP）；**未认证时技能降级**为「生成命令 + 展示，人工复制执行」。

## 分支流

- 本地功能分支 → MR 到 **`dev`** → `dev` 合入 `main`。（分支流唯一正文见 `.claude/rules/git-workflow.md`，本文与之对齐。）

## 授权边界（半自主，CRITICAL）

- 任何 `git push` / `glab issue create` / `glab mr create` / `glab issue comment` / `glab issue update` **执行前**，先展示将执行的完整命令与正文，等用户明确「确认发布」再发。
- **不自动关 Issue**：靠 MR 合并时 `Closes #ID` 自动关闭，**不执行** `glab issue update --state closed`。
- 全栈两段式 MR 时，`Closes #ID` **只写在最后一个（前端）MR**，避免后端先合就提前关 Issue；后端 MR 描述用 `Ref #ID`。

## 质量门（ship 前必过）

- 前端：`pnpm typecheck`（vue-tsc）0 error + `pnpm lint`。
- 后端：`ruff check app` + 相关 `pytest`（`tests/`）。
- 提交信息：中文 conventional commit（commitlint 校验），如 `feat(apifox): ...`。

## 产物落位（单一事实来源 = Issue）

- **Spec 正文的单一事实来源是 GitLab Issue**，仓库内不留 Spec 文件（`docs/specs/` 已废弃并删除）。
- 本地只允许**临时草稿**，写在仓库外（scratchpad），建 / 更新 Issue 后即弃，**不进 git**。
- 改 Spec = 改 Issue 描述（`glab issue update <ID> --description-file <草稿>`），不在别处另存第二份，避免漂移。
- Issue **描述** = 契约（稳定，要改就改它）；Issue **评论** = 进度与交接（只追加）。

## 中文编码硬约束（CRITICAL）

本机控制台为 GBK，且 **glab 1.108.0 没有 `--description-file` / `--message-file`**，只有 `-d` / `-m` 参数。Windows 上参数要经控制台码页才交给进程，长中文正文会被**双重编码**写坏——Issue #15 与 #21 曾整篇乱码，2026-07-24 从本地文件回填修复。因此：

- **禁止**用 `glab issue create -d "中文正文"` / `glab issue note -m "中文正文"` 发布长中文。
- 正文一律先写成 **UTF-8 草稿文件**，再走仓库脚本 `.claude/scripts/glab_cn.py`（内部用 `glab api --input <UTF-8 JSON>`，文件字节原样进 HTTP body，不经码页转换，且**自动读回校验**）：

```bash
python .claude/scripts/glab_cn.py create  --body-file <草稿.md>   # 标题取草稿首个 `# ` 行
python .claude/scripts/glab_cn.py update  <IID> --body-file <草稿.md>
python .claude/scripts/glab_cn.py comment <IID> --body-file <草稿.md>
python .claude/scripts/glab_cn.py check   <IID>                   # 只读校验
```

- 脚本以**非 0 退出码**表示乱码或与草稿不一致；非 0 时不得继续下一步。
- 纯 ASCII 的短正文（如 `Ref #12`）可继续用原生 `glab` 参数。

## 契约先行接缝（复用现有机制）

- 后端 Pydantic schema → `backend/openapi.json` → 前端 `pnpm gen:api-types` → `Schemas['XxxOut']`（前端硬约束第 2 条本就强制用生成类型，见 `.claude/rules/frontend.md`）。
- Issue 描述里的「接口契约」段是前后端唯一交接点：method/path、请求/响应 schema、错误码（如乐观锁 409）、鉴权；可挂 FE/BE checklist 展示两侧进度。
- **推进顺序**：① 后端实现 endpoint + schema → 更新 `openapi.json` → 后端 MR 到 `dev`（`Ref #ID`）；② 后端合入后前端 `pnpm gen:api-types` 取类型 → 前端实现 → 前端 MR 到 `dev`（`Closes #ID`）。
- **两种协作模式**：同一会话按上序做完两端；或只做一端，走下面的「交接（handoff）」把接力棒交给另一侧（人或另一会话）。

## 交接（handoff）

- **交接物只有一种形态：Issue 评论**，不产生任何新文件。接手方永远只需要一个 Issue ID 就能开工。
- 交出方（做完一端就停）在 Issue 上追加交接评论，格式：

```markdown
## 交接 · 后端 → 前端

- 后端 MR：!NN（已合入 dev ／ 待合）
- 契约状态：与描述段一致 ／ 偏离点：xxx
- openapi.json：已更新（commit abc1234）
- 接手第一步：`git pull origin dev && cd frontend && pnpm gen:api-types`
- 剩余：前端 checklist（见描述段「验收标准」）
```

- 接手方用 `glab issue view <ID> --comments` 重建上下文，从**最后一条**交接评论的「接手第一步」开工。
- 交接评论同样受授权边界约束（展示 → 确认 → 才发），同样受编码硬约束（`--message-file` + 读回校验）。
