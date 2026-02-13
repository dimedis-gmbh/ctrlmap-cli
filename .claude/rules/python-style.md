# Python Style Rules

- Target Python 3.9 compatibility. Do not use syntax introduced in 3.10+ (e.g., `match` statements, `X | Y` union types). Use `typing.Optional`, `typing.List`, `typing.Dict` etc.
- Use `from __future__ import annotations` at the top of every module for modern annotation syntax.
- Add type hints to all function parameters and return types.
- Use `dataclasses.dataclass` for data structures instead of plain dicts.
- Max line length: 120 characters.
- Linting: flake8. Type checking: mypy with `disallow_untyped_defs = True`.
