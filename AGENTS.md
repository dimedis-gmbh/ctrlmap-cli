# Repository Guidelines

## Project Structure & Module Organization
This repository segment is organized by document type under `export/`:
- `governance/`: governance-level statements and controls
- `policies/`: formal policy documents
- `procedures/`: step-by-step operational procedures
- `risks/`: risk descriptions, assessments, and mitigations
- `.ctrlmap-cli.ini`: local tool configuration marker

Keep each document in the folder matching its purpose. If a document spans multiple domains, place it in the primary domain and cross-link from related files.

## Build, Test, and Development Commands
There is no compile/build step in `export/`; contribution quality is maintained through content checks.
- `find . -maxdepth 2 -type f | sort`: list tracked content files
- `rg "TODO|FIXME" .`: find unresolved placeholders before PR
- `markdownlint "**/*.md"`: lint Markdown style (if installed)
- `npx prettier --check "**/*.md"`: verify Markdown formatting (optional)

Run checks from `export/` before opening a pull request.

## Coding Style & Naming Conventions
Use Markdown with clear, stable headings and short sections. Prefer sentence case in prose and consistent terminology across documents.
- File names: lowercase kebab-case, e.g. `incident-response-policy.md`
- Headings: start at `#` title, then `##`/`###` in order
- Lists: concise bullets; use numbered lists for ordered procedures
- Keep lines readable and avoid unnecessary HTML in Markdown

## Testing Guidelines
Testing is review-driven for this subtree.
- Validate internal links and section anchors
- Confirm procedural steps are executable and ordered
- Ensure policy statements are testable and unambiguous

Treat linting and manual review as the acceptance gate.

## Commit & Pull Request Guidelines
Current history is minimal (`Initial commit`), so use clear, imperative commit subjects moving forward.
- Good examples: `docs(policies): add password policy`, `docs(risks): update vendor risk scoring`
- Keep commits focused to one document set where possible

PRs should include:
- A short summary of what changed and why
- Affected paths (for example, `policies/` or `procedures/`)
- Any follow-up items or known gaps
