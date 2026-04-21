# `github-code-review` 增量迭代审查设计方案

> **状态**: 设计已定稿，待实现  
> **更新日期**: 2026-04-21  
> **关联**: `github-code-review/SKILL.md`

---

## 1. 背景与动机

当前 `github-code-review` skill 每次触发都走**完整审查流程**（5 个并行审查 Agent + issue 验证），这在以下场景存在明显问题：

- **Re-review 场景**：PR 已审查过一次，开发者修复了部分问题后再次触发 review，仍然走完整流程，重复审查未变更的代码
- **CI 自动化场景**：希望 kimi-cli 在 `--print` 模式下执行 CR 后，自动进入等待模式，持续监控 PR 修复状态，直到所有问题都解决后才退出进程
- **效率问题**：完整流程对同一 PR 重复执行，消耗不必要的 LLM token 和时间

---

## 2. 目标

1. **增量审查**：已审查过的 PR，再次触发时识别已有 review 评论，仅审查新增/修改的部分
2. **自动轮询**：发现问题后自动启动后台 watcher，定期检测 PR 是否有新 commit
3. **迭代退出**：当 PR 无新问题（或所有 reviewer 已 approve）时，进程自动退出
4. **非交互模式兼容**：全程支持 `--print` 模式，无需人工干预

---

## 3. 核心设计：增量审查 + Watcher 模式

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            首次审查流程（Round-1）                           │
│                                                                             │
│  用户触发 "review pr"                                                       │
│       │                                                                     │
│       ▼                                                                     │
│  Step 0: 审查类型判断                                                        │
│       │── 检查已有 Kimi CR review 评论 → 无 → 继续                          │
│       │                                                                     │
│       ▼                                                                     │
│  Step 1-9: 完整 CR（当前逻辑）                                               │
│       │── 发现问题 A、B、C                                                   │
│       │                                                                     │
│       ▼                                                                     │
│  Step 10: 发布 Round-1 review 评论                                           │
│       │                                                                     │
│       ▼                                                                     │
│  Step 11: 启动 Background Watcher Agent                                     │
│       │                                                                     │
│       ▼                                                                     │
│  主 agent turn 结束 → --print 进入 wait loop                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ... 5-10 分钟后，开发者 push 修复 ...

┌─────────────────────────────────────────────────────────────────────────────┐
│                         Re-review 轮次（Round-2+）                           │
│                                                                             │
│  Watcher 检测到新 commit → 结束 task → 发布 notification                     │
│       │                                                                     │
│       ▼                                                                     │
│  --print re-enter soul（收到 <system-reminder>）                             │
│       │                                                                     │
│       ▼                                                                     │
│  主 agent re-entry 处理                                                      │
│       │── 获取上次 Round-N review 评论（含问题列表 metadata）                │
│       │── 获取完整 diff（delta-reviewer 自行判断增量部分）                   │
│       │── 启动 delta-reviewer（1 个轻量级 Agent）                            │
│       │── 结果：A、B 已修复，C 仍在                                          │
│       │                                                                     │
│       ▼                                                                     │
│  Step 10: 发布 Round-2 review 评论（新评论，不编辑旧评论）                   │
│       │                                                                     │
│       ▼                                                                     │
│  Step 11: 再次启动 Background Watcher Agent                                 │
│       │                                                                     │
│       ▼                                                                     │
│  主 agent turn 结束 → --print 再次进入 wait loop                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ... 最终轮次：所有问题已解决 ...

┌─────────────────────────────────────────────────────────────────────────────┐
│                          最终轮次（全部 PASS）                               │
│                                                                             │
│  Watcher 检测到新 commit → 结束 task → 发布 notification                     │
│       │                                                                     │
│       ▼                                                                     │
│  主 agent re-entry：增量 CR → 所有问题已解决                                 │
│       │                                                                     │
│       ▼                                                                     │
│  发布 Round-N "All issues resolved ✓" review 评论                           │
│       │                                                                     │
│       ▼                                                                     │
│  不启动 watcher（无问题）                                                    │
│       │                                                                     │
│       ▼                                                                     │
│  主 agent turn 结束 → 无 active tasks → 进程退出                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. PR Review 评论格式（关键设计）

### 4.1 评论结构

所有由本 skill 发布的 review 评论使用**统一的结构化格式**，分为两部分：

**A. 人类可读部分（Markdown）**

```markdown
### Code Review | Round-{N}

Found {K} issues (Previous: {M}, Resolved: {R}, New: {new_count}):

1. {description} ({reason})
   - File: `{file}`
   - Lines: `{lines}`
   - Status: `open` | `resolved`

   https://github.com/owner/repo/blob/{sha}/{file}#L{start}-L{end}

🤖 Generated with Kimi Code CLI
```

**B. 机器可读 Metadata（HTML Comment，紧接在 review body 开头）**

```markdown
<!-- kimi-cr-meta
{"round":2,"pr_number":123,"head_sha":"abc123...","previous_head_sha":"def456...","total_issues":3,"resolved_count":2,"new_count":0,"issues":[{"id":"issue-1","description":"Missing error handling for OAuth callback","reason":"bug","file":"src/auth.ts","lines":"67-72","status":"resolved","first_round":1},{"id":"issue-3","description":"Memory leak: OAuth state not cleaned up","reason":"bug","file":"src/auth.ts","lines":"88-95","status":"open","first_round":1}],"timestamp":"2026-04-21T10:30:00Z"}
-->

### Code Review | Round-2
...
```

### 4.2 Metadata 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `round` | int | 当前轮次编号（从 1 开始） |
| `pr_number` | int | PR 编号 |
| `head_sha` | string | 当前 review 时的 PR head commit SHA |
| `previous_head_sha` | string \| null | 上一轮 review 时的 head SHA（Round-1 为 null） |
| `total_issues` | int | 当前轮次统计的问题总数 |
| `resolved_count` | int | 本轮标记为 resolved 的问题数 |
| `new_count` | int | 本轮新发现的问题数 |
| `issues` | array | 问题列表，每个元素含 `status`（`open` 或 `resolved`） |
| `timestamp` | ISO string | review 完成时间 |

### 4.3 为什么用 HTML Comment？

- GitHub Markdown 渲染时会**隐藏 HTML Comments**，不影响人类阅读
- 机器可以通过正则表达式 `<!-- kimi-cr-meta\n({.*})\n-->` 精确提取 JSON
- 不依赖 Markdown 文本解析，不受用户回复、emoji、链接格式干扰
- 即使后续有人回复评论，metadata 仍然在第一条评论 body 中保持不变

### 4.4 Round 编号规则

- **Round-1**：首次完整审查
- **Round-N（N ≥ 2）**：第 N 次增量审查（由 watcher 自动触发或用户手动触发）
- 每轮评论都是**新评论**，不编辑旧评论
- 多轮评论在 PR 下按时间顺序排列，方便追踪审查历史

---

## 5. 评论提取逻辑（Step 0）

### 5.1 获取 Review 评论

使用 `Shell` 执行：

```bash
gh pr view <PR> --json reviews
```

或获取更详细的 review 内容：

```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '.[] | {id: .id, body: .body, user: .user.login, submitted_at: .submitted_at}'
```

### 5.2 筛选 Kimi Code CLI 的评论

过滤条件：
1. `user.login` 是 bot 账号（即当前 `gh auth` 认证的账号）
2. 评论 body 包含 `"Generated with Kimi Code CLI"`
3. 评论 body 包含 `"<!-- kimi-cr-meta"`

### 5.3 获取最新一轮的 Metadata

```python
# 伪代码逻辑
kimi_reviews = [r for r in all_reviews 
                if "Generated with Kimi Code CLI" in r.body 
                and "<!-- kimi-cr-meta" in r.body]

# 按 submitted_at 排序，取最新一条
latest_review = max(kimi_reviews, key=lambda r: r.submitted_at)

# 提取 metadata
import re, json
match = re.search(r'<!-- kimi-cr-meta\n(.*?)\n-->', latest_review.body, re.DOTALL)
if match:
    metadata = json.loads(match.group(1))
    previous_issues = metadata["issues"]        # 上一轮的问题列表
    previous_head_sha = metadata["head_sha"]    # 上一轮的 head SHA
    previous_round = metadata["round"]          # 上一轮的 round 编号
```

### 5.4 判断是否需要增量审查

```
有 previous review metadata？
  ├─ 是 → 使用 `Shell` 执行 `gh pr view <PR> --json headRefOid --jq '.headRefOid'` 获取当前 head SHA
  │       ├─ 当前 SHA == previous SHA → 无新 commit → 输出 "No new commits since last review (Round-N)"
  │       └─ 当前 SHA != previous SHA → 有新 commit → 走增量流程（Round = previous_round + 1）
  └─ 否 → 首次审查 → 走完整流程（Round = 1）
```

---

## 6. Watcher Agent 详细设计

### 6.1 职责边界

**Watcher 只做"检测"，不做"审查"**：
- ✅ 检测新 commit（对比 head SHA）
- ✅ 检测 reviewer approval 状态
- ✅ 检测 PR closed/merged 状态
- ✅ 超时控制
- ❌ 不做代码分析
- ❌ 不启动其他 Agent

原因：background agent 的 `runtime.role != "root"`，无法调用 `Agent` 工具。

### 6.2 Prompt 模板

```markdown
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

### 6.3 输出格式

```
Status: monitoring PR #123
  Base SHA: abc123def456...

Round 1: SHA unchanged, state=OPEN, decision=PENDING (sleep 300s)
Round 2: SHA unchanged, state=OPEN, decision=PENDING (sleep 300s)
Round 3: NEW COMMIT DETECTED
  Previous SHA: abc123def456...
  Current SHA:  fed789abc012...
```

---

## 7. 主 Agent Re-entry 处理

### 7.1 识别 re-entry 场景

主 agent 需要区分：
- **用户新触发**的 "review pr" → 走 Step 0 判断流程
- **watcher 完成后的 re-entry** → 直接走增量流程

判断方式：检查用户输入是否包含 `<system-reminder>` 且 mention 了 watcher task：

```
if user_input 包含 "<system-reminder>" 和 "Background task completed" 和 "PR change watcher":
    → 走 Re-entry 增量流程
else:
    → 走 Step 0 正常流程（首次审查或用户手动触发）
```

### 7.2 Re-entry 处理流程

```markdown
## Re-entry 处理（watcher 触发）

1. 解析 notification：
   - 提取 watcher output 中的状态行
   - 判断：New commits / Approved / Timeout / PR closed

2. 分支处理：

   a. "New commits detected":
      - 使用 `Shell` 获取当前 PR head SHA（确认 watcher 报告的 SHA）
      - 使用 `Shell` 执行 `gh pr view <PR> --json reviews` 获取所有 review 评论
      - 筛选 Kimi CR 评论，提取最新一轮的 metadata（见第 5 节）
      - 使用 `Shell` 执行 `gh pr diff <PR>` 获取完整 diff
      - 启动 delta-reviewer Agent（前台）
      - 发布 Round-N review 评论（含 metadata）
      - 如果还有 open issues → 启动新的 Background Watcher（同 Step 10）
      - 如果无 open issues → 不启动 watcher

   b. "All reviewers approved":
      - 输出 "All reviewers have approved this PR. No further action needed."
      - 不启动 watcher

   c. "Timeout":
      - 输出 "No new commits detected within timeout. Previous issues may still be open."
      - 不启动 watcher

   d. "PR closed/merged":
      - 输出 "PR has been closed/merged. Stopping monitoring."
      - 不启动 watcher
```

### 7.3 用户手动触发时的增量流程

当用户手动触发 "review pr" 且 Step 0 检测到有 previous review metadata 时：

```markdown
## 手动触发的增量审查

Step 0 检测到 previous review（Round-{N}）：
1. 获取当前 PR head SHA
2. 对比 previous_head_sha：
   - 相同 → 输出 "No new commits since Round-{N} review. Use 'review pr --force' to re-review anyway."
   - 不同 → 进入增量流程

增量流程：
1. 提取 previous issues 列表
2. 获取完整 diff
3. 启动 delta-reviewer Agent
4. 发布 Round-{N+1} review 评论
5. 如果还有 open issues → 启动 watcher
6. 如果无问题 → 不启动 watcher
```

### 7.4 Delta-reviewer Agent 设计

```markdown
## delta-reviewer

输入：
- PR 完整 diff（gh pr diff 输出）
- 上一轮问题列表（从 metadata 提取，含 file/lines/description/status）
- 上一轮的 head SHA
- 当前 PR head SHA
- 相关规范文件（CLAUDE.md / AGENTS.md）

任务：
1. 对比上一轮问题列表和当前 diff：
   - 遍历每个 previous issue，检查其 file + lines 范围是否在 diff 中被修改
   - 如果被修改 → 仔细阅读对应代码，判断是否已修复 → 标记为 resolved
   - 如果未修改 → 标记为 still_open
2. 审查 diff 中其他新增/修改的代码，发现新问题
   - **特别注意**：修复 commit 可能引入新的问题，不要只关注原有问题的修复状态
   - 仔细审查修复代码本身的正确性
3. 忽略已确认修复的旧问题

输出 JSON：
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
```

---

## 8. 发布 Review 评论的格式（含 Metadata）

### 8.1 Round-1（首次审查）

```markdown
<!-- kimi-cr-meta
{"round":1,"pr_number":123,"head_sha":"abc123...","previous_head_sha":null,"total_issues":3,"resolved_count":0,"new_count":3,"issues":[{"id":"issue-1","description":"Missing error handling for OAuth callback","reason":"bug","file":"src/auth.ts","lines":"67-72","status":"open","first_round":1},{"id":"issue-2","description":"Inconsistent naming pattern","reason":"AGENTS.md","file":"src/utils.ts","lines":"23-28","status":"open","first_round":1},{"id":"issue-3","description":"Memory leak: OAuth state not cleaned up","reason":"bug","file":"src/auth.ts","lines":"88-95","status":"open","first_round":1}],"timestamp":"2026-04-21T10:00:00Z"}
-->

### Code Review | Round-1

Found 3 issues:

1. Missing error handling for OAuth callback (bug)

   https://github.com/owner/repo/blob/abc123.../src/auth.ts#L67-L72

2. Inconsistent naming pattern (AGENTS.md)

   https://github.com/owner/repo/blob/abc123.../src/utils.ts#L23-L28

3. Memory leak: OAuth state not cleaned up (bug)

   https://github.com/owner/repo/blob/abc123.../src/auth.ts#L88-L95

🤖 Generated with Kimi Code CLI
```

### 8.2 Round-N（增量审查）

```markdown
<!-- kimi-cr-meta
{"round":2,"pr_number":123,"head_sha":"fed789...","previous_head_sha":"abc123...","total_issues":1,"resolved_count":2,"new_count":0,"issues":[{"id":"issue-3","description":"Memory leak: OAuth state not cleaned up","reason":"bug","file":"src/auth.ts","lines":"88-95","status":"open","first_round":1}],"timestamp":"2026-04-21T10:30:00Z"}
-->

### Code Review | Round-2 (Re-check)

Previous Round-1 issues: 3
- **Resolved**: 2 (Missing error handling, Inconsistent naming)
- **Still open**: 1

New issues found: 0

#### Still Open from Round-1

3. Memory leak: OAuth state not cleaned up (bug)

   https://github.com/owner/repo/blob/fed789.../src/auth.ts#L88-L95

🤖 Generated with Kimi Code CLI
```

### 8.3 All Resolved（最终轮次）

```markdown
<!-- kimi-cr-meta
{"round":3,"pr_number":123,"head_sha":"aaa111...","previous_head_sha":"fed789...","total_issues":0,"resolved_count":1,"new_count":0,"issues":[],"timestamp":"2026-04-21T11:00:00Z"}
-->

### Code Review | Round-3 (Re-check)

Previous Round-2 issues: 1
- **Resolved**: 1 (Memory leak)
- **Still open**: 0

New issues found: 0

✅ **All issues resolved!**

🤖 Generated with Kimi Code CLI
```

---

## 9. 与现有流程的对比

| 维度 | 当前流程 | 新流程（Round-1） | 新流程（Round-N） |
|------|---------|------------------|------------------|
| 触发方式 | 用户手动 | 用户手动 | watcher 自动 / 用户手动 |
| 审查范围 | 全部 diff | 全部 diff | 增量 diff（delta-reviewer 自行判断） |
| 审查 Agent 数 | 5 个并行 | 5 个并行 | 1 个（delta-reviewer） |
| Issue 验证 | 每个 issue 单独验证 | 每个 issue 单独验证 | 简化为对比验证（由 delta-reviewer 完成） |
| 发布评论 | 单次 | Round-1 review 评论 | Round-N review 评论（新评论，不编辑旧评论） |
| 评论格式 | Markdown | Markdown + HTML Comment metadata | Markdown + HTML Comment metadata |
| 进程行为 | 完成后退出 | 发现问题后启动 watcher，进入 wait | watcher 完成后 re-enter，再决定 |
| 适用场景 | 一次性审查 | 首次审查 + 持续监控 | 修复后的自动复查 |

---

## 10. 关键改动点（SKILL.md）

### 10.1 新增 Step 0：审查类型判断

在现有 Step 1 之前插入：

```markdown
## Step 0: 审查类型判断

使用 `Shell` 执行 `gh pr view <PR> --json reviews` 获取所有 review 评论。

筛选 Kimi Code CLI 发布的 review 评论：
1. 检查评论 body 是否包含 "Generated with Kimi Code CLI"
2. 检查评论 body 是否包含 "<!-- kimi-cr-meta"
3. 按 submitted_at 排序，取最新一条
4. 用正则表达式提取 HTML Comment 中的 JSON metadata

判断：
- 有 previous review metadata → 获取当前 head SHA，对比 previous_head_sha
  - 相同 → 输出 "No new commits since Round-{N}"
  - 不同 → 走增量流程（Round = N + 1）
- 无 previous review metadata → 首次审查（Round = 1）

同时检查用户输入：
- 如果输入包含 `<system-reminder>` 且 mention watcher task → 走 Re-entry 处理
- 否则 → 正常流程
```

### 10.2 修改 Step 9：发布 PR Review 评论（必须）

使用 `Shell` 执行：

```bash
# 将 review body 写入临时文件（避免 shell 转义和长命令问题）
echo "<review_body>" > /tmp/kimi-cr-{pr_number}.md
gh pr review <PR> --comment --body-file /tmp/kimi-cr-{pr_number}.md
```

`<review_body>` 必须包含：
1. 顶部的 `<!-- kimi-cr-meta\n{json}\n-->` HTML Comment
2. Markdown 格式的人类可读部分
3. `"Generated with Kimi Code CLI"` 标识
4. `"### Code Review | Round-{N}"` 标题

### 10.3 新增 Step 10：启动 Background Watcher（可选）

在 Step 9 之后插入：

```markdown
## Step 10: 启动 Background Watcher（可选）

条件：Step 6 过滤后存在未解决的问题，且当前为首次审查或手动触发的增量审查

操作：
1. 使用 `Shell` 执行 `gh pr view <PR> --json headRefOid --jq '.headRefOid'` 获取当前 head SHA
2. 使用 `Agent` + `run_in_background=true` 启动 watcher agent
3. 向用户说明："已发现 N 个问题，已启动后台监控，修复后会自动复查"

条件：无问题 或 当前为 re-entry 且已无问题
操作：不启动 watcher，正常结束
```

### 10.4 新增【Re-entry 处理】章节

```markdown
## Re-entry 处理

当 --print 模式因 watcher 完成而 re-enter 时：

1. 解析 `<system-reminder>` 中的 watcher 输出
2. 获取当前 PR head SHA
3. 获取最新 Kimi CR review 评论，提取 metadata
4. 获取完整 diff
5. 启动 delta-reviewer Agent
6. 发布 Round-N review 评论
7. 根据 delta-reviewer 结果决定是否再次启动 watcher
```

### 10.5 新增【增量审查流程】章节

替代完整流程中的 Step 3-5：

```markdown
## 增量审查流程

1. 获取上一轮 review 评论的 metadata（含问题列表）
2. 获取完整 diff
3. 启动 delta-reviewer Agent（前台，1 个）
4. 收集结果：resolved / new / unresolved
5. 构建 Round-N review 评论（含 metadata + Markdown）
6. 发布 review 评论
```

### 10.6 新增 Watcher 和 Delta-reviewer 的 SubAgent 定义

在【SubAgent 详细定义】章节增加：
- `pr-watcher`：监控 PR 变更
- `delta-reviewer`：增量代码审查

---

## 11. 配置建议

用户需在 `~/.config/kimi/config.yaml` 中调整：

```yaml
background:
  # Watcher 最长运行时间（默认 900s = 15 分钟可能不够）
  agent_task_timeout_s: 3600

  # --print 模式最长等待时间（默认 3600s = 1 小时）
  print_wait_ceiling_s: 7200

  # 是否保持后台任务在退出后继续运行（必须 false，否则 --print 不会等待）
  keep_alive_on_exit: false
```

---

## 12. 边界情况处理

| 情况 | 处理方式 |
|------|---------|
| PR 在 watcher 运行期间被关闭 | Watcher 检测到 `state=CLOSED` → 结束，主 agent 输出 "PR closed" |
| PR 在 watcher 运行期间被合并 | Watcher 检测到 `state=MERGED` → 结束，主 agent 输出 "PR merged" |
| Watcher 超时（无新 commit） | Watcher 输出 "Timeout"，主 agent 输出等待超时提醒 |
| 增量审查发现新问题 | 合并到未解决问题列表，再次启动 watcher |
| 增量审查时 PR 已被关闭 | Step 7（最终资格审查）捕获，不发布评论 |
| Watcher 自身失败 | 主 agent re-entry 时检测到 failure，向用户报告 |
| 多个 re-review 轮次 | 每轮独立，状态通过 PR review 评论 metadata 持久化 |
| diff 超过 500 行 | delta-reviewer 仅分析新增/修改的 hunk，忽略未变更部分 |
| 用户手动触发但无新 commit | 输出 "No new commits since Round-{N}"，不启动 watcher |
| Metadata 提取失败（格式损坏） | Fallback 到完整流程，输出 "Previous review metadata corrupted, performing full re-review" |
| Round 编号达到 99 | 继续递增，无上限（实际很少会超过 10 轮） |

---

## 13. 非交互 `--print` 模式的完整时序图

```
用户: kimi --print "review pr #123"
  │
  ▼
Kimi CLI: 启动 session，加载 skill
  │
  ▼
主 Agent (root):
  │── Step 0: 检查 previous review → 无 → Round = 1
  │── Step 1-9: 完整 CR
  │── 发现问题 A、B、C
  │── Step 10: 发布 Round-1 review 评论（含 metadata）
  │── Step 11: 启动 Background Watcher Agent（base_sha = abc123）
  │── 输出: "Found 3 issues. Watcher started."
  │
  ▼
主 Agent turn 结束
  │
  ▼
--print: 检测到 active background task
  │── 进入 wait loop
  │── 每秒 reconcile() + sleep(1)
  │
  │        ... 8 分钟后 ...
  │
  ▼
开发者: push 修复 commit（修复 A、B）
  │
  ▼
Watcher Agent:
  │── Round 1-2: SHA 未变
  │── Round 3: head SHA 从 abc123 → fed789
  │── 输出: "New commits detected"
  │── Task 标记 completed
  │
  ▼
--print: reconcile() 发现 task completed
  │── has_pending_for_sink("llm") = true
  │── re-enter run_soul()
  │
  ▼
主 Agent (re-entry):
  │── 收到 <system-reminder>: watcher 完成
  │── 解析: "New commits detected"
  │── Step 0: 获取 Round-1 review 评论 → 提取 metadata
  │── 获取完整 diff
  │── 启动 delta-reviewer（前台 Agent）
  │── 结果: A、B 已修复，C 仍在
  │── Step 10: 发布 Round-2 review 评论（含 metadata）
  │── Step 11: 再次启动 Watcher（base_sha = fed789）
  │── 输出: "1 issue remaining. Watcher restarted."
  │
  ▼
主 Agent turn 结束
  │
  ▼
--print: 再次进入 wait loop
  │
  │        ... 10 分钟后 ...
  │
  ▼
开发者: push 修复 commit（修复 C）
  │
  ▼
Watcher Agent: 检测到新 commit → 结束
  │
  ▼
--print: re-enter run_soul()
  │
  ▼
主 Agent (re-entry):
  │── 获取 Round-2 metadata
  │── delta-reviewer: C 已修复，无新问题
  │── Step 10: 发布 Round-3 review 评论 "All issues resolved ✓"
  │── Step 11: 无 open issues → 不启动 watcher
  │
  ▼
主 Agent turn 结束
  │
  ▼
--print: 无 active tasks → 退出
  │── ExitCode.SUCCESS
  │
  ▼
Kimi CLI 进程结束
```

---

## 14. 待办 / 实现 checklist

- [ ] 更新 SKILL.md：新增 Step 0（审查类型判断）
- [ ] 更新 SKILL.md：修改 Step 9（发布评论含 metadata）
- [ ] 更新 SKILL.md：新增 Step 10（启动 watcher）
- [ ] 更新 SKILL.md：新增 Re-entry 处理章节
- [ ] 更新 SKILL.md：新增增量审查流程章节
- [ ] 更新 SKILL.md：新增 pr-watcher SubAgent 定义
- [ ] 更新 SKILL.md：新增 delta-reviewer SubAgent 定义
- [ ] 验证 `gh pr review --comment --body-file` 发布的长评论中 HTML Comment 是否被保留
- [ ] 验证 `gh pr view --json reviews` 能否正确获取 review 评论列表
- [ ] 测试 `--print` 模式下 background agent 完成后 re-enter 的 notification 格式
