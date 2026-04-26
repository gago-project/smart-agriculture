# Smart Agriculture 发布技能包

这套技能包把当前项目的真实发布链路，分别适配给：

- Codex
- Claude Code
- Cursor

目标不是抽象成“通用 Docker 发布手册”，而是固化当前这台维护机的真实链路：

1. `cloudflared`
2. `nginx` 监听 `127.0.0.1:5173`
3. Next Web 监听 `127.0.0.1:3000`
4. Python Agent 默认监听 `127.0.0.1:18010`

`ai.luyaxiang.com` 是正确域名。

## 文件位置

### Codex Skill（`.codex/skills/`）

- [`.codex/skills/smart-agriculture-release-workflow/SKILL.md`](.codex/skills/smart-agriculture-release-workflow/SKILL.md)
- [`.codex/skills/smart-agriculture-release-workflow/references/current-runtime.md`](.codex/skills/smart-agriculture-release-workflow/references/current-runtime.md)
- [`.codex/skills/smart-agriculture-release-workflow/agents/openai.yaml`](.codex/skills/smart-agriculture-release-workflow/agents/openai.yaml)

### Claude Code Skill（`.claude/skills/`）

- [`.claude/skills/smart-agriculture-release-workflow/SKILL.md`](.claude/skills/smart-agriculture-release-workflow/SKILL.md)
- [`.claude/skills/smart-agriculture-release-workflow/references/current-runtime.md`](.claude/skills/smart-agriculture-release-workflow/references/current-runtime.md)

### Cursor Rule（`.cursor/rules/`）

- [`.cursor/rules/smart-agriculture-release-workflow.mdc`](.cursor/rules/smart-agriculture-release-workflow.mdc)

## 安装方式

技能文件已直接放置在仓库规范路径中，无需手动复制安装。

### Codex

技能文件已位于仓库内 `.codex/skills/smart-agriculture-release-workflow/`，Codex 在执行时会自动从当前仓库的 `.codex/skills/` 目录加载。

若需复制到全局：

```bash
cp -R .codex/skills/smart-agriculture-release-workflow "${CODEX_HOME:-$HOME/.codex}/skills/"
```

### Claude Code

技能文件已位于仓库内 `.claude/skills/smart-agriculture-release-workflow/`，Claude Code 在当前项目中会自动读取。

若需复制到全局：

```bash
cp -R .claude/skills/smart-agriculture-release-workflow ~/.claude/skills/
```

### Cursor

Cursor 使用 Rules 机制。规则文件已位于 `.cursor/rules/smart-agriculture-release-workflow.mdc`，在此仓库中直接生效，无需额外操作。

## 建议触发语句

### Codex / Claude Code

- “使用 smart-agriculture-release-workflow 技能，把最新代码更新到 localhost 和 ai.luyaxiang.com”
- “按 smart-agriculture-release-workflow 检查当前发布链路有没有问题”

### Cursor

- “按 smart-agriculture-release-workflow 规则检查这个仓库的发布链路”
- “按当前 ai.luyaxiang.com 的真实运行方式，更新并验活服务”

## 这个技能包解决的核心问题

- 防止误把 `ai.yaxianglu.com` 当成目标域名
- 防止误以为当前生产入口是 Docker
- 防止只看 `/api/health` 就误判发布成功
- 防止误重启 `nginx` / `cloudflared`，而不是实际坏掉的 `3000` / `18010`
