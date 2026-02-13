# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ctrlmap-cli** is an unofficial Python CLI client for [ControlMap](https://www.scalepad.com/controlmap/) — a SaaS compliance document management system commonly used for ISO-27001. It exports data from ControlMap's undocumented REST API into machine/human-readable formats (Markdown, JSON, YAML) so LLMs can process them.

Distributed as a single-file Python zip-app. Requires Python 3.9+.

## Repository Layout

```
ctrlmap-cli/
├── ctrlmap_cli/          # Source code (Python package)
│   ├── __main__.py       # Zipapp entry point
│   ├── cli.py            # argparse-based CLI
│   ├── config.py         # .ctrlmap-cli.ini via configparser
│   ├── client.py         # HTTP client wrapping requests
│   ├── exceptions.py     # User-friendly exception hierarchy
│   ├── exporters/        # One exporter class per domain
│   ├── models/           # Dataclasses for API responses
│   └── formatters/       # Markdown, JSON, YAML writers
├── tests/                # pytest tests (mirrors package structure)
├── export/               # Output directory for exported data (gitignored)
├── plans/                # Planning documents
├── tasks/                # Task breakdown (Markdown with status frontmatter)
├── build.sh              # Bundles dependencies + creates zipapp
└── test.sh               # Runs pytest + flake8 + mypy
```

## Build & Development Commands

```bash
bash build.sh             # Build zipapp → dist/ctrlmap-cli
bash test.sh              # Run tests with coverage, linting, type checks

# Individual tools
python -m pytest tests/ --cov=ctrlmap_cli --cov-report=term-missing
python -m pytest tests/test_config.py -k "test_read"   # Run a single test
python -m flake8 ctrlmap_cli/
python -m mypy ctrlmap_cli/

# Run directly during development
python -m ctrlmap_cli --help
```

## Architecture

- **CLI layer** (`cli.py`): `argparse` handles `--init`, `--copy-all`, `--copy-gov`, `--copy-pols`, `--copy-pros`, `--copy-risks`. No subcommands — all flags are mutually exclusive.
- **HTTP client** (`client.py`): Wraps `requests.Session` with bearer token auth + `x-authprovider`/`x-tenanturi` headers. Maps HTTP errors to user-friendly exception subclasses.
- **Config** (`config.py`): Reads/writes `.ctrlmap-cli.ini` via `configparser`. Config stored as an `AppConfig` dataclass.
- **Exporters** (`exporters/`): One class per ControlMap domain (policies, governance, procedures, risks), all inheriting `BaseExporter`. Each fetches from the API, parses into dataclasses, and writes via formatters.
- **Formatters** (`formatters/`): Decoupled output writers. Each exporter writes all three formats (Markdown primary, JSON + YAML for structured data).
- **Error handling**: All exceptions inherit `CtrlMapError`. `__main__.py` catches this at the top level and prints user-friendly messages — no raw tracebacks.

## Key Decisions

- **External dependencies**: `requests`, `PyYAML`, and `markdownify` (bundled into zipapp via `pip install --target`).
- **stdlib for everything else**: `argparse`, `configparser`, `dataclasses`, `json`, `getpass`.
- **Python 3.9 compatibility**: No walrus operators in complex expressions, no `str | None` union syntax, use `from __future__ import annotations` or `typing.Optional`.
- **OOP with dataclasses**: API response data modeled as dataclasses, not raw dicts. Type hints on all function signatures.
- **No virtual env**: The project is designed to run without a venv. Dependencies are bundled at build time.

## ControlMap API

- Base URL: `https://api.eu.ctrlmap.com`
- Auth: `Authorization: Bearer <token>`, `x-authprovider: cmapjwt`, `x-tenanturi: <tenant>`
- ControlMap internally calls everything "procedures" — governance, policies, and procedures are distinguished by a `type` filter.
- Listing: `POST /procedures` with body `{"startpos":0,"pagesize":500,"rules":[{"field":"type","operator":"=","value":"<type>"}]}`
- Detail: `GET /procedure/{id}`
- Related: `GET /procedure/{id}/controls`, `/policies`, `/requirements`
- The `description` field is **double-URL-encoded HTML** — decode twice with `urllib.parse.unquote()`, then convert to Markdown.

## Markdown Output

- All generated Markdown files: max 120 characters per line.
- Linted with `markdownlint-cli2` (Node.js). Config: `.markdownlint-cli2.jsonc`.
- Output folders: `govs/`, `policies/`, `procedures/`, `risks/` (not the longer names).

## Task Tracking

Tasks live in `./tasks/` as Markdown files with a YAML frontmatter `status` field: `backlog`, `development`, `review`, `done`.
