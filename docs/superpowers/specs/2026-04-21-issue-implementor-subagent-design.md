# Issue Implementor Subagent-Driven 改造设计

> 基于 [Issue #1](https://github.com/zhuxixi/kimi-code-skills/issues/1) 和 brainstorming 讨论整理。

---

## 1. 问题描述

`issue-implementor` skill 当前是单 agent 串行执行完整流程（分支管理 → Issue 分析 → 方案设计 → 代码实现 → 完成），Kimi CLI 上下文窗口有限，执行到后面会遗忘最初目标（"实现 issue #27"），导致方向漂移或重复工作。

## 2. 改造方向

采用 **`superpowers:subagent-driven-development`** 模式重构，但**精简范围**：

- **Branch Setup、Issue Analysis、Design 将拆分到其他 skill**，不在本 skill 中处理
- `issue-implementor` **只聚焦于「拿到方案后 → 实现代码」这一核心环节**
- 输入从 "issue 编号" 变为 "已确认的 implementation plan"
- **没有 PLAN 的情况下，本 skill 无法处理**

## 3. 调研结果

### work_dir 参数
- 用户 fork (`zhuxixi/kimi-cli`) 已支持 `Agent(work_dir="...")`（PR #1933）
- upstream (`MoonshotAI/kimi-cli`) **尚未合并**
- **当前运行的 Kimi CLI 1.36.0 是官方版本，`work_dir` 不可用**
- 所有 subagent prompt 必须强制使用绝对路径

---

## 4. 改造方案

### 4.1 职责边界

| 环节 | 负责方 | 说明 |
|------|--------|------|
| Branch Setup | **其他 skill** | 创建/切换分支 |
| Issue Analysis | **其他 skill** | 读取 issue、提取需求 |
| Design / Plan | **其他 skill** | 生成 implementation plan |
| **Code Implementation** | **本 skill** ✅ | 按 plan 实现代码 |
| Final Review | **本 skill** ✅ | 整体验收 |
| **Git Commit** | **本 skill** ✅ | 提交所有变更 |
| PR 创建 | **其他 skill / 用户** | 可选 |

### 4.2 核心原则（来自 `subagent-driven-development`）

| 原则 | 说明 |
|------|------|
| **Fresh subagent per task** | 每个文件/模块一个全新 implementer subagent |
| **Two-stage review** | 每个 implementer 完成后 → Spec Reviewer → Code Quality Reviewer |
| **Controller 提供完整文本** | 主 agent 在 prompt 中给出 plan + 文件 spec，不让 subagent 去读 plan 文件 |
| **绝不并行 implementer** | 串行执行，避免文件冲突 |
| **Status 驱动** | DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED |

> 关于 Two-Stage Review 的成本：5 个 tasks = 15 个 subagent dispatch，成本确实高，但**省略 review 大概率出问题**，保留。

### 4.3 输入格式

本 skill 被触发时，应已具备以下信息（由上游 skill 提供）：

```json
{
  "repo_path": "/absolute/path/to/repo",
  "owner": "zhuxixi",
  "repo": "kimi-code-skills",
  "branch": "issue-27",
  "plan": {
    "title": "重构用户认证中间件",
    "tasks": [
      {
        "id": "task-1",
        "description": "创建 middleware/auth.py",
        "files_to_read": ["{repo_path}/middleware/__init__.py", "{repo_path}/config/settings.py"],
        "files_to_create": ["{repo_path}/middleware/auth.py"],
        "files_to_modify": [],
        "spec": "实现 JWT 验证逻辑，参考 config/settings.py 中的 SECRET_KEY 配置...",
        "dependencies": []
      },
      {
        "id": "task-2",
        "description": "修改 app.py 注册中间件",
        "files_to_read": ["{repo_path}/middleware/auth.py"],
        "files_to_create": [],
        "files_to_modify": ["{repo_path}/app.py"],
        "spec": "在 app 初始化时添加 auth middleware，依赖 task-1 创建的 middleware/auth.py...",
        "dependencies": ["task-1"]
      }
    ]
  }
}
```

**字段说明**:
- `repo_path`: 仓库绝对路径（平台无关，如 `/home/user/project` 或 `C:\Users\...`）
- `files_to_read`: 实现当前 task **前需要先读取**的参考文件（绝对路径）
- `files_to_create`: 当前 task 需要**创建**的文件（绝对路径）
- `files_to_modify`: 当前 task 需要**修改**的文件（绝对路径）
- `dependencies`: 当前 task 依赖的其他 task ID，必须等依赖 task 完成后才能执行

### 4.4 执行流程

```
输入: implementation plan + repo_path + branch
      ↓
┌─────────────────────────────────────────────────────────────┐
│              主 Agent（Controller）                          │
│  上下文只保留：plan 摘要、当前 task 进度、已完成的 tasks 结果  │
└─────────────────────────────────────────────────────────────┘
      ↓
按 dependencies 拓扑排序 tasks
      ↓
For each task in sorted_tasks (串行):
      ↓
  Implementer Subagent (coder)
    ├─ 输入: task.spec + 绝对路径 + 相关文件内容
    ├─ 工作: 创建/修改文件、编写代码、运行测试
    └─ 返回: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
      ↓ [DONE]
  Spec Reviewer Subagent (coder)
    ├─ 输入: task.spec + implementer 的修改摘要 + 文件路径
    ├─ 工作: 用 ReadFile 读取修改后的文件，确认完全符合 spec
    └─ 返回: compliant: true|false + missing/extra/notes
      ↓ [compliant: true]
  Code Quality Reviewer Subagent (coder)
    ├─ 输入: 修改后的文件路径 + 代码内容
    ├─ 工作: 评审代码质量、命名、边界、测试覆盖
    └─ 返回: approved: true|false + strengths/issues
      ↓ [approved: true]
  标记 task 完成 → 记录修改文件 → 进入下一个 task
      ↓
所有 tasks 完成后:
      ↓
Final Reviewer Subagent (coder)
    ├─ 输入: 所有修改 + 完整 plan
    └─ 返回: ready_for_pr: true|false + risks/recommendations
      ↓ [ready_for_pr: true]
Commit Subagent (coder)
    ├─ 输入: repo_path + branch + 明确列出的文件列表
    ├─ 工作: git add <明确文件> + git commit
    └─ 返回: commit SHA + message
      ↓
主 Agent 汇总输出
```

### 4.5 主 Agent Orchestration 决策树

主 agent 是唯一的 Controller，负责调度所有 subagent。其上下文始终只保留：
- plan 摘要
- 当前正在执行的 task ID
- 已完成的 tasks 结果列表
- 累计修改的文件集合（用于 Commit）

```
开始
  ↓
收到输入 (plan + repo_path + branch)
  ↓
按 dependencies 拓扑排序 tasks
  ↓
For each task in sorted_tasks:
  ↓
  Dispatch Implementer Subagent
    ↓
  收到返回:
    ├─ DONE → 进入 Spec Review
    ├─ DONE_WITH_CONCERNS → 评估 concerns:
    │   ├─ 严重（影响正确性）→ 要求 Implementer 修复 → 重新 dispatch
    │   └─ 轻微（风格、建议）→ 记录 notes → 进入 Spec Review
    ├─ NEEDS_CONTEXT → 主 agent 从 plan / 已完成 tasks / 文件系统中提取缺失信息 → 重新 dispatch
    └─ BLOCKED → 分析 blocker:
        ├─ 可解决（缺少信息、路径问题）→ 提供支持 → 重新 dispatch
        └─ 不可解决（依赖缺失、环境问题）→ 终止流程，向用户报告
  ↓
  Dispatch Spec Reviewer Subagent
    ↓
  收到返回:
    ├─ compliant: true → 进入 Code Quality Review
    └─ compliant: false → 提取 missing/extra → dispatch Implementer 修复 → 重新 Spec Review
  ↓
  Dispatch Code Quality Reviewer Subagent
    ↓
  收到返回:
    ├─ approved: true → Task 完成，记录结果，进入下一个 task
    └─ approved: false → 提取 issues → dispatch Implementer 修复 → 重新 Code Quality Review
  ↓
所有 tasks 完成:
  ↓
Dispatch Final Reviewer Subagent
  ↓
  ├─ ready_for_pr: true → Dispatch Commit Subagent
  └─ ready_for_pr: false → 提取 risks → 询问用户：修复后重试 / 终止
  ↓
Commit 完成:
  ↓
主 Agent 汇总输出
```

**关键规则**:
- 不并行 dispatch 两个 Implementer
- Review 发现问题 → Implementer 修复 → **必须重新 Review**（不跳过）
- 所有文件路径使用绝对路径，平台无关

### 4.6 绝对路径规范（所有 subagent prompt 必须包含）

```
你在仓库 `<ABSOLUTE_PATH>` 中工作。
所有文件操作必须使用**绝对路径**（平台无关格式）。
所有 git 命令使用 `git -C <ABSOLUTE_PATH> ...`。
禁止依赖 `cd` 命令或相对路径。

**示例**:
- Linux/macOS: `/home/user/project/src/main.py`
- Windows: `C:\Users\user\project\src\main.py`
```

---

## 5. 各角色详细设计

### 5.1 Implementer Subagent

**角色**: `coder`

**输入**:
```
仓库绝对路径: {repo_path}
当前分支: {branch}
Task ID: {task.id}
Task 描述: {task.description}
实现前需读取的文件（绝对路径）: {files_to_read}
需创建的文件（绝对路径）: {files_to_create}
需修改的文件（绝对路径）: {files_to_modify}
实现规范:
{task.spec}

注意:
- 所有路径必须用绝对路径
- 禁止 cd 命令
- 完成后运行相关测试
- 返回 JSON 格式结果
```

**返回格式**:
```json
{
  "status": "DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED",
  "modified_files": ["{repo_path}/src/file.py"],
  "new_files": ["{repo_path}/src/new_file.py"],
  "tests_added": true,
  "tests_passed": true,
  "self_review_notes": "...",
  "concerns": []
}
```

**状态处理**:
- `DONE` → 进入 Spec Review
- `DONE_WITH_CONCERNS` → 主 agent 评估 concerns，决定继续或要求修复
- `NEEDS_CONTEXT` → 主 agent 提供缺失信息，重新 dispatch
- `BLOCKED` → 主 agent 分析 blocker，可能升级给用户

### 5.2 Spec Reviewer Subagent

**角色**: `coder`

**输入**:
```
原始规范:
{task.spec}

实现者提交的修改摘要:
{implementer_output}

请评审:
1. 是否完全符合规范要求？
2. 有无遗漏的功能点？
3. 有无实现规范外的额外内容？
4. 文件路径是否正确？

**评审方式**:
请使用 ReadFile 工具读取以下修改后的文件，逐一核对代码是否符合规范：
{modified_and_new_file_paths}

输出 JSON:
{
  "compliant": true|false,
  "missing": ["..."],
  "extra": ["..."],
  "notes": "..."
}
```

**处理**:
- `compliant: false` → Implementer 修复 → 重新 Spec Review
- `compliant: true` → 进入 Code Quality Review

### 5.3 Code Quality Reviewer Subagent

**角色**: `coder`

**输入**:
```
修改的文件列表:
{file_paths}

代码内容（关键部分）:
{code_snippets}

请评审代码质量:
- 命名规范
- 边界处理
- 错误处理
- 测试覆盖
- 可读性

输出 JSON:
{
  "approved": true|false,
  "strengths": ["..."],
  "issues": [
    {"severity": "critical|important|minor", "description": "...", "file": "..."}
  ]
}
```

**处理**:
- `approved: false` → Implementer 修复 issues → 重新 Code Quality Review
- `approved: true` → Task 完成，进入下一个 task

### 5.4 Final Reviewer Subagent

**角色**: `coder`
**条件**: 所有 tasks 完成

**输入**:
```
完整 Plan:
{plan}

所有完成的 Tasks:
{task_results}

所有修改的文件:
{all_modified_files}

请做最终验收:
1. 所有 task 是否都完成了 plan 的目标？
2. 各 task 之间是否协调一致？
3. 有无回归风险？
4. 是否 ready for PR？

输出 JSON:
{
  "ready_for_pr": true|false,
  "overall_assessment": "...",
  "risks": ["..."],
  "recommendations": ["..."]
}
```

### 5.5 Commit Subagent

**角色**: `coder`
**条件**: Final Review 返回 `ready_for_pr: true`

**输入**:
```
仓库绝对路径: {repo_path}
当前分支: {branch}
待提交文件列表（由主 agent 从各 task 结果汇总）:
{files_to_commit}

请执行:
1. git -C {repo_path} status --short
2. git -C {repo_path} add {files_to_commit}
3. git -C {repo_path} commit -m "{type}: {description}"
   - type 和 description 由你根据变更内容自行决定
   - 遵循 conventional commits 规范

注意:
- 只 add 明确列出的文件，不要 add -A
- 所有 git 命令使用 git -C 绝对路径
- 禁止 cd 命令

返回 JSON:
{
  "status": "DONE|BLOCKED",
  "commit_sha": "abc123...",
  "commit_message": "feat: ...",
  "files_committed": ["..."]
}
```

**处理**:
- `DONE` → 主 Agent 汇总输出，建议创建 PR
- `BLOCKED` → 主 Agent 分析（如合并冲突、未配置 git user 等）

> **决策说明**: Commit message 由 subagent 自行决定 type 和 description，不需要主 agent 预生成。

---

## 6. 安全约束

1. **不碰 master/main** — 前提条件：上游 skill 已创建/切换到功能分支
2. **测试优先** — 每个 implementer task 必须运行相关测试（当前 task 的测试就够用了，不需要独立的集成测试环节）
3. **串行实现** — 不并行 dispatch 多个 implementer
4. **Review 顺序不可颠倒** — Spec Review 通过后才能 Code Quality Review
5. **不跳过 re-review** — reviewer 发现问题 → implementer 修复 → 必须重新 review

---

## 7. 明确不考虑的点

| 点 | 原因 |
|---|---|
| **回滚/重置机制** | PR 提交后再处理 |
| **与现有 `#27` 触发方式兼容** | 没有 PLAN 本 skill 无法处理 |
| **集成测试独立环节** | 当前 task 的测试就够用了 |

---

## 8. 待办

- [ ] 重写 `issue-implementor/SKILL.md`，采用本设计文档的 subagent-driven 架构
- [ ] 为每个角色设计可复用的 subagent prompt 模板
- [ ] 定义 JSON 返回格式的完整 schema
- [ ] 在真实 plan 上验证完整流程
