"""Runtime helpers to locate Playwright browser binaries for packaged builds."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Tuple

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
_RELATIVE_BROWSER_PATHS: Tuple[Path, ...] = (
    Path("playwright-browsers"),
    Path("build") / "playwright-browsers",
    Path("data") / "playwright-browsers",
    Path("playwright") / "driver" / "package" / ".local-browsers",
)


def _iter_browser_candidates() -> Iterable[Path]:
    """Yield potential locations that may contain downloaded Playwright browsers."""

    seen = set()
    frozen_root = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    for root in (frozen_root, PROJECT_ROOT):
        for relative in _RELATIVE_BROWSER_PATHS:
            candidate = (root / relative).resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            yield candidate


def configure_playwright_browsers_path() -> None:
    """Ensure the PLAYWRIGHT_BROWSERS_PATH environment variable is set when possible."""

    existing = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if existing and Path(existing).exists():
        return

    for candidate in _iter_browser_candidates():
        if candidate.exists():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(candidate)
            return

    if getattr(sys, "frozen", False):
        print(
            "⚠️ 未找到打包内置的 Playwright 浏览器资源。\n"
            "   如果是首次运行，请确保打包脚本已下载浏览器，或手动执行 `playwright install chromium`。"
        )
