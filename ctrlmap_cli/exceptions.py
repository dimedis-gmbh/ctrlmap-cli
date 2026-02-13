from __future__ import annotations


class CtrlMapError(Exception):
    """Base exception with user-friendly message."""
    pass


class ConfigError(CtrlMapError):
    pass
