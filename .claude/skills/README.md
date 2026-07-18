# 项目专属技能（.claude/skills/）

本目录放**只对本仓库有意义**的技能（进 git，团队共享）。跨项目通用的技能放个人级 `~/.claude/skills/`。

## 约定

- 每个技能一个子目录，内含 `SKILL.md`，YAML frontmatter 必须有 `name` 与 `description`（`description` 要写清触发时机，Claude 据此决定何时调用）。
- 技能正文写「流程/步骤」，引用仓库既有文件与约定（如 `.claude/rules/*.md`、`services/apifox/*`），不复制规则正文。

## 现有

- `apifox-usecase-gen/` —— apifox 模块接口用例生成套路（骨架，待补全）。
