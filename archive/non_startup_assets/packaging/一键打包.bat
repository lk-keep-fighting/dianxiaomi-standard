@echo off
chcp 65001 >nul
title 店小秘自动化工具 - Windows打包

echo ========================================
echo    店小秘自动化工具 - Windows打包
echo ========================================
echo.

echo 🔍 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python环境，请先安装Python 3.8+
    echo 📥 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

echo 📦 正在运行打包脚本...
python build_windows.py

echo.
echo 🏁 打包流程完成！
echo 📁 检查 build_output 目录中的可执行文件
echo.

pause