# Incremental Code Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add incremental re-review and background watcher capabilities to the `github-code-review` skill, enabling automatic re-check after PR fixes in `--print` mode.

**Architecture:** The skill gains (1) a Step 0 that detects previous Kimi review comments via HTML-comment metadata, (2) structured review comments with embedded JSON metadata, (3) a background watcher agent that polls for new commits, and (4) a re-entry flow triggered by watcher completion notifications in `--print` mode.

**Tech Stack:** Markdown (SKILL.md), `gh` CLI, Kimi CLI `Agent` + `Shell` tools.

---

## File Structure

| File | Action | Responsibility |
|------|--------|--------------|
| `github-code-review/SKILL.md` | Modify | The only file to change. All new logic lives inside this skill document. |

---

## Task 1: Add Step 0 — Review Type Detection

**Files:**
- Modify: `github-code-review/SKILL.md` — Insert new section after "## 执行流程" heading and before "### Step 1: PR 资格审查"

- [ ] **Step 1.1: Insert Step 0 section**

  Locate the line:
  ```markdown
  ## 执行流程
  ```
  
  After it, insert:
  ```markdown
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
  - 否 → 首次审查，`Round = 1`，继续 Step 1

  #### 0.4 异常情况

  - Metadata 提取失败（格式损坏或正则不匹配）→ 输出警告，fallback 到完整流程
  - `gh pr view --json reviews` 失败 → 视为无 previous review，继续正常流程
  ```

- [ ] **Step 1.2: Update "内部执行模板" to include Step 0**

  Locate in the "内部执行模板" section:
  ```markdown
  1. **提取 PR 编号**
     - 从用户输入中提取 PR 号...
  ```

  Change the numbering so Step 0 comes first. Replace the first item with:
  ```markdown
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
     - 从用户输入中提取 PR 号...
  ```

  Then renumber all subsequent steps (2→3, 3→4, etc.).

- [ ] **Step 1.3: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add Step 0 review type detection with metadata extraction"
  ```

---

## Task 2: Modify Step 9 — Publish Structured Review Comments with Metadata

**Files:**
- Modify: `github-code-review/SKILL.md` — Replace the Step 9 section and the "示例输出" / "评论格式要求" sections

- [ ] **Step 2.1: Replace Step 9 content**

  Locate:
  ```markdown
  ### Step 9: 发布 PR 评论（必须）

  使用 `Shell` 执行以下命令发布 PR 评论：
  ...
  ```

  Replace everything from "### Step 9" through the end of that subsection with:
  ```markdown
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
  - `issues`: 问题数组，每个元素含 `id`, `description`, `reason`, `file`, `lines`, `status`（"open" 或 "resolved"）, `first_round`
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
  - 此步骤必须执行。只要有资格审查通过，无论是否发现问题，都必须发布评论
  - 如果 `gh pr review` 命令失败，向用户报告错误详情，不重复尝试
  ```

- [ ] **Step 2.2: Update "示例输出" section**

  Locate the "### 发现问题时的输出" subsection under "## 示例输出". Replace it with:
  ```markdown
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

  Also replace "### 无问题时的输出" with:
  ```markdown
  ### 无问题时的输出（Round-1）

  ```markdown
  <!-- kimi-cr-meta
  {"round":1,"pr_number":123,"head_sha":"abc123def4567890123456789012345678901234","previous_head_sha":null,"total_issues":0,"resolved_count":0,"new_count":0,"issues":[],"timestamp":"2026-04-21T10:00:00Z"}
  -->

  ### Code Review | Round-1

  No issues found. Checked for bugs, CLAUDE.md and AGENTS.md compliance.

  🤖 Generated with Kimi Code CLI
  ```
  ```

- [ ] **Step 2.3: Add Round-N example output**

  After the "无问题时的输出" example, insert:
  ```markdown
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
  ```

- [ ] **Step 2.4: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add structured review comments with HTML metadata"
  ```

---

## Task 3: Add Step 10 — Launch Background Watcher

**Files:**
- Modify: `github-code-review/SKILL.md` — Insert after Step 9 section

- [ ] **Step 3.1: Insert Step 10 section**

  After the end of Step 9 (after "如果 `gh pr review` 命令失败..."), insert:
  ```markdown
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
  ```

- [ ] **Step 3.2: Update "内部执行模板" to include Step 10**

  In the "内部执行模板" section, after the current Step 10 (which will become Step 11 after renumbering from Task 1), add:
  ```markdown
  11. **Step 10: 启动 Background Watcher（可选）**
      - 条件：Step 6 过滤后存在 `status="open"` 的 issues，且当前为首次审查或手动触发的增量审查
      - 使用 `Shell` 执行 `gh pr view <PR> --json headRefOid` 获取当前 head SHA
      - 使用 `Agent` + `run_in_background=true` 启动 pr-watcher agent
      - 输出 watcher 启动信息
      - 不满足条件 → 不启动 watcher，正常结束
  ```

- [ ] **Step 3.3: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add Step 10 background watcher launch"
  ```

---

## Task 4: Add "Re-entry 处理" Chapter

**Files:**
- Modify: `github-code-review/SKILL.md` — Insert before "## gh 命令参考"

- [ ] **Step 4.1: Insert Re-entry 处理 chapter**

  Locate "## gh 命令参考". Before it, insert:
  ```markdown
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
  - `"Timeout"` → 输出等待超时提醒，不启动新 watcher

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
  ```

- [ ] **Step 4.2: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add re-entry handling chapter for watcher notifications"
  ```

---

## Task 5: Add "增量审查流程" Chapter

**Files:**
- Modify: `github-code-review/SKILL.md` — Insert after the "Re-entry 处理" chapter

- [ ] **Step 5.1: Insert 增量审查流程 chapter**

  After "## Re-entry 处理", before "## gh 命令参考", insert:
  ```markdown
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
  ```

- [ ] **Step 5.2: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add incremental review flow chapter"
  ```

---

## Task 6: Add New SubAgent Definitions

**Files:**
- Modify: `github-code-review/SKILL.md` — Add to "## SubAgent 详细定义" section

- [ ] **Step 6.1: Add pr-watcher SubAgent**

  After "### issue-validator" subsection in "## SubAgent 详细定义", insert:
  ```markdown
  ### pr-watcher

  **输入**: PR 编号、仓库 owner/repo、监控开始时的 head SHA (`base_sha`)、轮询间隔、最大等待时间
  **输出**: 状态文本（"New commits detected" / "All reviewers approved" / "PR closed" / "Timeout"）

  **任务**:
  1. 记录 `start_time`
  2. 循环执行（最多 `max_iterations = max_wait_s / poll_interval_s` 次）：
     a. `Shell: sleep {poll_interval_s}`
     b. `Shell: gh pr view {PR} --json headRefOid,state,reviewDecision`
     c. 如果 `state` 为 `CLOSED` 或 `MERGED` → 输出 `"PR state changed to {state}"` → 结束
     d. 如果 `reviewDecision` 为 `APPROVED` → 输出 `"All reviewers approved"` → 结束
     e. 如果当前 `headRefOid` != `base_sha` → 输出 `"New commits detected. Previous SHA: {base_sha}, Current SHA: {current_sha}"` → 结束
     f. 检查是否超过 `max_wait_time`
  3. 超时 → 输出 `"Timeout: no new commits after {max_wait_s}s"`

  **约束**:
  - 只使用 `Shell` 工具执行 `gh` 命令
  - 不读取代码文件
  - 不做代码分析
  - 每次循环输出当前状态（如 `"Round X: SHA unchanged, state=OPEN, decision=PENDING"`）
  ```

- [ ] **Step 6.2: Add delta-reviewer SubAgent**

  After "### pr-watcher", insert:
  ```markdown
  ### delta-reviewer

  **输入**: PR 完整 diff、previous_issues 列表、previous_head_sha、current_head_sha、相关规范文件
  **输出**: JSON `{resolved_issues, new_issues, unresolved_issues, pass}`

  **任务**:
  1. 对比 `previous_issues` 和当前 diff：
     - 遍历每个 previous issue，检查其 `file` + `lines` 范围是否在 diff 中被修改
     - 如果代码行被修改 → 仔细阅读对应代码，判断是否已修复 → 加入 `resolved_issues`
     - 如果代码行未修改 → 加入 `unresolved_issues`
  2. 审查 diff 中新增/修改的代码（排除已确认 resolved 的部分），发现新问题 → 加入 `new_issues`
     - **特别注意**：修复 commit 可能引入新的问题，不要只关注原有问题的修复状态
     - 仔细审查修复代码本身的正确性
  3. 对于规范类问题，检查 CLAUDE.md / AGENTS.md 中相关规则是否仍适用

  **输出 JSON 格式**:
  ```json
  {
    "resolved_issues": [
      {
        "original_id": "issue-1",
        "description": "Missing error handling for OAuth callback",
        "reason": "bug",
        "file": "src/auth.ts",
        "lines": "67-72",
        "resolution_note": "Error handling added in new commit"
      }
    ],
    "new_issues": [
      {
        "id": "issue-4",
        "description": "New race condition in callback",
        "reason": "logic",
        "file": "src/auth.ts",
        "lines": "100-105",
        "suggestion": "Add mutex lock"
      }
    ],
    "unresolved_issues": [
      {
        "original_id": "issue-3",
        "description": "Memory leak: OAuth state not cleaned up",
        "reason": "bug",
        "file": "src/auth.ts",
        "lines": "88-95"
      }
    ],
    "pass": false
  }
  ```

  **约束**:
  - 只关注被修改的代码，不评论原有代码
  - 对于已修复的问题，必须简要说明修复方式（`resolution_note`）
  - 对于未修复的问题，保持原描述不变
  - 新问题使用新的 `id`，不影响原有 issue 编号
  ```

- [ ] **Step 6.3: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add pr-watcher and delta-reviewer subagent definitions"
  ```

---

## Task 7: Update Edge Cases Table

**Files:**
- Modify: `github-code-review/SKILL.md` — Add rows to existing table

- [ ] **Step 7.1: Add new edge cases**

  Locate the "## 边界情况处理" table. Append new rows:
  ```markdown
  | 用户手动触发但无新 commit | Step 0 检测 → 输出 "No new commits since Round-{N}"，不启动 watcher |
  | Metadata 提取失败 | Fallback 到完整流程，输出 "Previous review metadata corrupted" |
  | Watcher 超时（无新 commit） | Watcher 输出 "Timeout"，主 agent 输出等待超时提醒 |
  | Watcher 检测到 reviewer approved | Watcher 输出 "All reviewers approved"，主 agent 结束监控 |
  | Watcher 检测到 PR closed/merged | Watcher 输出 "PR state changed"，主 agent 结束监控 |
  | Round 编号溢出（>99） | 继续递增，无上限 |
  | re-entry 时 PR 已关闭 | Re-entry Step R2 捕获，不执行增量审查 |
  | re-entry 时 delta-reviewer 失败 | 输出错误信息，不启动新 watcher |
  ```

- [ ] **Step 7.2: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add edge cases for incremental review and watcher"
  ```

---

## Task 8: Update SubAgent Prompt Templates

**Files:**
- Modify: `github-code-review/SKILL.md` — Add to "## SubAgent Prompt 模板参考"

- [ ] **Step 8.1: Add pr-watcher prompt template**

  After "### issue-validator prompt 模板", insert:
  ```markdown
  ### pr-watcher prompt 模板

  ```
  你是一个 PR 变更监控器。你的唯一任务是检测 GitHub PR 是否有新的 commit 或状态变化。

  输入参数：
  - PR 编号: {pr_number}
  - 仓库 owner/repo: {owner}/{repo}
  - 监控开始时的 head SHA: {base_sha}
  - 轮询间隔: {poll_interval_s} 秒（默认 300）
  - 最大等待时间: {max_wait_s} 秒（默认 3600）

  执行流程：

  1. 记录 start_time = 当前时间
  2. 循环执行（最多 {max_iterations} 次）：
     a. `Shell: sleep {poll_interval_s}`
     b. `Shell: gh pr view {pr_number} --json headRefOid,state,reviewDecision`
        → 解析 JSON，获取当前 head SHA、state、reviewDecision

     c. 如果 state == "CLOSED" 或 "MERGED"：
        → 输出 "PR state changed to {state}"
        → 结束

     d. 如果 reviewDecision == "APPROVED"：
        → 输出 "All reviewers approved"
        → 结束

     e. 如果当前 head SHA != {base_sha}：
        → 输出 "New commits detected. Previous SHA: {base_sha}, Current SHA: {current_sha}"
        → 结束

     f. 检查是否超过 max_wait_time
  3. 超时：输出 "Timeout: no new commits after {max_wait_s}s"

  约束：
  - 只使用 Shell 工具执行 gh 命令
  - 不读取代码文件
  - 不做代码分析
  - 每次循环必须输出当前状态（如 "Round X: SHA unchanged, state=OPEN, decision=PENDING"）
  ```
  ```

- [ ] **Step 8.2: Add delta-reviewer prompt template**

  After "### pr-watcher prompt 模板", insert:
  ```markdown
  ### delta-reviewer prompt 模板

  ```
  你是一个增量代码审查员。你的任务是对比上一轮发现的问题和当前 PR 的最新 diff，判断哪些问题已被修复，并发现新问题。

  输入：
  - PR 完整 diff：{diff}
  - 上一轮问题列表：{previous_issues}
  - 上一轮 head SHA：{previous_head_sha}
  - 当前 head SHA：{current_head_sha}
  - 相关规范文件：{guidelines}

  要求：
  1. 遍历每个 previous issue，检查其 file + lines 范围是否在 diff 中被修改：
     - 被修改 → 仔细阅读对应代码，判断是否已修复 → 加入 resolved_issues，附 resolution_note
     - 未修改 → 加入 unresolved_issues
  2. 审查 diff 中其他新增/修改的代码，发现新问题 → 加入 new_issues
     - **特别注意**：修复 commit 可能引入新的问题，不要只关注原有问题的修复状态
     - 仔细审查修复代码本身的正确性
  3. 忽略已确认 resolved 的旧问题
  4. 对于规范类问题，确认规则是否仍适用于当前变更
  5. 输出 JSON：{"resolved_issues": [...], "new_issues": [...], "unresolved_issues": [...], "pass": boolean}
  ```
  ```

- [ ] **Step 8.3: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add pr-watcher and delta-reviewer prompt templates"
  ```

---

## Task 9: Update gh Command Reference

**Files:**
- Modify: `github-code-review/SKILL.md` — Add to "## gh 命令参考"

- [ ] **Step 9.1: Add new gh commands**

  Locate "## gh 命令参考" code block. Append:
  ```bash
  # 获取 PR review 评论列表（含 review body 和提交时间）
  gh pr view <PR> --json reviews --jq '.reviews[] | {body: .body, submitted_at: .submitted_at}'

  # 获取 PR head commit SHA（用于对比是否有新 commit）
  gh pr view <PR> --json headRefOid --jq '.headRefOid'

  # 获取 PR reviewDecision（APPROVED / CHANGES_REQUESTED / PENDING）
  gh pr view <PR> --json reviewDecision

  # 获取 PR commits 列表
  gh api repos/{owner}/{repo}/pulls/{number}/commits
  ```

- [ ] **Step 9.2: Commit**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): add gh commands for metadata extraction and head SHA"
  ```

---

## Task 10: Final Review and Integration Test

**Files:**
- Modify: `github-code-review/SKILL.md` — Read-only review

- [ ] **Step 10.1: Read the complete modified SKILL.md**

  Run: `cat github-code-review/SKILL.md | head -100`
  Verify: File loads without syntax errors

- [ ] **Step 10.2: Check for consistency issues**

  Search for:
  - `"Step 9"` references that should say "Step 10" (watcher launch)
  - Missing `"Round"` references in comment format examples
  - `"Previous review"` or `"metadata"` mentioned without definition
  - Any `TBD` or `TODO` placeholders

- [ ] **Step 10.3: Verify all spec requirements are covered**

  Cross-reference with `docs/superpowers/specs/2026-04-21-incremental-code-review-design.md`:
  - [ ] Step 0: Review type detection ✓
  - [ ] Structured comments with HTML metadata ✓
  - [ ] Step 10: Background watcher launch ✓
  - [ ] Re-entry handling chapter ✓
  - [ ] Incremental review flow chapter ✓
  - [ ] pr-watcher subagent definition ✓
  - [ ] delta-reviewer subagent definition ✓
  - [ ] Updated edge cases ✓
  - [ ] Updated gh command reference ✓

- [ ] **Step 10.4: Commit final integration**

  ```bash
  git add github-code-review/SKILL.md
  git commit -m "feat(code-review): integrate incremental review with watcher and re-entry (closes #<issue>)"
  ```

---

## Spec Coverage Checklist

| Spec Requirement | Implementing Task |
|------------------|-------------------|
| Step 0: Review type detection with metadata extraction | Task 1 |
| HTML Comment metadata format in review comments | Task 2 |
| Round-N comment formats (Round-1, Round-N, All Resolved) | Task 2 |
| Step 10: Background watcher launch | Task 3 |
| Re-entry handling for watcher notifications | Task 4 |
| Incremental review flow (delta-reviewer) | Task 5 |
| pr-watcher subagent definition | Task 6 |
| delta-reviewer subagent definition | Task 6 |
| Updated edge cases | Task 7 |
| Prompt templates for new subagents | Task 8 |
| Additional gh commands | Task 9 |

---

## Placeholder Scan

No `TBD`, `TODO`, or vague requirements remain in this plan. Every step contains:
- Exact file path
- Exact markdown text to insert or replace
- Exact commit commands

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-21-incremental-code-review.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
