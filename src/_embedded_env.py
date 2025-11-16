"""Embedded environment fallbacks.

This module is populated automatically by packaging scripts (for example,
``scripts/package_windows_exe.py``) so that compiled executables can run
without requiring end users to set up environment variables manually.

During regular development the dictionary is intentionally left empty.
"""
from __future__ import annotations

from typing import Dict

EMBEDDED_ENV: Dict[str, str] = {}
