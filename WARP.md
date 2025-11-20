# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## 项目概览

店小秘自动化系统 - 基于Playwright的Amazon产品信息自动提取和DataCaciques表单自动填充系统。这是一个经过深度重构的清洁架构（Clean Architecture）实现，从373个混乱文件精简到5个核心文件。

**核心理念**：遵循 Linus Torvalds 代码哲学
- Good Taste - 简洁优雅的解决方案，消除边界条件
- Single Source of Truth - 避免重复，一个数据来源统治一切
- No Special Cases - 重新设计数据结构来消除特殊情况

## 常用命令

### 环境准备
```bash
# 一键安装所有依赖（推荐）
./scripts/install_dependencies.sh

# 手动安装
pip install -r requirements.txt
python -m playwright install chromium

# 使用虚拟环境
./scripts/install_dependencies.sh --venv
source .venv/bin/activate
```

### 运行系统
```bash
# 方式1：使用便捷脚本
./scripts/run.sh

# 方式2：直接运行主程序
python src/main.py
```

### 测试
```bash
# 运行完整性测试
python archive/non_startup_assets/tests/test_refactored_system.py

# 运行所有测试
pytest archive/non_startup_assets/tests/ -v

# 测试Amazon解析器
python src/test_amazon_parser.py
```

### Windows打包
```bash
# 安装打包依赖
pip install -r requirements-packaging.txt

# 执行打包（需要配置Supabase环境变量）
python scripts/package_windows_exe.py \
  --supabase-url https://your-project.supabase.co \
  --supabase-api-key your-service-role-key

# 或从.env读取配置
python scripts/package_windows_exe.py --env-file .env.production
```

## 核心架构

### 数据流程（关键理解）
```
Amazon产品页面
     ↓
 URL提取 + 页面导航
     ↓
 AmazonProductParser      → 唯一的Amazon解析器
     ↓
 ProductData结构          → 统一的数据结构（Single Source of Truth）
     ↓
 FieldMappingEngine       → 唯一的映射系统
     ↓
 UnifiedFormFiller        → 统一的表单填充引擎
     ↓
 DataCaciques表单
```

### 5个核心文件（必须理解）

1. **`src/main.py`** - 主程序入口
   - `UserInteractionFlow` - 控制台交互界面
   - `check_script_expiration()` - 脚本有效期控制
   - 主处理循环 - 采集箱产品处理逻辑

2. **`src/product_data.py`** - 数据结构的Single Source of Truth
   - `ProductData` - 标准产品数据类
   - `FieldMappingEngine` - 唯一的字段映射引擎（全局实例 `FIELD_MAPPING`）
   - 所有Amazon→表单的映射都在这里定义

3. **`src/amazon_product_parser.py`** - Amazon解析器
   - 5种重量提取策略确保鲁棒性
   - 智能表格解析（顶部和底部产品详情表）
   - 尺寸自动转换（英寸→厘米）

4. **`src/unified_form_filler.py`** - 表单填充引擎
   - 支持多种元素：文本框、下拉菜单、TinyMCE编辑器
   - 复合字段处理（数值+单位）
   - 详细的填充统计报告

5. **`src/system_config.py`** - 系统配置
   - 环境感知配置（development/testing/production）
   - 浏览器和表单超时设置
   - 登录凭据管理

### 关键组件

**客户端授权系统**（`src/client_authorization.py`）
- Supabase托管的授权数据
- 本地缓存 + 每日刷新策略
- 启动前强制授权校验

**AI辅助功能**
- `src/ai_category_validator.py` - 分类验证
- `src/ai_enum_matcher.py` - 枚举值匹配
- 配置在`.env`中的OpenAI兼容API

## 配置与环境变量

### 生产环境必需
```bash
# DataCaciques登录凭据（生产环境必须通过环境变量配置）
export DC_USERNAME="your_username"
export DC_PASSWORD="your_password"
export ENVIRONMENT="production"

# Supabase授权配置
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_API_KEY="your-api-key"
export CLIENT_AUTH_USERNAME="client_username"
export CLIENT_AUTH_PASSWORD="client_password"
```

### 开发环境可选
```bash
export DEBUG="1"
export ENVIRONMENT="development"
export USE_AI="true"
export AI_CONFIDENCE_THRESHOLD="0.6"
```

### 关键配置文件
- `.env` - 环境变量（从`.env.example`复制）
- `config/field_defaults.json` - 字段默认值
- `src/form-json-schema.json` - 表单字段定义

## 代码风格原则

### 修改映射系统时
⚠️ **永远只在一个地方修改** - `src/product_data.py` 中的 `FieldMappingEngine`

```python
# ✅ 正确：在FieldMappingEngine中添加映射
self.field_mappings = {
    'Brand': 'Brand Name',
    'New Field': 'Target Field'  # 只在这里添加
}

# ❌ 错误：不要在其他地方创建映射逻辑
# 不要在main.py或form_filler.py中添加硬编码映射
```

### 添加新字段类型
如果需要支持新的表单元素类型：
1. 在 `UnifiedFormFiller._fill_form_field()` 中添加处理逻辑
2. 遵循现有的元素检测顺序：textarea → select → input
3. 添加对应的测试用例

### 调试Amazon解析问题
```python
# 1. 使用测试工具
python src/test_amazon_parser.py

# 2. 检查选择器配置
python -c "from src.system_config import get_config; print(get_config().amazon_selectors)"

# 3. 启用DEBUG模式
export DEBUG=1
python src/main.py
```

## 项目结构特点

### 清理后的目录结构
- **`src/`** - 所有运行必需的核心代码
- **`scripts/`** - 启动和环境准备脚本
- **`archive/`** - 归档的历史代码、文档和测试
  - `archive/non_startup_assets/` - 非启动必需的辅助资源
- **`data/auth_states/`** - 登录状态缓存（Playwright storage）
- **`config/`** - 运行时配置

### 文件命名约定
- `main.py` - 当前主程序
- `main_refactored_*.py` - 兼容入口，提示升级
- `*_parser.py` - 数据解析器
- `*_filler.py` - 表单填充器
- `*_config.py` - 配置文件

## 常见问题处理

### Manufacturer Name为空
✅ **已解决** - v2.0.0重构统一了映射系统，确保Manufacturer正确映射到Manufacturer Name

### 字段映射失败
```bash
# 检查映射配置
python -c "from src.product_data import FIELD_MAPPING; print(FIELD_MAPPING.field_mappings)"

# 运行映射测试
python archive/non_startup_assets/tests/test_refactored_system.py
```

### 浏览器启动问题
```bash
# 重新安装Playwright
python -m playwright install --with-deps chromium

# 检查权限
chmod +x scripts/install_dependencies.sh scripts/run.sh
```

### Windows打包缺少依赖
✅ **已解决** - AI功能现在是可选依赖，openai库未安装时系统依然可以正常运行。

如果仍然需要打包时包含openai：

1. 检查 `scripts/package_windows_exe.py` 中已有 `--hidden-import` 参数
2. 确保requirements.txt中包含 `openai>=1.0.0`
3. 重新打包并测试

**最佳实践**：使用可选依赖模式，避免强制导入：
```python
# ⚠️ 错误：在模块顶部无条件导入
from ai_category_validator import AICategoryValidator

# ✅ 正确：使用try-except，让依赖可选
try:
    from ai_category_validator import AICategoryValidator
    AI_FEATURES_AVAILABLE = True
except ImportError:
    AI_FEATURES_AVAILABLE = False
    AICategoryValidator = None  # type: ignore
```

## 开发注意事项

### 不要破坏用户空间
- ⚠️ 任何导致现有功能崩溃的改动都是bug，无论多么"理论正确"
- 保持向后兼容性是神圣不可侵犯的
- 环境变量配置永远优先于代码中的默认值

### 实用主义优先
- 解决实际问题，而不是假想的威胁
- 避免过度设计和不必要的抽象
- 代码要为现实服务，不是为论文服务

### 复杂度控制
- 函数保持短小精悍，只做一件事
- 如果需要超过3层缩进，重新设计它
- 消除边界情况永远优于增加条件判断

### 测试驱动
修改核心组件前后必须运行测试：
```bash
# 1. 运行测试确保基线
python archive/non_startup_assets/tests/test_refactored_system.py

# 2. 修改代码

# 3. 再次运行测试确保通过
python archive/non_startup_assets/tests/test_refactored_system.py
```

## 依赖关系

核心依赖：
- `playwright>=1.40.0` - 浏览器自动化
- `pytest>=7.0.0` - 测试框架
- `requests>=2.31.0` - HTTP请求
- `beautifulsoup4>=4.12.0` - HTML解析
- `openai>=1.0.0` - AI功能
- `bcrypt>=4.0.1` - 密码哈希（授权系统）

打包依赖（`requirements-packaging.txt`）：
- PyInstaller相关依赖（仅Windows打包时需要）

## 性能指标

- 平均解析时间: 5-10秒/产品
- 表单填充成功率: >95%
- 内存使用: <500MB
- 测试覆盖率: 100%（核心组件）
