# Spec 工作流使用指南

面向团队成员的**上手文档**：需求怎么进来、规格落在哪、代码怎么出去、两个人怎么接力。

> **本文只讲「怎么用」。** 硬约束（授权边界 / 质量门 / 分支流）的唯一正文在 [`.claude/rules/spec-workflow.md`](../.claude/rules/spec-workflow.md)，本文不复制，冲突时以规则文件为准。

## 一句话

需求先对齐 → 规格落成 **GitLab Issue** → 照 Issue 编码 → MR 合 `dev`。跨端接力时，交接物也写在同一个 Issue 上。

**Spec 的单一事实来源是 GitLab Issue**，仓库里不存规格文件（原 `docs/specs/` 已于 2026-07-24 废弃删除）。要改规格就改 Issue 描述，不在别处另存第二份。

---

## 准备一次就够

```bash
glab auth login --hostname git.dbsportapixxxutikb.com   # protocol 选 HTTP
```

未认证也能用，只是 AI 会降级成「生成命令给你，人工复制执行」。

---

## 四个阶段（对 Claude Code 说这些话就进）

| 说什么 | 阶段 | 做什么 |
|---|---|---|
| 「帮我理需求 / 对齐需求 / 深挖一下」 | 对齐 | 只追问不写码，逼出目标、范围、edge case、对现有模块的影响 |
| 「生成 spec / 出规格」 | 出规格 | 提炼结构化规格 → **停下让你拍板** → 建 Issue |
| 「按 spec 实现 / ship」 | 实施 | 照 Issue 编码 → 过质量门 → 建 MR |
| 「交接 / 接手 / 我只做后端」 | 接力 | 交出或接手，交接物写成 Issue 评论 |

规格包含六段：**背景 / 目标 / 范围 / 接口契约 / 验收标准 / 影响面**。其中「接口契约」是前后端唯一交接点（method、path、请求响应 schema、错误码如乐观锁 409、鉴权）。

---

## 场景一：单端需求

```
帮我理需求：apifox 场景要支持复制
    ↓  连环追问，产出对齐要点
生成 spec
    ↓  写草稿 → 弹三选一（直接建 / 改了再建 / 先不建）
    ↓  选「建」→ 发 Issue → 自动校验编码 → 得到 #ID
按 spec 实现
    ↓  编码 → 前端 typecheck+lint ／ 后端 ruff+pytest
    ↓  展示 MR 命令（描述写 Closes #ID）→ 停住等你确认
确认发布
```

Issue 靠 MR 合并时的 `Closes #ID` 自动关闭，**不手工 close**。

## 场景二：全栈，一个人做完两端

契约先行，后端先落：

1. **后端**：endpoint + schema → 更新 `backend/openapi.json` → MR 到 `dev`，描述写 **`Ref #ID`**
2. 后端合入 `dev` 后，**前端**：`pnpm gen:api-types` 取类型 → 实现 → MR 到 `dev`，描述写 **`Closes #ID`**

> `Closes` **只写在最后一个 MR**。后端 MR 就写 `Closes` 的话，后端一合 Issue 就提前关了，前端还没做。

## 场景三：只做一端，交给别人

后端做完说 **`交接`**：

1. 先过本端质量门 —— **不带病交接**，交出去的坑接手方看不见
2. 本端 MR 用 `Ref #ID`（不是 `Closes`）
3. 生成交接评论 → 展示 → 你确认 → 发到 Issue

交接评论模板，四项缺一不可：

```markdown
## 交接 · 后端 → 前端

- 后端 MR：!42（已合入 dev ／ 待合）
- 契约状态：与描述段一致 ／ 偏离点：xxx
- openapi.json：已更新（commit abc1234）
- 接手第一步：`git pull origin dev && cd frontend && pnpm gen:api-types`
- 剩余：前端 checklist（见描述段「验收标准」）
```

## 场景四：接手别人交来的 Issue

新会话里只要有个 Issue 号，说 **`接手 #23`**：

1. 导出 Issue 再读（见下方脚本 `show`）
2. **描述段 = 契约**（以它为准）；**最后一条交接评论 = 你的起点**，前面的评论只作历史
3. 交接评论写「MR 待合」→ 先停下确认，**不要基于未合入的契约动手**
4. 复述「做哪端、起点在哪、验收几条」，确认后再编码
5. 你这端是最后一端 → MR 写 `Closes #ID`

---

## Issue 读写：一律走脚本

```bash
python .claude/scripts/glab_cn.py create  --body-file 草稿.md    # 建 Issue，标题取草稿首个 `# ` 行
python .claude/scripts/glab_cn.py update  23 --body-file 草稿.md  # 改描述（= 改规格）
python .claude/scripts/glab_cn.py comment 23 --body-file 草稿.md  # 追加评论（交接物）
python .claude/scripts/glab_cn.py check   23                     # 只读校验编码
python .claude/scripts/glab_cn.py show    23 --out out.md         # 导出 UTF-8 供阅读
```

脚本以**非 0 退出码**表示正文写坏或与草稿不一致 —— 非 0 就是没发成功，别往下走。

### 为什么必须用脚本

`glab` 1.108.0 **没有** `--description-file` / `--message-file`，正文只能经 `-d` / `-m` 走命令行参数。Windows 上参数要先经控制台码页（GBK）才交给进程，**长中文正文会被双重编码写坏**，而且 glab 不报错。

Issue **#15、#21 的描述就是这么整篇变成乱码的**，2026-07-24 才发现并从本地文件回填修复。脚本改走 `glab api --input <UTF-8 JSON>`，文件字节原样进 HTTP body，不经任何码页转换，并强制读回校验。

纯 ASCII 的短正文（如 `Ref #12`）可以继续用原生 `glab`。

### 另一个坑：终端显示的假乱码

在 GBK 终端里直接 `glab issue view 23 --comments`，**正文再干净也会显示成乱码**，容易误判成数据坏了。所以读 Issue 一律：

```bash
python .claude/scripts/glab_cn.py show 23 --out out.md
```

再打开 `out.md` 看。想确认数据本身好不好，用 `check`。

---

## 几条必须知道的规矩

- **每个外发动作都会停**：`git push`、建 Issue、建 MR、发评论，AI 都先把完整命令和正文摆出来，等你说「确认」才执行。
- **不自动关 Issue**：只靠 MR 合并时的 `Closes #ID`。
- **分支流**：本地功能分支 → MR 到 `dev` → `dev` 合入 `main`。
- **质量门**（ship 前必过）：前端 `pnpm typecheck` 0 error + `pnpm lint`；后端 `ruff check app` + 相关 `pytest`。
- **提交信息**：中文 conventional commit，`commitlint` 会校验。

完整表述见 [`.claude/rules/spec-workflow.md`](../.claude/rules/spec-workflow.md)。

---

## Cursor 用户

Cursor 没有技能机制，但规则是同一份（`.cursor/rules/spec.mdc` 以 `alwaysApply` 引用同一个规则文件）。按本文的阶段顺序手动走即可，Issue 读写同样用上面的脚本。

---

## 不用每次都走全套

改 bug、调样式、小重构，直接动手就行。这套流程是给**值得留下决策记录**的需求用的。

判断标准很简单：**这件事三个月后会有人问「当初为什么这么定」吗？** 会 —— 走 Spec；不会 —— 直接干。
