# Code Reviews

When asked for a code review, behave like a senior Python architect focused on readable, understandable, and maintainable code.

Inspect all uncommitted changes, including untracked files.
Inspect not only changed lines, but also nearby impacted code paths (callers, callees, and related tests) for regressions.

If a code review request does not include a task number from `./tasks`, ask for it.

Read the task status from the task file frontmatter header.
If the status is not `review` (case-insensitive), abort.

Sort all findings strictly by severity using `high`, `medium`, `low`.
Within each severity level, order findings by impact (highest impact first).
Use this fixed severity rubric:
- `high`: likely production bug, data loss/corruption risk, security issue, or major behavioral regression.
- `medium`: maintainability, reliability, or performance concern with meaningful impact.
- `low`: minor clarity/style issue or low-impact improvement.

Every finding is `must-fix (before merge)`.
Each finding must include a precise file/line reference and a concrete fix recommendation.

Do not abort on failing tests or lint/type checks. Continue the review and report each failing check as a finding.
Always run linting yourself during review using `flake8 .` (whole repository), as defined in `./.claude/rules/python-style.md`.
Always run type checking yourself during review using `mypy .` (whole repository), as defined in `./.claude/rules/python-style.md`.
Always run tests yourself during review: `python -m pytest tests/ --cov=ctrlmap_cli --cov-report=term-missing`.

If `flake8`, `mypy`, or the test command cannot be executed due to environment/setup issues, abort the review.
If you have a clear recommendation to fix the environment/setup issue, ask for user confirmation before applying the fix.

Code reviews must always verify coverage is within the desired range defined in `./.claude/rules/testing.md` and report the result.
Code reviews must always verify that all rules in `./.claude/rules/` have been followed.

Present findings to the user and store them in a file next to the task file, for example `./tasks/01-my-task.codereview.md`.
Always create or update this review file, even when there are no findings.
If the review file already exists, append a new timestamped review entry instead of overwriting content.
Use ISO 8601 UTC for timestamps, for example `2026-02-13T14:30:00Z`.
When there are no findings, explicitly state "no findings" and still include residual risks and testing gaps.

Use this mandatory output template in both chat and the `*.codereview.md` file:
- Summary: task ID, reviewed scope, and overall outcome.
- Checks Run: exact commands executed and their pass/fail status. For failed checks, include brief relevant error excerpts.
- Findings: sorted by severity (`high`, `medium`, `low`); for each finding include file/line, impact, concrete fix recommendation, and `must-fix (before merge)` label.
- Coverage: required coverage targets from `./.claude/rules/testing.md`, measured coverage, and pass/fail assessment.
- Residual Risks: remaining technical or product risks after proposed fixes.
- Testing Gaps: missing or weak test scenarios.
- Recommendation: clear merge recommendation and must-fix items before merge.

End the code review with a clear recommendation and the question whether the user wants all recommendations implemented.

If clear recommendations or learnings for further development can be derived from the review, tell the user.
Only include rule update suggestions when there are concrete rule updates to propose.
If rules can be improved or new rules are appropriate, provide clear recommendations and ask whether those rule updates should be implemented.
