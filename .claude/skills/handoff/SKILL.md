---
name: handoff
description: 跨端/跨会话接力——只做一端就停时把交接物写成 Issue 评论交出去，或接手别人交来的 Issue 时从评论重建上下文再开工。用户说「交接 / 接手 / 我只做后端 / 前端接着做 / 交给另一个会话」时触发。仅本仓库适用。
---

# handoff（跨端 / 跨会话接力）

> Spec 驱动工作流的横向技能：`grill-with-docs` → `to-spec` → `implement-and-ship`，其中任一端做完就停时走本技能。规则见 `.claude/rules/spec-workflow.md`。
> 铁律：**交接物只有一种形态——Issue 评论，不产生任何新文件**。接手方只需一个 Issue ID 就能开工。

本技能双向。先判断方向，再走对应流程。

## 方向 A：交出（做完一端，交给另一侧）

### 1. 先过质量门
本端的质量门必须先过（前端 `pnpm typecheck` + `pnpm lint`；后端 `ruff check app` + 相关 `pytest`）。**不带病交接**——交出去的坑接手方看不见。

### 2. 本端 MR 用 `Ref #ID`
只做一端时 MR 描述写 `Ref #ID`，**不写 `Closes`**（`Closes` 只留给最后一端，避免提前关 Issue）。

### 3. 写交接评论
正文落 UTF-8 临时文件（scratchpad，不进仓库），格式：

```markdown
## 交接 · 后端 → 前端

- 后端 MR：!NN（已合入 dev ／ 待合）
- 契约状态：与描述段一致 ／ 偏离点：xxx
- openapi.json：已更新（commit abc1234）
- 接手第一步：`git pull origin dev && cd frontend && pnpm gen:api-types`
- 剩余：前端 checklist（见描述段「验收标准」）
```

必填四项，缺一不可：
- **本端 MR 号 + 是否已合入 `dev`**（决定接手方能不能立刻取到契约）
- **契约状态**：实现与 Issue 描述「接口契约」段一致，还是有偏离；有偏离必须逐条列出
- **接手第一步**：可直接复制执行的命令
- **剩余**：接手方要做的 checklist 指向

### 4. 展示 → 确认 → 发 → 校验
```bash
python .claude/scripts/glab_cn.py comment <ID> --body-file <scratchpad草稿路径>
```
- 展示完整正文与命令，**停住**等用户「确认发布」。
- **不要**用 `glab issue note -m "中文"`：本机 GBK 控制台会把中文双重编码写坏（Issue #15、#21 前车之鉴），且 glab 1.108.0 无 `--message-file`。脚本内部走 `glab api --input` 并自动读回校验，见 `.claude/rules/spec-workflow.md`「中文编码硬约束」。
- 脚本退出码 0 才算发成功，之后删掉临时草稿。

## 方向 B：接手（拿到一个 Issue ID 从头进入）

### 1. 重建上下文（按序读，不要跳）
```bash
python .claude/scripts/glab_cn.py show <ID> --out <scratchpad>/issue<ID>.md
```
然后用 **Read 工具**打开导出的文件。**不要**直接 `glab issue view --comments`：本机终端是 GBK，正文再干净也会显示成乱码，容易误判 Issue 坏了。导出文件里评论已按时间正序排好。

- **描述段** = 契约与验收标准（稳定，以它为准）。
- **最后一条交接评论** = 当前进度与你的起点。前面的评论只作历史参考，冲突时以最后一条为准。

### 2. 核对前置条件
- 交接评论说后端 MR「已合入 `dev`」→ 照「接手第一步」执行。
- 说「待合」→ **先停下问用户**是否等合入，不要基于未合入的契约动手。
- 契约状态标了偏离点 → 以**实际代码/`openapi.json`** 为准，并提醒用户 Issue 描述需要同步更新。

### 3. 复述再开工
开工前用两三句复述：本次要做哪一端、起点是什么、验收标准有哪几条。**用户确认后**再进 `implement-and-ship` 编码。

### 4. 本端是最后一端时
MR 描述写 `Closes #ID`（Issue 靠合并自动关，**不执行** `glab issue update --state closed`）。

## 不做

- 不产生任何交接文件（不写 `docs/specs/`、不写 handoff.md —— Spec 的单一事实来源是 Issue）。
- 不在用户确认前发评论 / 建 MR / push。
- 不在质量门未过时交出。
- 不基于未合入 `dev` 的契约闷头开工。
