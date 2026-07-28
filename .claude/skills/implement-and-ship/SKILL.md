---
name: implement-and-ship
description: 对照定稿 Spec 编码，过质量门（前端 typecheck/lint、后端 ruff/pytest），再半自主收尾——生成 glab mr create / issue comment 命令展示待确认后发，MR 目标分支 dev，不自动关 Issue。用户说「按 spec 实现 / ship / 实现并提交」时触发。仅本仓库适用。
---

# implement-and-ship（实施 + 半自主收尾）

> Spec 驱动工作流第 3 步：`grill-with-docs` → `to-spec` → 本技能（跨端接力走 `handoff`）。规则见 `.claude/rules/spec-workflow.md`。
> 半自主铁律：**MR/评论命令生成后必须展示、等「确认发布」才执行；不自动关 Issue**。

## 流程

### 1. 对照 Spec 编码
- **Spec 正文在 GitLab Issue，不在仓库里**。开工前读：`glab issue view <ID> --comments`（描述段 = 契约与验收标准；评论 = 进度与交接）。
- 严格按 Issue 描述段的范围与接口契约实现，不擅自扩范围。
- 遵守分层（apifox：routers/services/repositories/models）与前后端硬约束（`.claude/rules/frontend.md` / `backend.md`）。

### 2. 过质量门（ship 前必过）
- 前端：`pnpm typecheck`（0 error）+ `pnpm lint`。
- 后端：`ruff check app` + 相关 `pytest`。
- 任一不过 → 修完再收尾，不带病 ship。

### 3. 全栈推进顺序（契约先行、后端先落）
1. **后端**：实现 endpoint + schema → 更新 `backend/openapi.json` → 后端 MR 到 `dev`，描述用 `Ref #ID`（**不写 Closes**）。
2. 后端契约合入 `dev` 后，**前端** `pnpm gen:api-types` 取类型 → 实现 → 前端 MR 到 `dev`，描述写 `Closes #ID`。
- **只在最后一个（前端）MR 写 `Closes`**，避免后端先合提前关 Issue。单端任务则该端 MR 直接写 `Closes`。

**单端出口**：本次只做一端、另一端交给别人（或另一个会话）时，做完本端**就停**——MR 用 `Ref #ID`，然后转 `handoff` 技能发交接评论，不要接着动另一端。

### 4. 半自主收尾（生成命令 → 展示 → 确认后发）
```bash
# MR：标题用中文 conventional commit，目标分支 dev
glab mr create --source-branch <本地分支> --target-branch dev \
  --title "feat(apifox): xxx" --description "Closes #ID  /* 或 Ref #ID */"

# Issue 追加中文总结：正文落 UTF-8 草稿（scratchpad），走脚本发，勿拼进 -m 参数
python .claude/scripts/glab_cn.py comment <ID> --body-file <scratchpad草稿路径>
```
- 展示完整命令与正文，**停住**等用户「确认发布」。
- **编码硬约束**：本机 GBK 控制台 + glab 1.108.0 无 `--message-file`，中文拼参数会双重编码报废（Issue #15、#21 前车之鉴）。中文一律走上面的脚本（内部 `glab api --input` + 自动读回校验），见 `.claude/rules/spec-workflow.md`。MR 标题/描述若含中文同理，勿用超长中文描述拼参数。
- **不执行** `glab issue update --state closed`（Issue 靠合并自动关）。

## 不做
- 不在用户确认前 push / 建 MR / 发评论。
- 不自动关闭 Issue。
- 不跳过质量门。
