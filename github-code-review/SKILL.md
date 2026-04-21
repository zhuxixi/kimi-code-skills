---
name: github-code-review
description: |
  GitHub Pull Request 自动化代码审查工具。
  复刻 Claude Code 官方 code-review 插件工作流，使用多 Agent 并行审查 PR 变更，
  通过 issue 验证机制过滤误报，支持 CLAUDE.md 和 AGENTS.md 双重规范检查。
  使用 gh CLI 发布 PR 评论，无需额外 MCP 配置。
  
  触发词: "review pr", "审查 pr", "pr review", "github review", "review pull request"
---

# GitHub Code Review Skill

GitHub Pull Request 自动化代码审查工具。复刻 Claude Code 官方 code-review 插件工作流，使用多 Agent 并行审查 PR 变更，通过 issue 验证机制过滤误报，支持 CLAUDE.md 和 AGENTS.md 双重规范检查。使用 gh CLI 发布 PR 评论，无需额外 MCP 配置。

## 使用方式

在任意 Git 仓库中，使用以下方式触发审查：

```
review pr
审查 pr
pr review
github review
review pull request
```

可以带 PR 编号：

```
review pr #123
审查 pr 456
github review 789
review pull request owner/repo#101
```

如果不提供 PR 编号，默认使用当前分支关联的 PR。通过 `Shell` 执行 `gh pr view --json number` 获取当前分支关联的 PR 编号。如果当前分支没有关联的 PR，则提示用户明确提供 PR 编号。

提取 PR 编号的规则：
- 支持 `#123` 格式
- 支持直接数字如 `456`
- 支持 `owner/repo#123` 格式
- 如果用户没有提供，使用当前分支关联 PR

## 前置要求

1. **GitHub CLI (gh)** 已安装并认证：
   ```bash
   gh --version
   gh auth status
   ```
   如未认证，运行 `gh auth login` 完成认证。认证时需要确保有该仓库的读取和评论权限。

2. 当前目录在 Git 仓库中，且有 GitHub remote。可以通过 `git remote -v` 验证。

3. 用户对本仓库有读取 PR 和在 PR 下发表评论的权限。

## 执行流程

### Step 0: 审查类型判断

在正式审查之前，先判断本次审查的类型：首次完整审查、用户手动触发的增量审查、还是 watcher 完成后的自动 re-entry。

#### 0.1 检测 re-entry 场景

检查用户输入是否包含 `<system-reminder>` 且 mention "Background task completed" 和 "PR change watcher"：
- 如果是 → 直接跳转至【Re-entry 处理】章节，跳过 Step 1-9
- 如果不是 → 继续正常流程

#### 0.2 检测 previous review metadata

使用 `Shell` 执行：
```bash
gh pr view <PR> --json reviews --jq '.reviews[] | {body: .body, submitted_at: .submitted_at}'
```

筛选 Kimi Code CLI 发布的 review 评论：
1. 评论 body 包含 `"Generated with Kimi Code CLI"`
2. 评论 body 包含 `"<!-- kimi-cr-meta"`

按 `submitted_at` 排序，取最新一条。使用正则表达式提取 HTML Comment 中的 JSON metadata：
```
<!-- kimi-cr-meta\n(.*?)\n-->
```

解析 metadata 字段：`round`, `head_sha`, `previous_head_sha`, `issues`。

#### 0.3 判断分支

**有 previous review metadata？**
- 是 → 使用 `Shell` 执行 `gh pr view <PR> --json headRefOid --jq '.headRefOid'` 获取当前 head SHA
  - 当前 SHA == `previous_head_sha` → **无新 commit**
    - 输出：`"No new commits since Round-{round} review. Previous issues may still be open."`
    - 列出仍 open 的 issues
    - 不启动 watcher，结束
  - 当前 SHA != `previous_head_sha` → **有新 commit**
    - 标记当前为 `Round = round + 1`
    - 提取 `previous_issues = issues`
    - 进入【增量审查流程】，跳过 Step 1-9
- 否 → 首次审查 → 走完整流程（Round = 1）

#### 0.4 异常情况

- Metadata 提取失败（格式损坏或正则不匹配）→ 输出警告，fallback 到完整流程
- `gh pr view --json reviews` 失败 → 视为无 previous review，继续正常流程

### Step 1: PR 资格审查

使用 `Shell` 执行 `gh pr view <PR>` 和 `gh pr view <PR> --comments` 检查 PR 状态。

检查以下任一条件：
- PR 是否已关闭 (state: CLOSED)
- PR 是否为草稿 (isDraft: true)
- PR 是否是 trivial PR（如 dependabot、renovate、纯格式化、仅修改配置文件）
- PR 是否是自动化 PR（PR 标题或描述包含 "automated"、"bot" 等标识）
- PR 是否已有本 bot 发布的审查评论（在评论中搜索 "Code Review" 和 "Generated with"）

如果上述任一条件为真，立即停止执行，向用户说明原因，不继续审查。

重要例外：即使 PR 是 Claude 或 Kimi 生成的，仍然进行审查。Claude/Kimi 生成的 PR 也可能存在规范违规或逻辑错误，因此不跳过。

如何判断 trivial PR：
- 标题包含 "bump"、"update"、"dependabot"、"renovate"、"format"、"lint"
- 只修改了配置文件（如 `.github/workflows`、`.prettierrc`、锁文件）
- 变更行数极少且明显无意义

如何判断已有 bot 评论：
- 遍历 `gh pr view --comments` 输出
- 搜索评论内容中是否包含 "Code Review" 和 "Generated with Kimi Code CLI"
- 如果找到，说明已经审查过

### Step 2: 收集项目规范

使用 `Shell` 执行 `gh pr diff <PR> --name-only` 获取变更文件列表。

根据变更文件路径，读取以下规范文件（使用 `ReadFile` 工具）：
- 根目录的 `CLAUDE.md`
- 根目录的 `AGENTS.md`
- 变更文件所在子目录的 `CLAUDE.md`
- 变更文件所在子目录的 `AGENTS.md`

例如，如果变更文件为 `src/utils/helpers.py`，则需要检查：
- `./CLAUDE.md`
- `./AGENTS.md`
- `./src/CLAUDE.md`
- `./src/AGENTS.md`
- `./src/utils/CLAUDE.md`
- `./src/utils/AGENTS.md`

将读取到的规范文件内容汇总为一个规范上下文字符串，供后续审查 Agent 使用。如果某目录下没有规范文件，则跳过。

注意：子目录的规范文件优先于父目录。如果存在冲突，以最深目录的规范为准。

### Step 3: 获取 PR 摘要

使用 `Shell` 执行以下命令：
- `gh pr view <PR>` 获取 PR 标题和描述
- `gh pr diff <PR>` 获取完整 diff

使用 `Agent` 启动 summarizer subagent，输入包括：
- PR 标题
- PR 描述
- PR diff 内容

summarizer 输出一段简洁的变更摘要（不超过 300 字），帮助后续审查 Agent 快速理解变更意图。

### Step 4: 5 个并行审查 Agent

启动 5 个并行 `Agent`，每个接收相同的输入包：PR diff、变更摘要、PR 标题和描述、相关的规范文件内容。

**Agent 1: CLAUDE.md compliance checker**
- 检查变更是否违反 `CLAUDE.md` 中的明确规则
- 必须引用具体规则原文
- 仅关注 PR 修改的内容，不评论原有代码
- 输出 JSON 格式问题列表

**Agent 2: CLAUDE.md compliance checker (redundant)**
- 与 Agent 1 相同任务，独立运行
- 用于交叉验证，减少漏检和误报
- 两个独立的 checker 可以提高规范检查的召回率和准确率

**Agent 3: AGENTS.md compliance checker**
- 检查变更是否违反 `AGENTS.md` 中的明确规则
- 必须引用具体规则原文
- 注意区分适用于代码审查的规则 vs 仅适用于编码行为的规则
- 仅关注 PR 修改的内容

**Agent 4: Obvious bug scanner**
- 仅基于 diff 内容扫描明显 Bug
- 不读取额外上下文文件，避免引入外部噪音
- 关注：编译/解析错误、缺失导入、未解析引用、确定性逻辑错误
- 忽略风格问题和主观判断

**Agent 5: Logic / security analyzer**
- 分析变更代码的逻辑和安全性
- 仅关注被修改的代码
- 关注：资源泄漏、错误处理缺失、明显安全漏洞、竞态条件
- 忽略输入依赖的假设性问题

每个 Agent 输出 JSON 格式的问题列表：
```json
[
  {
    "description": "问题描述",
    "reason": "问题原因类别",
    "file": "文件路径",
    "lines": "行号范围",
    "suggestion": "修复建议"
  }
]
```

如果未发现任何问题，输出空列表 `[]`。

JSON 字段说明：
- `description`: 简洁描述问题，1-2 句话
- `reason`: 问题类别，如 "CLAUDE.md"、"AGENTS.md"、"bug"、"logic"
- `file`: 相对于仓库根目录的文件路径
- `lines`: 行号范围，格式如 "45-52"
- `suggestion`: 可选的修复建议

### Step 5: Issue 验证

对 Step 4 中发现的每一个 issue，启动一个并行 `Agent` 进行验证。

验证 agent 输入：
- 单个 issue 的完整信息
- PR diff
- 相关规范文件内容

验证 agent 执行以下检查：
1. 该 issue 描述的问题是否真实存在于代码中？
2. 对于规范类 issue（reason 包含 CLAUDE.md 或 AGENTS.md）：规则是否在规范文件中被明确表述，且适用于当前变更？
3. 对于 bug 类 issue（reason 包含 bug 或 logic）：代码逻辑是否确实错误？是否是 PR 引入的？
4. 该 issue 是否是误读代码导致的误报？

验证 agent 输出 JSON：
```json
{
  "valid": true,
  "explanation": "验证说明"
}
```

或：
```json
{
  "valid": false,
  "explanation": "该问题不存在，因为..."
}
```

只有 `valid: true` 的 issue 才会进入下一步。`valid: false` 的 issue 被直接丢弃。

issue 验证是本 Skill 的核心过滤机制。通过独立的验证 agent 重新审视每个问题，可以有效过滤误报，确保最终发布的问题都是高质量的、可操作的。

### Step 6: 过滤与汇总

对通过验证的 issue 进行后处理：

1. **丢弃无效 issue**：移除所有 `valid: false` 的 issue
2. **去重**：如果多个 issue 的 `file`、`lines`、`reason` 相同或高度相似，合并为一个
3. **排序优先级**：
   - 1. CLAUDE.md 合规问题
   - 2. AGENTS.md 合规问题
   - 3. bug 问题
   - 4. logic / security 问题

去重规则：
- 如果两个 issue 指向同一个文件、同一行范围、且原因相同，视为重复
- 如果描述内容高度相似（超过 80% 相似度），也视为重复
- 合并时保留描述更详细、建议更具体的一个

### Step 7: 最终资格审查

使用 `Shell` 执行 `gh pr view <PR> --json state` 再次检查 PR 状态。

如果 PR 已关闭 (closed) 或已合并 (merged)，立即停止执行，不发布评论。这是为了防止在审查过程中 PR 状态发生变化，避免对已关闭的 PR 发布无意义的评论。

最终资格审查是必要的，因为整个审查流程（特别是并行 Agent 执行）可能需要数分钟时间，在此期间 PR 状态可能发生变化。

### Step 8: 终端输出

输出 Markdown 格式的审查报告到终端。

如果发现问题的格式：
```markdown
### Code Review

Found N issues:

1. {description} ({reason})

https://github.com/owner/repo/blob/{full-sha}/{file}#L{start}-L{end}

2. {description} ({reason})

https://github.com/owner/repo/blob/{full-sha}/{file}#L{start}-L{end}
```

如果没有问题的格式：
```markdown
### Code Review

No issues found. Checked for bugs, CLAUDE.md and AGENTS.md compliance.
```

代码链接格式要求：
- 使用 `Shell` 执行 `git rev-parse HEAD` 获取完整 SHA（40 字符）
- 链接格式必须严格为：`https://github.com/owner/repo/blob/[sha]/path#L[start]-L[end]`
- 行范围至少包含 1 行上下文（评论目标行的前后至少各 1 行）
- 从 `gh pr diff` 中提取准确的行号信息
- 仓库 owner 和 repo 名可通过 `gh pr view --json headRepositoryOwner,headRepository` 获取

行号提取方法：
- 在 diff 中，新增内容以 `+` 开头，对应的行号在 diff hunk 头部标明
- 例如 `@@ -45,7 +67,9 @@` 表示旧文件从第 45 行开始，新文件从第 67 行开始
- 计算目标代码在新文件中的实际行号

### Step 9: 构建并发布 PR Review 评论（必须）

此步骤构建包含 metadata 的结构化 review 评论，并发布到 PR。

#### 9.1 构建评论 Body

评论由两部分组成：

**Part A: HTML Comment Metadata（机器可读，GitHub 渲染时隐藏）**

在评论 body 最开头插入：
```markdown
<!-- kimi-cr-meta
{"round":{round},"pr_number":{pr_number},"head_sha":"{head_sha}","previous_head_sha":"{previous_head_sha}","total_issues":{total},"resolved_count":{resolved},"new_count":{new},"issues":[{issues_json}],"timestamp":"{iso_timestamp}"}
-->
```

Metadata 字段：
- `round`: 当前轮次（首次审查为 1，增量审查为 N+1）
- `pr_number`: PR 编号
- `head_sha`: 当前 PR head commit 的完整 SHA（40 字符）
- `previous_head_sha`: 上一轮 review 时的 head SHA（Round-1 为 null）
- `total_issues`: 当前轮次统计的问题总数
- `resolved_count`: 本轮标记为 resolved 的问题数（Round-1 为 0）
- `new_count`: 本轮新发现的问题数
- `issues`: 问题数组，每个元素含 `status`（"open" 或 "resolved"）
- `timestamp`: ISO 8601 格式时间戳

**Part B: Markdown 人类可读部分**

Round-1 格式：
```markdown
### Code Review | Round-1

Found {N} issues:

1. {description} ({reason})

   https://github.com/owner/repo/blob/{sha}/{file}#L{start}-L{end}

🤖 Generated with Kimi Code CLI
```

Round-N（N ≥ 2，增量审查）格式：
```markdown
### Code Review | Round-{N} (Re-check)

Previous Round-{N-1} issues: {M}
- **Resolved**: {R} ({resolved_issue_descriptions})
- **Still open**: {M-R}

New issues found: {new_count}

#### Still Open from Previous Rounds

{remaining_issue_list}

#### New Issues

{new_issue_list}

🤖 Generated with Kimi Code CLI
```

All issues resolved 格式：
```markdown
### Code Review | Round-{N} (Re-check)

Previous Round-{N-1} issues: {M}
- **Resolved**: {M}
- **Still open**: 0

New issues found: 0

✅ **All issues resolved!**

🤖 Generated with Kimi Code CLI
```

#### 9.2 发布 Review 评论

使用 `Shell` 执行：
```bash
# 将 review body 写入临时文件（避免 shell 转义和长命令问题）
echo "<review_body>" > /tmp/kimi-cr-{pr_number}.md
gh pr review <PR> --comment --body-file /tmp/kimi-cr-{pr_number}.md
```

注意：
- 每轮审查都发布**新评论**，不编辑旧评论
- `<review_body>` 必须包含 HTML Comment metadata + Markdown 人类可读部分
- 必须包含 `"🤖 Generated with Kimi Code CLI"` 标识，用于后续识别
- 必须包含 `"### Code Review | Round-{N}"` 标题
- 此步骤必须执行。只要有资格审查通过，无论是否发现问题，都必须发布评论
- 如果 `gh pr review` 命令失败，向用户报告错误详情，不重复尝试

### Step 10: 启动 Background Watcher（可选）

此步骤在发现问题后启动后台监控，自动检测 PR 的新 commit。

#### 启动条件

同时满足：
1. Step 6 过滤后存在 `status="open"` 的 issues（即还有未解决的问题）
2. 当前为 Round-1 首次审查，或用户手动触发的增量审查（非 watcher 触发的 re-entry）

如果上述条件不满足（无 open issues，或当前是 watcher 触发的 re-entry 但已无问题）：
- 不启动 watcher
- 如果是 re-entry 且全部解决 → 输出 "All issues resolved ✓"
- 进程正常结束

#### 操作步骤

1. 使用 `Shell` 执行 `gh pr view <PR> --json headRefOid --jq '.headRefOid'` 获取当前 head SHA 作为 `base_sha`

2. 使用 `Agent` + `run_in_background=true` 启动 pr-watcher agent：
   - `description`: `"PR change watcher"`（简短，用于 TaskList 显示）
   - `prompt`: 包含 PR 编号、仓库 owner/repo、`base_sha`、轮询间隔（默认 300s）、最大等待时间（默认 3600s）
   - `timeout`: 3600（1 小时，与 `print_wait_ceiling_s` 配合）

3. 输出到终端：
   ```
   Found {N} open issues. Started background watcher to monitor fixes.
   Will re-review automatically when new commits are pushed.
   Task ID: {task_id}
   ```

#### 不启动 watcher 的场景

- 首次审查无问题 → 已输出 "No issues found"，进程结束
- re-entry 后增量审查无 open issues → 已输出 "All issues resolved ✓"，进程结束
- PR 在 Step 7 被判定为已关闭/已合并 → 已在 Step 7 停止

## HIGH SIGNAL 原则

### 只标记以下问题

- **编译/解析错误**：语法错误、无法通过编译的代码
- **缺失导入**：使用了未导入的模块、函数、类
- **未解析引用**：引用了不存在的变量、函数、属性
- **确定性逻辑错误**：代码逻辑明显错误，不依赖外部输入即可判定
- **明确规范违规**：`CLAUDE.md` 或 `AGENTS.md` 中明确、无歧义地禁止的行为（必须附带规则原文引用）

### 绝不标记以下问题

- **代码风格问题**：缩进、命名风格、括号位置等
- **一般代码质量问题**：函数过长、圈复杂度高等
- **输入依赖的潜在问题**："如果用户传入非法值..."、"如果网络超时..." 等假设性场景
- **主观性建议**："这里可以优化..."、"建议换一种写法..." 等没有明确对错的意见
- **PR 未修改的原有代码中的问题**：只审查变更内容
- **Linter / TypeChecker 可以捕获的问题**：如果静态分析工具已经能发现，不重复报告
- **已被 lint-ignore 注释忽略的规则**：代码中明确有 `eslint-disable`、`type: ignore` 等注释的，尊重开发者意图

## 边界情况处理

| 情况 | 处理方式 |
|------|----------|
| PR 已关闭/已合并 | Step 1 或 Step 7 捕获，停止执行并向用户说明 |
| PR 是草稿 | Step 1 捕获，停止执行并向用户说明 |
| PR 是 trivial/自动化 | Step 1 捕获，停止执行并向用户说明 |
| 已有 bot 评论 | Step 1 捕获，停止执行并向用户说明，避免重复审查 |
| PR 由 Claude/Kimi 生成 | 正常审查，不跳过 |
| 无 CLAUDE.md / AGENTS.md | 仅执行 bug scanner 和 logic analyzer |
| 大 PR（超过 50 个文件） | 正常处理，并行 Agent 保证效率 |
| 所有 issue 验证为无效 | 输出 "No issues found" |
| 审查过程中 PR 关闭 | Step 7 捕获，不发布评论 |
| `gh` 命令失败 | 向用户报告错误详情，停止执行 |
| 当前分支无关联 PR | 提示用户提供 PR 编号 |
| 提取不到完整 SHA | 使用 `git rev-parse HEAD` 重试，失败则报错 |
| Agent 返回格式错误的 JSON | 尝试解析，失败则忽略该 Agent 的输出 |
| diff 过大无法完整处理 | 仅分析前 500 行变更，其余部分标记为 "部分分析" |

## SubAgent 详细定义

### summarizer

**输入**: PR 标题、PR 描述、PR diff
**输出**: 一段简洁的变更摘要（不超过 300 字）

**任务**:
1. 阅读 PR 标题和描述，理解变更的意图和背景
2. 阅读 diff 内容，识别主要修改点
3. 忽略纯格式化和配置变更的细节
4. 输出简洁摘要，突出关键的功能变更、架构调整或重要修复

### claude-compliance-checker

**输入**: PR diff、PR 摘要、相关 CLAUDE.md 文件内容
**输出**: JSON 问题列表 `[{description, reason, file, lines, suggestion}]`

**任务**:
1. 阅读所有相关 CLAUDE.md 文件
2. 识别文件中明确陈述的规则和要求
3. 检查 PR 变更是否违反这些规则
4. 每个问题必须引用具体规则原文
5. 仅关注 PR 修改的内容，忽略原有代码
6. 如果没有明确违规，返回空列表
7. 不报告主观判断或模糊规则

reason 字段应包含 "CLAUDE.md"。

### agents-compliance-checker

**输入**: PR diff、PR 摘要、相关 AGENTS.md 文件内容
**输出**: JSON 问题列表 `[{description, reason, file, lines, suggestion}]`

**任务**:
1. 阅读所有相关 AGENTS.md 文件
2. 识别文件中明确陈述的规则和要求
3. 区分适用于代码审查的规则 vs 仅适用于编码行为的规则
4. 检查 PR 变更是否违反适用于审查的规则
5. 每个问题必须引用具体规则原文
6. 仅关注 PR 修改的内容，忽略原有代码
7. 如果没有明确违规，返回空列表

reason 字段应包含 "AGENTS.md"。

### bug-scanner

**输入**: PR diff
**输出**: JSON 问题列表 `[{description, reason, file, lines, suggestion}]`

**任务**:
1. 仅关注变更本身，不读取额外上下文文件
2. 扫描明显的逻辑错误、空值处理、竞态条件等
3. 关注严重 Bug，忽略小问题和吹毛求疵
4. 忽略可能的误报和假设性场景
5. 只报告确定性问题
6. 返回发现的问题列表，无问题返回空列表

reason 字段应为 "bug"。

### logic-analyzer

**输入**: PR diff、PR 摘要
**输出**: JSON 问题列表 `[{description, reason, file, lines, suggestion}]`

**任务**:
1. 分析变更代码的逻辑和安全性
2. 仅关注被修改的代码
3. 关注资源泄漏、错误处理、明显安全漏洞
4. 忽略输入依赖的假设性问题
5. 忽略风格问题和主观建议
6. 返回发现的问题列表，无问题返回空列表

reason 字段应为 "logic" 或 "security"。

### issue-validator

**输入**: 单个 issue、PR diff、相关规范文件内容
**输出**: JSON `{valid: boolean, explanation: string}`

**任务**:
1. 重新审查 issue 对应的目标代码
2. 判断问题是否真实存在于代码中
3. 对于规范类 issue：检查规则是否在规范文件中被明确表述，且适用于当前变更
4. 对于 bug 类 issue：检查代码逻辑是否确实错误，是否是 PR 引入的
5. 如果是误报，说明原因
6. 返回验证结果和解释

## 内部执行模板

当用户触发此 Skill 时，遵循以下精确执行流程：

1. **Step 0: 审查类型判断**
   - 检查用户输入是否为 watcher 触发的 re-entry（`<system-reminder>` + "PR change watcher"）
   - 如果是 re-entry → 跳转至【Re-entry 处理】
   - 否则：使用 `Shell` 执行 `gh pr view <PR> --json reviews` 获取 review 评论列表
   - 筛选含 `"Generated with Kimi Code CLI"` 和 `"<!-- kimi-cr-meta"` 的评论
   - 提取最新一轮的 JSON metadata
   - 对比 `previous_head_sha` 与当前 `headRefOid`
   - 无新 commit → 输出状态报告并结束
   - 有新 commit → 标记 `Round = N + 1`，进入【增量审查流程】
   - 无 previous review → `Round = 1`，继续下一步

2. **提取 PR 编号**
   - 从用户输入中提取 PR 号（支持 `#123`、直接数字、或 `owner/repo#123` 格式）
   - 如果没有提供，使用 `Shell` 执行 `gh pr view --json number` 获取当前分支关联的 PR
   - 如果当前分支无关联 PR，提示用户提供 PR 编号

3. **Step 1: PR 资格审查**
   - 使用 `Shell` 执行 `gh pr view <PR>` 获取 PR 状态
   - 使用 `Shell` 执行 `gh pr view <PR> --comments` 获取评论列表
   - 检查是否 closed、draft、trivial、automated、已有 bot 评论
   - 如不符合，返回说明原因并停止

4. **Step 2: 收集项目规范**
   - 使用 `Shell` 执行 `gh pr diff <PR> --name-only` 获取修改文件列表
   - 使用 `ReadFile` 读取根目录和变更文件所在目录的 `CLAUDE.md` 和 `AGENTS.md`
   - 汇总规范文件内容

5. **Step 3: 获取 PR 摘要**
   - 使用 `Shell` 执行 `gh pr view <PR>` 获取标题和描述
   - 使用 `Shell` 执行 `gh pr diff <PR>` 获取 diff
   - 使用 `Agent` 启动 summarizer subagent 总结变更

6. **Step 4: 5 个并行审查 Agent**
   使用 `Agent` 并行启动以下 subagent：
   - claude-compliance-checker（检查 CLAUDE.md 合规性）
   - claude-compliance-checker（第二个独立 checker）
   - agents-compliance-checker（检查 AGENTS.md 合规性）
   - bug-scanner（扫描明显 Bug）
   - logic-analyzer（分析逻辑和安全性）

7. **Step 5: Issue 验证**
   - 收集所有 Agent 发现的问题
   - 为每个 issue 使用 `Agent` 并行启动 issue-validator 验证
   - 收集每个验证结果

8. **Step 6: 过滤与汇总**
   - 过滤掉 `valid: false` 的 issue
   - 按 file、lines、reason 去重
   - 按优先级排序：CLAUDE.md → AGENTS.md → bug → logic

9. **Step 7: 最终资格审查**
   - 使用 `Shell` 执行 `gh pr view <PR> --json state` 检查 PR 是否仍然开放
   - 如已关闭或合并，停止并提示用户

10. **Step 8: 终端输出**
   - 使用 `Shell` 执行 `git rev-parse HEAD` 获取完整 SHA
   - 使用 `Shell` 执行 `gh pr view <PR> --json headRepositoryOwner,headRepository` 获取仓库信息
   - 格式化 Markdown 报告
   - 输出到终端

11. **Step 9: 构建并发布 PR Review 评论**
    - 构建包含 HTML Comment metadata 的结构化评论 body
    - 使用 `Shell` 执行 `gh pr review <PR> --comment --body-file /tmp/kimi-cr-{pr_number}.md`
    - 向用户确认完成

12. **Step 10: 启动 Background Watcher（可选）**
    - 条件：Step 6 过滤后存在 `status="open"` 的 issues，且当前为首次审查或手动触发的增量审查
    - 使用 `Shell` 执行 `gh pr view <PR> --json headRefOid` 获取当前 head SHA
    - 使用 `Agent` + `run_in_background=true` 启动 pr-watcher agent
    - 输出 watcher 启动信息
    - 不满足条件 → 不启动 watcher，正常结束

## Re-entry 处理

当 `--print` 模式因 background watcher 完成而 re-enter 时，主 agent 会收到一个 `<system-reminder>` 形式的通知。本章节定义该场景的处理流程。

### 触发条件

用户输入包含：
- `<system-reminder>` 标签
- `"Background task completed"`
- `"PR change watcher"`

满足以上条件时，跳过 Step 0-9 的正常流程，直接执行本章节定义的逻辑。

### Re-entry 执行流程

**Step R1: 解析 watcher 结果**

从 `<system-reminder>` 中提取 watcher 的 output 文本，解析状态：
- `"New commits detected"` → 进入增量审查
- `"All reviewers approved"` → 输出 approval 状态，不启动新 watcher
- `"PR state changed to CLOSED/MERGED"` → 输出 PR 状态变更，不启动新 watcher
- `"Timeout"` → 输出等待超时，不启动新 watcher

**Step R2: 获取当前状态（仅 "New commits detected" 分支）**

1. 使用 `Shell` 执行 `gh pr view <PR> --json headRefOid,state` 确认当前 PR 状态
2. 如果 `state` 为 `CLOSED` 或 `MERGED` → 输出 "PR already closed/merged" → 不启动 watcher → 结束
3. 使用 `Shell` 执行 `gh pr view <PR> --json reviews` 获取 review 评论列表
4. 筛选 Kimi CR 评论，提取最新一轮 metadata（同 Step 0.2）
5. 获取 `previous_issues` 列表和 `previous_head_sha`

**Step R3: 获取完整 diff**

使用 `Shell` 执行 `gh pr diff <PR>` 获取完整 diff。

**Step R4: 执行增量审查**

启动 delta-reviewer Agent（前台，非 background）：
- 输入：完整 diff + previous_issues + 相关规范文件
- 等待 delta-reviewer 完成
- 收集结果：resolved_issues / new_issues / unresolved_issues

**Step R5: 构建并发布 Round-N review 评论**

同 Step 9，但：
- `round = previous_round + 1`
- `previous_head_sha = previous_head_sha`
- `head_sha = 当前 headRefOid`
- `resolved_count = len(resolved_issues)`
- `new_count = len(new_issues)`
- issues 列表中已修复的标记 `status="resolved"`，未修复的标记 `status="open"`，新问题标记 `status="open"`

**Step R6: 决定是否继续监控**

- 如果 `unresolved_issues` 非空 或 `new_issues` 非空 → 启动新的 Background Watcher（同 Step 10）
- 如果全部为空 → 输出 "All issues resolved ✓"，不启动 watcher，结束

### 非 "New commits detected" 分支的处理

**"All reviewers approved"**：
- 输出：`"All reviewers have approved this PR. No further action needed."`
- 不启动 watcher

**"PR closed/merged"**：
- 输出：`"PR has been {state}. Stopping monitoring."`
- 不启动 watcher

**"Timeout"**：
- 输出：`"No new commits detected within timeout. Previous issues may still be open:"`
- 列出之前仍 open 的 issues
- 不启动 watcher

## 增量审查流程

当检测到 PR 有新的 commit（相对于上一轮 review）时，执行增量审查而非完整审查。本流程替代完整流程中的 Step 3-5。

### 适用场景

- Step 0 检测到 previous review metadata 且当前 head SHA != previous_head_sha
- Re-entry 处理中 watcher 检测到新 commit

### 输入

- `previous_issues`: 从上一轮 metadata 提取的问题列表（含 `id`, `description`, `reason`, `file`, `lines`, `status`, `first_round`）
- `previous_head_sha`: 上一轮 review 时的 head SHA
- `current_head_sha`: 当前 PR head SHA
- PR 完整 diff（`gh pr diff` 输出）
- 相关规范文件（CLAUDE.md / AGENTS.md）

### 执行步骤

**Step Δ1: 获取完整 diff**

使用 `Shell` 执行 `gh pr diff <PR>` 获取完整 diff。

**Step Δ2: 启动 delta-reviewer Agent**

使用 `Agent` 启动 delta-reviewer（前台，1 个 Agent）：

输入：
- PR 完整 diff
- `previous_issues` 列表
- `previous_head_sha`
- `current_head_sha`
- 相关规范文件内容

**Step Δ3: 收集 delta-reviewer 结果**

delta-reviewer 输出 JSON：
```json
{
  "resolved_issues": [
    {
      "original_id": "issue-1",
      "description": "...",
      "reason": "bug",
      "file": "src/auth.ts",
      "lines": "67-72",
      "resolution_note": "Error handling added in new commit"
    }
  ],
  "new_issues": [
    {
      "id": "issue-4",
      "description": "...",
      "reason": "logic",
      "file": "src/auth.ts",
      "lines": "100-105",
      "suggestion": "..."
    }
  ],
  "unresolved_issues": [
    {
      "original_id": "issue-3",
      "description": "...",
      "reason": "bug",
      "file": "src/auth.ts",
      "lines": "88-95"
    }
  ],
  "pass": false
}
```

**Step Δ4: 汇总问题列表**

构建当前轮次的完整 issues 列表：
- `resolved_issues` → 保留原 `id`，标记 `status="resolved"`
- `unresolved_issues` → 保留原 `id`，标记 `status="open"`
- `new_issues` → 生成新 `id`（如 `"issue-{max_id+1}"`），标记 `status="open"`，`first_round = current_round`

**Step Δ5: 继续至 Step 6（过滤与汇总）**

将汇总后的问题列表传入 Step 6，继续执行 Step 6-9-10 的标准流程。

### 与完整流程的区别

| 步骤 | 完整流程 | 增量流程 |
|------|---------|---------|
| Step 3 | summarizer + 5 个审查 Agent | delta-reviewer 1 个 Agent |
| Step 4 | 5 个并行审查 Agent | 由 delta-reviewer 替代 |
| Step 5 | 每个 issue 单独验证 | 由 delta-reviewer 内部完成对比验证 |
| 输出 | 全新问题列表 | resolved + new + unresolved 分类 |

## gh 命令参考

本 Skill 使用以下 `gh` 命令：

```bash
# 获取当前分支关联的 PR 编号
gh pr view --json number

# 获取 PR 详情
gh pr view <PR>

# 获取 PR 评论
gh pr view <PR> --comments

# 获取 PR 状态
gh pr view <PR> --json state

# 获取变更文件列表
gh pr diff <PR> --name-only

# 获取完整 diff
gh pr diff <PR>

# 获取仓库信息
gh pr view <PR> --json headRepositoryOwner,headRepository

# 发布 PR 评论
echo "<review_body>" > /tmp/kimi-cr-{pr_number}.md
gh pr review <PR> --comment --body-file /tmp/kimi-cr-{pr_number}.md
```

## 示例输出

### Round-1 发现问题时的输出

```markdown
<!-- kimi-cr-meta
{"round":1,"pr_number":123,"head_sha":"abc123def4567890123456789012345678901234","previous_head_sha":null,"total_issues":3,"resolved_count":0,"new_count":3,"issues":[{"id":"issue-1","description":"Missing error handling for OAuth callback","reason":"bug","file":"src/auth.ts","lines":"67-72","status":"open","first_round":1},{"id":"issue-2","description":"Inconsistent naming pattern","reason":"AGENTS.md","file":"src/utils.ts","lines":"23-28","status":"open","first_round":1},{"id":"issue-3","description":"Memory leak: OAuth state not cleaned up","reason":"bug","file":"src/auth.ts","lines":"88-95","status":"open","first_round":1}],"timestamp":"2026-04-21T10:00:00Z"}
-->

### Code Review | Round-1

Found 3 issues:

1. Missing error handling for OAuth callback (CLAUDE.md: "Always handle OAuth errors explicitly")

https://github.com/owner/repo/blob/abc123def4567890123456789012345678901234/src/auth.ts#L67-L72

2. Memory leak: OAuth state not cleaned up (bug: missing cleanup in finally block)

https://github.com/owner/repo/blob/abc123def4567890123456789012345678901234/src/auth.ts#L88-L95

3. Inconsistent naming pattern (AGENTS.md: "Use camelCase for all new functions")

https://github.com/owner/repo/blob/abc123def4567890123456789012345678901234/src/utils.ts#L23-L28

🤖 Generated with Kimi Code CLI
```

### 无问题时的输出（Round-1）

```markdown
<!-- kimi-cr-meta
{"round":1,"pr_number":123,"head_sha":"abc123def4567890123456789012345678901234","previous_head_sha":null,"total_issues":0,"resolved_count":0,"new_count":0,"issues":[],"timestamp":"2026-04-21T10:00:00Z"}
-->

### Code Review | Round-1

No issues found. Checked for bugs, CLAUDE.md and AGENTS.md compliance.

🤖 Generated with Kimi Code CLI
```

### Round-2 增量审查输出（部分问题已修复）

```markdown
<!-- kimi-cr-meta
{"round":2,"pr_number":123,"head_sha":"fed789abc0123456789012345678901234567890","previous_head_sha":"abc123def4567890123456789012345678901234","total_issues":1,"resolved_count":2,"new_count":0,"issues":[{"id":"issue-3","description":"Memory leak: OAuth state not cleaned up","reason":"bug","file":"src/auth.ts","lines":"88-95","status":"open","first_round":1}],"timestamp":"2026-04-21T10:30:00Z"}
-->

### Code Review | Round-2 (Re-check)

Previous Round-1 issues: 3
- **Resolved**: 2 (Missing error handling, Inconsistent naming)
- **Still open**: 1

New issues found: 0

#### Still Open from Round-1

3. Memory leak: OAuth state not cleaned up (bug: missing cleanup in finally block)

https://github.com/owner/repo/blob/fed789abc0123456789012345678901234567890/src/auth.ts#L88-L95

🤖 Generated with Kimi Code CLI
```

### Round-3 全部修复输出

```markdown
<!-- kimi-cr-meta
{"round":3,"pr_number":123,"head_sha":"aaa111bbb222333444555666777888999000aaaa","previous_head_sha":"fed789abc0123456789012345678901234567890","total_issues":0,"resolved_count":1,"new_count":0,"issues":[],"timestamp":"2026-04-21T11:00:00Z"}
-->

### Code Review | Round-3 (Re-check)

Previous Round-2 issues: 1
- **Resolved**: 1 (Memory leak)
- **Still open**: 0

New issues found: 0

✅ **All issues resolved!**

🤖 Generated with Kimi Code CLI
```

## 评论格式要求

代码链接必须遵循以下精确格式，否则 GitHub Markdown 无法正确渲染：

```
https://github.com/owner/repo/blob/[full-sha]/path/file.ext#L[start]-L[end]
```

要求：
- 使用完整 SHA（40 字符，不是缩写）
- `#L` 表示行号
- 行范围格式：`L[start]-L[end]`
- 至少包含 1 行上下文（评论目标行的前后至少各 1 行）

## 故障排除

### 问题：无法获取 PR 信息

**原因**：`gh` 未安装、未认证、或当前目录不在 Git 仓库中。

**解决**：
1. 运行 `gh --version` 确认已安装
2. 运行 `gh auth status` 确认已认证
3. 运行 `git remote -v` 确认有 GitHub remote

### 问题：审查后没有发布评论

**原因**：
- PR 在审查过程中被关闭或合并（Step 7 拦截）
- `gh pr review` 命令失败
- PR 未通过资格审查

**排查**：
1. 检查终端输出中的资格审查结果
2. 检查 Step 7 的输出
3. 检查 `gh pr review` 是否有错误信息

### 问题：Agent 输出格式错误

**原因**：SubAgent 没有按要求输出 JSON。

**解决**：
- 在 prompt 中明确要求输出 JSON
- 如果解析失败，忽略该 Agent 的输出，继续处理其他 Agent 的结果

### 问题：代码链接无法点击

**原因**：SHA 不完整、格式不正确、或行号计算错误。

**解决**：
- 确保使用 `git rev-parse HEAD` 获取完整 40 字符 SHA
- 确保格式严格为 `https://github.com/owner/repo/blob/[sha]/path#L[start]-L[end]`

## 常见误报类型

以下是审查 Agent 容易产生误报的场景，issue-validator 应特别注意识别：

1. **原有问题**：问题在 PR 之前就已经存在，不是本次变更引入的
2. **误读逻辑**：Agent 误解了代码的执行路径或条件分支
3. **过度推断**：从代码中推导出了没有直接证据支持的结论
4. **假设性问题**：基于某种假设场景（如极端输入）提出的问题
5. **规范误用**：将不适用于当前代码类型的规范规则强加于此
6. **上下文缺失**：由于未读取完整上下文而做出的错误判断

## 性能说明

- 5 个并行审查 Agent 可以同时运行，不受顺序依赖
- Issue 验证 Agent 的数量取决于发现的问题数量，也可以并行执行
- 大 PR 的审查时间可能较长，但并行架构可以充分利用并发能力
- 如果 diff 超过 500 行，建议仅分析前 500 行变更

## 设计原理

本 Skill 复刻 Claude Code 官方 code-review 插件的核心设计：

1. **多 Agent 并行**：从不同角度独立审查，避免单一视角的盲区
2. **冗余检查**：两个 CLAUDE.md checker 独立运行，通过交叉验证提高可靠性
3. **Issue 验证**：每个发现的问题都经过独立验证，大幅降低误报率
4. **HIGH SIGNAL**：只报告高置信度的问题，避免噪音淹没真正重要的问题
5. **终端与 PR 同步**：终端输出和 PR 评论完全一致，确保透明性

## 与其他工具的区别

| 特性 | github-code-review | 本地 linter | 人工审查 |
|------|-------------------|-------------|---------|
| 目标 | GitHub PR | 本地代码 | GitHub PR |
| 规范检查 | 支持 CLAUDE.md + AGENTS.md | 不支持 | 依赖审查者记忆 |
| 误报过滤 | 独立 issue 验证 | 规则驱动 | 人工判断 |
| 自动化 | 全自动 | 半自动 | 手动 |
| 输出 | PR 评论 | 终端/CI | PR 评论 |

## 最佳实践

### 对于项目维护者

1. **维护清晰的 CLAUDE.md 和 AGENTS.md**：明确的规范 = 更好的审查
2. **定期更新规范**：根据反复出现的问题更新规范文件
3. **将审查作为合并前的标准步骤**：在关键 PR 上运行此 Skill

### 对于开发者

1. **不要对 trivial PR 使用**：Skill 会自动跳过，无需手动触发
2. **审查结果作为起点**：Agent 发现是起点，不是终点，仍需人工判断
3. **积极反馈误报**：如果某类误报反复出现，更新规范文件或调整代码

## 限制说明

1. 本 Skill 仅支持 GitHub 仓库，不支持 GitLab、Bitbucket 等其他平台。
2. 本 Skill 依赖 `gh` CLI，无法在没有安装 `gh` 的环境中运行。
3. 对于极大的 PR（超过 1000 行变更），审查可能不够全面。
4. 本 Skill 不能替代完整的测试套件和人工代码审查。
5. 对于非代码文件的变更（如图片、二进制文件），无法进行有效审查。
6. 本 Skill 不具备执行代码或运行测试的能力，仅进行静态分析。

## 工具使用规范

- **必须**使用 `Shell` 工具执行所有 `gh` 和 `git` 命令
- **必须**使用 `Agent` 工具启动所有审查和验证 subagent
- **禁止**提及或假设任何 MCP 工具（如 `pull_request_read`、`add_issue_comment`）
- **禁止**创建 `scripts/` 目录或依赖外部资源文件
- **禁止**使用 `task` 或其他非 `Agent` 方式启动 subagent

## SubAgent Prompt 模板参考

以下是各 SubAgent 的推荐 prompt 结构，执行时应根据实际输入填充具体内容：

### claude-compliance-checker prompt 模板

```
你是一个代码规范审查员。你的任务是检查 PR 变更是否违反了 CLAUDE.md 中的明确规则。

输入：
- PR 摘要：{summary}
- PR diff：{diff}
- 相关 CLAUDE.md 内容：{claude_md_content}

要求：
1. 只关注 PR 修改的代码，忽略原有代码
2. 每个报告的问题必须引用 CLAUDE.md 中的具体规则原文
3. 不报告主观判断、模糊规则或风格问题
4. 输出 JSON 数组，每个元素包含 description、reason（必须包含 "CLAUDE.md"）、file、lines、suggestion
5. 如果没有明确违规，输出空数组 []
```

### agents-compliance-checker prompt 模板

```
你是一个代码规范审查员。你的任务是检查 PR 变更是否违反了 AGENTS.md 中的明确规则。

输入：
- PR 摘要：{summary}
- PR diff：{diff}
- 相关 AGENTS.md 内容：{agents_md_content}

要求：
1. 只关注 PR 修改的代码，忽略原有代码
2. 区分适用于代码审查的规则 vs 仅适用于编码行为的规则
3. 每个报告的问题必须引用 AGENTS.md 中的具体规则原文
4. 输出 JSON 数组，每个元素包含 description、reason（必须包含 "AGENTS.md"）、file、lines、suggestion
5. 如果没有明确违规，输出空数组 []
```

### bug-scanner prompt 模板

```
你是一个 Bug 扫描器。你的任务是基于 diff 内容扫描明显的 Bug。

输入：
- PR diff：{diff}

要求：
1. 仅基于 diff 内容判断，不读取额外文件
2. 只报告确定性问题：编译错误、缺失导入、未解析引用、明显逻辑错误
3. 忽略风格问题、假设性场景和主观判断
4. 输出 JSON 数组，每个元素包含 description、reason（必须为 "bug"）、file、lines、suggestion
5. 如果没有发现 Bug，输出空数组 []
```

### logic-analyzer prompt 模板

```
你是一个逻辑和安全分析器。你的任务是分析变更代码的逻辑正确性和安全性。

输入：
- PR 摘要：{summary}
- PR diff：{diff}

要求：
1. 仅关注被修改的代码
2. 关注资源泄漏、错误处理缺失、明显安全漏洞
3. 忽略输入依赖的假设性问题、风格问题和主观建议
4. 输出 JSON 数组，每个元素包含 description、reason（"logic" 或 "security"）、file、lines、suggestion
5. 如果没有发现问题，输出空数组 []
```

### issue-validator prompt 模板

```
你是一个 issue 验证器。你的任务是验证一个代码审查问题是否真实存在。

输入：
- 待验证 issue：{issue_json}
- PR diff：{diff}
- 相关规范文件内容：{guidelines}

要求：
1. 重新审视 issue 对应的目标代码
2. 判断问题是否真实存在
3. 对于规范类 issue：确认规则是否在规范文件中被明确表述且适用
4. 对于 bug 类 issue：确认代码逻辑是否确实错误且由 PR 引入
5. 输出 JSON：{"valid": boolean, "explanation": "string"}
```

## 审查结果示例解析

### 有效 issue 示例

```json
{
  "description": "函数返回了未初始化的变量，在错误路径中可能导致未定义行为",
  "reason": "bug",
  "file": "src/api/handlers.py",
  "lines": "45-52",
  "suggestion": "在错误路径中为 result 设置默认值或提前返回"
}
```

### 无效 issue 示例（应被 validator 过滤）

```json
{
  "description": "这个函数名不够描述性",
  "reason": "CLAUDE.md",
  "file": "src/utils.py",
  "lines": "12-15",
  "suggestion": "改为更具描述性的名字"
}
```
过滤原因：CLAUDE.md 中并未明确规定函数命名的具体要求，属于主观判断。

## 版本说明

本 Skill 基于 Claude Code 官方 code-review 插件的工作流进行复刻和本地化适配，主要变更包括：
- 使用 `gh` CLI 替代 MCP 工具进行 PR 读写
- 增加 AGENTS.md 规范检查支持
- 使用 issue 验证机制替代置信度评分机制
- 针对 Kimi CLI 的 `Shell` 和 `Agent` 工具进行适配
