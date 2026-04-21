# Issue Implementor Subagent Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the `issue-implementor` skill from a simple procedural workflow into a subagent-driven architecture with specialized agents for issue analysis, repo scanning, solution design, task planning, implementation, and verification — mirroring the sophistication of `github-code-review`.

**Architecture:** The skill is decomposed into 5 sequential phases. Phases 2–5 leverage dedicated subagents with precise input/output contracts. Phase 1 (branch management) and phase coordination remain main-agent responsibilities. Each subagent has a single responsibility: `issue-analyzer` extracts structured requirements; `repo-scanner` maps the codebase; `solution-designer` plans the fix; `task-planner` breaks it into ordered steps; `impl-executor` carries out one step; `test-verifier` validates the outcome; `change-summarizer` produces the final report.

**Tech Stack:** Markdown (SKILL.md), `gh` CLI, `git`, Kimi CLI `Agent` + `Shell` + `ReadFile`/`WriteFile` tools.

---

## File Structure

| File | Action | Responsibility |
|------|--------|--------------|
| `issue-implementor/SKILL.md` | Rewrite | Core skill document. Contains execution flow, 7 subagent definitions, internal template, boundary cases, and examples. |
| `README.md` | Modify | Update the skill description table to reflect new trigger words and capabilities. |

---

## Task 1: Rewrite SKILL.md — Header, Usage, and Phase 1 (Branch Management)

**Files:**
- Modify: `issue-implementor/SKILL.md` (full rewrite of existing file)

- [ ] **Step 1.1: Overwrite SKILL.md with header, usage, and Phase 1**

  Replace the entire current content of `issue-implementor/SKILL.md` with:
  ```markdown
  ---
  name: issue-implementor
  description: |
    实现 GitHub Issue 的完整工作流 - 从分支管理到代码实现，智能分析 issue 内容并执行开发任务。
    使用多 Subagent 并行分析、设计、实现和验证，支持 issue 内自带方案或自动设计方案两种模式。
    
    触发词: "实现 issue", "开发 issue", "fix issue", "implement issue", "#\d+"
  ---

  # Issue Implementor Skill

  根据 GitHub Issue 自动完成从分支创建到代码实现的完整开发流程。
  通过专用 Subagent 分工协作：分析 issue、扫描仓库、设计解决方案、规划任务、执行实现、测试验证。

  ## 使用方式

  在任意 Git 仓库中，使用以下方式触发：

  ```
  实现 issue #27
  开发 issue 42
  fix issue #123
  implement issue 456
  #27
  ```

  提取 issue 编号的规则：
  - 支持 `#123` 格式
  - 支持直接数字如 `456`
  - 如果用户没有提供，提示用户明确提供 issue 编号

  ## 前置要求

  1. **GitHub CLI (gh)** 已安装并认证：
     ```bash
     gh --version
     gh auth status
     ```
     如未认证，运行 `gh auth login` 完成认证。认证时需要确保有该仓库的读取和在 issue 下评论的权限。

  2. 当前目录在 Git 仓库中，且有 GitHub remote。可以通过 `git remote -v` 验证。

  3. 用户对本仓库有读取 issue 和推送分支的权限。

  ## 执行流程

  ### Phase 1: 分支管理

  1. **提取 issue 编号**
     - 从用户输入中提取 issue 号（支持 `#123`、直接数字）
     - 如果没有提供，提示用户提供 issue 编号

  2. **获取 Issue 基本信息**
     - 使用 `Shell` 执行 `gh issue view <number> --json number,title,state,labels,body`
     - 如果 issue 不存在 → 停止，提示用户检查编号
     - 如果 issue 已关闭 → 询问是否重新打开或继续实现

  3. **检查本地分支**
     - 使用 `Shell` 执行 `git branch --list '*{number}*'` 检查是否存在相关本地分支
     - 如果存在分支（如 `issue-27`、`fix-27`、`feature-27`）：
       - 使用 `Shell` 执行 `git status --short` 检查是否有未提交修改
       - 如有未提交修改 → 询问用户：继续、暂存(stash)后继续、或新建分支
       - 如无未提交修改 → 切换到该分支
     - 如果不存在分支：
       - 使用 `Shell` 执行 `git checkout main || git checkout master` 切换到默认分支
       - 使用 `Shell` 执行 `git pull` 拉取最新代码
       - 使用 `Shell` 执行 `git checkout -b issue-{number}` 创建新分支

  4. **分支命名规范**
     ```
     issue-{number}            # 默认命名
     feature/issue-{number}    # 功能开发（复杂 feature）
     fix/issue-{number}        # Bug 修复
     ```
  ```

- [ ] **Step 1.2: Run a structure check**

  Run:
  ```bash
  git diff --stat
  ```
  Expected: `issue-implementor/SKILL.md` shows ~80 lines added, old content removed.

- [ ] **Step 1.3: Commit**

  ```bash
  git add issue-implementor/SKILL.md
  git commit -m "feat(issue-implementor): rewrite header, usage, and Phase 1 branch management"
  ```

---

## Task 2: Add Phase 2 — Issue Analysis with Subagent Definitions

**Files:**
- Modify: `issue-implementor/SKILL.md`

- [ ] **Step 2.1: Append Phase 2 and subagent definitions to SKILL.md**

  Append to `issue-implementor/SKILL.md`:
  ```markdown

  ### Phase 2: Issue 分析

  启动两个并行 `Agent` 分别进行 issue 内容分析和仓库结构扫描。

  #### 2.1 启动 issue-analyzer

  使用 `Agent` 启动 issue-analyzer subagent：
  - **输入**：issue 标题、body、labels、comments（通过 `gh issue view <number> --json title,body,labels,comments` 获取）
  - **输出**：结构化 JSON 分析结果

  issue-analyzer 输出格式：
  ```json
  {
    "has_plan": true,
    "plan_summary": "在 middleware/auth.py 中添加 JWT 验证逻辑",
    "requirements": [
      "添加 JWT token 解析中间件",
      "验证 token 签名和过期时间",
      "未授权请求返回 401"
    ],
    "issue_type": "feature",
    "complexity": "medium",
    "affected_areas": ["authentication", "middleware"],
    "uncertainties": ["是否需要支持 refresh token"]
  }
  ```

  JSON 字段说明：
  - `has_plan`: issue 描述中是否包含明确的实现方案
  - `plan_summary`: 如 has_plan 为 true，提取方案摘要（不超过 100 字）
  - `requirements`: 从 issue 中提取的具体需求列表，每条一项独立需求
  - `issue_type`: `"bug"` | `"feature"` | `"enhancement"` | `"refactor"` | `"docs"`
  - `complexity`: `"low"` | `"medium"` | `"high"`
  - `affected_areas`: 可能受影响的模块/功能领域列表
  - `uncertainties`: 需要向用户澄清的疑问列表（如无则空数组）

  #### 2.2 启动 repo-scanner

  同时，使用 `Agent` 启动 repo-scanner subagent：
  - **输入**：issue 标题、issue body（前 500 字）、项目根目录结构
  - **输出**：结构化 JSON 扫描结果

  repo-scanner 通过 `Shell` 执行以下命令收集信息：
  ```bash
  # 项目结构
  find . -maxdepth 2 -type f -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" -o -name "*.rs" -o -name "*.java" | head -50
  ls -la
  cat package.json 2>/dev/null || cat pyproject.toml 2>/dev/null || cat Cargo.toml 2>/dev/null || cat go.mod 2>/dev/null
  ```

  repo-scanner 输出格式：
  ```json
  {
    "tech_stack": "Python / FastAPI / SQLAlchemy",
    "relevant_files": [
      {
        "path": "src/middleware/auth.py",
        "reason": "现有认证中间件，最可能需修改的文件"
      },
      {
        "path": "src/models/user.py",
        "reason": "用户模型，可能需添加 token 相关字段"
      }
    ],
    "project_patterns": "使用依赖注入管理中间件，测试放在 tests/ 目录，命名使用 snake_case",
    "test_setup": "pytest tests/，有 conftest.py 配置 fixtures"
  }
  ```

  JSON 字段说明：
  - `tech_stack`: 项目主要技术栈简介
  - `relevant_files`: 与 issue 可能相关的文件列表，每项含路径和关联原因
  - `project_patterns`: 项目编码模式、架构风格的简要描述
  - `test_setup`: 测试框架和运行方式

  #### 2.3 整合分析结果

  收集 issue-analyzer 和 repo-scanner 的输出后：
  1. 如果 `uncertainties` 非空 → 向用户展示问题，等待澄清后再继续
  2. 如果 `has_plan` 为 true → 进入 Phase 4（直接按方案实现）
  3. 如果 `has_plan` 为 false → 进入 Phase 3（自动设计解决方案）

  ## SubAgent 详细定义

  ### issue-analyzer

  **输入**: issue 标题、body、labels、comments（JSON 格式，通过 `gh issue view` 获取）
  **输出**: JSON 分析结果 `{has_plan, plan_summary, requirements, issue_type, complexity, affected_areas, uncertainties}`

  **任务**:
  1. 仔细阅读 issue 标题和描述，理解核心需求或 bug 报告
  2. 阅读 comments，查看是否有补充信息或讨论中的方案
  3. 判断 issue 是否包含明确的实现方案：
     - 如果描述中包含 "应该在 X 文件做 Y"、"建议实现方式"、具体代码示例等 → `has_plan = true`
     - 如果只有问题描述和需求，没有具体实现指导 → `has_plan = false`
  4. 提取所有具体需求，去重，按优先级排序
  5. 判断 issue 类型和复杂度：
     - `low`: 单文件修改，< 50 行，无架构变化
     - `medium`: 多文件修改，< 200 行，可能涉及接口变更
     - `high`: 大规模重构，> 200 行，或涉及架构设计决策
  6. 列出所有不确定或需要用户澄清的问题
  7. 输出严格 JSON，不要包裹在 markdown 代码块中

  ### repo-scanner

  **输入**: issue 标题、issue body 前 500 字、项目根目录文件列表、主要配置文件内容
  **输出**: JSON 扫描结果 `{tech_stack, relevant_files, project_patterns, test_setup}`

  **任务**:
  1. 分析项目技术栈：识别主要编程语言、框架、构建工具
  2. 根据 issue 内容，使用 `grep` 或 `find` 搜索相关代码：
     ```bash
     grep -r "keyword" --include="*.py" --include="*.ts" -l . 2>/dev/null | head -20
     ```
     其中 keyword 从 issue 标题和描述中提取（函数名、模块名、错误信息等）
  3. 识别最可能需要修改的文件，给出关联理由
  4. 总结项目编码模式：目录结构约定、命名规范、架构模式（MVC、微服务等）
  5. 识别测试框架和运行命令
  6. 输出严格 JSON，不要包裹在 markdown 代码块中
  ```

- [ ] **Step 2.2: Verify append succeeded**

  Run:
  ```bash
  grep -c "issue-analyzer" issue-implementor/SKILL.md
  ```
  Expected: output >= 3

- [ ] **Step 2.3: Commit**

  ```bash
  git add issue-implementor/SKILL.md
  git commit -m "feat(issue-implementor): add Phase 2 issue analysis with issue-analyzer and repo-scanner subagents"
  ```

---

## Task 3: Add Phase 3 — Solution Design with Subagent Definitions

**Files:**
- Modify: `issue-implementor/SKILL.md`

- [ ] **Step 3.1: Append Phase 3 and subagent definitions**

  Append to `issue-implementor/SKILL.md`:
  ```markdown

  ### Phase 3: 方案设计（仅当 issue 无明确方案时）

  当 Phase 2 判定 `has_plan = false` 时，启动 solution-designer 和 task-planner 设计实现方案。

  #### 3.1 启动 solution-designer

  使用 `Agent` 启动 solution-designer subagent：
  - **输入**：issue-analyzer 输出 + repo-scanner 输出 + 相关文件内容（通过 `ReadFile` 读取 repo-scanner 标记的 relevant_files）
  - **输出**：结构化 JSON 设计方案

  solution-designer 输出格式：
  ```json
  {
    "approach_summary": "在现有 auth 中间件中添加 JWT 验证，使用 PyJWT 库",
    "files_to_create": [
      {
        "path": "src/utils/jwt_helper.py",
        "purpose": "JWT token 的编码、解码和验证工具函数"
      }
    ],
    "files_to_modify": [
      {
        "path": "src/middleware/auth.py",
        "changes": "在请求处理流程中添加 JWT 验证调用"
      },
      {
        "path": "requirements.txt",
        "changes": "添加 PyJWT 依赖"
      }
    ],
    "files_to_read": [
      "src/config.py",
      "src/exceptions.py"
    ],
    "estimated_effort": "medium",
    "risks": ["需要确保 JWT secret 的配置方式与现有 config 系统兼容"],
    "testing_strategy": "添加单元测试验证 token 生成和验证逻辑，添加集成测试验证中间件行为"
  }
  ```

  JSON 字段说明：
  - `approach_summary`: 实现方案概述，不超过 150 字
  - `files_to_create`: 需要新建的文件列表，每项含路径和用途
  - `files_to_modify`: 需要修改的文件列表，每项含路径和变更描述
  - `files_to_read`: 设计过程中需要参考但未标记修改的文件
  - `estimated_effort`: `"low"` | `"medium"` | `"high"`，应与 issue-analyzer 的 complexity 一致
  - `risks`: 实现风险列表
  - `testing_strategy`: 测试策略简述

  #### 3.2 用户确认

  向用户展示 solution-designer 的输出（转换为易读的 Markdown 格式）：
  ```markdown
  ## 方案设计

  **实现思路**: {approach_summary}

  **新建文件**:
  - `src/utils/jwt_helper.py` - JWT token 的编码、解码和验证工具函数

  **修改文件**:
  - `src/middleware/auth.py` - 在请求处理流程中添加 JWT 验证调用
  - `requirements.txt` - 添加 PyJWT 依赖

  **风险**: {risks}

  **测试策略**: {testing_strategy}

  是否按此方案执行？（确认后将开始逐步实现）
  ```

  等待用户确认：
  - 用户确认 → 进入 Phase 4
  - 用户提出修改 → 调整方案后重新展示，直到确认
  - 用户取消 → 停止执行，保持当前分支状态

  ### solution-designer

  **输入**: issue-analyzer 输出 JSON、repo-scanner 输出 JSON、relevant_files 的内容
  **输出**: JSON 设计方案 `{approach_summary, files_to_create, files_to_modify, files_to_read, estimated_effort, risks, testing_strategy}`

  **任务**:
  1. 阅读 issue-analyzer 提取的需求列表，确保理解所有要求
  2. 阅读 repo-scanner 标记的相关文件内容，理解现有代码结构和模式
  3. 阅读 `files_to_read` 中列出的参考文件（如配置文件、异常定义等）
  4. 设计最小可行的实现方案，遵循 YAGNI 原则：
     - 只修改实现需求所必需的文件
     - 不引入不必要的抽象层
     - 复用现有代码和模式
  5. 评估风险：技术风险、与现有代码的兼容性风险、测试覆盖风险
  6. 制定测试策略：需要哪些测试来验证实现正确
  7. 输出严格 JSON

  **约束**:
  - 方案必须与 repo-scanner 识别的项目模式一致
  - 不引入与现有技术栈不匹配的依赖或框架
  - 优先修改现有文件，新建文件仅在必要时
  ```

- [ ] **Step 3.2: Verify append succeeded**

  Run:
  ```bash
  grep -c "solution-designer" issue-implementor/SKILL.md
  ```
  Expected: output >= 3

- [ ] **Step 3.3: Commit**

  ```bash
  git add issue-implementor/SKILL.md
  git commit -m "feat(issue-implementor): add Phase 3 solution design with solution-designer subagent"
  ```

---

## Task 4: Add Phase 4 — Implementation with Task Planner and Executor

**Files:**
- Modify: `issue-implementor/SKILL.md`

- [ ] **Step 4.1: Append Phase 4 and subagent definitions**

  Append to `issue-implementor/SKILL.md`:
  ```markdown

  ### Phase 4: 代码实现

  #### 4.1 启动 task-planner

  使用 `Agent` 启动 task-planner subagent：
  - **输入**：
    - 如果 `has_plan = true`: issue-analyzer 的 `plan_summary` + `requirements` + repo-scanner 的 `relevant_files`
    - 如果 `has_plan = false`: solution-designer 的完整输出
  - **输出**：有序的任务列表 JSON

  task-planner 输出格式：
  ```json
  {
    "tasks": [
      {
        "id": 1,
        "description": "创建 JWT 工具模块 src/utils/jwt_helper.py",
        "files": ["src/utils/jwt_helper.py"],
        "action": "create",
        "test_command": "pytest tests/utils/test_jwt_helper.py -v",
        "estimated_time": "10min"
      },
      {
        "id": 2,
        "description": "修改认证中间件集成 JWT 验证",
        "files": ["src/middleware/auth.py"],
        "action": "modify",
        "test_command": "pytest tests/middleware/test_auth.py -v",
        "estimated_time": "15min"
      },
      {
        "id": 3,
        "description": "添加 PyJWT 依赖到 requirements.txt",
        "files": ["requirements.txt"],
        "action": "modify",
        "test_command": "pip install -r requirements.txt && pytest tests/ -k auth",
        "estimated_time": "5min"
      }
    ]
  }
  ```

  JSON 字段说明：
  - `tasks`: 有序任务列表，按依赖关系排序（先底层工具，后上层集成）
  - 每个 task 包含：
    - `id`: 任务序号，从 1 开始
    - `description`: 任务描述，清晰说明要做什么
    - `files`: 本任务涉及的文件路径列表
    - `action`: `"create"` | `"modify"` | `"delete"`
    - `test_command`: 完成本任务后应运行的测试命令
    - `estimated_time`: 预估时间（仅用于信息展示）

  #### 4.2 逐任务执行

  按 `tasks` 顺序，为每个任务启动一个 `impl-executor` subagent。

  对每个任务：
  1. 使用 `Agent` 启动 impl-executor，传入：
     - 当前任务的完整信息（id, description, files, action, test_command）
     - 项目上下文（tech_stack, project_patterns, test_setup 来自 repo-scanner）
     - 如果是 `modify` 操作，通过 `ReadFile` 读取目标文件的当前内容传入
     - 如果是 `create` 操作，传入相关参考文件的内容

  2. impl-executor 执行完成后，检查状态：
     - **DONE**: 任务成功完成，运行 `test_command` 验证
     - **DONE_WITH_CONCERNS**: 任务完成但有疑虑，向用户展示疑虑
     - **NEEDS_CONTEXT**: 需要额外信息，提供后继续
     - **BLOCKED**: 无法继续，向用户说明阻塞原因，等待决策

  3. 如果测试命令失败：
     - 将错误输出反馈给 impl-executor，要求修复
     - 最多重试 2 次
     - 如果仍失败 → 向用户展示错误，询问是否继续

  4. 每完成 1-2 个任务，使用 `Shell` 执行：
     ```bash
     git add <changed-files>
     git commit -m "feat(issue-{number}): task {id} - {description}"
     ```

  ### task-planner

  **输入**: issue-analyzer 输出、repo-scanner 输出、(可选) solution-designer 输出
  **输出**: JSON 任务列表 `{tasks: [{id, description, files, action, test_command, estimated_time}]}`

  **任务**:
  1. 分析所有需要创建和修改的文件
  2. 按依赖关系排序任务：
     - 先创建底层工具/模块
     - 后修改使用这些工具的上层代码
     - 配置变更（如依赖）通常放在前面
  3. 为每个任务设计具体的测试验证命令
  4. 确保每个任务只涉及 1-3 个文件，保持任务聚焦
  5. 如果任务过多（> 8 个），建议拆分为多个子 issue 或标记为 high complexity
  6. 输出严格 JSON

  ### impl-executor

  **输入**: 单个 task 对象 + 项目上下文 + 相关文件当前内容
  **输出**: 执行状态 + 变更摘要

  **任务**:
  1. 阅读任务描述和涉及文件的内容
  2. 根据 `action` 执行操作：
     - `create`: 使用 `WriteFile` 创建新文件，内容符合项目模式
     - `modify`: 使用 `StrReplaceFile` 或 `WriteFile` 修改文件，尽量使用最小改动
     - `delete`: 使用 `Shell` 执行 `git rm` 或标记删除
  3. 编写代码时遵循：
     - repo-scanner 识别的项目编码模式
     - 与现有代码风格一致
     - 添加必要的注释和文档字符串
  4. 如果任务包含测试命令，运行测试验证
  5. 返回执行结果：
     ```json
     {
       "status": "DONE",
       "summary": "创建了 src/utils/jwt_helper.py，包含 encode_token、decode_token、verify_token 三个函数",
       "files_changed": ["src/utils/jwt_helper.py"]
     }
     ```

  **约束**:
  - 一次只处理一个任务，不提前实现后续任务的内容
  - 修改文件时使用精确的行范围替换，避免大面积重写
  - 如无必要不添加新依赖；如需添加，明确说明
  ```

- [ ] **Step 4.2: Verify append succeeded**

  Run:
  ```bash
  grep -c "impl-executor" issue-implementor/SKILL.md
  ```
  Expected: output >= 3

- [ ] **Step 4.3: Commit**

  ```bash
  git add issue-implementor/SKILL.md
  git commit -m "feat(issue-implementor): add Phase 4 implementation with task-planner and impl-executor subagents"
  ```

---

## Task 5: Add Phase 5 — Verification and Completion with Subagent Definitions

**Files:**
- Modify: `issue-implementor/SKILL.md`

- [ ] **Step 5.1: Append Phase 5 and subagent definitions**

  Append to `issue-implementor/SKILL.md`:
  ```markdown

  ### Phase 5: 验证与完成

  #### 5.1 启动 test-verifier

  所有任务执行完成后，使用 `Agent` 启动 test-verifier subagent：
  - **输入**：原始 issue requirements、所有变更文件的 git diff、repo-scanner 的 test_setup
  - **输出**：验证结果 JSON

  test-verifier 执行以下检查：
  1. 运行项目完整测试套件（如果测试运行时间短于 5 分钟）
  2. 检查变更是否满足 issue 中的所有 requirements
  3. 检查是否有明显的回归问题（如导入错误、语法错误）
  4. 检查新增代码是否有基本的测试覆盖

  test-verifier 输出格式：
  ```json
  {
    "all_requirements_met": true,
    "tests_pass": true,
    "test_summary": "42 passed, 0 failed, 3 new tests added",
    "regressions": [],
    "issues": [],
    "recommendations": ["建议为 JWT 过期场景添加边界测试"]
  }
  ```

  JSON 字段说明：
  - `all_requirements_met`: 是否满足 issue 中所有需求
  - `tests_pass`: 测试是否全部通过
  - `test_summary`: 测试结果摘要
  - `regressions`: 发现的回归问题列表
  - `issues`: 验证中发现的问题列表（如需求未满足、测试缺失）
  - `recommendations`: 改进建议列表（非阻塞）

  如果 `all_requirements_met` 为 false 或 `tests_pass` 为 false：
  - 向用户展示问题详情
  - 询问是否修复或继续
  - 如选择修复，返回 Phase 4 追加修复任务

  #### 5.2 启动 change-summarizer

  验证通过后，使用 `Agent` 启动 change-summarizer subagent：
  - **输入**：所有 git diff、task-planner 的任务列表及完成状态、test-verifier 的结果
  - **输出**: Markdown 格式的变更摘要

  change-summarizer 输出格式：
  ```markdown
  ## Issue #{number} 实现摘要

  ### 变更概览
  - 新建文件: {N} 个
  - 修改文件: {N} 个
  - 删除文件: {N} 个
  - 总新增行数: {N}+
  - 总删除行数: {N}-

  ### 详细变更
  1. **src/utils/jwt_helper.py** (新建)
     - 实现 JWT token 的编码、解码和验证
  2. **src/middleware/auth.py** (修改)
     - 集成 JWT 验证到请求处理流程
  3. **requirements.txt** (修改)
     - 添加 PyJWT 依赖

  ### 测试情况
  {test-verifier 的 test_summary}

  ### 建议
  - 建议进行 code review 后创建 PR
  - 分支: `issue-{number}`
  ```

  #### 5.3 完成处理

  向用户展示 change-summarizer 的输出，并询问：
  1. 是否需要推送分支到远程：
     ```bash
     git push -u origin issue-{number}
     ```
  2. 是否需要协助创建 PR：
     ```bash
     gh pr create --title "Fix #${number}: {issue_title}" --body "{summary}"
     ```

  ### test-verifier

  **输入**: issue requirements 列表、完整 git diff、repo-scanner 的 test_setup
  **输出**: JSON 验证结果 `{all_requirements_met, tests_pass, test_summary, regressions, issues, recommendations}`

  **任务**:
  1. 逐一检查每个 requirement 是否在代码变更中有对应实现
  2. 根据 test_setup 运行完整测试：
     ```bash
     pytest tests/ -v 2>&1 | tail -20
     ```
     或对应项目的测试命令
  3. 检查 diff 中是否有明显的语法错误、缺失导入、未定义引用
  4. 检查新增功能是否有对应的测试代码（通过 diff 中 tests/ 目录的变化判断）
  5. 输出严格 JSON

  **约束**:
  - 不引入新的代码变更，只做验证
  - 如果测试运行时间超过 5 分钟，只运行与变更相关的测试子集
  - 对于 recommendations，只提供高价值的建议，避免吹毛求疵

  ### change-summarizer

  **输入**: 完整 git diff、task-planner 的任务列表及完成状态、test-verifier 结果
  **输出**: Markdown 变更摘要

  **任务**:
  1. 统计变更数据：新建/修改/删除文件数，新增/删除行数
  2. 按文件列出变更内容，用 1-2 句话描述每个文件的改动
  3. 引用 test-verifier 的测试结果
  4. 给出下一步操作建议（code review、创建 PR）
  5. 输出纯 Markdown，不使用 JSON
  ```

- [ ] **Step 5.2: Verify append succeeded**

  Run:
  ```bash
  grep -c "test-verifier" issue-implementor/SKILL.md
  ```
  Expected: output >= 3

- [ ] **Step 5.3: Commit**

  ```bash
  git add issue-implementor/SKILL.md
  git commit -m "feat(issue-implementor): add Phase 5 verification with test-verifier and change-summarizer subagents"
  ```

---

## Task 6: Add Boundary Cases, Internal Execution Template, and Examples

**Files:**
- Modify: `issue-implementor/SKILL.md`

- [ ] **Step 6.1: Append boundary cases table**

  Append to `issue-implementor/SKILL.md`:
  ```markdown

  ## 边界情况处理

  | 情况 | 处理方式 |
  |------|---------|
  | Issue 不存在 | Phase 1 捕获，停止并提示用户检查编号 |
  | Issue 已关闭 | 询问是否重新打开或继续实现 |
  | 分支已存在且有未提交修改 | 询问用户：继续、stash 后继续、或新建分支 |
  | 本地无 main/master 分支 | 使用 `git branch -r` 查找远程默认分支，基于远程创建 |
  | issue 无明确方案 | 进入 Phase 3，自动设计后等待用户确认 |
  | 方案设计后用户不确认 | 停止执行，保持分支状态，不推送 |
  | impl-executor BLOCKED | 向用户说明阻塞原因，等待决策 |
  | 测试失败且重试 2 次仍失败 | 向用户展示错误，询问是否继续或修复 |
  | 任务数量超过 8 个 | 向用户提示复杂度较高，建议拆分 issue |
  | 变更涉及 > 10 个文件 | 标记为 high complexity，建议分阶段实现 |
  | 实现过程中 issue 被关闭 | 继续完成当前任务后停止，询问是否仍要推送 |
  | 实现过程中出现新 comments | 重新启动 issue-analyzer 分析新信息 |
  | 项目无测试框架 | test-verifier 跳过测试运行，仅做代码检查 |
  | gh CLI 命令失败 | 向用户报告错误详情，停止执行 |
  | git 命令失败 | 向用户报告错误详情，停止执行 |
  ```

- [ ] **Step 6.2: Append internal execution template**

  Append to `issue-implementor/SKILL.md`:
  ```markdown

  ## 内部执行模板

  当用户触发此 Skill 时，遵循以下精确执行流程：

  1. **提取 issue 编号**
     - 从用户输入提取（支持 `#123`、直接数字）
     - 未提供 → 提示用户

  2. **Phase 1: 分支管理**
     - `gh issue view <number> --json number,title,state,labels,body`
     - 检查 issue 存在性和状态
     - `git branch --list '*{number}*'` 检查本地分支
     - 存在且干净 → 切换
     - 存在且有修改 → 询问用户
     - 不存在 → `git checkout main/master && git pull && git checkout -b issue-{number}`

  3. **Phase 2: Issue 分析（并行 Subagent）**
     - 启动 `issue-analyzer`：输入 issue 详情
     - 同时启动 `repo-scanner`：输入 issue 标题 + 项目结构
     - 收集两者输出
     - uncertainties 非空 → 向用户展示并等待澄清
     - has_plan = true → 跳至 Phase 4（使用 issue 自带方案）
     - has_plan = false → 继续 Phase 3

  4. **Phase 3: 方案设计（仅无计划时）**
     - 启动 `solution-designer`：输入 Phase 2 的所有输出
     - 向用户展示方案 Markdown
     - 等待用户确认
     - 确认后进入 Phase 4

  5. **Phase 4: 代码实现**
     - 启动 `task-planner`：输入方案信息
     - 遍历 tasks 列表：
       - 对每个 task 启动 `impl-executor`
       - 检查状态，处理 NEEDS_CONTEXT / BLOCKED
       - 运行 task 的 test_command
       - 失败 → 反馈给 impl-executor 修复（最多 2 次重试）
       - 每 1-2 个 task 执行 `git commit`

  6. **Phase 5: 验证与完成**
     - 启动 `test-verifier`：输入 requirements + 完整 diff
     - 检查 all_requirements_met 和 tests_pass
     - 有问题 → 询问用户是否修复
     - 启动 `change-summarizer`：输入 diff + tasks + verification
     - 向用户展示摘要
     - 询问是否 push 分支和创建 PR

  ## 工作流程示例

  ### 示例 1: Issue 有明确方案

  ```
  用户: #27

  AI:
  1. 创建并切换到分支 issue-27
  2. 读取 issue #27: "Add user authentication middleware"
  3. issue-analyzer: has_plan=true, plan_summary="在 middleware/auth.py 实现 JWT 验证"
  4. repo-scanner: 识别到 src/middleware/auth.py 和相关测试
  5. 进入 Phase 4（跳过方案设计）
  6. task-planner: 分解为 3 个任务
  7. impl-executor 逐个执行：
     - Task 1: 创建 jwt_helper.py
     - Task 2: 修改 auth.py
     - Task 3: 添加依赖
  8. test-verifier: 42 passed, 0 failed
  9. change-summarizer: 生成摘要
  10. 完成，展示修改
  ```

  ### 示例 2: Issue 无具体方案

  ```
  用户: #42

  AI:
  1. 创建并切换到分支 issue-42
  2. 读取 issue #42: "Improve search performance"
  3. issue-analyzer: has_plan=false, requirements=["提升搜索响应速度"]
  4. repo-scanner: 识别到 search 模块使用数据库直接查询
  5. solution-designer: 设计 Redis 缓存层方案
  6. 向用户展示方案，获得确认
  7. task-planner: 分解为 5 个任务
  8. impl-executor 逐个执行
  9. test-verifier: 验证性能和功能
  10. 完成，展示修改
  ```

  ### 示例 3: 需要用户澄清

  ```
  用户: #55

  AI:
  1. 创建并切换到分支 issue-55
  2. issue-analyzer: uncertainties=["是否支持 OAuth 2.0 以外的协议？", "token 过期时间期望是多少？"]
  3. 向用户展示问题：
     - 是否支持 OAuth 2.0 以外的协议？
     - token 过期时间期望是多少？
  4. 用户回复：仅支持 OAuth 2.0，过期时间 1 小时
  5. issue-analyzer 重新运行，uncertainties 为空
  6. 继续后续流程
  ```
  ```

- [ ] **Step 6.3: Verify completeness**

  Run:
  ```bash
  grep -c "## " issue-implementor/SKILL.md
  ```
  Expected: output >= 10 (indicating all major sections are present)

  Run:
  ```bash
  grep -c "### " issue-implementor/SKILL.md
  ```
  Expected: output >= 15 (indicating all subsections are present)

- [ ] **Step 6.4: Commit**

  ```bash
  git add issue-implementor/SKILL.md
  git commit -m "feat(issue-implementor): add boundary cases, internal template, and workflow examples"
  ```

---

## Task 7: Update README.md Skill Description

**Files:**
- Modify: `README.md`

- [ ] **Step 7.1: Update the issue-implementor row in README.md**

  Locate in `README.md`:
  ```markdown
  | [issue-implementor](./issue-implementor) | GitHub Issue 实现工作流 | `实现 issue`, `开发 issue` |
  ```

  Replace with:
  ```markdown
  | [issue-implementor](./issue-implementor) | GitHub Issue 子agent驱动实现工作流 | `实现 issue`, `开发 issue`, `fix issue`, `implement issue`, `#\d+` |
  ```

- [ ] **Step 7.2: Verify change**

  Run:
  ```bash
  grep "issue-implementor" README.md
  ```
  Expected: line contains "子agent驱动" and "fix issue"

- [ ] **Step 7.3: Commit**

  ```bash
  git add README.md
  git commit -m "docs: update issue-implementor description in README"
  ```

---

## Task 8: Final Validation

**Files:**
- Read: `issue-implementor/SKILL.md`

- [ ] **Step 8.1: Validate SKILL.md structure**

  Run:
  ```bash
  # Check all required sections exist
  grep -q "## 执行流程" issue-implementor/SKILL.md && echo "OK: 执行流程"
  grep -q "## SubAgent 详细定义" issue-implementor/SKILL.md && echo "OK: SubAgent 详细定义"
  grep -q "## 边界情况处理" issue-implementor/SKILL.md && echo "OK: 边界情况处理"
  grep -q "## 内部执行模板" issue-implementor/SKILL.md && echo "OK: 内部执行模板"
  grep -q "## 工作流程示例" issue-implementor/SKILL.md && echo "OK: 工作流程示例"
  ```
  Expected: All 5 lines output "OK"

- [ ] **Step 8.2: Validate all 7 subagents are defined**

  Run:
  ```bash
  for agent in issue-analyzer repo-scanner solution-designer task-planner impl-executor test-verifier change-summarizer; do
    grep -q "### $agent" issue-implementor/SKILL.md && echo "OK: $agent" || echo "MISSING: $agent"
  done
  ```
  Expected: All 7 lines output "OK"

- [ ] **Step 8.3: Validate no placeholders**

  Run:
  ```bash
  grep -in "TBD\|TODO\|implement later\|fill in details\|appropriate error handling\|add validation\|handle edge cases\|Similar to Task\|Write tests for the above" issue-implementor/SKILL.md || echo "No placeholders found - PASS"
  ```
  Expected: "No placeholders found - PASS"

- [ ] **Step 8.4: Final commit (if any changes)**

  ```bash
  git diff --cached --quiet || git commit -m "chore(issue-implementor): final validation and polish"
  ```

---

## Self-Review Checklist

**1. Spec coverage:**
- [x] Phase 1: Branch management with all edge cases (existing branch, uncommitted changes, missing main)
- [x] Phase 2: Issue analysis with parallel issue-analyzer + repo-scanner
- [x] Phase 3: Solution design with user confirmation gate
- [x] Phase 4: Task planning + sequential implementation with per-task executor
- [x] Phase 5: Verification with test-verifier + completion with change-summarizer
- [x] 7 Subagents defined with precise input/output contracts
- [x] Boundary cases table covering 16 scenarios
- [x] Internal execution template with exact step order
- [x] 3 workflow examples (has plan, no plan, needs clarification)
- [x] README update with new trigger words

**2. Placeholder scan:**
- [x] No "TBD", "TODO", "implement later"
- [x] No vague instructions like "add appropriate error handling"
- [x] No "similar to Task N" references
- [x] Every code step shows exact code
- [x] Every task shows exact file paths

**3. Type consistency:**
- [x] `has_plan` used consistently as boolean across issue-analyzer output and flow decisions
- [x] `complexity`/`estimated_effort` values consistent: low/medium/high
- [x] `action` values consistent: create/modify/delete
- [x] `status` values consistent: DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED
- [x] Issue number placeholder consistently `{number}` throughout
