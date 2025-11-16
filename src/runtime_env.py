"""Runtime environment utilities.

This module centralizes environment variable access so that packaged builds can
optionally embed required secrets (for example, Supabase credentials) without
requiring end users to configure them manually.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

try:  # pragma: no cover - optional module generated during packaging
    from _embedded_env import EMBEDDED_ENV as _EMBEDDED_ENV  # type: ignore
except Exception:  # pragma: no cover - fall back to empty defaults when missing
    _EMBEDDED_ENV: Dict[str, str] = {}


def _normalize_key(name: str) -> str:
    """Normalize environment variable keys for consistent lookups."""
    return name.upper()


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return the environment variable ``name`` with embedded fallbacks."""

    value = os.getenv(name)
    if value is not None and value != "":
        return value

    normalized = _normalize_key(name)
    if normalized in _EMBEDDED_ENV:
        return _EMBEDDED_ENV[normalized]

    return default


def require_env(name: str, default: Optional[str] = None) -> str:
    """Return ``name`` or raise ``RuntimeError`` when it cannot be resolved."""

    value = get_env(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def embedded_snapshot() -> Dict[str, str]:
    """Expose a copy of the embedded environment dictionary (for diagnostics)."""

    return dict(_EMBEDDED_ENV)
