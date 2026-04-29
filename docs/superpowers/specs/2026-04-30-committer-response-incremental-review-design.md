# Design: Committer Response Awareness in Incremental Code Review

## Problem Statement

During incremental review (Round-2, Round-3, and re-entry), the github-code-review skill only extracts its own metadata from previous Kimi CR comments. It does **not** read other PR comments where the committer may have responded to raised issues. This causes:

1. **Repeated noise**: Issues the committer explicitly explained and decided not to fix (e.g., "wontfix", "by design") continue being marked as "Still open" in subsequent rounds.
2. **False positive persistence**: Committer clarifications (e.g., "this function strictly returns X") are ignored, leading delta-reviewer to construct hypothetical issues based on wrong assumptions.

### Concrete Case (PR #182 in jfox project)

| Issue | Round-1 | Round-2 | Round-3 | Committer Actual Response |
|-------|---------|---------|---------|---------------------------|
| 1, 3, 4 | open | open | open | **Won't fix** — explained in two rounds of comments |
| 5, 6 | — | open | **Resolved** ✅ | Fix confirmed |
| 8 | — | — | open (false positive) | Committer clarified `_http_health_check` only returns dict/None |

If incremental review had read committer comments, issues 1/3/4 would not remain open, and issue 8 would not have been raised.

## Root Cause

Current incremental review flow (Re-entry Step R2 / Step 0.2) does only two things:
1. Get current PR state (state, head SHA)
2. Filter Kimi CR comments, extract previous round metadata

**Missing step 3**: Read all PR comments, parse committer responses to previous issues.

## Goals

1. Reduce repetitive noise by respecting committer decisions (wontfix, by design).
2. Reduce false positives by feeding committer clarifications into subsequent review rounds.
3. Maintain transparency: clearly distinguish "open", "resolved", and "acknowledged/wontfix" states in published review comments.
4. Minimal structural change: reuse existing `gh pr view --comments` command, extend metadata format, update delta-reviewer prompt.

## Non-Goals

1. **Not** building a full NLP parser for arbitrary natural language. We target common explicit signals.
2. **Not** changing the core 5-agent parallel review architecture for Round-1.
3. **Not** automatically closing issues without committer explicit signal. Only mark as "acknowledged" when committer clearly states intent.

## Design

### Overview

Add a **committer-comment-parser** step to the incremental review flow. After extracting previous Kimi CR metadata, fetch all PR comments, identify committer responses to previously raised issues, classify them, and feed the classification into downstream processing.

### Changes to Incremental Review Flow

#### Step 0.2 (Detect Previous Review Metadata) — Extended

After extracting `previous_issues` from Kimi CR metadata:

1. **Fetch all PR comments** using existing command:
   ```bash
   gh pr view <PR> --comments
   ```
2. **Filter out Kimi CR comments** (already identified). The remaining comments are committer / human reviewer comments.
3. **Parse committer responses** for each `previous_issue` with `status="open"`:
   - Search committer comments for references to the issue (by description keywords, file/line mentions, or issue number if committer quotes it).
   - Classify the response into one of four categories (see Classification below).
4. **Update issue status** in `previous_issues` before passing to delta-reviewer:
   - `acknowledged` / `wontfix` → keep in list but mark with `resolution` field
   - `clarified` → add `committer_note` field
   - `resolved` → mark `status="resolved"` (rare, usually delta-reviewer catches it, but committer may confirm)

#### Step R2 (Re-entry — Get Current State) — Extended

Same extension as Step 0.2. After extracting `previous_issues` from the latest Kimi CR review comment, fetch and parse committer comments before launching delta-reviewer.

#### Step Δ2 (Delta-Reviewer Input) — Extended

Pass the enriched `previous_issues` list to delta-reviewer. Each issue now may include:
- `resolution`: `"acknowledged"` | `"wontfix"` | `"clarified"` | `null`
- `committer_note`: string (explanation or clarification from committer)

Update delta-reviewer prompt to instruct:
1. For issues with `resolution="acknowledged"` or `"wontfix"`: **do not** re-report as open. Move to a separate `acknowledged_issues` list.
2. For issues with `committer_note`: factor the clarification into judgment. If the clarification invalidates the issue (e.g., "function always returns dict" nullifies a "missing null check" issue), mark as resolved with `resolution_note` citing the clarification.
3. For all other open issues: apply existing diff-based logic.

### Classification of Committer Responses

| Signal Keywords (case-insensitive) | Classification | Action |
|------------------------------------|----------------|--------|
| "wontfix", "won't fix", "by design", "intentional", "not a bug", "不需要修复", "不修复", "设计如此" | `wontfix` | Mark as acknowledged, exclude from "Still open" count |
| "fixed", "已修复", "done", "resolved", "addressed" | `resolved` | Mark status=resolved (delta-reviewer should verify) |
| "clarify", "说明", "actually", "context:", "returns", "只返回", "strictly" | `clarified` | Add `committer_note`, pass to delta-reviewer |
| No clear signal | `null` | No change, proceed as before |

**Note**: Classification is heuristic. When in doubt, classify as `clarified` rather than `wontfix`, to preserve human judgment in the loop.

### Metadata Format Update

Extend the `issues` array elements in `<!-- kimi-cr-meta -->`:

```json
{
  "id": "issue-1",
  "description": "...",
  "reason": "bug",
  "file": "src/auth.ts",
  "lines": "67-72",
  "status": "open",
  "first_round": 1,
  "resolution": null,
  "committer_note": null
}
```

New fields:
- `resolution`: `"acknowledged"` | `"wontfix"` | `"resolved"` | `null`
- `committer_note`: string or null

### Round-N Comment Format Update

When publishing Round-N review (N ≥ 2), if there are acknowledged/wontfix issues, render them in a dedicated section:

```markdown
### Code Review | Round-{N} (Re-check)

Previous Round-{N-1} issues: {M}
- **Resolved**: {R}
- **Acknowledged / Won't Fix**: {A}
- **Still open**: {M - R - A}

New issues found: {new_count}

#### Acknowledged / Won't Fix

1. /shutdown endpoint lacks authentication (committer: daemon binds to localhost only, no auth needed)

#### Still Open from Previous Rounds

{remaining_issue_list}

#### New Issues

{new_issue_list}

🤖 Generated with Kimi Code CLI
```

Rules:
- If `acknowledged_issues` is empty, omit the "Acknowledged / Won't Fix" section entirely.
- Acknowledged issues are **not** counted in "Still open".
- They are **not** included in the watcher continuation condition (watcher only cares about truly open issues).

### Delta-Reviewer Output Format Update

Add `acknowledged_issues` to the delta-reviewer output JSON:

```json
{
  "resolved_issues": [...],
  "acknowledged_issues": [
    {
      "original_id": "issue-1",
      "description": "...",
      "reason": "bug",
      "file": "src/auth.ts",
      "lines": "67-72",
      "committer_note": "daemon binds to localhost only, authentication not needed for local service"
    }
  ],
  "new_issues": [...],
  "unresolved_issues": [...],
  "pass": false
}
```

### SubAgent Prompt Updates

#### delta-reviewer (updated prompt additions)

After existing instructions, add:

```
Additional instructions for committer responses:

Some previous issues may have committer responses attached (resolution field):
- "acknowledged" / "wontfix": The committer explicitly declined to fix. DO NOT re-report these as open. Move them to the acknowledged_issues list.
- "clarified": The committer provided additional context (in committer_note). Use this context when judging whether the issue is still valid. If the clarification invalidates the issue, mark it as resolved with a resolution_note citing the clarification.
- No resolution / null: Apply normal diff-based judgment.
```

#### New SubAgent: comment-parser (optional, can be inline)

Because comment parsing is deterministic and rule-based, it can be performed inline by the main agent using `Shell` + string matching, rather than a separate subagent. This avoids an extra LLM call for a task better suited to simple heuristics.

**Inline parsing logic** (performed by main agent):
1. Run `gh pr view <PR> --comments`
2. Extract comment bodies (non-Kimi-CR)
3. For each open previous issue, check if any committer comment contains:
   - The issue description substring (first 10 words) or
   - The file path + line range mentioned in the issue or
   - "issue-1", "issue-2", etc. if committer quoted the id
4. If matched, classify using keyword heuristics (table above)
5. Update the issue object with `resolution` and `committer_note`

### Flow Diagram (Updated Incremental Review)

```
[Detect previous metadata]
        ↓
[Extract previous_issues from Kimi CR]
        ↓
[Fetch all PR comments via gh]
        ↓
[Filter out Kimi CR comments]
        ↓
[Parse committer responses → classify]
        ↓
[Enrich previous_issues with resolution/committer_note]
        ↓
[Launch delta-reviewer with enriched issues]
        ↓
[delta-reviewer outputs: resolved + acknowledged + new + unresolved]
        ↓
[Build Round-N comment with Acknowledged section if needed]
        ↓
[Publish review comment with updated metadata]
        ↓
[Start watcher if unresolved or new issues exist]
```

## Testing Strategy

1. **Unit test comment parsing logic** (can be done with sample comment bodies):
   - Comment containing "wontfix" + issue description → classification = wontfix
   - Comment containing "actually returns dict" + issue description → classification = clarified
   - Comment with no matching keywords → classification = null

2. **Integration test with mock PR**:
   - Create a test PR with known issues
   - Run Round-1 review
   - Post committer comments with wontfix and clarifications
   - Trigger Round-2 (re-entry or manual)
   - Verify acknowledged issues are excluded from "Still open"
   - Verify clarified issues are passed to delta-reviewer

3. **Regression test**:
   - PR with no committer comments → behavior identical to current flow
   - PR with committer comments unrelated to issues → no false classifications

## Rollback Plan

If the heuristic parser produces too many false classifications:
1. Revert to current flow (skip comment parsing)
2. Or tighten classification keywords to require more explicit signals

## Files to Modify

- `github-code-review/SKILL.md` — Update Step 0.2, Step R2, Step Δ2, metadata format, comment format, delta-reviewer prompt

## Out of Scope

- No new files or directories created
- No external dependencies added
- No changes to gh CLI usage patterns
