# 店小秘自动化 (Digital Chief Automation)

一个基于 Playwright 的浏览器自动化工具，专为数字营销和数据提取而设计。

## 🚀 项目概述

本项目是一个功能强大的浏览器自动化解决方案，使用 Python 和 Playwright 构建，旨在自动化各种 Web 交互任务，包括：

- 🛒 电商产品信息自动填充
- 📊 数据提取和处理
- 🧪 端到端测试
- 🔄 重复性工作流程自动化

## 📁 项目结构

```
店小秘自动化/
├── src/
│   ├── __init__.py
│   ├── main.py                    # 主应用程序入口
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py              # 配置文件
│   └── tests/
│       ├── __init__.py
│       └── test_example.py        # 测试用例
├── install_dependencies.sh        # Unix/Linux 依赖安装脚本
├── install_dependencies.bat       # Windows 依赖安装脚本
├── run.sh                         # Unix/Linux 运行脚本
├── run.bat                        # Windows 运行脚本
├── requirements.txt               # Python 依赖
├── playwright.config.py           # Playwright 配置
├── setup.py                       # 项目安装配置
├── .gitignore                     # Git 忽略文件
└── README.md                      # 项目文档
```

## 🔧 安装指南

### 系统要求

- Python 3.7 或更高版本
- pip 包管理器
- 支持的操作系统：Windows、macOS、Linux

### 快速安装

#### 方法一：使用安装脚本（推荐）

**Linux/macOS:**
```bash
# 赋予执行权限
chmod +x install_dependencies.sh

# 运行安装脚本
./install_dependencies.sh

# 可选：创建虚拟环境
./install_dependencies.sh --venv
```

**Windows:**
```cmd
# 直接运行安装脚本
install_dependencies.bat

# 可选：创建虚拟环境
install_dependencies.bat --venv
```

#### 方法二：手动安装

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器
python -m playwright install

# 3. 验证安装
python -c "import playwright; print('安装成功！')"
```

## 🏃‍♂️ 使用方法

### 运行主应用程序

**使用运行脚本:**
```bash
# Linux/macOS
./run.sh

# Windows
run.bat
```

**直接运行:**
```bash
python src/main.py
```

### 运行测试

```bash
# 运行所有测试
pytest src/tests/

# 运行特定测试文件
pytest src/tests/test_example.py

# 运行测试并生成报告
pytest src/tests/ --html=report.html
```

### 环境变量配置

创建 `.env` 文件来配置敏感信息：

```bash
# 登录凭据
DC_USERNAME=your_username
DC_PASSWORD=your_password

# 可选：环境设置
ENVIRONMENT=development
```

## ⚙️ 配置说明

### Playwright 配置

在 `playwright.config.py` 中可以配置：
- 浏览器类型（Chromium、Firefox、WebKit）
- 超时设置
- 视窗大小
- 无头模式设置

### 应用配置

在 `src/config/config.py` 中可以配置：
- 浏览器设置
- 超时时间
- URL 地址
- 重试次数
- 文件路径

## 🔧 开发指南

### 虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 代码规范

- 使用 Python 3.7+ 语法
- 遵循 PEP 8 代码风格
- 添加类型注解
- 编写文档字符串

### 添加新功能

1. 在 `src/` 目录下创建新模块
2. 添加相应的测试文件
3. 更新配置文件（如需要）
4. 更新文档

## 🧪 测试

项目包含完整的测试套件：

- **单元测试**: 测试个别功能模块
- **集成测试**: 测试组件间交互
- **端到端测试**: 测试完整用户流程
- **跨浏览器测试**: 确保在不同浏览器中正常工作

## 📝 主要功能

- ✅ **自动登录**: 自动处理网站登录流程
- ✅ **产品信息提取**: 从亚马逊等电商网站提取产品详情
- ✅ **表单自动填充**: 自动填写产品规格和属性
- ✅ **多浏览器支持**: 支持 Chromium、Firefox、WebKit
- ✅ **会话管理**: 保存和恢复登录状态
- ✅ **错误处理**: 完善的异常处理和重试机制
- ✅ **配置管理**: 灵活的配置系统
- ✅ **测试框架**: 完整的自动化测试套件
- 🕐 **使用期限**: 8小时使用期限控制（分发版本）

## 🔒 安全注意事项

- 🚫 不要在代码中硬编码敏感信息
- 🔐 使用环境变量存储账号密码
- 📋 遵守目标网站的服务条款
- 🛡️ 注意反机器人保护措施
- 🔍 定期更新依赖项以修复安全漏洞

## 🚨 故障排除

### 常见问题

**问题：Playwright 安装失败**
```bash
# 解决方案：手动安装浏览器
python -m playwright install --with-deps
```

**问题：权限被拒绝**
```bash
# Linux/macOS 解决方案：
chmod +x install_dependencies.sh
chmod +x run.sh
```

**问题：Python 版本不兼容**
```bash
# 检查 Python 版本
python --version
# 需要 Python 3.7+
```

### 调试模式

启用调试模式查看详细信息：
```bash
# 设置环境变量
export DEBUG=1
python src/main.py
```

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 🕐 脚本分发管理

如需将脚本分发给他人使用（带有8小时使用期限）：

```bash
# 检查当前状态
python manage_expiration.py status

# 重置期限计时器（分发前使用）
python manage_expiration.py reset

# 创建干净的分发包（推荐）
python manage_expiration.py package
```

📄 详细说明请查看: [EXPIRATION_GUIDE.md](EXPIRATION_GUIDE.md)

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如果您遇到任何问题或需要帮助：

- 📧 发送邮件至项目维护者
- 🐛 在 GitHub 上创建 Issue
- 📖 查阅 [Playwright 官方文档](https://playwright.dev/python/)

---

**注意**: 请确保在使用此工具时遵守相关网站的服务条款和法律法规。