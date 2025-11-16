@echo off
chcp 65001 >nul
title 店小秘自动化工具 - Windows环境准备

echo ==========================================
echo   店小秘自动化工具 - Windows环境准备
echo ==========================================
echo.

echo 🔍 正在检查Python环境...
python --version 2>nul
if errorlevel 1 (
    echo ❌ 未检测到Python环境
    echo.
    echo 📥 请先安装Python 3.8+:
    echo    1. 访问 https://www.python.org/downloads/
    echo    2. 下载并安装最新版本的Python
    echo    3. 安装时勾选 "Add Python to PATH"
    echo    4. 重新运行此脚本
    echo.
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
python --version
echo.

echo 📦 正在升级pip...
python -m pip install --upgrade pip
echo.

echo 📋 正在安装项目依赖...
if exist requirements.txt (
    python -m pip install -r requirements.txt
    echo ✅ 项目依赖安装完成
) else (
    echo ⚠️ 未找到requirements.txt，手动安装核心依赖...
    python -m pip install playwright requests beautifulsoup4
)
echo.

echo 🌐 正在安装Playwright浏览器...
python -m playwright install
if errorlevel 1 (
    echo ⚠️ 浏览器安装可能失败，请检查网络连接
) else (
    echo ✅ Playwright浏览器安装完成
)
echo.

echo 🔧 正在安装打包工具...
python -m pip install pyinstaller>=5.13.0
echo ✅ PyInstaller安装完成
echo.

echo ==========================================
echo 🎉 环境准备完成！
echo.
echo 📋 接下来的步骤：
echo    1. 双击 "直接打包.py" 开始打包程序
echo    2. 或者双击 "一键打包.bat" 使用批处理方式
echo    3. 或者运行 "python 直接打包.py" 命令行方式
echo.
echo 💡 如果要直接运行源代码版本：
echo    python src/main_refactored_dianxiaomi.py
echo ==========================================
echo.

pause