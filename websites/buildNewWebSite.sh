# 复制模板到新项目
mkdir my-automation-project
cp tpl/template_main.py my-automation-project/main.py
cp tpl/run.sh my-automation-project/run.sh
cd my-automation-project

# 安装依赖
# pip install playwright
# python -m playwright install chromium

# 配置并运行
export DEBUG=1

chmod +x run.sh