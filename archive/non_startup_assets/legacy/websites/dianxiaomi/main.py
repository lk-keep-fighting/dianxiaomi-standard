#!/usr/bin/env python3
"""
Amazon商品页自动化表单填写模板

这是一个自包含的模板项目，用于基于Amazon商品页面进行自动化表单填写开发。
您可以复制这个文件到新项目，修改表单填写逻辑以适应不同的目标网站。

功能特点：
- 自包含：所有必要功能都在这一个文件中
- 模板化：易于修改以适应不同网站
- Amazon解析：完整的Amazon商品信息提取
- 表单填写：可配置的表单自动化框架

使用方法：
1. 复制此文件到新项目
2. 修改网站配置部分
3. 调整表单填写逻辑
4. 运行测试

作者：Linus风格实现
版本：Template v1.0
"""

from operator import truediv
import os
from playwright.sync_api._generated import Page
import sys
import time
import re
import json
import traceback
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Playwright, Page, BrowserContext



# ================== 配置部分 ==================
class Config:
    """项目配置 - 修改此部分以适应不同网站"""
    
    # 网站配置
    SITE_NAME = '店小秘'  # 修改为目标网站名称
    SITE_URL ='www.dianxiaomi.com' # 修改为目标网站URL
    
    # 认证配置
    USERNAME_ENV = "USERNAME"  # 修改环境变量名
    PASSWORD_ENV = "PASSWORD"  # 修改环境变量名
    
    # 浏览器配置
    HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'
    BROWSER_TIMEOUT = 60000
    
    # Amazon配置
    AMAZON_LANGUAGE = "en_US"
    AMAZON_CURRENCY = "USD"
    
    @classmethod
    def getStatePath(cls) -> str:
        user_name = cls.get_credentials()['username']
        """获取保存状态的文件路径"""
        return user_name + "_auth.json"
    # 调试配置
    DEBUG = os.getenv('DEBUG', '0') == '1'
    
    @classmethod
    def get_credentials(cls) -> Dict[str, str]:
        """获取认证凭据"""
        return {
            'username': os.getenv(cls.USERNAME_ENV, ''),
            'password': os.getenv(cls.PASSWORD_ENV, '')
        }


# ================== Amazon解析部分 ==================
@dataclass
class ProductInfo:
    """Amazon产品信息数据结构"""
    title: str = ""
    brand: str = ""
    manufacturer: str = ""
    details: Dict[str, str] = None
    weight: str = "10"
    dimensions: Dict[str, str] = None
    features: List[str] = None
    asin: str = ""
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.dimensions is None:
            self.dimensions = {}
        if self.features is None:
            self.features = []
    
    def has_valid_data(self) -> bool:
        return bool(self.title or self.details)


class AmazonParser:
    """Amazon商品页面解析器"""
    
    def __init__(self, page: Page, debug: bool = False):
        self.page = page
        self.debug = debug
    
    def parse_product(self) -> ProductInfo:
        """解析Amazon商品页面"""
        if self.debug:
            print("🔍 开始解析Amazon商品页面...")
        
        product = ProductInfo()
        
        # 提取基本信息
        product.title = self._extract_title()
        product.asin = self._extract_asin()
        product.details = self._extract_details()
        product.brand, product.manufacturer = self._extract_brand_info()
        product.weight = self._extract_weight()
        product.dimensions = self._extract_dimensions()
        product.features = self._extract_features()
        
        if self.debug:
            print(f"✅ 解析完成: 标题={bool(product.title)}, 详情={len(product.details)}项")
        
        return product
    
    def _extract_title(self) -> str:
        """提取商品标题"""
        selectors = ["#productTitle", "h1.a-size-large", ".product-title"]
        
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible():
                    title = element.inner_text().strip()
                    if title:
                        if self.debug:
                            print(f"📝 商品标题: {title[:50]}...")
                        return title
            except:
                continue
        
        if self.debug:
            print("⚠️ 未能提取商品标题")
        return ""
    
    def _extract_asin(self) -> str:
        """提取ASIN"""
        try:
            url = self.page.url
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
            if asin_match:
                asin = asin_match.group(1)
                if self.debug:
                    print(f"🏷️ ASIN: {asin}")
                return asin
        except:
            pass
        return ""
    
    def _extract_details(self) -> Dict[str, str]:
        """提取商品详情"""
        details = {}
        
        # 多种表格选择器
        table_selectors = [
            "#productDetails_detailBullets_sections1",
            "#detail-bullets",
            "#productDetails_techSpec_section_1",
            ".prodDetTable"
        ]
        
        for selector in table_selectors:
            try:
                table = self.page.locator(selector)
                if table.count() > 0:
                    rows = table.locator("tr, .a-row")
                    for i in range(rows.count()):
                        try:
                            row = rows.nth(i)
                            key_elem = row.locator("td:first-child, .a-span3, .a-text-bold").first
                            value_elem = row.locator("td:last-child, .a-span9, .a-color-base").first
                            
                            if key_elem.count() > 0 and value_elem.count() > 0:
                                key = key_elem.inner_text().strip()
                                value = value_elem.inner_text().strip()
                                
                                if key and value and len(key) < 100:
                                    # 清理键名
                                    key = key.replace('\u200e', '').replace('\u200b', '').strip()
                                    if key.endswith(':'):
                                        key = key[:-1]
                                    
                                    details[key] = value
                                    if self.debug:
                                        print(f"  ✓ {key}: {value[:40]}...")
                        except:
                            continue
            except Exception as e:
                if self.debug:
                    print(f"⚠️ 解析表格失败 {selector}: {e}")
                continue
        
        if self.debug:
            print(f"📊 提取到 {len(details)} 个详情项")
        return details
    
    def _extract_brand_info(self) -> tuple[str, str]:
        """提取品牌信息"""
        brand = ""
        manufacturer = ""
        
        brand_keys = ['Brand', 'Manufacturer', 'Made by', 'Company']
        
        for key, value in self.details.items():
            key_lower = key.lower()
            if any(brand_key.lower() in key_lower for brand_key in brand_keys):
                if not brand:
                    brand = value
                if not manufacturer:
                    manufacturer = value
        
        if self.debug:
            print(f"🏷️ 品牌信息: Brand={brand}, Manufacturer={manufacturer}")
        return brand, manufacturer
    
    def _extract_weight(self) -> str:
        """提取重量信息"""
        weight_keys = ["Item Weight", "Product Weight", "Shipping Weight", "Weight"]
        
        for key, value in self.details.items():
            if any(weight_key.lower() in key.lower() for weight_key in weight_keys):
                weight_match = re.search(r'([0-9]+\.?[0-9]*)\s*(pounds?|lbs?|oz)', value, re.IGNORECASE)
                if weight_match:
                    weight_value = weight_match.group(1)
                    unit = weight_match.group(2).lower()
                    
                    # 转换为磅
                    if 'oz' in unit:
                        weight_value = str(round(float(weight_value) / 16, 2))
                    
                    if self.debug:
                        print(f"⚖️ 重量: {weight_value} lbs")
                    return weight_value
        
        if self.debug:
            print("⚠️ 未找到重量信息，使用默认值")
        return "10"
    
    def _extract_dimensions(self) -> Dict[str, str]:
        """提取尺寸信息"""
        dimensions = {}
        dimension_keys = ["Product Dimensions", "Package Dimensions", "Item Dimensions", "Dimensions"]
        
        for key, value in self.details.items():
            if any(dim_key.lower() in key.lower() for dim_key in dimension_keys):
                # 解析尺寸格式: "10 x 8 x 6 inches"
                dim_match = re.search(r'([0-9]+\.?[0-9]*)\s*[\"x×]\s*([0-9]+\.?[0-9]*)\s*[\"x×]\s*([0-9]+\.?[0-9]*)', value)
                if dim_match:
                    dimensions = {
                        'length': dim_match.group(1),
                        'width': dim_match.group(2),
                        'height': dim_match.group(3)
                    }
                    if self.debug:
                        print(f"📏 尺寸: {value}")
                    break
        
        return dimensions
    
    def _extract_features(self) -> List[str]:
        """提取特性要点"""
        features = []
        
        try:
            bullets = self.page.locator("#feature-bullets ul li")
            for i in range(min(bullets.count(), 10)):  # 最多10个特性
                try:
                    bullet_text = bullets.nth(i).inner_text().strip()
                    if bullet_text and not bullet_text.startswith("Make sure") and len(bullet_text) > 10:
                        features.append(bullet_text[:200])  # 限制长度
                except:
                    continue
            
            if self.debug:
                print(f"📋 提取到 {len(features)} 个特性要点")
        except Exception as e:
            if self.debug:
                print(f"⚠️ 提取特性失败: {e}")
        
        return features


# ================== 表单填写部分 ==================
class FormFiller:
    """表单自动化填写器 - 修改此部分以适应不同网站的表单结构"""
    
    def __init__(self, page: Page, debug: bool = False):
        self.page = page
        self.debug = debug
        self.stats = {'successful_fills': 0, 'failed_fills': 0}
    
    def fill_form_with_product(self, product: ProductInfo) -> Dict[str, Any]:
        """使用商品信息填写表单 - 主要修改此方法"""
        if self.debug:
            print("📝 开始自动填写表单...")
        
        try:
            # =============== 修改此部分以适应目标网站 ===============
            
            # 1. 获取表单容器（根据目标网站调整）
            form_container = self._get_form_container()
            
            if not form_container:
                raise Exception("未找到表单容器")
            
            # 2. 填写基本信息字段
            self._fill_basic_fields(form_container, product)
            
            # 3. 填写商品详情字段
            self._fill_detail_fields(form_container, product)
            
            # 4. 填写复合字段（重量、尺寸等）
            self._fill_compound_fields(form_container, product)
            
            # 5. 填写富文本字段（特性描述等）
            self._fill_rich_text_fields(form_container, product)
            
            # ========================================================
            
            if self.debug:
                print(f"✅ 表单填写完成: 成功={self.stats['successful_fills']}, 失败={self.stats['failed_fills']}")
            
            return self.stats
            
        except Exception as e:
            if self.debug:
                print(f"❌ 表单填写失败: {e}")
            return {'error': str(e), **self.stats}
    
    def _get_form_container(self):
        """获取表单容器 - 根据目标网站修改选择器"""
        try:
            # 示例：数字酋长的iframe结构
            main_frame = self.page.locator('iframe[name="iframeModal_flag_0"]').content_frame
            edit_frame = main_frame.locator('iframe[name^="iframeModal_editPostTemplet"]').content_frame
            return edit_frame
        except Exception as e:
            if self.debug:
                print(f"⚠️ 获取表单容器失败: {e}")
            return None
    
    def _fill_basic_fields(self, container, product: ProductInfo):
        """填写基本字段 - 根据目标网站的字段映射修改"""
        field_mappings = {
            # Amazon字段 -> 目标网站字段名
            'title': 'Product Title',
            'brand': 'Manufacturer Name',
            'manufacturer': 'Manufacturer Name',
            'asin': 'UPC',
        }
        
        for product_field, form_field in field_mappings.items():
            value = getattr(product, product_field, '')
            if value:
                self._fill_form_field(container, form_field, value)
    
    def _fill_detail_fields(self, container, product: ProductInfo):
        """填写详情字段 - 根据目标网站调整映射规则"""
        detail_mappings = {
            # Amazon详情键 -> 目标网站字段名
            'Brand': 'Manufacturer Name',
            'Manufacturer': 'Manufacturer Name', 
            'Color': 'Color',
            'Material': 'Material',
            'Model': 'Model Number',
            'Item model number': 'Model Number',
        }
        
        for amazon_key, form_field in detail_mappings.items():
            if amazon_key in product.details:
                value = product.details[amazon_key]
                self._fill_form_field(container, form_field, value)
    
    def _fill_compound_fields(self, container, product: ProductInfo):
        """填写复合字段（数值+单位）- 根据目标网站调整"""
        # 重量字段
        if product.weight and product.weight != "10":
            self._fill_compound_field(container, 'Assembled Product Weight', product.weight, 'lb (磅)')
        
        # 尺寸字段
        if product.dimensions:
            dimension_fields = {
                'Assembled Product Depth': product.dimensions.get('length', ''),
                'Assembled Product Width': product.dimensions.get('width', ''),
                'Assembled Product Height': product.dimensions.get('height', '')
            }
            
            for field_name, value in dimension_fields.items():
                if value:
                    self._fill_compound_field(container, field_name, value, 'in (英寸)')
        
        # Net Content（固定值）
        self._fill_compound_field(container, 'Net Content', '1', 'Each (每个)')
    
    def _fill_rich_text_fields(self, container, product: ProductInfo):
        """填写富文本字段 - 根据目标网站调整"""
        if product.features:
            # 将特性要点组合为Key Features
            features_text = "\\n".join([f"• {feature}" for feature in product.features[:5]])
            self._fill_tinymce_field(container, 'Key Features', features_text)
    
    def _fill_form_field(self, container, field_name: str, value: str):
        """填写表单字段 - 根据目标网站的选择器模式调整"""
        try:
            # 示例选择器模式：使用attrkey属性
            selector = f"div[attrkey='{field_name}']"
            field_container = container.locator(selector)
            field_container.wait_for(state="visible", timeout=5000)
            
            # 尝试文本域
            textarea = field_container.locator("textarea")
            if textarea.count() > 0:
                textarea.first.fill(str(value))
                self.stats['successful_fills'] += 1
                if self.debug:
                    print(f"✅ 填写字段 {field_name}: {value}")
                return
            
            # 尝试输入框
            input_elem = field_container.locator("input")
            if input_elem.count() > 0:
                input_elem.first.fill(str(value))
                self.stats['successful_fills'] += 1
                if self.debug:
                    print(f"✅ 填写字段 {field_name}: {value}")
                return
            
            if self.debug:
                print(f"⚠️ 未找到可填写的输入元素: {field_name}")
                
        except Exception as e:
            self.stats['failed_fills'] += 1
            if self.debug:
                print(f"⚠️ 填写字段失败 {field_name}: {e}")
    
    def _fill_compound_field(self, container, field_name: str, value: str, unit: str):
        """填写复合字段（数值+单位）"""
        try:
            selector = f"div[attrkey='{field_name}']"
            field_container = container.locator(selector)
            field_container.wait_for(state="visible", timeout=5000)
            
            # 填写数值
            number_input = field_container.locator("input")
            if number_input.count() > 0:
                number_input.first.fill(str(value))
            
            # 填写单位
            unit_select = field_container.locator("select")
            if unit_select.count() > 0:
                try:
                    unit_select.first.select_option(label=unit)
                except:
                    pass  # 单位选择失败不影响数值填写
            
            self.stats['successful_fills'] += 1
            if self.debug:
                print(f"✅ 填写复合字段 {field_name}: {value} {unit}")
                
        except Exception as e:
            self.stats['failed_fills'] += 1
            if self.debug:
                print(f"⚠️ 填写复合字段失败 {field_name}: {e}")
    
    def _fill_tinymce_field(self, container, field_name: str, content: str):
        """填写TinyMCE富文本字段"""
        try:
            selector = f"div[attrkey='{field_name}']"
            field_container = container.locator(selector)
            field_container.wait_for(state="visible", timeout=5000)
            
            # 查找TinyMCE iframe
            tinymce_iframe = field_container.locator("iframe")
            if tinymce_iframe.count() > 0:
                iframe_content = tinymce_iframe.first.content_frame()
                body = iframe_content.locator("body")
                if body.count() > 0:
                    body.first.fill(content)
                    self.stats['successful_fills'] += 1
                    if self.debug:
                        print(f"✅ 填写富文本字段 {field_name}")
                    return
            
            # 降级到普通文本域
            textarea = field_container.locator("textarea")
            if textarea.count() > 0:
                textarea.first.fill(content)
                self.stats['successful_fills'] += 1
                if self.debug:
                    print(f"✅ 填写文本域 {field_name}")
                
        except Exception as e:
            self.stats['failed_fills'] += 1
            if self.debug:
                print(f"⚠️ 填写富文本字段失败 {field_name}: {e}")


# ================== 网站操作部分 ==================
class WebsiteAutomation:
    """网站自动化操作 - 修改此部分以适应目标网站的登录和导航逻辑"""
    
    def __init__(self, page: Page, context: BrowserContext, debug: bool = False):
        self.page = page
        self.context = context
        self.debug = debug

    def login_if_needed(self) -> bool:
        """登录网站 - 根据目标网站修改登录逻辑"""
        try:
            credentials = Config.get_credentials()
            if not credentials['username'] or not credentials['password']:
                if self.debug:
                    print("⚠️ 未配置登录凭据")
                return False
            
            # =============== 修改此部分以适应目标网站登录流程 ===============
            
            # 示例：检查是否已登录
            if self._is_logged_in():
                if self.debug:
                    print("✅ 已登录，无需重复登录")
                return True
            else:
              
                # 填写登录表单
                # self.page.fill("#username", credentials['username'])
                # self.page.fill("#password", credentials['password'])
                # self.page.click("button[type='submit']")
                input("请输入登录信息后按回车键")
                state_path= Config.getStatePath()
                self.context.storage_state(path=state_path)
                print(f"✅ 会话状态已保存到 {state_path}")
            # 等待登录完成
            # 验证登录结果
            if self._is_logged_in():
                if self.debug:
                    print("✅ 登录成功")
                return True
            else:
                if self.debug:
                    print("❌ 登录失败")
                return False
            
            # ================================================================
            
        except Exception as e:
            if self.debug:
                print(f"❌ 登录过程异常: {e}")
            return False
    
    def navigate_to_form_page(self) -> bool:
        """导航到表单页面 - 根据目标网站修改"""
        try:
            # =============== 修改此部分以适应目标网站导航逻辑 ===============
            input("等待输入数据行号跳转编辑页，按回车键确认\n")
            # ================================================================
            return True
        except Exception as e:
            if self.debug:
                print(f"❌ 导航异常: {e}")
            return False
    
    def _is_logged_in(self) -> bool:
        """检查登录状态 - 根据目标网站修改检查逻辑"""
        try:
            # 示例：检查登录状态的方法
            # 方法1：检查特定元素是否存在
            # logout_button = self.page.locator("i.sign-out")
            # if logout_button.count() > 0:
            #     return True
            
            # 方法2：检查URL
            if "home" in self.page.url:
                print("已登录到home页面")
                self.page.goto("https://www.dianxiaomi.com/web/sheinProduct/draft")
                return True
            
            # 方法3：检查cookie或本地存储
            # cookies = self.context.cookies()
            # return any(cookie['name'] == 'auth_token' for cookie in cookies)
            
            return False
            
        except Exception as e:
            print(f"❌ 检查登录状态异常: {e}")
            return False
    
    def extract_amazon_url_from_page(self) -> Optional[str]:
        """从页面提取Amazon URL - 根据目标网站修改"""
        try:
            # =============== 修改此部分以适应目标网站的URL提取逻辑 ===============
            
            # 示例：从链接或输入框提取Amazon URL
            url_selectors = [
                # "a.linkUrl",  # 链接
                # "input[name='productUrl']",  # 输入框
                "input[name='sourceUrl']",  # 输入框
                # "input[placeholder*='amazon']",  # 包含amazon的输入框
            ]
            print("self.latest_page.title")
            print(self.latest_page.title)
            
            for selector in url_selectors:
                try:
                    elements = self.latest_page.locator(selector)
                    if elements.count() > 0:
                        element = elements.first
                        print(f"🔗 找到Amazon element: {element}")
                        # 尝试获取href或value
                        url = element.get_attribute("href") or element.get_attribute("value")
                        if url and "amazon.com" in url and "/dp/" in url:
                            if self.debug:
                                print(f"🔗 找到Amazon URL: {url}")
                            return url
                except:
                    continue
            
            # ================================================================
            
            if self.debug:
                print("⚠️ 未找到Amazon URL")
            return None
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ 提取Amazon URL失败: {e}")
            return None


# ================== 主程序部分 ==================
class AutomationApp:
    """自动化应用主类"""
    
    def __init__(self, debug: bool = True):
        self.debug = debug
    
    def run(self):
        """运行自动化流程"""
        print(f"🚀 启动 {Config.SITE_NAME} 自动化表单填写")
        print("="*50)
        
        try:
            with sync_playwright() as playwright:
                # 启动浏览器
                browser = playwright.chromium.launch(
                    headless=Config.HEADLESS,
                    slow_mo=100 if self.debug else 0
                )
                state_path= Config.getStatePath()
                if(os.path.exists(state_path)):
                    context = browser.new_context(
                        storage_state=state_path
                    )
                else:
                    context = browser.new_context() 
                page = context.new_page()
                
                try:
                    # 执行自动化流程
                    self._execute_automation_workflow(page, context)
                    
                finally:
                    browser.close()
                    
        except Exception as e:
            print(f"❌ 程序异常: {e}")
            if self.debug:
                traceback.print_exc()
    
    def _execute_automation_workflow(self, page: Page, context: BrowserContext):
        """执行完整的自动化工作流程"""
        
        # 1. 网站操作
        website = WebsiteAutomation(page, context, self.debug)
          # 导航到登录页面
        page.goto(f"https://{Config.SITE_URL}")
        # 2. 登录网站
        if not website.login_if_needed():
            print("❌ 登录失败，程序退出")
            return
        
        # 3. 导航到表单页面
        if not website.navigate_to_form_page():
            print("❌ 导航失败，程序退出")
            return
        
        # 4. 提取Amazon URL
        amazon_url = website.extract_amazon_url_from_page()
        if not amazon_url:
            print("❌ 未找到Amazon商品URL，程序退出")
            return
        
        # 5. 解析Amazon商品信息
        product_info = self._parse_amazon_product(amazon_url, context)
        if not product_info.has_valid_data():
            print("❌ Amazon商品信息解析失败，程序退出")
            return
        
        # 6. 填写表单
        form_filler = FormFiller(page, self.debug)
        result = form_filler.fill_form_with_product(product_info)
        
        # 7. 输出结果
        self._print_result(result, product_info)
    
    def _parse_amazon_product(self, amazon_url: str, context: BrowserContext) -> ProductInfo:
        """解析Amazon商品信息"""
        print("📊 解析Amazon商品信息...")
        
        amazon_page = context.new_page()
        try:
            # 构建完整URL
            full_url = f"{amazon_url}?language={Config.AMAZON_LANGUAGE}&currency={Config.AMAZON_CURRENCY}"
            amazon_page.goto(full_url, timeout=Config.BROWSER_TIMEOUT)
            
            # 等待页面加载
            amazon_page.wait_for_load_state("networkidle")
            
            # 解析商品信息
            parser = AmazonParser(amazon_page, self.debug)
            product_info = parser.parse_product()
            
            return product_info
            
        finally:
            amazon_page.close()
            print("✅ Amazon页面已关闭")
    
    def _print_result(self, result: Dict[str, Any], product_info: ProductInfo):
        """打印执行结果"""
        print("\n" + "="*50)
        print("📊 自动化执行结果")
        print("="*50)
        
        print(f"🏷️ 商品标题: {product_info.title[:50]}...")
        print(f"🔖 品牌: {product_info.brand}")
        print(f"⚖️ 重量: {product_info.weight} lbs")
        print(f"📦 详情项数: {len(product_info.details)}")
        
        if 'error' in result:
            print(f"❌ 表单填写失败: {result['error']}")
        else:
            print(f"✅ 成功填写: {result.get('successful_fills', 0)} 个字段")
            print(f"⚠️ 填写失败: {result.get('failed_fills', 0)} 个字段")
        
        print("="*50)


# ================== 程序入口 ==================
def main():
    """主函数"""
    print("""
█████╗ ███████╗███████╗ ██████╗ ██████╗ ███╗   ███╗    ████████╗███████╗███╗   ███╗██████╗ ██╗      █████╗ ████████╗███████╗
██╔══██╗██╔════╝██╔════╝██╔═══██╗██╔══██╗████╗ ████║    ╚══██╔══╝██╔════╝████╗ ████║██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔════╝
███████║█████╗  █████╗  ██║   ██║██████╔╝██╔████╔██║       ██║   █████╗  ██╔████╔██║██████╔╝██║     ███████║   ██║   █████╗  
██╔══██║██╔══╝  ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║       ██║   ██╔══╝  ██║╚██╔╝██║██╔═══╝ ██║     ██╔══██║   ██║   ██╔══╝  
██║  ██║██║     ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║       ██║   ███████╗██║ ╚═╝ ██║██║     ███████╗██║  ██║   ██║   ███████╗
╚═╝  ╚═╝╚═╝     ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝       ╚═╝   ╚══════╝╚═╝     ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
    """)
    
    print("Amazon商品页自动化表单填写模板")
    print("适用于任何基于Amazon商品信息的表单自动化需求")
    print()
    
    # 检查环境变量
    credentials = Config.get_credentials()
    if not credentials['username'] or not credentials['password']:
        print("⚠️ 请设置环境变量:")
        print(f"   export {Config.USERNAME_ENV}='your_username'")
        print(f"   export {Config.PASSWORD_ENV}='your_password'")
        print()
        print("可选配置:")
        print("   export DEBUG=1          # 启用调试模式")
        print("   export HEADLESS=true    # 启用无头模式")
        print()
    
    # 启动应用
    app = AutomationApp(debug=Config.DEBUG)
    app.run()


if __name__ == "__main__":
    main()
