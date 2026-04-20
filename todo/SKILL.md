---
name: todo
description: Use when user says "记录todo", "添加待办", "新建任务", "创建待办", "查看待办", "看板状态", "列出任务", "待办事项", "更新任务状态", "标记完成", "删除待办", "what's next", "下一步", or wants to manage GitHub issues as todo items for any repository
---

# GitHub Todo Manager

使用 GitHub CLI (`gh`) 管理仓库的 Issues 作为待办事项。

## Core Principle
通过 GitHub Issues + 标签管理待办，适用于任何仓库，无需预配置项目ID。

## 前置要求

确保已安装 GitHub CLI 并已认证：

```bash
# 检查 gh 是否安装
gh --version

# 如果未安装，访问 https://cli.github.com/ 下载

# 登录认证
gh auth login

# 验证认证状态
gh auth status
```

---

## When to Use

- 用户说 "记录todo"、"添加待办"、"新建任务"、"创建待办"
- 用户说 "查看待办"、"看板状态"、"列出任务"、"待办事项"
- 用户说 "更新任务状态"、"标记完成"
- 用户说 "删除待办"、"移除任务"
- 用户说 "what's next"、"下一步"、"next tasks"

## Workflow

### 1. 确定目标仓库

**优先基于当前目录自动获取远程仓库信息：**

```bash
# ===== Bash/Ubuntu =====
# 从 git remote 获取当前仓库的 owner/repo
REPO_INFO=$(git remote get-url origin 2>/dev/null | sed -E 's/.*github\.com[:/]([^/]+)\/([^/]+)\.git$/\1\/\2/')
echo "当前仓库: $REPO_INFO"

# 如果上面的命令失败，尝试另一种格式
if [ -z "$REPO_INFO" ]; then
  REPO_INFO=$(git remote get-url origin 2>/dev/null | sed -E 's/.*github\.com[:/]([^/]+)\/([^/]+)$/\1\/\2/')
fi

# ===== PowerShell =====
# 从 git remote 获取当前仓库的 owner/repo
$remoteUrl = git remote get-url origin 2>$null
if ($remoteUrl -match 'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$') {
    $REPO_INFO = "$($matches[1])/$($matches[2])"
    Write-Host "当前仓库: $REPO_INFO"
}
```

**如果当前目录不是 git 仓库或无法获取远程信息，再询问用户：**

```
"请提供仓库信息（格式：owner/repo，例如：boboyung/boktionary）"
```

---

### 2. 查看待办（最常用）

使用 `gh issue list` 列出所有 open 状态的 issues：

```bash
# ===== Bash/Ubuntu =====
# 列出所有 open issues
gh issue list --repo owner/repo --state open

# 只列出带 todo 标签的
gh issue list --repo owner/repo --state open --label todo

# 按状态筛选
gh issue list --repo owner/repo --state open --label todo --json number,title,labels,createdAt

# ===== PowerShell =====
# 列出所有 open issues
gh issue list --repo owner/repo --state open

# 只列出带 todo 标签的
gh issue list --repo owner/repo --state open --label todo

# 获取 JSON 格式便于处理
gh issue list --repo owner/repo --state open --label todo --json number,title,labels,createdAt | ConvertFrom-Json
```

---

### 3. 添加待办

使用 `gh issue create` 创建新 issue：

```bash
# ===== Bash/Ubuntu =====
gh issue create --repo owner/repo \
  --title "[P1] 任务标题" \
  --body "## 任务描述

详细描述任务内容

## 待办
- [ ] 步骤1
- [ ] 步骤2

## 备注
补充信息" \
  --label todo,enhancement

# ===== PowerShell =====
gh issue create --repo owner/repo `
  --title "[P1] 任务标题" `
  --body "## 任务描述`n`n详细描述任务内容`n`n## 待办`n- [ ] 步骤1`n- [ ] 步骤2`n`n## 备注`n补充信息" `
  --label todo,enhancement
```

---

### 4. 更新任务状态

通过 `gh issue edit` 修改 labels 或使用 `gh issue close`/`gh issue reopen`：

```bash
# ===== Bash/Ubuntu =====

# 标记为进行中：添加 in-progress 标签
gh issue edit 123 --repo owner/repo --add-label in-progress

# 标记为完成：关闭 issue（并添加 done 标签）
gh issue close 123 --repo owner/repo --comment "已完成"
gh issue edit 123 --repo owner/repo --add-label done

# 重新打开
gh issue reopen 123 --repo owner/repo

# ===== PowerShell =====

# 标记为进行中：添加 in-progress 标签
gh issue edit 123 --repo owner/repo --add-label in-progress

# 标记为完成：关闭 issue（并添加 done 标签）
gh issue close 123 --repo owner/repo --comment "已完成"
gh issue edit 123 --repo owner/repo --add-label done

# 重新打开
gh issue reopen 123 --repo owner/repo
```

---

### 5. 删除待办

直接关闭 issue（GitHub issue 无法真正删除，只能关闭）：

```bash
# ===== Bash/Ubuntu =====
# 关闭待办（标记为 not_planned）
gh issue close 123 --repo owner/repo --reason not_planned --comment "取消此任务"

# ===== PowerShell =====
# 关闭待办（标记为 not_planned）
gh issue close 123 --repo owner/repo --reason not_planned --comment "取消此任务"
```

---

## 状态标签约定

| 状态 | 标签组合 | 含义 |
|------|----------|------|
| Todo | `todo` (open) | 待处理 |
| In Progress | `todo` + `in-progress` (open) | 进行中 |
| Done | `todo` + `done` (closed) | 已完成 |
| Cancelled | `todo` (closed, not_planned) | 已取消 |

---

## 常用查询模式

```bash
# ===== Bash/Ubuntu =====

# 获取所有待办（按状态分组）
REPO="owner/repo"

# 待处理（open + todo 标签，但没有 in-progress 标签）
echo "📋 Todo:"
gh issue list --repo $REPO --state open --label todo --json number,title,createdAt | jq -r '.[] | "#\(.number): \(.title)"'

# 进行中
gh issue list --repo $REPO --state open --label todo --label in-progress --json number,title,createdAt | jq -r '.[] | "#\(.number): \(.title)"'

# 已完成（最近10个）
echo "✅ Done:"
gh issue list --repo $REPO --state closed --label todo --limit 10 --json number,title,closedAt | jq -r '.[] | "#\(.number): \(.title)"'

# ===== PowerShell =====

# 获取所有待办（按状态分组）
$REPO="owner/repo"

# 待处理
echo "📋 Todo:"
gh issue list --repo $REPO --state open --label todo --json number,title,createdAt | ConvertFrom-Json | ForEach-Object { "#$($_.number): $($_.title)" }

# 进行中
echo "🔄 In Progress:"
gh issue list --repo $REPO --state open --label todo --label in-progress --json number,title,createdAt | ConvertFrom-Json | ForEach-Object { "#$($_.number): $($_.title)" }

# 已完成（最近10个）
echo "✅ Done:"
gh issue list --repo $REPO --state closed --label todo --limit 10 --json number,title,closedAt | ConvertFrom-Json | ForEach-Object { "#$($_.number): $($_.title)" }
```

---

## 高级搜索

使用 `gh search issues` 进行更复杂的搜索：

```bash
# ===== Bash/Ubuntu =====

# 搜索所有 open issues
gh search issues --repo owner/repo --state open

# 搜索特定标签的 issues
gh search issues --repo owner/repo --state open --label todo

# 搜索分配给特定用户的 issues
gh search issues --repo owner/repo --state open --assignee @me

# 搜索包含特定关键词的 issues
gh search issues "性能优化" --repo owner/repo --state open

# ===== PowerShell =====

# 搜索所有 open issues
gh search issues --repo owner/repo --state open

# 搜索特定标签的 issues
gh search issues --repo owner/repo --state open --label todo

# 搜索分配给特定用户的 issues
gh search issues --repo owner/repo --state open --assignee @me
```

---

## 最佳实践

1. **自动添加 todo 标签**：创建待办时始终添加 `todo` 标签
2. **使用优先级前缀**：`[P0]` `[P1]` `[P2]` 在标题中表示优先级
3. **清晰的描述模板**：包含任务描述、检查清单、备注等部分
4. **状态转换**：使用 labels 而非 milestones 来管理看板状态（更轻量）

---

## 示例对话

**用户**: "查看当前待办"

**Kimi**:
```bash
# Bash/Ubuntu
gh issue list --repo owner/repo --state open --label todo --json number,title,labels,createdAt

# PowerShell
gh issue list --repo owner/repo --state open --label todo --json number,title,labels,createdAt | ConvertFrom-Json
```

---

**用户**: "记录一个 todo：优化数据库查询性能"

**Kimi**:
```bash
# Bash/Ubuntu
gh issue create --repo owner/repo \
  --title "[P1] 优化数据库查询性能" \
  --body "## 任务描述
优化数据库查询性能，提升响应速度。

## 待办
- [ ] 分析慢查询日志
- [ ] 添加必要索引
- [ ] 优化查询语句
- [ ] 性能测试验证

## 备注
- 目标：查询时间 < 100ms
- 相关表：words, pronunciations" \
  --label todo,performance

# PowerShell
gh issue create --repo owner/repo `
  --title "[P1] 优化数据库查询性能" `
  --body "## 任务描述`n优化数据库查询性能，提升响应速度。`n`n## 待办`n- [ ] 分析慢查询日志`n- [ ] 添加必要索引`n- [ ] 优化查询语句`n- [ ] 性能测试验证`n`n## 备注`n- 目标：查询时间 < 100ms`n- 相关表：words, pronunciations" `
  --label todo,performance
```

---

## 常用 gh issue 命令速查表

| 操作 | 命令 |
|-----|------|
| Issue 列表 | `gh issue list --repo owner/repo --state open` |
| 创建 Issue | `gh issue create --repo owner/repo --title "xxx" --body "yyy" --label todo` |
| 查看 Issue | `gh issue view NUMBER --repo owner/repo` |
| 关闭 Issue | `gh issue close NUMBER --repo owner/repo` |
| 重新打开 | `gh issue reopen NUMBER --repo owner/repo` |
| 添加评论 | `gh issue comment NUMBER --repo owner/repo --body "xxx"` |
| 编辑标签 | `gh issue edit NUMBER --repo owner/repo --add-label xxx` |
| 搜索 Issues | `gh search issues --repo owner/repo --state open --label todo` |
