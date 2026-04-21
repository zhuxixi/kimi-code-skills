# Subagent Definitions

This document defines all subagents used by the issue-implementor skill.

Read the definition for a subagent before dispatching it.

---

## issue-analyzer

Analyze a GitHub issue and extract structured information.

**Input:**
- Issue title
- Issue body
- Labels
- Comments (from `gh issue view --json title,body,labels,comments`)

**Output:** JSON
```json
{
  "has_plan": true,
  "plan_summary": "Add JWT validation in middleware/auth.py",
  "requirements": [
    "Add JWT token parsing middleware",
    "Validate token signature and expiration",
    "Return 401 for unauthorized requests"
  ],
  "issue_type": "feature",
  "complexity": "medium",
  "affected_areas": ["authentication", "middleware"],
  "uncertainties": ["Support refresh tokens?"]
}
```

**Fields:**
- `has_plan` (bool): Whether the issue description contains an explicit implementation plan
- `plan_summary` (string | null): Summary of the plan if `has_plan` is true (max 100 chars)
- `requirements` (string[]): List of concrete requirements extracted from the issue
- `issue_type` (string): One of `"bug"`, `"feature"`, `"enhancement"`, `"refactor"`, `"docs"`
- `complexity` (string): One of `"low"`, `"medium"`, `"high"`
  - `low`: single file, < 50 lines, no architectural change
  - `medium`: multiple files, < 200 lines, possible interface change
  - `high`: large refactor, > 200 lines, or architectural decision needed
- `affected_areas` (string[]): Module or functional areas likely affected
- `uncertainties` (string[]): Questions that need user clarification (empty if none)

**Tasks:**
1. Read the issue title and description carefully
2. Read comments for supplementary info or discussed plans
3. Determine if an explicit plan exists:
   - Contains "should do X in Y file", "suggested approach", code examples → `has_plan = true`
   - Only problem description and requirements → `has_plan = false`
4. Extract all concrete requirements, deduplicate, sort by priority
5. Classify issue type and complexity
6. List any uncertainties that need clarification
7. Output strict JSON, not wrapped in markdown code blocks

---

## repo-scanner

Scan the repository structure and identify relevant files for an issue.

**Input:**
- Issue title
- Issue body (first 500 chars)
- Project root directory listing

**Output:** JSON
```json
{
  "tech_stack": "Python / FastAPI / SQLAlchemy",
  "relevant_files": [
    {
      "path": "src/middleware/auth.py",
      "reason": "Existing auth middleware, most likely file to modify"
    }
  ],
  "project_patterns": "Dependency injection for middleware, tests in tests/, snake_case naming",
  "test_setup": "pytest tests/, conftest.py configures fixtures"
}
```

**Fields:**
- `tech_stack` (string): Brief tech stack description
- `relevant_files` (object[]): Files likely related to the issue, each with `path` and `reason`
- `project_patterns` (string): Coding conventions, architecture style, naming conventions
- `test_setup` (string): Test framework and how to run it

**Tasks:**
1. Identify the main programming language, framework, and build tools
2. Search for relevant code using keywords from the issue:
   ```bash
   grep -r "keyword" --include="*.py" --include="*.ts" -l . 2>/dev/null | head -20
   ```
3. List the most likely files to modify with reasons
4. Summarize project conventions: directory structure, naming, architecture patterns
5. Identify the test framework and standard test command
6. Output strict JSON, not wrapped in markdown code blocks

---

## solution-designer

Design an implementation approach when the issue lacks a built-in plan.

**Input:**
- issue-analyzer output
- repo-scanner output
- Contents of files marked as `relevant_files` by repo-scanner

**Output:** JSON
```json
{
  "approach_summary": "Add JWT validation to existing auth middleware using PyJWT",
  "files_to_create": [
    {
      "path": "src/utils/jwt_helper.py",
      "purpose": "JWT encode/decode/verify utility functions"
    }
  ],
  "files_to_modify": [
    {
      "path": "src/middleware/auth.py",
      "changes": "Add JWT verification call to request handling flow"
    }
  ],
  "files_to_read": ["src/config.py", "src/exceptions.py"],
  "estimated_effort": "medium",
  "risks": ["JWT secret config must be compatible with existing config system"],
  "testing_strategy": "Unit tests for token logic, integration tests for middleware behavior"
}
```

**Fields:**
- `approach_summary` (string): Plan overview (max 150 chars)
- `files_to_create` (object[]): New files with `path` and `purpose`
- `files_to_modify` (object[]): Existing files with `path` and `changes` description
- `files_to_read` (string[]): Reference files to consult but not modify
- `estimated_effort` (string): `"low"`, `"medium"`, or `"high"`
- `risks` (string[]): Implementation risks
- `testing_strategy` (string): How to test the implementation

**Tasks:**
1. Read the requirements from issue-analyzer
2. Read relevant file contents to understand existing code
3. Read reference files (`files_to_read`) for context
4. Design a minimal viable solution following YAGNI:
   - Only modify files necessary to meet requirements
   - Do not introduce unnecessary abstraction layers
   - Reuse existing code and patterns
5. Assess risks: technical, compatibility, test coverage
6. Define testing strategy
7. Output strict JSON, not wrapped in markdown code blocks

**Constraints:**
- Align with project patterns identified by repo-scanner
- Do not introduce dependencies incompatible with the existing tech stack
- Prefer modifying existing files over creating new ones unless necessary

---

## task-planner

Break a solution into ordered, independently executable tasks.

**Input:**
- issue-analyzer output
- repo-scanner output
- solution-designer output (if Phase 3 ran)

**Output:** JSON
```json
{
  "tasks": [
    {
      "id": 1,
      "description": "Create JWT utility module src/utils/jwt_helper.py",
      "files": ["src/utils/jwt_helper.py"],
      "action": "create",
      "test_command": "pytest tests/utils/test_jwt_helper.py -v",
      "estimated_time": "10min"
    }
  ]
}
```

**Fields:**
- `tasks` (object[]): Ordered task list
  - `id` (number): Task sequence starting at 1
  - `description` (string): Clear task description
  - `files` (string[]): Files involved in this task
  - `action` (string): `"create"`, `"modify"`, or `"delete"`
  - `test_command` (string): Test to run after completing this task
  - `estimated_time` (string): Rough time estimate for info only

**Tasks:**
1. List all files to create and modify
2. Order by dependency:底层 utilities first, then integrations, config changes early
3. Design a test command for each task
4. Keep each task focused on 1-3 files
5. If more than 8 tasks, flag as high complexity and suggest splitting the issue
6. Output strict JSON, not wrapped in markdown code blocks

---

## impl-executor

Execute a single task from the task plan.

**Input:**
- Single task object from task-planner
- Project context (tech_stack, project_patterns, test_setup)
- Current contents of files to modify (for `modify` action)
- Reference file contents (for `create` action)

**Output:** JSON
```json
{
  "status": "DONE",
  "summary": "Created src/utils/jwt_helper.py with encode_token, decode_token, verify_token",
  "files_changed": ["src/utils/jwt_helper.py"]
}
```

**Status values:**
- `DONE`: Task completed successfully
- `DONE_WITH_CONCERNS`: Completed but with noted concerns
- `NEEDS_CONTEXT`: Needs additional information to proceed
- `BLOCKED`: Cannot complete; blocker identified

**Tasks:**
1. Read the task description and involved files
2. Execute the `action`:
   - `create`: Use `WriteFile` to create the new file, matching project patterns
   - `modify`: Use `StrReplaceFile` or `WriteFile` for minimal changes
   - `delete`: Use `Shell` with `git rm` or mark for deletion
3. Follow repo-scanner's identified patterns and existing code style
4. Add necessary comments and docstrings
5. Run the task's `test_command` if provided
6. Return result JSON

**Constraints:**
- Handle only one task at a time; do not implement future tasks prematurely
- Use precise line-range replacements when modifying files
- Do not add new dependencies unless necessary; if added, explicitly state why

---

## test-verifier

Verify that implementation meets all requirements and tests pass.

**Input:**
- Original requirements list from issue-analyzer
- Full git diff of all changes
- repo-scanner test_setup info

**Output:** JSON
```json
{
  "all_requirements_met": true,
  "tests_pass": true,
  "test_summary": "42 passed, 0 failed, 3 new tests added",
  "regressions": [],
  "issues": [],
  "recommendations": ["Add edge-case test for JWT expiration"]
}
```

**Fields:**
- `all_requirements_met` (bool): Whether every requirement is satisfied
- `tests_pass` (bool): Whether the test suite passes
- `test_summary` (string): Brief test result summary
- `regressions` (string[]): Any regressions found
- `issues` (string[]): Verification problems (unmet requirements, missing tests)
- `recommendations` (string[]): Non-blocking improvement suggestions

**Tasks:**
1. Check each requirement against the code changes for corresponding implementation
2. Run the full test suite (or relevant subset if full suite exceeds 5 minutes):
   ```bash
   pytest tests/ -v 2>&1 | tail -20
   ```
3. Scan the diff for obvious syntax errors, missing imports, unresolved references
4. Check whether new functionality has test coverage (look for tests/ changes in diff)
5. Output strict JSON, not wrapped in markdown code blocks

**Constraints:**
- Do not make new code changes; only verify
- If tests take longer than 5 minutes, run only the subset related to changed files
- Keep recommendations high-value; avoid nitpicking

---

## change-summarizer

Produce a human-readable summary of all changes made.

**Input:**
- Full git diff
- task-planner task list with completion status
- test-verifier result

**Output:** Markdown text (not JSON)

**Example output:**
```markdown
## Issue #27 Implementation Summary

### Overview
- New files: 1
- Modified files: 2
- Lines added: 87
- Lines removed: 12

### Changes
1. **src/utils/jwt_helper.py** (new)
   - JWT token encode/decode/verify utilities
2. **src/middleware/auth.py** (modified)
   - Integrated JWT verification into request flow
3. **requirements.txt** (modified)
   - Added PyJWT dependency

### Tests
42 passed, 0 failed, 3 new tests added

### Next steps
- Review the changes
- Branch: `issue-27`
```

**Tasks:**
1. Count new/modified/deleted files and added/removed lines
2. List each changed file with a 1-2 sentence description of what changed
3. Include test-verifier's test summary
4. Suggest next steps (code review, create PR)
5. Output plain Markdown, not wrapped in JSON
