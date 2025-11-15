# -*- mode: python ; coding: utf-8 -*-

"""
数字酬长自动化工具 - PyInstaller配置文件

专门优化Playwright和Web自动化应用的打包配置
"""

import os
from pathlib import Path

block_cipher = None

# 数据文件列表
datas = [
    # 配置文件
    ('config', 'config') if os.path.exists('config') else None,
    ('src/config', 'src/config') if os.path.exists('src/config') else None,
    
    # 必要的文档文件
    ('README.md', '.') if os.path.exists('README.md') else None,
    ('requirements.txt', '.') if os.path.exists('requirements.txt') else None,
    
    # JSON配置文件
    ('config/field_defaults.json', 'config') if os.path.exists('config/field_defaults.json') else None,
    ('src/form-json-schema.json', 'src') if os.path.exists('src/form-json-schema.json') else None,
    ('form_config.json', '.') if os.path.exists('form_config.json') else None,
]

# 过滤掉None值
datas = [item for item in datas if item is not None]

# 隐式导入列表 - 包含所有必要的模块
hiddenimports = [
    # Playwright核心模块
    'playwright',
    'playwright.sync_api',
    'playwright.async_api', 
    'playwright._impl',
    'playwright._impl._browser',
    'playwright._impl._page',
    'playwright._impl._frame',
    'playwright._impl._locator',
    'playwright.sync_api._generated',
    'playwright._impl._connection',
    'playwright._impl._transport',
    
    # 项目自定义模块
    'amazon_product_parser',
    'product_data',
    'unified_form_filler', 
    'ai_category_validator',
    'csv_logger',
    'system_config',
    'automation_engine',
    'dom_field_parser',
    'field_defaults_manager',
    
    # Web相关
    'requests',
    'urllib3',
    'ssl',
    'certifi',
    'charset_normalizer',
    
    # HTML解析
    'bs4',
    'beautifulsoup4',
    'lxml',
    'html.parser',
    
    # JSON和数据处理
    'json',
    'csv',
    'datetime',
    'time',
    'typing',
    'collections',
    'dataclasses',
    
    # 正则和字符串处理
    're',
    'unicodedata',
    
    # 文件和系统操作
    'os',
    'sys',
    'pathlib',
    'shutil',
    'tempfile',
    
    # 网络和异步
    'asyncio',
    'socket',
    'threading',
    'concurrent.futures',
    
    # 错误处理和日志
    'logging',
    'traceback',
    'warnings',
]

# 排除不需要的大型模块以减小体积
excludes = [
    'tkinter',
    'tkinter.ttk',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'PIL',
    'Pillow',
    'PyQt5',
    'PyQt6', 
    'PySide2',
    'PySide6',
    'django',
    'flask',
    'tornado',
    'twisted',
    'jupyter',
    'notebook',
    'ipython',
    'sphinx',
    'pytest',
    'unittest',
    'doctest',
]

# 分析配置
a = Analysis(
    ['src/main_refactored_dianxiaomi.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ配置
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# EXE配置
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='数字酋长自动化工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        # 排除这些文件不进行UPX压缩，避免兼容性问题
        'vcruntime140.dll',
        'python*.dll',
        'api-*.dll',
    ],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加.ico文件路径，例如: 'icon.ico'
    version_file=None,  # 可以添加版本信息文件
)