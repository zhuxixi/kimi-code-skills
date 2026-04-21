# Boundary Cases

How the issue-implementor skill handles edge scenarios and failures.

| Case | Handling |
|------|----------|
| Issue does not exist | Phase 1 catches it. Stop and prompt user to check the issue number. |
| Issue is closed | Ask user whether to reopen the issue or continue implementation on a new branch. |
| Local branch exists with uncommitted changes | Ask user: continue anyway, stash changes and continue, or create a different branch. |
| No main/master branch locally | Use `git branch -r` to find the remote default branch, then base the new branch off the remote tracking branch. |
| Issue has no explicit plan | Enter Phase 3. solution-designer creates a plan, present to user, wait for confirmation before proceeding. |
| User rejects the designed plan | Stop execution. Preserve current branch state. Do not push anything. |
| impl-executor returns BLOCKED | Present the blocker reason to the user and wait for a decision on how to proceed. |
| impl-executor returns NEEDS_CONTEXT | Provide the requested context and re-dispatch the same task. |
| Test fails and 2 retries still fail | Present the error to the user. Ask whether to continue, abort, or handle manually. |
| Task list exceeds 8 tasks | Warn user about high complexity. Suggest splitting the issue into smaller ones. |
| Changes affect more than 10 files | Flag as high complexity. Recommend staging the implementation. |
| Issue gets closed during implementation | Finish the current task, then stop. Ask user whether to still push the branch. |
| New comments appear during implementation | Re-run issue-analyzer on the updated issue to incorporate new information. |
| Project has no test framework | test-verifier skips test execution and performs only static code checks. |
| `gh` CLI command fails | Report the exact error to the user and stop execution. |
| `git` command fails | Report the exact error to the user and stop execution. |
| `git push` fails (e.g., no write access) | Report the error. Offer to retry or stop. |
| `gh pr create` fails | Report the error. Show the command that failed so the user can run it manually. |
| Worktree directory not ignored | Add directory to `.gitignore`, commit the change, then proceed with worktree creation. |
| Worktree already exists for issue | `cd` into existing worktree, verify branch state, continue. |
| Worktree branch has uncommitted changes | Same as dirty branch: ask user whether to continue, stash, or reset. |
| Worktree creation fails | Report git error. Common causes: branch already exists, path conflicts. |
| Baseline tests fail in worktree | Report failures to user. Ask whether to proceed or investigate first. |
| User wants to keep worktree after PR | Do not remove. Leave worktree for further edits. |
| User wants worktree removed after PR | Run `git worktree remove <path>`. If branch is fully merged, optionally delete branch. |
