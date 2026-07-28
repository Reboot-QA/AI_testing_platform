---
name: to-spec
description: 把对齐好的需求提炼为结构化 Spec（背景/目标/范围/接口契约/验收标准/影响面），半自主生成 glab issue create 命令与正文，展示待用户确认后再发；Spec 正文只存 GitLab Issue，本地不留文件。用户说「生成 spec / 出规格 / 写规格」时触发。仅本仓库适用。
---

# to-spec（生成规格 + 半自主发 Issue）

> Spec 驱动工作流第 2 步：`grill-with-docs` → 本技能 → `implement-and-ship`（跨端接力走 `handoff`）。规则见 `.claude/rules/spec-workflow.md`。
> 半自主铁律：**生成 Spec 后不得径直建 Issue；必须显式跳出选项让用户拍板，用户选「建」才执行 `glab issue create`**，绝不自动发。
> 落位铁律：**Spec 正文的单一事实来源是 GitLab Issue，仓库内不留 Spec 文件**。本地只写临时草稿，落 scratchpad（仓库外），发完即弃。

## 流程

### 1. 提炼结构化 Spec（写成 UTF-8 草稿）
基于对齐要点产出 Spec 正文，写进 scratchpad 的临时 `.md`（**不要**写进 `docs/`、不要进 git），含：
- **背景**：为什么做，解决的问题。
- **目标**：可验证的成功标准。
- **范围**：做什么 / 不做什么。
- **接口契约**（前后端唯一交接点）：每个 endpoint 的 method + path（`/api/v1/apifox/...`）、请求/响应 schema 字段、错误码（如乐观锁 409）、鉴权要求。
- **验收标准**：可勾选的 checklist，含质量门（前端 typecheck/lint、后端 ruff/pytest）。全栈任务可拆 FE / BE 两组，便于两侧展示进度。
- **影响面**：触及的分层文件、权限、SSE、前端类型生成。

### 2. 建 Issue 前——显式跳出让用户选择（强制停顿点）
草稿写好后**不要径直建 Issue**。先展示 Spec 摘要 + 拟用的 `glab issue create` 命令与正文，然后**明确跳出一个选择**（用选择交互，非默认往下走）让用户在至少这几项里定：

1. **确认建 Issue**：用当前标题/正文直接发。
2. **调整后再建**：改标题 / 正文 / 加 label / 指派人，改完再发。
3. **暂不建**：草稿留在 scratchpad，Issue 稍后建或人工建（也是 glab 未认证时的降级路径，见 spec-workflow.md）。注意这只是**临时状态**，草稿不是 Spec 的家。

只有用户选「建」之后才执行 `glab issue create`。

### 3. 发布（编码硬约束，CRITICAL）
本机控制台 GBK，且 glab 1.108.0 **没有** `--description-file`；中文正文拼进命令行参数会双重编码报废（Issue #15、#21 前车之鉴）。**必须**走仓库脚本，它内部用 `glab api --input` 传 UTF-8 文件并自动读回校验：

```bash
python .claude/scripts/glab_cn.py create --body-file <scratchpad草稿路径>
```
- 标题默认取草稿首个 `# ` 行，无需再走 `--title` 参数。
- 脚本会打印 `#ID`、`CLEAN` 与 `EXACT MATCH`，并以退出码表示成败。

### 4. 收尾
- 脚本退出码 0（`CLEAN` + `EXACT MATCH`）→ 删掉 scratchpad 草稿，本步完成。
- 非 0 → **不要继续**，排查后用 `python .claude/scripts/glab_cn.py update <ID> --body-file <草稿>` 重发。

## 产出
- GitLab Issue `#ID`（Spec 正文的唯一落点）。
- 结束语提示：「Spec 已落 Issue #ID 并校验通过，可以说『按 spec 实现』进入 `implement-and-ship`；若本次只做一端，做完说『交接』走 `handoff`」。

## 不做
- 不在用户确认前执行任何 glab 命令。
- **不往仓库里写 Spec 文件**（`docs/specs/` 已废弃删除，Spec 只存 Issue）。
- 不跳过读回校验。
- 不写实现代码（那是下一步）。
