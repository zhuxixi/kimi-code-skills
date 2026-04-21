# Workflow Examples

Concrete walkthroughs of how the issue-implementor skill handles different scenarios.

---

## Example 1: Issue with an Existing Plan

```
User: #27

AI:
1. Extract issue number: 27
2. Phase 1 — Branch management:
   - Check local branches: none matching *27*
   - Checkout main, pull latest
   - Create and switch to branch issue-27
3. Phase 2 — Parallel analysis:
   - issue-analyzer:
     - has_plan: true
     - plan_summary: "Implement JWT validation in middleware/auth.py"
     - requirements: ["Add JWT parsing", "Validate signature", "Return 401 on failure"]
     - complexity: medium
   - repo-scanner:
     - tech_stack: Python / FastAPI
     - relevant_files: [src/middleware/auth.py, src/config.py]
     - test_setup: pytest tests/
   - has_plan = true → skip Phase 3
4. Phase 4 — Implementation:
   - task-planner outputs 3 tasks:
     1. Create src/utils/jwt_helper.py
     2. Modify src/middleware/auth.py
     3. Add PyJWT to requirements.txt
   - impl-executor runs each task sequentially
   - Tests pass after each task
   - Commit after task 2 and task 3
5. Phase 5 — Verification:
   - test-verifier: all requirements met, 42 passed, 0 failed
   - change-summarizer produces Markdown summary
6. Completion:
   - Present summary to user
   - Offer to push branch and create PR
```

---

## Example 2: Issue Without a Specific Plan

```
User: #42

AI:
1. Extract issue number: 42
2. Phase 1 — Branch management:
   - Branch issue-42 exists and is clean
   - Switch to issue-42
3. Phase 2 — Parallel analysis:
   - issue-analyzer:
     - has_plan: false
     - requirements: ["Improve search response speed"]
     - complexity: medium
     - affected_areas: ["search"]
   - repo-scanner:
     - tech_stack: Python / Django / PostgreSQL
     - relevant_files: [src/search/views.py, src/search/queries.py]
     - project_patterns: "ORM queries in queries.py, views handle HTTP layer"
4. Phase 3 — Solution design:
   - solution-designer proposes:
     - Approach: Add Redis caching layer for frequent search queries
     - New files: src/search/cache.py
     - Modified files: src/search/views.py, src/search/queries.py, requirements.txt
     - Risks: ["Cache invalidation on data updates"]
   - Present plan to user
   - User confirms
5. Phase 4 — Implementation:
   - task-planner breaks into 5 tasks
   - impl-executor executes each
   - One test fails on task 3 → feed error back → impl-executor fixes → passes
6. Phase 5 — Verification:
   - test-verifier confirms requirements met
   - change-summarizer generates summary
7. Completion:
   - Present summary
   - User opts to push branch and create PR
```

---

## Example 3: Issue with Uncertainties Requiring Clarification

```
User: #55

AI:
1. Extract issue number: 55
2. Phase 1 — Branch management:
   - Create and switch to issue-55
3. Phase 2 — Parallel analysis:
   - issue-analyzer:
     - has_plan: false
     - requirements: ["Add OAuth authentication"]
     - uncertainties: [
         "Support protocols other than OAuth 2.0?",
         "What should the token expiration time be?"
       ]
   - repo-scanner completes normally
4. Handle uncertainties:
   - Present questions to user:
     - "Support protocols other than OAuth 2.0?"
     - "What should the token expiration time be?"
   - User replies: "Only OAuth 2.0, 1 hour expiration"
5. Re-run issue-analyzer with clarified context:
   - uncertainties: []
   - has_plan: false
6. Phase 3 — Solution design:
   - solution-designer creates plan
   - User confirms
7. Phases 4-5 — Implementation and verification proceed normally
8. Completion:
   - Present summary
   - Offer next steps
```
