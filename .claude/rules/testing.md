# Testing Rules

- Tests live in `tests/` at the repo root, mirroring the package structure (e.g., `tests/test_config.py` for `ctrlmap_cli/config.py`).
- Use `tmp_path` fixture for any test that writes to disk.
- Use `monkeypatch` or `unittest.mock` for mocking — no real HTTP calls in tests.
- Target 75% overall test coverage. Core modules (config, client, exporters) should be above 90%.
- Run tests with: `python -m pytest tests/ --cov=ctrlmap_cli --cov-report=term-missing`
