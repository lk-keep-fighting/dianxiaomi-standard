#!/usr/bin/env python3
"""
独立的 Windows 单文件打包脚本（Miaoshou Collector）

用途：将 src/miaoshou/main.py 打包为单个可执行文件（.exe），并内置 Playwright 浏览器资源。
要求：
- 安装打包依赖：pip install -r requirements-packaging.txt
- 安装 Playwright 浏览器：python -m playwright install chromium
- 安装 Excel 导出库：pip install xlsxwriter

用法示例：
- python scripts/package_miaoshou_exe.py --name miaoshou-collector

生成位置：dist/windows/<name>.exe
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
ENTRY_PATH = SRC_DIR / "miaoshou" / "main.py"
DEFAULT_APP_NAME = "miaoshou-collector"
DIST_DIR = PROJECT_ROOT / "dist" / "windows"
BUILD_DIR = PROJECT_ROOT / "build" / "windows"
PLAYWRIGHT_BROWSERS_DIR = PROJECT_ROOT / "build" / "playwright-browsers"
PLAYWRIGHT_BROWSERS_TARGET = "playwright-browsers"


def ensure_pyinstaller_available() -> str:
    """返回 pyinstaller 可执行路径，不存在则提示安装。"""
    candidate = shutil.which("pyinstaller")
    if candidate:
        return candidate
    raise RuntimeError(
        "PyInstaller 未安装。请先运行 `pip install -r requirements-packaging.txt` 再继续。"
    )


def ensure_playwright_browsers_installed(browsers: Tuple[str, ...] = ("chromium",)) -> Path:
    """确保 Playwright 浏览器已下载，并返回目录路径。"""
    target = PLAYWRIGHT_BROWSERS_DIR
    target.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(target)
    command = [sys.executable, "-m", "playwright", "install", *browsers]

    print("🌐 确保 Playwright 浏览器已安装:", ", ".join(browsers))
    subprocess.run(command, check=True, cwd=str(PROJECT_ROOT), env=env)
    return target


def resolve_add_data_args(extra_entries: Optional[List[Tuple[Path, str]]] = None) -> List[str]:
    """构建 PyInstaller 的 --add-data 参数。"""
    entries: List[Tuple[Path, str]] = [
        (PROJECT_ROOT / "config", "config"),
        (PROJECT_ROOT / "data", "data"),
    ]
    if extra_entries:
        entries.extend(extra_entries)

    args: List[str] = []
    separator = ";" if os.name == "nt" else ":"
    for src, target in entries:
        if not src.exists():
            continue
        args.extend(["--add-data", f"{src}{separator}{target}"])
    return args


def build_executable(app_name: str) -> None:
    """执行打包为单个 EXE 的流程。"""
    pyinstaller = ensure_pyinstaller_available()

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    playwright_browsers_dir = ensure_playwright_browsers_installed()
    extra_data = [(playwright_browsers_dir, PLAYWRIGHT_BROWSERS_TARGET)]

    command: List[str] = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        app_name or DEFAULT_APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
        # Playwright 相关收集
        "--hidden-import",
        "playwright.sync_api._generated",
        "--collect-all",
        "playwright",
        # Excel 导出库收集
        "--hidden-import",
        "xlsxwriter",
        "--collect-all",
        "xlsxwriter",
        # 将 src 放入模块搜索路径
        "--paths",
        str(SRC_DIR),
    ]
    command.extend(resolve_add_data_args(extra_data))
    command.append(str(ENTRY_PATH))

    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(playwright_browsers_dir)

    print("🛠️ 运行打包命令:")
    print(" ".join(command))
    subprocess.run(command, check=True, cwd=str(PROJECT_ROOT), env=env)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        default=DEFAULT_APP_NAME,
        help="生成的可执行文件名称（默认: miaoshou-collector）",
    )
    args = parser.parse_args(argv)

    if platform.system() != "Windows":
        print("⚠️ 当前系统并非 Windows。建议在 Windows 环境中执行打包。")

    print(f"▶️ 入口脚本: {ENTRY_PATH}")
    print(f"📦 输出名称: {args.name or DEFAULT_APP_NAME}.exe")

    try:
        build_executable(args.name)
        print("\n✅ 打包完成，生成的可执行文件位于 dist/windows 目录下。")
    except subprocess.CalledProcessError as exc:
        print("❌ 打包过程失败，请检查错误信息：")
        print(str(exc))
        return 1
    except Exception as exc:
        print("❌ 打包失败：", str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
