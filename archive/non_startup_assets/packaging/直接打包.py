#!/usr/bin/env python3
"""
直接打包脚本 - 简化版Windows打包工具

快速将main_refactored_dianxiaomi.py打包成Windows可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_environment():
    """检查打包环境"""
    print("🔍 检查打包环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version.split()[0]}")
    
    # 检查主程序文件
    main_file = Path("src/main_refactored_dianxiaomi.py")
    if not main_file.exists():
        print("❌ 找不到主程序文件: src/main_refactored_dianxiaomi.py")
        return False
    
    print("✅ 主程序文件存在")
    return True

def install_pyinstaller():
    """安装PyInstaller"""
    print("📦 检查并安装PyInstaller...")
    
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
        return True
    except ImportError:
        print("📥 正在安装PyInstaller...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "pyinstaller>=5.13.0"
            ])
            print("✅ PyInstaller安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller安装失败: {e}")
            return False

def clean_build_dirs():
    """清理构建目录"""
    print("🧹 清理旧的构建文件...")
    
    dirs_to_clean = ["build", "dist", "__pycache__", "build_output"]
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  ✅ 已清理: {dir_name}")

def run_pyinstaller():
    """运行PyInstaller打包"""
    print("🔨 开始打包...")
    
    # PyInstaller命令参数
    cmd = [
        "pyinstaller",
        "--onefile",  # 打包成单个可执行文件
        "--console",  # 保留控制台窗口
        "--name=店小秘自动化工具",
        "--distpath=build_output",
        "--workpath=build_temp",
        "--specpath=build_temp",
        
        # 添加必要的隐式导入
        "--hidden-import=playwright",
        "--hidden-import=playwright.sync_api",
        "--hidden-import=amazon_product_parser",
        "--hidden-import=product_data",
        "--hidden-import=unified_form_filler",
        "--hidden-import=ai_category_validator",
        "--hidden-import=csv_logger",
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--hidden-import=beautifulsoup4",
        
        # 添加数据文件
        "--add-data=config;config",
        "--add-data=src/config;src/config",
        "--add-data=requirements.txt;.",
        
        # 排除不需要的模块
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        
        # 主程序文件
        "src/main_refactored_dianxiaomi.py"
    ]
    
    print(f"📋 执行命令: {' '.join(cmd[:5])}... (完整命令很长)")
    
    try:
        # 运行打包命令
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print("✅ 打包成功！")
            
            # 检查输出文件
            exe_path = Path("build_output/店小秘自动化工具.exe")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / 1024 / 1024
                print(f"📁 可执行文件: {exe_path}")
                print(f"📏 文件大小: {size_mb:.1f} MB")
                return True
            else:
                print("❌ 未找到生成的可执行文件")
                return False
        else:
            print("❌ 打包失败")
            print("错误输出:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 打包过程中出现异常: {e}")
        return False

def create_run_instructions():
    """创建运行说明"""
    instructions = """
# 店小秘自动化工具 - 使用说明

## 🚀 运行程序
1. 双击 `店小秘自动化工具.exe` 启动程序
2. 首次运行会自动安装浏览器组件（需要网络连接）
3. 按照程序提示进行操作

## ⚠️ 重要提醒
1. 请确保网络连接正常
2. 首次运行可能需要较长时间下载浏览器
3. 如遇杀毒软件报警，请添加信任
4. 建议以管理员身份运行

## 🔧 故障排除
- 如果程序无法启动，请检查Windows Defender或其他杀毒软件
- 如果网络连接有问题，请检查防火墙设置
- 需要技术支持请联系开发者

---
生成时间: {datetime}
"""
    
    import datetime as dt
    instructions = instructions.format(
        datetime=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    with open("build_output/使用说明.txt", "w", encoding="utf-8") as f:
        f.write(instructions)
    
    print("📖 已创建使用说明文件")

def main():
    """主函数"""
    print("=" * 50)
    print("  店小秘自动化工具 - 直接打包")
    print("=" * 50)
    print()
    
    # 1. 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，无法继续")
        input("按回车键退出...")
        sys.exit(1)
    
    # 2. 安装PyInstaller
    if not install_pyinstaller():
        print("\n❌ PyInstaller安装失败，无法继续")
        input("按回车键退出...")
        sys.exit(1)
    
    # 3. 清理旧文件
    clean_build_dirs()
    
    # 4. 开始打包
    if run_pyinstaller():
        # 5. 创建说明文件
        create_run_instructions()
        
        print("\n" + "=" * 50)
        print("🎉 打包完成！")
        print("📁 输出目录: build_output/")
        print("🚀 可执行文件: build_output/店小秘自动化工具.exe")
        print("📖 使用说明: build_output/使用说明.txt")
        print("=" * 50)
        
        # 询问是否立即测试
        try:
            test = input("\n🤔 是否现在测试运行程序？(y/n): ").lower().strip()
            if test in ['y', 'yes', '是']:
                print("🧪 启动测试...")
                exe_path = "build_output/店小秘自动化工具.exe"
                subprocess.Popen([exe_path], shell=True)
        except KeyboardInterrupt:
            pass
    else:
        print("\n❌ 打包失败，请检查错误信息")
        
    input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户取消操作")
    except Exception as e:
        print(f"\n❌ 程序出现异常: {e}")
        input("按回车键退出...")