#!/usr/bin/env python3
"""
修复打包环境 - 解决PyInstaller兼容性问题

主要解决：
1. pathlib包冲突问题
2. 其他PyInstaller兼容性问题
"""

import subprocess
import sys
import os
from pathlib import Path

def fix_pathlib_conflict():
    """修复pathlib包冲突"""
    print("🔧 修复pathlib包冲突...")
    
    try:
        # 尝试移除可能冲突的pathlib包
        subprocess.run([
            sys.executable, "-m", "pip", "uninstall", "pathlib", "-y"
        ], capture_output=True)
        
        # 使用conda移除（如果在conda环境中）
        try:
            result = subprocess.run([
                "conda", "remove", "pathlib", "-y"
            ], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 通过conda成功移除pathlib")
            else:
                print("ℹ️ conda移除pathlib失败或不存在")
        except FileNotFoundError:
            print("ℹ️ 未检测到conda环境")
        
        print("✅ pathlib冲突修复完成")
        return True
        
    except Exception as e:
        print(f"⚠️ pathlib修复过程中出现问题: {e}")
        return False

def check_pyinstaller_compatibility():
    """检查PyInstaller兼容性"""
    print("🔍 检查PyInstaller兼容性...")
    
    try:
        # 测试PyInstaller导入
        import PyInstaller
        print(f"✅ PyInstaller版本: {PyInstaller.__version__}")
        
        # 检查关键依赖
        critical_packages = [
            'playwright', 'requests', 'beautifulsoup4'
        ]
        
        missing_packages = []
        for pkg in critical_packages:
            try:
                __import__(pkg)
                print(f"✅ {pkg} - 已安装")
            except ImportError:
                missing_packages.append(pkg)
                print(f"❌ {pkg} - 未安装")
        
        if missing_packages:
            print(f"⚠️ 缺少依赖包: {', '.join(missing_packages)}")
            return False
        
        return True
            
    except ImportError:
        print("❌ PyInstaller未正确安装")
        return False

def create_simple_spec():
    """创建简化的spec文件"""
    print("📝 创建简化的spec配置...")
    
    simple_spec = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main_refactored_dianxiaomi.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.sync_api',
        'requests',
        'bs4',
        'beautifulsoup4',
        'amazon_product_parser',
        'product_data',
        'unified_form_filler',
        'ai_category_validator', 
        'csv_logger',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib', 
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open("simple_build.spec", "w", encoding="utf-8") as f:
        f.write(simple_spec)
    
    print("✅ 简化spec文件已创建: simple_build.spec")

def run_simple_build():
    """运行简化的构建"""
    print("🔨 尝试简化构建...")
    
    try:
        cmd = [
            "pyinstaller",
            "simple_build.spec",
            "--distpath=build_output",
            "--workpath=build_temp",
            "--clean"
        ]
        
        print("📋 执行构建命令...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 简化构建成功！")
            
            # 检查输出文件
            exe_path = Path("build_output/数字酋长自动化工具.exe")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / 1024 / 1024
                print(f"📁 可执行文件: {exe_path}")
                print(f"📏 文件大小: {size_mb:.1f} MB")
                return True
            else:
                print("⚠️ 构建完成但未找到exe文件")
                return False
        else:
            print("❌ 简化构建失败")
            print("错误信息:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 构建过程异常: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("  修复打包环境 - PyInstaller兼容性")
    print("=" * 50)
    print()
    
    # 1. 修复pathlib冲突
    if not fix_pathlib_conflict():
        print("❌ pathlib修复失败")
        return
    
    # 2. 检查兼容性
    if not check_pyinstaller_compatibility():
        print("❌ 兼容性检查失败")
        return
    
    # 3. 创建简化配置
    create_simple_spec()
    
    # 4. 尝试构建
    print("\n🤔 是否尝试简化构建？")
    user_input = input("输入 y 继续，其他键退出: ").lower().strip()
    
    if user_input in ['y', 'yes', '是']:
        if run_simple_build():
            print("\n🎉 构建成功完成！")
        else:
            print("\n❌ 构建失败，请检查错误信息")
    else:
        print("\n📝 环境修复完成，可以手动运行构建")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 用户取消操作")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        input("按回车键退出...")