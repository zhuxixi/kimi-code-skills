---
name: issue-implementor
description: |
  Implement GitHub Issues end-to-end using subagent-driven development. Automates worktree setup,
  branch management, issue analysis, solution design, task planning, implementation, and verification.
  Use when user mentions: "实现 issue", "开发 issue", "fix issue", "implement issue",
  or any message containing an issue reference like "#123", "issue #42", "#27".
  Also triggers on requests to implement, fix, or develop a specific GitHub issue number.
  Creates an isolated git worktree for each issue and dispatches specialized subagents
  (issue-analyzer, repo-scanner, solution-designer, task-planner, impl-executor,
  test-verifier, change-summarizer) to complete the work.
---

# Issue Implementor

Implement GitHub Issues from branch creation to code completion using specialized subagents
for analysis, design, planning, execution, and verification.

## Usage

Trigger with any of these patterns:

```
实现 issue #27
开发 issue 42
fix issue #123
implement issue 456
#27
```

Extract issue numbers from:
- `#123` format
- Plain digits like `456`
- Prompt user if no number provided

## Prerequisites

1. **GitHub CLI (gh)** installed and authenticated:
   ```bash
   gh --version
   gh auth status
   ```
   Run `gh auth login` if not authenticated. Need read access to issues and push access to the repo.

2. Current directory in a Git repo with a GitHub remote. Verify with `git remote -v`.

3. Permission to read issues and push branches.

## Execution Flow

### Phase 1: Branch Management & Worktree Setup

1. Extract issue number from user input
2. Fetch issue basics:
   ```bash
   gh issue view <number> --json number,title,state,labels,body
   ```
   - Issue does not exist → stop, prompt user to check number
   - Issue is closed → ask whether to reopen or continue
3. Determine worktree directory:
   - Check existing directories in priority order:
     ```bash
     ls -d .worktrees 2>/dev/null || ls -d worktrees 2>/dev/null
     ```
   - If `.worktrees/` exists → use it
   - If `worktrees/` exists → use it
   - If neither exists → check `CLAUDE.md` for worktree preference
   - If no preference found → ask user (default `.worktrees/`)
   - For project-local directories, verify ignored:
     ```bash
     git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
     ```
     - Not ignored → add to `.gitignore`, commit, then proceed
4. Check for existing worktree:
   ```bash
   git worktree list
   ```
   - If worktree for `issue-{number}` exists → `cd` into it, skip to step 6
5. Create worktree with new branch and record absolute path:
   ```bash
   git worktree add <worktree-dir>/issue-{number} -b issue-{number}
   ```
   - Record the absolute path of the worktree as `$WORKTREE_PATH`
   - This path must be passed to every subagent via the `work_dir` parameter
   Branch naming:
   ```
   issue-{number}           # default
   feature/issue-{number}   # complex feature
   fix/issue-{number}       # bug fix
   ```
6. Run project setup inside worktree (auto-detect):
   ```bash
   cd $WORKTREE_PATH && [ -f package.json ] && npm install
   cd $WORKTREE_PATH && [ -f Cargo.toml ] && cargo build
   cd $WORKTREE_PATH && [ -f requirements.txt ] && pip install -r requirements.txt
   cd $WORKTREE_PATH && [ -f pyproject.toml ] && poetry install
   cd $WORKTREE_PATH && [ -f go.mod ] && go mod download
   ```
   > **Important:** Each Shell command must explicitly `cd $WORKTREE_PATH` because
   > Shell sessions do not persist working-directory changes across calls.
7. Verify clean baseline inside worktree (optional but recommended):
   - Run project-appropriate test command with `cd $WORKTREE_PATH && ...`
   - If tests fail → report to user, ask whether to proceed
   - If tests pass → report ready

All subsequent phases operate inside the worktree directory. Every subagent
must be launched with `work_dir=$WORKTREE_PATH` (absolute path) so its file
tools and Shell commands operate in the correct directory.

### Phase 2: Issue Analysis

Launch two parallel `Agent` instances:

1. **issue-analyzer** — analyze issue content
   - Launch with `work_dir=$WORKTREE_PATH`
   - Input: issue title, body, labels, comments
   - Output: `{has_plan, plan_summary, requirements, issue_type, complexity, affected_areas, uncertainties}`
   - See [references/subagents.md](references/subagents.md#issue-analyzer) for full definition

2. **repo-scanner** — scan codebase structure
   - Launch with `work_dir=$WORKTREE_PATH`
   - Input: issue title, body preview, project root listing
   - Output: `{tech_stack, relevant_files, project_patterns, test_setup}`
   - See [references/subagents.md](references/subagents.md#repo-scanner) for full definition

After collecting both outputs:
- `uncertainties` non-empty → present to user, wait for clarification, then re-run issue-analyzer
- `has_plan = true` → skip Phase 3, go to Phase 4
- `has_plan = false` → go to Phase 3

### Phase 3: Solution Design

Only when issue has no built-in plan.

1. Launch **solution-designer**
   - Launch with `work_dir=$WORKTREE_PATH`
   - Input: issue-analyzer output + repo-scanner output + contents of relevant files
   - Output: `{approach_summary, files_to_create, files_to_modify, files_to_read, estimated_effort, risks, testing_strategy}`
   - See [references/subagents.md](references/subagents.md#solution-designer) for full definition

2. Present plan to user in Markdown:
   ```markdown
   ## Solution Design

   **Approach**: {approach_summary}

   **New files**: {files_to_create}
   **Modified files**: {files_to_modify}
   **Risks**: {risks}
   **Testing**: {testing_strategy}

   Proceed with this plan?
   ```

3. Wait for user confirmation:
   - Confirmed → go to Phase 4
   - Requested changes → adjust and re-present
   - Cancelled → stop, preserve branch state

### Phase 4: Implementation

1. Launch **task-planner**
   - Launch with `work_dir=$WORKTREE_PATH`
   - Input: solution info (from issue plan or designed solution) + repo-scanner context
   - Output: ordered task list `{tasks: [{id, description, files, action, test_command, estimated_time}]}`
   - See [references/subagents.md](references/subagents.md#task-planner) for full definition

2. Execute tasks sequentially with **impl-executor**
   - One `Agent` per task, each with `work_dir=$WORKTREE_PATH`
   - Input: single task + project context + current file contents
   - Output: `{status, summary, files_changed}`
   - See [references/subagents.md](references/subagents.md#impl-executor) for full definition

3. Per-task verification:
   - Run the task's `test_command`
   - Failed → feed error back to impl-executor for fix (max 2 retries)
   - Still failed → present to user, ask whether to continue or abort

4. Commit every 1-2 tasks:
   ```bash
   git add <files>
   git commit -m "feat(issue-{number}): task {id} - {description}"
   ```

### Phase 5: Verification & Completion

1. Launch **test-verifier**
   - Launch with `work_dir=$WORKTREE_PATH`
   - Input: original requirements + full git diff + test setup info
   - Output: `{all_requirements_met, tests_pass, test_summary, regressions, issues, recommendations}`
   - See [references/subagents.md](references/subagents.md#test-verifier) for full definition

2. If `all_requirements_met = false` or `tests_pass = false`:
   - Present issues to user
   - Ask whether to fix or continue
   - Fix chosen → return to Phase 4 with correction tasks

3. Launch **change-summarizer**
   - Launch with `work_dir=$WORKTREE_PATH`
   - Input: full diff + task list + test-verifier result
   - Output: Markdown summary
   - See [references/subagents.md](references/subagents.md#change-summarizer) for full definition

4. Present summary to user, then ask:
   - Push branch from worktree?
     ```bash
     cd $WORKTREE_PATH && git push -u origin issue-{number}
     ```
   - Create PR?
     ```bash
     cd $WORKTREE_PATH && gh pr create --title "Fix #${number}: {issue_title}" --body "{summary}"
     ```
   - Remove worktree?
     ```bash
     git worktree remove $WORKTREE_PATH
     ```

## Internal Execution Template

When triggered, execute in this exact order:

1. **Extract issue number** from user input (or prompt)
2. **Phase 1**: Set up worktree and branch
   - Determine worktree directory (`.worktrees/` or `worktrees/`)
   - Verify directory is ignored (project-local)
   - Check for existing worktree with `git worktree list`
   - Create worktree: `git worktree add <dir>/issue-{number} -b issue-{number}`
   - Record absolute path as `$WORKTREE_PATH`
   - Run auto-detected project setup inside worktree (`cd $WORKTREE_PATH && ...`)
   - Run baseline tests inside worktree
3. **Phase 2**: Launch issue-analyzer + repo-scanner in parallel
   - Both subagents launched with `work_dir=$WORKTREE_PATH`
   - Handle uncertainties if any
   - Route to Phase 3 or 4 based on `has_plan`
4. **Phase 3** (if needed): Launch solution-designer with `work_dir=$WORKTREE_PATH`,
   present to user, wait for confirmation
5. **Phase 4**: Launch task-planner with `work_dir=$WORKTREE_PATH`,
   then loop through tasks with impl-executor (each with `work_dir=$WORKTREE_PATH`)
   - Run per-task tests (`cd $WORKTREE_PATH && <test-command>`)
   - Commit every 1-2 tasks (`cd $WORKTREE_PATH && git commit ...`)
6. **Phase 5**: Launch test-verifier with `work_dir=$WORKTREE_PATH`,
   handle failures, then launch change-summarizer with `work_dir=$WORKTREE_PATH`
7. **Wrap up**: Present summary, offer push and PR creation
   - Optionally offer to remove worktree after PR is created:
     ```bash
     git worktree remove $WORKTREE_PATH
     ```

## Subagent Reference

All subagent definitions live in [references/subagents.md](references/subagents.md):
- issue-analyzer
- repo-scanner
- solution-designer
- task-planner
- impl-executor
- test-verifier
- change-summarizer

Read the relevant subagent definition before dispatching it.

## Boundary Cases

See [references/boundary-cases.md](references/boundary-cases.md) for the full table.

Key scenarios covered: issue not found, issue closed, dirty existing branch, no main/master branch, user rejects plan, executor blocked, test failures after retry, large task counts, issue closed mid-implementation, no test framework, gh/git failures.

## Workflow Examples

See [references/examples.md](references/examples.md) for concrete walkthroughs:
1. Issue with an existing plan
2. Issue requiring solution design
3. Issue with uncertainties needing user clarification
