#!/usr/bin/env python3
"""
Playwright 辅助模块 - 处理打包后的浏览器路径问题
"""
import os
import sys
from pathlib import Path


def get_playwright_browsers_path():
    """
    获取 Playwright 浏览器安装路径

    在打包的可执行文件中，需要使用系统安装的 Playwright 浏览器
    而不是尝试从可执行文件中提取
    """
    # 检查是否在 PyInstaller 打包环境中运行
    if getattr(sys, 'frozen', False):
        # 在打包环境中，使用用户主目录下的 Playwright 浏览器
        # Windows: C:\Users\<username>\AppData\Local\ms-playwright
        # macOS: ~/Library/Caches/ms-playwright
        # Linux: ~/.cache/ms-playwright
        if sys.platform == 'win32':
            browsers_path = Path.home() / 'AppData' / 'Local' / 'ms-playwright'
        elif sys.platform == 'darwin':
            browsers_path = Path.home() / 'Library' / 'Caches' / 'ms-playwright'
        else:
            browsers_path = Path.home() / '.cache' / 'ms-playwright'

        # 设置环境变量，让 Playwright 使用系统浏览器
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browsers_path)

        return browsers_path
    else:
        # 在开发环境中，使用默认路径
        return None


def ensure_browsers_installed():
    """
    确保 Playwright 浏览器已安装

    如果在打包环境中运行且浏览器未安装，返回安装提示
    """
    if getattr(sys, 'frozen', False):
        browsers_path = get_playwright_browsers_path()

        # 检查 Chromium 是否存在
        chromium_paths = list(browsers_path.glob('chromium-*/chrome-win/chrome.exe')) if browsers_path else []

        if not chromium_paths or not chromium_paths[0].exists():
            return False, f"""
╔══════════════════════════════════════════════════════════════════╗
║ Playwright 浏览器未安装                                          ║
╠══════════════════════════════════════════════════════════════════╣
║ 首次运行需要安装 Playwright 浏览器。                             ║
║ 请在命令行中执行以下命令：                                        ║
║                                                                  ║
║     playwright install chromium                                  ║
║                                                                  ║
║ 如果提示找不到 playwright 命令，请先安装：                        ║
║     pip install playwright                                       ║
║     playwright install chromium                                  ║
║                                                                  ║
║ 浏览器将安装到: {browsers_path}
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""

    return True, None


# 在模块加载时自动设置路径
get_playwright_browsers_path()
