# kimi-code-skills

Kimi CLI skills collection focused on code review and development workflows.

> 将 Kimi CLI 自定义 skills 集中管理，方便跨设备同步和分享。

## Skills 列表

| Skill | 描述 | 触发词 |
|-------|------|--------|
| [github-code-review](./github-code-review) | GitHub PR 自动化代码审查 | `review pr`, `审查 pr`, `pr review` |
| [issue-creator](./issue-creator) | 会话 Issue 创建器 | `创建 issue`, `记录到 issue`, `总结成 issue` |
| [issue-implementor](./issue-implementor) | GitHub Issue 实现工作流 | `实现 issue`, `开发 issue` |
| [summary-and-commit](./summary-and-commit) | 总结并提交会话内容 | `sam`, `summary and commit`, `总结并提交` |
| [todo](./todo) | GitHub Issues 看板管理 | `记录todo`, `添加待办`, `看板状态` |
| [markdown-pro](./markdown-pro) | 专业 Markdown 文档生成 | `生成文档`, `创建 changelog`, `生成 README` |

## 安装

将本仓库中的 skill 目录复制到 Kimi CLI 的 skills 目录：

```bash
# macOS/Linux
cp -r ./<skill-name> ~/.config/agents/skills/

# Windows
Copy-Item -Recurse .\<skill-name> $env:USERPROFILE\.config\agents\skills\
```

或使用符号链接（推荐，方便同步更新）：

```bash
# macOS/Linux
ln -s $(pwd)/<skill-name> ~/.config/agents/skills/<skill-name>

# Windows (PowerShell, 管理员)
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.config\agents\skills\<skill-name>" -Target "$(pwd)\<skill-name>"
```

## 定位

当前主要聚焦 **Code Review** 工作流：

- PR 自动审查（github-code-review）
- Issue 追踪管理（issue-creator / issue-implementor / todo）
- 会话总结与提交（summary-and-commit）

后续会逐步扩展更多开发工作流相关的 skill。

## 参考

- [Kimi CLI](https://github.com/MoonshotAI/kimi-cli)
- [SKILL.md 规范](https://github.com/MoonshotAI/kimi-cli/blob/main/docs/skills.md)
