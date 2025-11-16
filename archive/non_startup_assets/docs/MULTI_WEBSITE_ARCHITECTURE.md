# 多网站自动化架构设计方案

## 🎯 设计目标

**核心需求**: 基于现有店小秘自动化系统，设计支持多个目标网站的表单填充架构，实现"一套Amazon抓取，多站点填充"。

## 🏗️ 架构设计原则

### Linus式设计哲学
1. **Single Source of Truth** - Amazon解析器保持唯一
2. **No Special Cases** - 用Strategy Pattern消除网站特定分支
3. **Never Break Userspace** - 现有店小秘功能完全兼容

## 📋 架构方案

### 核心组件架构图
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Amazon页面    │───▶│  ProductData     │───▶│  WebsiteStrategy    │
│   统一抓取      │    │  (统一数据结构)  │    │   (网站特定逻辑)    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                                          │
                       ┌──────────────────────────────────┼──────────────────────────────────┐
                       │                                  ▼                                  │
            ┌─────────────────────┐              ┌─────────────────────┐              ┌─────────────────────┐
            │ DataCaciquesStrategy│              │  WalmartStrategy    │              │   EbayStrategy      │
            │ (店小秘-现有)     │              │   (沃尔玛-新)       │              │   (eBay-新)         │
            └─────────────────────┘              └─────────────────────┘              └─────────────────────┘
```

### 目录结构设计
```
src/
├── core/                           # 核心通用组件
│   ├── amazon_product_parser.py    # Amazon解析器(不变)
│   ├── product_data.py             # 统一数据结构(不变)
│   └── system_config.py            # 系统配置(扩展)
├── websites/                       # 网站特定策略
│   ├── base/
│   │   ├── website_strategy.py     # 网站策略抽象基类
│   │   └── form_filler_base.py     # 表单填充基类
│   ├── datacaciques/              # 店小秘实现
│   │   ├── datacaciques_strategy.py
│   │   ├── datacaciques_config.py
│   │   └── datacaciques_form_filler.py
│   ├── walmart/                   # 沃尔玛实现(示例)
│   │   ├── walmart_strategy.py
│   │   ├── walmart_config.py
│   │   └── walmart_form_filler.py
│   └── ebay/                      # eBay实现(示例)
│       ├── ebay_strategy.py
│       ├── ebay_config.py
│       └── ebay_form_filler.py
├── automation_engine.py           # 统一自动化引擎
└── main_multi_site.py             # 多网站主程序
```

## 🔧 技术实现

### 1. WebsiteStrategy抽象基类
```python
# src/websites/base/website_strategy.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from playwright.sync_api import Page, BrowserContext
from core.product_data import ProductData

class WebsiteStrategy(ABC):
    """网站策略抽象基类"""
    
    @abstractmethod
    def get_site_name(self) -> str:
        """返回网站名称"""
        pass
    
    @abstractmethod
    def validate_environment(self, page: Page) -> bool:
        """验证是否在正确的网站环境"""
        pass
    
    @abstractmethod
    def authenticate(self, page: Page, context: BrowserContext) -> bool:
        """处理网站登录认证"""
        pass
    
    @abstractmethod
    def navigate_to_form(self, page: Page) -> Any:
        """导航到目标表单页面并返回表单句柄"""
        pass
    
    @abstractmethod
    def fill_form(self, form_handle: Any, product_data: ProductData) -> Dict[str, Any]:
        """填充表单并返回结果统计"""
        pass
    
    @abstractmethod
    def get_field_mappings(self) -> Dict[str, str]:
        """返回字段映射配置"""
        pass
```

### 2. DataCaciques策略实现(保持现有功能)
```python
# src/websites/datacaciques/datacaciques_strategy.py
from websites.base.website_strategy import WebsiteStrategy
from .datacaciques_form_filler import DataCaciquesFormFiller
from .datacaciques_config import DataCaciquesConfig

class DataCaciquesStrategy(WebsiteStrategy):
    """店小秘网站策略 - 基于现有实现"""
    
    def __init__(self):
        self.config = DataCaciquesConfig()
        self.form_filler = None
    
    def get_site_name(self) -> str:
        return "DataCaciques"
    
    def validate_environment(self, page: Page) -> bool:
        # 检查是否在店小秘环境
        return "datacaciques" in page.url or "店小秘" in page.title()
    
    def authenticate(self, page: Page, context: BrowserContext) -> bool:
        # 使用现有的登录逻辑
        return self._handle_datacaciques_login(page, context)
    
    def navigate_to_form(self, page: Page) -> Any:
        # 返回现有的iframe结构
        main_frame = page.locator('iframe[name="iframeModal_flag_0"]').content_frame
        edit_frame = main_frame.locator('iframe[name^="iframeModal_editPostTemplet"]').content_frame
        return edit_frame
    
    def fill_form(self, edit_frame: Any, product_data: ProductData) -> Dict[str, Any]:
        # 使用现有的UnifiedFormFiller逻辑
        if not self.form_filler:
            self.form_filler = DataCaciquesFormFiller(edit_frame)
        return self.form_filler.fill_form(product_data)
    
    def get_field_mappings(self) -> Dict[str, str]:
        # 返回现有的FIELD_MAPPING
        return self.config.get_field_mappings()
```

### 3. 统一自动化引擎
```python
# src/automation_engine.py
from typing import Dict, Type
from core.product_data import ProductData
from core.amazon_product_parser import AmazonProductParser
from websites.base.website_strategy import WebsiteStrategy

class AutomationEngine:
    """统一自动化引擎 - 协调Amazon抓取和网站填充"""
    
    def __init__(self):
        self.strategies: Dict[str, WebsiteStrategy] = {}
    
    def register_strategy(self, strategy: WebsiteStrategy):
        """注册网站策略"""
        self.strategies[strategy.get_site_name()] = strategy
    
    def execute_automation(self, amazon_url: str, target_site: str, 
                          context, page) -> Dict[str, Any]:
        """执行完整自动化流程"""
        
        # 1. Amazon数据抓取(通用)
        product_data = self._extract_amazon_data(amazon_url, context)
        
        # 2. 网站特定处理
        strategy = self.strategies.get(target_site)
        if not strategy:
            raise ValueError(f"不支持的网站: {target_site}")
        
        # 3. 网站认证和表单填充
        if strategy.authenticate(page, context):
            form_handle = strategy.navigate_to_form(page)
            return strategy.fill_form(form_handle, product_data)
        else:
            raise Exception(f"{target_site} 认证失败")
    
    def _extract_amazon_data(self, amazon_url: str, context) -> ProductData:
        """通用Amazon数据抓取"""
        amazon_page = context.new_page()
        try:
            amazon_page.goto(amazon_url + '?language=en_US&currency=USD')
            parser = AmazonProductParser(amazon_page)
            return parser.parse_product()
        finally:
            amazon_page.close()
```

### 4. 多网站主程序
```python
# src/main_multi_site.py
#!/usr/bin/env python3
"""
多网站自动化主程序
支持多个目标网站的表单填充，共享Amazon产品数据抓取
"""

from automation_engine import AutomationEngine
from websites.datacaciques.datacaciques_strategy import DataCaciquesStrategy
# from websites.walmart.walmart_strategy import WalmartStrategy
# from websites.ebay.ebay_strategy import EbayStrategy

def main():
    # 初始化自动化引擎
    engine = AutomationEngine()
    
    # 注册支持的网站策略
    engine.register_strategy(DataCaciquesStrategy())
    # engine.register_strategy(WalmartStrategy())
    # engine.register_strategy(EbayStrategy())
    
    # 从命令行参数或配置文件获取目标网站
    target_site = "DataCaciques"  # 默认保持现有行为
    
    # 执行自动化
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 导航到目标网站...
            # 获取Amazon URL...
            
            result = engine.execute_automation(amazon_url, target_site, context, page)
            print(f"✅ {target_site} 自动化完成: {result}")
            
        finally:
            browser.close()

if __name__ == "__main__":
    main()
```

## 🔄 迁移策略

### 第一步：保持向后兼容
1. 现有 `main_refactored.py` 保持不变，确保用户无感知
2. 将现有组件逐步抽象到新架构中

### 第二步：逐步重构
1. 创建基类和抽象接口
2. 将店小秘逻辑包装为Strategy实现
3. 创建AutomationEngine统一调度

### 第三步：扩展新网站
1. 基于Strategy模式添加新网站支持
2. 每个网站独立配置和实现
3. 共享Amazon解析和ProductData

## 📊 架构优势

### 代码复用性
- **Amazon解析**: 100%复用，零重复代码
- **ProductData结构**: 统一数据模型，跨网站兼容
- **核心逻辑**: 登录、导航、错误处理等通用逻辑复用

### 可扩展性
- **新增网站**: 只需实现WebsiteStrategy接口
- **独立开发**: 每个网站策略相互独立
- **配置分离**: 网站特定配置独立管理

### 维护性
- **职责分离**: Amazon抓取与网站填充解耦
- **测试简化**: 每个策略独立测试
- **错误隔离**: 单个网站问题不影响其他网站

## 🎯 实施优先级

### Phase 1 (立即实施)
1. ✅ 创建抽象基类和接口
2. ✅ 重构店小秘为Strategy实现
3. ✅ 创建AutomationEngine引擎

### Phase 2 (扩展阶段)
1. 实现第二个网站策略(Walmart/eBay)
2. 完善配置系统和错误处理
3. 添加网站选择UI或配置文件

### Phase 3 (优化阶段)
1. 性能优化和监控
2. 更丰富的字段映射支持
3. 图形化网站管理界面

---

## 🏆 总结

这个架构设计遵循了**Clean Architecture**和**Strategy Pattern**的最佳实践，实现了：

- **Single Responsibility**: 每个组件职责单一明确
- **Open/Closed Principle**: 对扩展开放，对修改封闭
- **Never Break Userspace**: 现有功能完全保留

通过这个设计，用户可以轻松添加新的目标网站支持，同时保持Amazon数据抓取的统一性和代码的可维护性。
