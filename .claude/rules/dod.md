# Definition of Done (DoD)

Use this checklist before changing a task status to `review` or `done`.

## Gate 1: Ready for Review

A task is **ready for review** only if all items below are true:

- [ ] Task requirements from `./tasks/<id>-*.md` are fully implemented.
- [ ] All relevant rules in `./.claude/rules/` are followed (`python-style`, `testing`, `architecture`, `error-handling`, `markdown-output`, and this DoD).
- [ ] New and changed files are included in the review scope (including untracked files).
- [ ] Tests were added or updated for changed behavior.
- [ ] Mandatory quality checks were executed and passed (see commands below).
- [ ] If linting or tests fail, the task **must not** be flagged as `review`.

## Gate 2: Done

A task is **done** only if all items below are true:

- [ ] Code review for the task was completed and documented in `./tasks/<id>-*.codereview.md`.
- [ ] There are no open `must-fix (before merge)` findings.
- [ ] Mandatory checks were re-run after final fixes and still pass.
- [ ] Task frontmatter status is updated only after the above checks are satisfied.

## Mandatory Commands After Development

Run this single command:

```bash
./run-all-tests.sh
```

It must execute, at minimum:

```bash
python -m flake8 .
python -m mypy .
python -m pytest tests/ --cov=ctrlmap_cli --cov-report=term-missing --cov-fail-under=75
```

Coverage policy:

- Overall coverage must be at least `75%`.
- Core module coverage must be above `90%` for `ctrlmap_cli/config.py`, `ctrlmap_cli/client.py`, and `ctrlmap_cli/exporters/*`.
