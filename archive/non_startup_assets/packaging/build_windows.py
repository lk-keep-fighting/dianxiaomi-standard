#!/usr/bin/env python3
"""
Windows打包脚本 - 将main_refactored_dianxiaomi.py打包成Windows可执行程序

依赖：
- PyInstaller
- 所有项目依赖库

使用方法：
python build_windows.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """安装PyInstaller"""
    print("🔧 检查PyInstaller...")
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
    except ImportError:
        print("📦 正在安装PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller安装完成")

def prepare_build_environment():
    """准备构建环境"""
    print("🛠️ 准备构建环境...")
    
    # 创建build目录
    build_dir = Path("build_output")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    
    # 创建spec目录用于临时文件
    spec_dir = Path("spec_files")
    if spec_dir.exists():
        shutil.rmtree(spec_dir)
    spec_dir.mkdir()
    
    print("✅ 构建环境准备完成")
    return build_dir, spec_dir

def create_pyinstaller_spec():
    """创建PyInstaller配置文件"""
    print("📝 创建PyInstaller配置文件...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 分析主程序及其依赖
a = Analysis(
    ['src/main_refactored_dianxiaomi.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # 包含配置文件和资源
        ('config/*.json', 'config'),
        ('src/config/*.json', 'src/config'),
        ('*.md', '.'),
        ('*.txt', '.'),
    ],
    hiddenimports=[
        # Playwright相关
        'playwright',
        'playwright.sync_api',
        'playwright.sync_api._generated',
        
        # 项目模块
        'amazon_product_parser',
        'product_data', 
        'unified_form_filler',
        'ai_category_validator',
        'csv_logger',
        'system_config',
        
        # 标准库隐式导入
        'csv',
        'json',
        'datetime',
        'time',
        'os',
        're',
        'sys',
        'typing',
        
        # 第三方库
        'requests',
        'beautifulsoup4',
        'bs4',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 处理pyz文件
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='店小秘自动化工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保持控制台窗口以显示日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加ico文件路径
)
'''
    
    spec_file = Path("spec_files/main_refactored_dianxiaomi.spec")
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ 配置文件已创建: {spec_file}")
    return spec_file

def create_requirements_for_build():
    """创建打包专用的requirements文件"""
    print("📋 创建打包专用依赖文件...")
    
    build_requirements = '''# Windows打包专用依赖
pyinstaller>=5.13.0

# 核心依赖
playwright>=1.40.0
requests>=2.31.0
beautifulsoup4>=4.12.0

# 可选依赖（根据需要）
selenium>=4.15.0
pytest>=7.0.0
'''
    
    with open("requirements_build.txt", 'w', encoding='utf-8') as f:
        f.write(build_requirements)
    
    print("✅ 打包依赖文件已创建: requirements_build.txt")

def create_build_batch():
    """创建Windows批处理脚本"""
    print("🖥️ 创建Windows批处理脚本...")
    
    batch_content = '''@echo off
chcp 65001 >nul
echo ========================================
echo    店小秘自动化工具 - Windows打包
echo ========================================

echo.
echo 📦 正在安装打包依赖...
pip install -r requirements_build.txt

echo.
echo 🛠️ 正在构建Windows程序...
pyinstaller spec_files/main_refactored_dianxiaomi.spec --distpath build_output --workpath build_temp --clean

echo.
echo ✅ 构建完成！
echo 📁 可执行文件位置: build_output/店小秘自动化工具.exe
echo.

echo 🔧 正在安装Playwright浏览器...
cd build_output
"店小秘自动化工具.exe" --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ 可执行文件测试失败，请检查构建过程
) else (
    echo ✅ 可执行文件构建成功！
)

echo.
echo 📋 使用说明：
echo 1. 运行前请确保安装了Playwright浏览器：playwright install
echo 2. 双击 build_output/店小秘自动化工具.exe 运行程序
echo 3. 如遇问题，请检查控制台输出信息

pause
'''
    
    with open("build_windows.bat", 'w', encoding='utf-8') as f:
        f.write(batch_content)
    
    print("✅ Windows批处理脚本已创建: build_windows.bat")

def create_installer_script():
    """创建安装器脚本"""
    print("🚀 创建安装器脚本...")
    
    installer_content = '''#!/usr/bin/env python3
"""
店小秘自动化工具 - 一键安装脚本

自动安装所有依赖并准备运行环境
"""

import subprocess
import sys
import os
from pathlib import Path

def install_dependencies():
    """安装Python依赖"""
    print("📦 正在安装Python依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Python依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ Python依赖安装失败: {e}")
        return False
    return True

def install_playwright_browsers():
    """安装Playwright浏览器"""
    print("🌐 正在安装Playwright浏览器...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        print("✅ Playwright浏览器安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ Playwright浏览器安装失败: {e}")
        return False
    return True

def main():
    print("=" * 50)
    print("  店小秘自动化工具 - 一键安装")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        sys.exit(1)
    
    print(f"✅ Python版本: {sys.version}")
    
    # 安装依赖
    if not install_dependencies():
        print("❌ 安装失败，请检查网络连接和权限")
        sys.exit(1)
    
    # 安装浏览器
    if not install_playwright_browsers():
        print("❌ 浏览器安装失败，请检查网络连接")
        sys.exit(1)
    
    print("\\n" + "=" * 50)
    print("🎉 安装完成！现在可以运行程序了")
    print("💡 运行命令: python src/main_refactored_dianxiaomi.py")
    print("=" * 50)

if __name__ == "__main__":
    main()
'''
    
    with open("install.py", 'w', encoding='utf-8') as f:
        f.write(installer_content)
    
    print("✅ 安装器脚本已创建: install.py")

def create_readme():
    """创建Windows用户说明文档"""
    print("📖 创建用户说明文档...")
    
    readme_content = '''# 店小秘自动化工具 - Windows版本

## 🚀 快速开始

### 方法一：使用可执行文件（推荐）
1. 双击 `build_windows.bat` 开始构建Windows程序
2. 构建完成后，运行 `build_output/店小秘自动化工具.exe`

### 方法二：使用Python脚本
1. 运行 `python install.py` 安装所有依赖
2. 运行 `python src/main_refactored_dianxiaomi.py` 启动程序

## 📋 系统要求

- Windows 10/11 (64位)
- Python 3.8+ (如果使用脚本方式)
- 至少2GB可用内存
- 稳定的网络连接

## 🛠️ 手动构建（开发者）

```bash
# 1. 安装构建依赖
pip install -r requirements_build.txt

# 2. 构建可执行文件
pyinstaller spec_files/main_refactored_dianxiaomi.spec --distpath build_output

# 3. 安装浏览器支持
playwright install
```

## 📁 文件说明

- `店小秘自动化工具.exe` - 主程序（构建后生成）
- `install.py` - 一键安装脚本
- `build_windows.bat` - Windows构建脚本
- `requirements.txt` - Python依赖列表
- `src/` - 源代码目录

## ⚠️ 注意事项

1. **首次运行**：程序会自动下载浏览器组件，需要网络连接
2. **防火墙**：请允许程序访问网络
3. **杀毒软件**：可能误报，请添加信任
4. **权限**：建议以管理员身份运行

## 🔧 故障排除

### 程序无法启动
- 检查Python环境（如果使用脚本方式）
- 确认所有依赖已正确安装
- 查看控制台错误信息

### 浏览器相关问题
```bash
# 重新安装浏览器支持
playwright install
```

### 网络连接问题
- 检查网络连接
- 确认代理设置
- 尝试关闭VPN

## 📞 技术支持

如遇问题，请提供：
1. 操作系统版本
2. 错误信息截图
3. 控制台输出日志

---
© 2024 店小秘自动化工具
'''
    
    with open("README_WINDOWS.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ 用户说明文档已创建: README_WINDOWS.md")

def build_executable():
    """构建可执行文件"""
    print("🔨 开始构建Windows可执行文件...")
    
    try:
        # 运行PyInstaller
        cmd = [
            "pyinstaller",
            "spec_files/main_refactored_dianxiaomi.spec",
            "--distpath", "build_output",
            "--workpath", "build_temp",
            "--clean"
        ]
        
        print(f"📋 执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✅ 构建成功！")
            print(f"📁 输出目录: build_output/")
            return True
        else:
            print("❌ 构建失败")
            print(f"错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 构建过程中出现异常: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("    店小秘自动化工具 - Windows打包工具")
    print("=" * 60)
    
    # 检查当前目录
    if not Path("src/main_refactored_dianxiaomi.py").exists():
        print("❌ 找不到主程序文件，请在项目根目录运行此脚本")
        sys.exit(1)
    
    try:
        # 1. 安装PyInstaller
        install_pyinstaller()
        
        # 2. 准备构建环境
        build_dir, spec_dir = prepare_build_environment()
        
        # 3. 创建配置文件
        spec_file = create_pyinstaller_spec()
        
        # 4. 创建辅助文件
        create_requirements_for_build()
        create_build_batch()
        create_installer_script()
        create_readme()
        
        # 5. 询问是否立即构建
        user_input = input("\n🤔 是否立即开始构建？(y/n): ").lower().strip()
        
        if user_input in ['y', 'yes', '是', '']:
            success = build_executable()
            
            if success:
                print("\n" + "=" * 60)
                print("🎉 构建完成！")
                print("📁 可执行文件位置: build_output/店小秘自动化工具.exe")
                print("📖 使用说明: README_WINDOWS.md")
                print("🚀 也可以运行 build_windows.bat 重新构建")
                print("=" * 60)
            else:
                print("\n❌ 构建失败，请检查错误信息")
        else:
            print("\n📝 所有配置文件已准备完成")
            print("🚀 稍后可运行 build_windows.bat 开始构建")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户取消操作")
    except Exception as e:
        print(f"\n❌ 构建过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()