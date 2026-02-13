#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

if [[ -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

echo "==> Running flake8"
python -m flake8 .

echo "==> Running mypy"
python -m mypy .

COVERAGE_JSON="$(mktemp)"
trap 'rm -f "${COVERAGE_JSON}"' EXIT

echo "==> Running pytest with coverage"
python -m pytest tests/ \
    --cov=ctrlmap_cli \
    --cov-report=term-missing \
    --cov-report="json:${COVERAGE_JSON}" \
    --cov-fail-under=75

echo "==> Verifying core-module coverage thresholds (>90%)"
python - "${COVERAGE_JSON}" <<'PY'
from __future__ import annotations

import json
import sys
from typing import List, Optional, Tuple


def percent_covered(files: dict, module_path: str) -> Optional[float]:
    summary = files.get(module_path, {}).get("summary", {})
    value = summary.get("percent_covered")
    return float(value) if value is not None else None


coverage_path = sys.argv[1]
with open(coverage_path, "r", encoding="utf-8") as fp:
    report = json.load(fp)

files = report.get("files", {})
errors: List[str] = []

targets = [
    ("ctrlmap_cli/config.py", 90.0),
    ("ctrlmap_cli/client.py", 90.0),
]

for module_path, threshold in targets:
    value = percent_covered(files, module_path)
    if value is None:
        errors.append(f"{module_path}: missing coverage data (required > {threshold:.0f}%)")
    elif value <= threshold:
        errors.append(f"{module_path}: {value:.1f}% (required > {threshold:.0f}%)")

exporter_values: List[Tuple[str, float]] = []
for module_path, metadata in files.items():
    if not module_path.startswith("ctrlmap_cli/exporters/"):
        continue
    summary = metadata.get("summary", {})
    value = summary.get("percent_covered")
    if value is not None:
        exporter_values.append((module_path, float(value)))

if not exporter_values:
    errors.append("ctrlmap_cli/exporters/*: missing coverage data (required > 90%)")
else:
    worst_module, worst_value = min(exporter_values, key=lambda item: item[1])
    if worst_value <= 90.0:
        errors.append(f"{worst_module}: {worst_value:.1f}% (required > 90%)")

if errors:
    print("Core-module coverage check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Core-module coverage check passed.")
PY

echo "All mandatory checks passed."
