# Error Handling Rules

- All custom exceptions must inherit from `CtrlMapError` (defined in `ctrlmap_cli/exceptions.py`).
- Exception messages must be user-friendly and actionable. Tell the user what went wrong and how to fix it.
  - Good: `"Authentication failed. Your bearer token may have expired. Run ctrlmap-cli --init to set a new token."`
  - Bad: `"HTTP 401 Unauthorized"`
- Never let raw Python tracebacks reach the user. `__main__.py` catches `CtrlMapError` at the top level.
- Catch `requests` exceptions in `client.py` and re-raise as `ApiError` subclasses.
