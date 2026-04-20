---
name: summary-and-commit
description: 总结当前会话的工作内容，更新 SESSION.md 会话历史（保留最近5个详细摘要 + 较早的简要摘要），并提交所有更改到 git。当用户说 "sam"、"summary and commit"、"总结并提交" 或类似请求时使用。
---

# 总结并提交 (全局技能)

总结会话工作，提交更改，更新 SESSION.md 会话历史。

> **全局技能**: 该技能在所有项目中可用。它会在当前工作目录创建/更新会话历史文件。
> 
> **触发词**: "sam"、"summary and commit"、"总结并提交"

## 工作流程

当用户请求触发时，按顺序执行以下步骤：

### 步骤 1: 检查并提交当前更改

首先，检查仓库中是否有未提交的更改：

```bash
git status --porcelain
```

如果有更改：
1. 暂存所有更改：`git add -A`
2. 根据更改生成提交信息
3. 提交：`git commit -m "message"`
4. 记录提交哈希值用于最终报告

**提交信息格式：**
```
type: 简要描述

- 更改 1
- 更改 2
```

### 步骤 2: 生成会话摘要

根据对话历史和已完成的任务，生成简洁的摘要：

- **限制**: 每个会话最多 500 个汉字
- **包含**: 完成的主要任务、关键决策、结果
- **格式**: 项目符号或短段落
- **语言**: 如果用户使用中文，优先使用中文

### 步骤 3: 更新 SESSION.md

在项目根目录创建或更新 `SESSION.md` 文件。

**SESSION.md 格式：**
```markdown
# Session History

> 开发会话历史记录 | Development Session History
>
> 由 summary-and-commit skill 自动生成和更新
> Auto-generated and updated by summary-and-commit skill

---

## Recent Sessions (最近5次)

### Session {N} - {YYYY-MM-DD}

{详细摘要，不超过500汉字}

### Session {N-1} - {YYYY-MM-DD}

...

## Earlier Sessions (历史会话)

- **Session {N-6}** ({YYYY-MM-DD}): {一句话简短总结}
- **Session {N-7}** ({YYYY-MM-DD}): {一句话简短总结}

---

*Total: {N} sessions | Last Updated: {YYYY-MM-DD}*
```

**保留规则：**
- **最近 5 个会话**保留**完整详细摘要**（每个最多 500 汉字）
- 超过 5 个的会话：转换为**一行简要摘要**（类似 changelog）
- 最多保留 **40 个会话**（超出时删除最早的）

### 步骤 4: 分析并更新 AGENTS.md 和 CLAUDE.md（可选）

检查项目根目录是否存在 `AGENTS.md` 和/或 `CLAUDE.md`。

如果文件存在，执行以下操作：

1. **分析会话摘要**：判断本次会话是否包含需要更新到文档的重要内容：
   - 架构/设计变更
   - 技术栈调整
   - 开发规范更新
   - 工作流程变更
   - 重要决策记录
   - 安全/性能相关变更

2. **更新时间戳**：自动更新文件中的 `Last Updated: YYYY-MM-DD` 字段

3. **提示更新内容**：如果检测到重要变更，提示用户考虑手动更新文档内容

**执行命令**：

```bash
python ~/.config/agents/skills/summary-and-commit/scripts/analyze_and_update_docs.py "会话摘要"
```

**说明**：
- 脚本会智能分析会话内容，识别关键词
- 自动更新时间戳
- 如需内容更新，会给出提示建议
- 不会自动修改文档的实际内容

### 步骤 5: 提交会话文件更改（条件性）

检查步骤 3-4 中是否修改了任何文件：

```bash
git status --porcelain
```

如果有文件更改：
1. 暂存：`git add SESSION.md AGENTS.md CLAUDE.md`（仅存在的文件）
2. 提交：`git commit -m "docs: update session history"`
3. 报告新的提交哈希值

## 实现脚本

使用 `scripts/update_session.py` 脚本更新会话历史：

**脚本位置**: `~/.config/agents/skills/summary-and-commit/scripts/update_session.py`

**使用方法：**

```bash
# 方式 1: 直接传递参数
python ~/.config/agents/skills/summary-and-commit/scripts/update_session.py "会话摘要内容"

# 方式 2: 通过管道传递
echo "会话摘要内容" | python ~/.config/agents/skills/summary-and-commit/scripts/update_session.py

# 方式 3: 指定输出文件路径
python ~/.config/agents/skills/summary-and-commit/scripts/update_session.py "会话摘要内容" ./SESSION.md
```

**脚本功能：**
- 解析现有的 SESSION.md 文件
- 添加新会话记录
- 维护保留规则（最近5个详细，较早的简要，最多40个）
- 自动处理会话编号和日期

### 文档分析和更新脚本

使用 `scripts/analyze_and_update_docs.py` 脚本分析和更新项目文档：

**脚本位置**: `~/.config/agents/skills/summary-and-commit/scripts/analyze_and_update_docs.py`

**使用方法：**

```bash
# 分析和更新 AGENTS.md 和 CLAUDE.md
python ~/.config/agents/skills/summary-and-commit/scripts/analyze_and_update_docs.py "会话摘要"

# 分析指定文件
python ~/.config/agents/skills/summary-and-commit/scripts/analyze_and_update_docs.py "会话摘要" AGENTS.md
```

**脚本功能：**
- 智能分析会话摘要，识别重要关键词（架构、规范、决策等）
- 判断是否需要更新项目文档内容
- 自动更新 `Last Updated` 时间戳
- 给出更新建议提示

**检测关键词包括：**
- 架构/设计/重构/模块/组件
- 技术栈/框架/依赖/版本
- 规范/约定/标准/指南
- 流程/工作流/CI/CD/部署
- 决策/方案/选型/变更
- 安全/认证/性能/优化

## 输出格式

按以下顺序向用户报告：

```
## Session Summary

**已完成工作：**
- {任务1}
- {任务2}
- ...

**更改的文件：**
- {文件1} ({操作})
- {文件2} ({操作})
- ...

**会话历史：**
- SESSION.md: ✅ 已创建/更新 (Session {N}, 共 {N} 个)
- AGENTS.md: ✅ 已更新时间戳 / ⏭️ 未找到
- CLAUDE.md: ✅ 已更新时间戳 / ⏭️ 未找到

**提交记录：**
1. {commit_hash_1} - {commit_message_1} (代码提交)
2. {commit_hash_2} - docs: update session history (会话记录)
```

## 示例

用户："总结并提交"

助手响应：
```
## Session Summary

**已完成工作：**
- 配置 GitHub MCP Remote 模式访问组织私有仓库
- 成功列出并访问 boboyung 下 7 个私有仓库
- 使用 gh 命令将看板 Draft Items 转为正式 Issues

**更改的文件：**
- mcp.json (已修改)
- SESSION.md (已创建)

**会话历史：**
- SESSION.md: ✅ 已创建 (Session 1, 共 1 个)
- AGENTS.md: ✅ 已更新时间戳，检测到架构相关变更，建议检查内容
- CLAUDE.md: ⏭️ 未找到

**提交记录：**
1. 84ba8b4 - chore: configure GitHub MCP and migrate project board
2. a1b2c3d - docs: update session history
```

## 全局技能说明

### 文件位置

| 文件 | 用途 | 是否必需 |
|------|------|----------|
| `SESSION.md` | 主要会话历史（详细） | **是** |
| `AGENTS.md` | Agent 指南（仅更新时间戳） | 否（如存在） |
| `CLAUDE.md` | 开发者指南（仅更新时间戳） | 否（如存在） |

### Claude Code 兼容性

该技能适用于：
- **Kimi Code CLI**: 从 `~/.config/agents/skills/` 读取
- **Claude Code**: 从 `~/.claude/skills/` 读取

两者使用相同的 SKILL.md 格式，都可通过 "sam"、"summary and commit"、"总结并提交" 触发。
