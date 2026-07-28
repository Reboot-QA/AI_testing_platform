# 项目专属技能（.claude/skills/）

本目录放**只对本仓库有意义**的技能（进 git，团队共享）。跨项目通用的技能放个人级 `~/.claude/skills/`。

## 约定

- 每个技能一个子目录，内含 `SKILL.md`，YAML frontmatter 必须有 `name` 与 `description`（`description` 要写清触发时机，Claude 据此决定何时调用）。
- 技能正文写「流程/步骤」，引用仓库既有文件与约定（如 `.claude/rules/*.md`、`services/apifox/*`），不复制规则正文。

## 现有

Spec 驱动工作流四件套（规则见 `.claude/rules/spec-workflow.md`）：

- `grill-with-docs/` —— ① 深度对话对齐，只问不写。
- `to-spec/` —— ② 提炼结构化 Spec，半自主发 GitLab Issue（Spec 正文只存 Issue，仓库内不留文件）。
- `implement-and-ship/` —— ③ 对照 Issue 编码 + 过质量门 + 半自主建 MR。
- `handoff/` —— 横向：只做一端就停时把交接物写成 Issue 评论交出／接手时从评论重建上下文。

其他：

- `apifox-usecase-gen/` —— apifox 模块接口用例生成套路（骨架，待补全）。
