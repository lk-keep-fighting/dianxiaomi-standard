# Amazon自动化表单填写模板使用指南

## 🎯 模板简介

`template_main.py` 是一个**自包含的Amazon商品页自动化表单填写模板**，专门设计用于快速开发不同网站的自动化表单填写功能。

### 核心特性
- ✅ **自包含**: 所有功能都在一个文件中，无外部依赖
- ✅ **模板化**: 清晰的模块分离，易于修改
- ✅ **完整Amazon解析**: 提取标题、品牌、重量、尺寸、特性等
- ✅ **智能表单填写**: 支持文本框、下拉框、富文本编辑器
- ✅ **配置驱动**: 通过修改配置适应不同网站

## 🚀 快速开始

### 1. 复制模板
```bash
cp template_main.py /path/to/your/new/project/main.py
cd /path/to/your/new/project/
```

### 2. 安装依赖
```bash
pip install playwright
python -m playwright install chromium
```

### 3. 配置环境变量
```bash
export DC_USERNAME="your_username"
export DC_PASSWORD="your_password"
export DEBUG=1
```

### 4. 运行测试
```bash
python main.py
```

## 🔧 配置不同网站

### 步骤1: 修改网站配置
在 `Config` 类中修改基本配置：

```python
class Config:
    # 网站配置
    SITE_NAME = "YourSite"              # 修改为目标网站名称
    SITE_URL = "yoursite.com"           # 修改为目标网站URL
    
    # 认证配置  
    USERNAME_ENV = "YOURSITE_USERNAME"  # 修改环境变量名
    PASSWORD_ENV = "YOURSITE_PASSWORD"  # 修改环境变量名
```

### 步骤2: 调整登录逻辑
在 `WebsiteAutomation.login_if_needed()` 方法中：

```python
def login_if_needed(self) -> bool:
    # 导航到登录页面
    self.page.goto(f"https://{Config.SITE_URL}/login")
    
    # 填写登录表单（修改选择器）
    self.page.fill("#email", credentials['username'])     # 修改用户名输入框选择器
    self.page.fill("#password", credentials['password'])   # 修改密码输入框选择器
    self.page.click(".login-btn")                         # 修改登录按钮选择器
```

### 步骤3: 修改表单容器获取
在 `FormFiller._get_form_container()` 方法中：

```python
def _get_form_container(self):
    # 示例1：简单表单容器
    return self.page.locator("#product-form")
    
    # 示例2：iframe嵌套表单
    main_frame = self.page.locator('iframe[name="main"]').content_frame
    return main_frame.locator('form.product-form')
    
    # 示例3：多层iframe（如店小秘）
    main_frame = self.page.locator('iframe[name="iframeModal_flag_0"]').content_frame
    edit_frame = main_frame.locator('iframe[name^="iframeModal_editPostTemplet"]').content_frame
    return edit_frame
```

### 步骤4: 配置字段映射
在 `FormFiller._fill_basic_fields()` 和 `_fill_detail_fields()` 中：

```python
def _fill_basic_fields(self, container, product: ProductInfo):
    field_mappings = {
        # Amazon字段 -> 目标网站字段名（修改右侧的值）
        'title': 'product_name',           # 产品标题字段
        'brand': 'manufacturer',           # 品牌字段  
        'asin': 'sku',                     # SKU字段
    }

def _fill_detail_fields(self, container, product: ProductInfo):
    detail_mappings = {
        # Amazon详情键 -> 目标网站字段名（修改右侧的值）
        'Brand': 'brand_name',
        'Color': 'product_color', 
        'Material': 'material_type',
        'Model': 'model_number',
    }
```

### 步骤5: 调整选择器模式
在 `FormFiller._fill_form_field()` 方法中：

```python
def _fill_form_field(self, container, field_name: str, value: str):
    # 模式1: 使用ID选择器
    selector = f"#{field_name.lower().replace(' ', '_')}"
    
    # 模式2: 使用name属性
    selector = f"input[name='{field_name}']"
    
    # 模式3: 使用data属性
    selector = f"input[data-field='{field_name}']"
    
    # 模式4: 使用attrkey属性（店小秘风格）
    selector = f"div[attrkey='{field_name}']"
```

## 📋 常见网站适配模式

### 标准HTML表单
```python
def _get_form_container(self):
    return self.page.locator("#product-form")

def _fill_form_field(self, container, field_name: str, value: str):
    selector = f"input[name='{field_name.lower()}']"
    container.locator(selector).fill(value)
```

### React/Vue单页应用
```python
def _get_form_container(self):
    # 等待React组件加载
    self.page.wait_for_selector("[data-testid='product-form']")
    return self.page.locator("[data-testid='product-form']")

def _fill_form_field(self, container, field_name: str, value: str):
    selector = f"input[data-testid='{field_name.lower()}']"
    container.locator(selector).fill(value)
```

### 多步骤向导表单
```python
def fill_form_with_product(self, product: ProductInfo) -> Dict[str, Any]:
    # 步骤1：基本信息
    self._fill_step1_basic_info(product)
    self.page.click("button.next-step")
    
    # 步骤2：详细信息  
    self._fill_step2_details(product)
    self.page.click("button.next-step")
    
    # 步骤3：确认提交
    self._fill_step3_confirmation(product)
```

### iframe嵌套表单
```python
def _get_form_container(self):
    # 等待iframe加载
    iframe = self.page.wait_for_selector("iframe[src*='form']")
    frame_content = self.page.frame(name="form-iframe").content_frame
    return frame_content
```

## 🔍 调试技巧

### 1. 启用调试模式
```bash
export DEBUG=1
python main.py
```

### 2. 禁用无头模式观察过程
```bash
export HEADLESS=false
python main.py
```

### 3. 添加断点调试
```python
def _fill_form_field(self, container, field_name: str, value: str):
    try:
        # 调试：打印选择器和值
        print(f"🔍 尝试填写: {field_name} = {value}")
        
        selector = f"div[attrkey='{field_name}']"
        field_container = container.locator(selector)
        
        # 调试：检查元素是否存在
        if field_container.count() == 0:
            print(f"⚠️ 未找到元素: {selector}")
            return
            
        # ... 填写逻辑
```

### 4. 页面截图调试
```python
def _execute_automation_workflow(self, page: Page, context: BrowserContext):
    # 在关键步骤添加截图
    page.screenshot(path="step1-login.png")
    
    # 登录逻辑...
    
    page.screenshot(path="step2-form.png")
    
    # 表单填写逻辑...
```

## 🛠️ 高级定制

### 1. 添加自定义字段处理
```python
def _fill_custom_field_type(self, container, field_name: str, value: str):
    """处理特殊字段类型"""
    if field_name == "Upload Image":
        # 文件上传
        file_input = container.locator("input[type='file']")
        file_input.set_input_files("path/to/image.jpg")
    elif field_name == "Date Field":
        # 日期选择
        date_input = container.locator("input[type='date']")
        date_input.fill("2024-01-01")
```

### 2. 添加验证逻辑
```python
def _validate_form_submission(self) -> bool:
    """验证表单提交是否成功"""
    try:
        # 等待成功提示
        success_msg = self.page.wait_for_selector(".success-message", timeout=10000)
        return True
    except:
        # 检查错误信息
        error_msg = self.page.locator(".error-message")
        if error_msg.count() > 0:
            print(f"❌ 表单提交失败: {error_msg.inner_text()}")
        return False
```

### 3. 添加重试机制
```python
def _fill_form_field_with_retry(self, container, field_name: str, value: str, max_retries: int = 3):
    """带重试的字段填写"""
    for attempt in range(max_retries):
        try:
            self._fill_form_field(container, field_name, value)
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ 字段 {field_name} 填写失败，已重试 {max_retries} 次")
                return False
            time.sleep(1)  # 等待1秒后重试
```

## 📊 使用场景

### 电商平台商品上架
- **Amazon → Shopify**: 商品信息同步
- **Amazon → WooCommerce**: 自动化商品导入
- **Amazon → Magento**: 批量商品添加

### 分销商系统
- **Amazon → 分销商平台**: 自动化商品资料录入
- **Amazon → ERP系统**: 商品主数据管理
- **Amazon → 库存系统**: 商品信息同步

### 数据收集和分析
- **Amazon → CRM**: 潜在产品线研究
- **Amazon → 数据库**: 竞品信息收集
- **Amazon → Excel**: 产品对比分析

## ❗ 注意事项

### 1. 合规使用
- 遵守目标网站的服务条款
- 控制请求频率，避免对服务器造成压力
- 不要用于恶意或非法目的

### 2. 错误处理
- 始终添加适当的异常处理
- 对网络超时和页面加载失败做好准备
- 实现优雅的降级策略

### 3. 维护性
- 定期测试模板是否仍然有效
- 关注目标网站的页面结构变化
- 保持选择器和逻辑的更新

## 🚀 部署建议

### 开发环境
```bash
export DEBUG=1
export HEADLESS=false
python main.py
```

### 生产环境
```bash
export DEBUG=0
export HEADLESS=true
python main.py
```

### 定时任务
```bash
# 使用cron定时执行
0 2 * * * cd /path/to/project && python main.py >> automation.log 2>&1
```

---

## 📞 技术支持

这个模板设计为**即插即用**，通过修改几个关键配置点就能适应不同的目标网站。如果遇到特殊需求，可以：

1. 参考模板中的详细注释
2. 使用调试模式分析页面结构
3. 根据目标网站的特点调整相应逻辑

**记住**: 这个模板的核心价值在于Amazon解析部分是通用的，只需要修改网站特定的登录、导航和表单填写逻辑即可！
