# CSV日志系统文档

## 概述

CSV日志系统提供了统一的日志记录功能，用于记录AI分类审核和处理异常。系统被提取到独立的工具文件中，便于维护和复用。

## 核心组件

### 1. CSV日志记录器 (`src/csv_logger.py`)

#### CSVLogger 类

主要的日志记录器类，提供以下功能：

- 📝 分类审核记录
- 🚨 处理异常记录  
- 📊 统计信息查询
- 📋 日志汇总报告

#### 核心方法

```python
from src.csv_logger import CSVLogger

# 创建日志记录器
logger = CSVLogger()

# 记录分类问题
logger.write_unreasonable_category(
    product_url="https://amazon.com/product",
    title="产品标题",
    current_category="当前分类",
    ai_reason="AI分析原因", 
    suggested_category="建议分类"
)

# 记录处理异常
logger.write_processing_exception(
    product_url="https://amazon.com/product",
    title="产品标题",
    current_category="当前分类",
    exception_type="ElementNotFoundError",
    error_message="详细错误信息",
    operation_step="表单填充"
)

# 显示今日汇总
logger.print_daily_summary()
```

## 文件结构

### 分类审核文件
**文件名**: `unreasonable_categories_YYYYMMDD.csv`

| 列名 | 描述 | 示例 |
|------|------|------|
| 时间 | 记录时间戳 | 2024-12-01 14:30:25 |
| 商品链接 | Amazon产品URL | https://amazon.com/product/B123... |
| 商品标题 | 产品标题(截取100字符) | 实木床头柜简约现代... |
| 当前分类 | 页面显示的分类 | 床头柜(Nightstands) |
| AI分析原因 | AI分析理由(截取200字符) | 根据产品特征分析... |
| AI建议分类 | AI推荐的分类 | 储物柜(Storage Cabinets) |
| 处理状态 | 人工处理状态 | 待处理/已采用AI建议/保持原分类 |

### 异常记录文件
**文件名**: `processing_exceptions_YYYYMMDD.csv`

| 列名 | 描述 | 示例 |
|------|------|------|
| 时间 | 记录时间戳 | 2024-12-01 14:30:25 |
| 商品链接 | 出错的产品URL | https://amazon.com/product/B123... |
| 商品标题 | 产品标题(截取100字符) | 某个出错的产品... |
| 当前分类 | 产品分类 | 某个分类 |
| 操作步骤 | 出错的操作阶段 | 表单填充/产品处理/保存操作 |
| 异常类型 | Python异常类型 | ElementNotFoundError |
| 错误信息 | 详细错误描述(截取300字符) | 无法找到指定的页面元素... |
| 处理状态 | 异常处理状态 | 待分析/已修复/已知问题 |
| 备注 | 人工添加的备注 | 已联系开发团队修复 |

## 状态管理

### 分类审核状态

| 状态 | 含义 | 下一步操作 |
|------|------|------------|
| 待处理 | 新记录，等待人工审核 | 人工确认分类正确性 |
| 已采用AI建议 | 确认采用AI建议的分类 | 在平台上修改分类 |
| 保持原分类 | 确认当前分类正确 | 无需操作 |
| 需要人工修改 | 需要设定其他分类 | 人工研究并设定正确分类 |
| 已跳过 | 暂时跳过处理 | 后续重新评估 |

### 异常处理状态

| 状态 | 含义 | 下一步操作 |
|------|------|------------|
| 待分析 | 新异常，等待分析 | 技术人员分析原因 |
| 已修复 | 问题已解决 | 无需操作 |
| 已知问题 | 已知的系统问题 | 等待系统更新 |
| 需要忽略 | 可忽略的异常 | 无需操作 |
| 待进一步分析 | 需要深入研究 | 技术团队深入分析 |

## 审核工具

### 增强版审核工具 (`enhanced_review_tool.py`)

提供交互式界面处理两种类型的记录：

```bash
python enhanced_review_tool.py
```

#### 功能特性

- 📋 **文件列表**: 自动识别分类审核和异常记录文件
- 📊 **统计信息**: 显示各状态的记录数量
- 🔍 **逐条审核**: 交互式审核每条记录
- ✅ **状态更新**: 批量或单个更新处理状态
- 📝 **备注功能**: 为异常记录添加处理备注

#### 使用流程

1. **启动工具**
   ```bash
   python enhanced_review_tool.py
   ```

2. **选择文件类型**
   - 分类审核文件：处理AI标记的分类问题
   - 异常记录文件：分析和修复处理异常

3. **交互式审核**
   - 查看详细信息
   - 选择处理方式
   - 添加备注说明
   - 更新处理状态

## 集成使用

### 在主程序中的集成

```python
# 导入日志工具
from csv_logger import write_unreasonable_category_to_csv, write_processing_exception_to_csv

# 记录分类问题
if not is_reasonable:
    write_unreasonable_category_to_csv(
        product_url=web_url,
        title=title, 
        current_category=category_name,
        ai_reason=reason,
        suggested_category=suggested_category
    )

# 记录处理异常
try:
    # 某些处理操作
    process_product()
except Exception as e:
    write_processing_exception_to_csv(
        product_url=web_url,
        title=title,
        current_category=category,
        exception_type=type(e).__name__,
        error_message=str(e),
        operation_step="产品处理"
    )
```

### 程序结束时的汇总

```python
# 显示今日处理汇总
from csv_logger import csv_logger
csv_logger.print_daily_summary()
```

输出示例：
```
📊 日期 20241201 汇总
==================================================
📝 分类审核记录: 15 条
🚨 处理异常记录: 3 条
📁 生成的文件:
   • unreasonable_categories_20241201.csv (2048 bytes)
   • processing_exceptions_20241201.csv (1024 bytes)
==================================================
```

## 最佳实践

### 1. 日常维护

- 📅 **每日审核**: 及时处理当天的记录
- 📂 **定期归档**: 将已处理完成的文件移动到归档目录
- 📊 **周期报告**: 定期分析异常模式，改进系统

### 2. 团队协作

- 👥 **分工明确**: 分类审核和异常分析可由不同人员负责
- 🔄 **状态同步**: 及时更新处理状态，避免重复工作
- 📝 **备注详细**: 为后续处理提供足够的上下文信息

### 3. 系统优化

- 🔍 **模式识别**: 分析高频异常，优化代码逻辑
- 📈 **性能监控**: 通过异常记录识别性能瓶颈
- 🛠️ **持续改进**: 根据记录反馈持续优化系统

### 4. 数据管理

- 💾 **备份重要**: 定期备份重要的审核数据
- 🗂️ **分类存储**: 按项目或时间分类存储历史数据
- 🔒 **权限控制**: 控制敏感审核数据的访问权限

## 故障排除

### 常见问题

1. **文件编码问题**
   ```bash
   # 检查文件编码
   file *.csv
   
   # 转换编码
   iconv -f utf-8 -t utf-8-sig input.csv > output.csv
   ```

2. **权限错误**
   ```bash
   # 修改文件权限
   chmod 644 *.csv
   ```

3. **CSV格式损坏**
   - 使用Excel等工具修复
   - 重新生成文件

### 性能优化

- 📊 **大文件处理**: 超过1000条记录时考虑分批处理
- 🔄 **并发限制**: 避免多人同时编辑同一文件
- 💾 **内存管理**: 大数据集时使用流式处理

这个CSV日志系统提供了完整的记录、审核和管理功能，确保所有重要信息都能被妥善处理和跟踪。