#!/usr/bin/env python3
"""
Amazon产品解析器 - 核心通用组件

职责：
1. 统一的Amazon产品页面解析逻辑
2. 提取产品详情、标题、重量等信息
3. 跨网站复用，与具体表单填充解耦

设计原则：
- Single Source of Truth for Amazon parsing
- No website-specific logic
- Good Taste: Simple and reliable
"""

from playwright.sync_api._generated import Locator
import re
from typing import Dict, List, Optional, Any
from playwright.sync_api import Page
# 导入ProductData（避免循环导入）
from .product_data import ProductData


class AmazonProductParser:
    """
    Amazon产品解析器 - 统一的Amazon页面解析引擎
    
    这是重构后的统一解析器，整合了原本分散在多个文件中的163行重复代码
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.parsed_data = None
        self.weight_strategies = [
            self._extract_weight_from_table,
            self._extract_weight_from_specifications,
            self._extract_weight_from_features,
            self._extract_weight_from_bullets,
            self._extract_weight_from_text
        ]
    
    def parse_product(self) -> "ProductData":
        """
        解析Amazon产品页面
        
        Returns:
            ProductData实例，包含所有解析的产品信息
        """
        
        print("🔍 开始Amazon产品页面解析...")
        # 持续监测并点击反爬虫拦截按钮，直到按钮消失
        while True:
            continue_button = self.page.locator("button.a-button-text[alt='Continue shopping']")
            if continue_button.count() > 0 and continue_button.is_visible():
                print("⚠️ 检测到反爬虫拦截，尝试点击Continue按钮...")
                try:
                    self.page.wait_for_timeout(2000)
                    # 点击Continue按钮
                    continue_button.click()
                    # 等待页面重新加载
                    self.page.wait_for_load_state("domcontentloaded")
                    print("✅ 点击Continue按钮成功，页面已重新加载")
                    # 等待一段时间以确保页面稳定
                    self.page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"⚠️ 点击Continue按钮失败: {e}")
            else:
                print("✅ 反爬虫拦截按钮已消失，继续解析流程")
                break
        print("检查配送地址是否为纽约10001")
        deliver_to = self.page.locator("#glow-ingress-line2").inner_text()
        print(f"deliver_to: {deliver_to}")
        if not deliver_to.__contains__("10001"):
            print("配送地点不是纽约10001，准备切换")
            language_button = self.page.locator("#nav-global-location-popover-link")
            language_button.wait_for(timeout=2000)
            print("切换语言和地区设置")
            language_button.click()
            
            # Wait for the location dialog to appear
            self.page.wait_for_selector("#GLUXZipUpdateInput", timeout=10000)
            
            # Fill the zip code
            zip_input = self.page.locator("#GLUXZipUpdateInput")
            zip_input.fill("10001")
            print("已填写邮政编码: 10001")
            
            # Click the Apply button
            apply_button = self.page.locator("#GLUXZipUpdate")
            apply_button.click()
            print("已点击应用按钮")
            input("切换成功后回车键继续...")
            # self.page.press("body", "Enter")
            # try:
            #     self.page.wait_for_selector("[id='GLUXConfirmClose'][type='submit']", timeout=2000)
            #     confirm_button = self.page.locator("[id='GLUXConfirmClose'][type='submit']")
            #     confirm_button.click()
            #     print("已点击确认按钮")
            # except Exception as e:
            #     print(f"⚠️ 错误: {e}")
            # try:
            #     self.page.get_by_role("button", name="完成").click(timeout=1000)
            #     print("已点击完成按钮")
            # except Exception as e:
            #     print(f"⚠️ 错误: {e}")
            # try:
            #     self.page.get_by_role("button", name="Done").click(timeout=1000)
            #     print("已点击Done按钮")
            # except Exception as e:
            #     print(f"⚠️ 错误: {e}")
            # Wait for page to load
            self.page.wait_for_load_state("domcontentloaded")
            
            # 然后点击 glowDoneButton
            self.page.wait_for_selector("button[name='glowDoneButton']", timeout=5000)
            done_button = self.page.locator("button[name='glowDoneButton']")
            done_button.click()
            print("已点击完成按钮")
            
            # 等待页面加载完成
            self.page.wait_for_load_state("domcontentloaded")
            
        # 提取基本信息
        commonInfo = self._extract_common()
        title = self._extract_title()
        details = self._extract_product_details()
        weight_value = self._extract_weight_with_strategies()
        dimensions = self._extract_dimensions()
        
        # 创建ProductData实例
        product_data = ProductData(
            title=title,
            common_info=commonInfo,
            details=details,
            weight_value=weight_value,
            dimensions=dimensions
        )
        
        # 解析结果统计
        print(f"✅ 解析完成: 标题={bool(title)}, 详情={len(details)}项, 重量={weight_value}")
        
        return product_data
    
    def _extract_common(self) -> dict:
        """提取产品ASIN"""
        commonInfo = {}
        commonInfo['asin'] = self.page.url.split('/dp/')[1].split('?')[0].replace('/','')
        price_str = self.page.locator("#corePrice_feature_div span.a-offscreen").first.inner_text()
        commonInfo['price'] = float(price_str.replace('$', ''))
        delivery_price_str = self.page.locator("span[data-csa-c-delivery-type='delivery']").first.get_attribute('data-csa-c-delivery-price')
        commonInfo['delivery_price'] = 0
        if delivery_price_str!='FREE':
            commonInfo['delivery_price'] = float((delivery_price_str or '0').replace('$', '')) if delivery_price_str != 'FREE' else 0
        return commonInfo
                    
    def _extract_title(self) -> str:
        """提取产品标题"""
        title_selectors = [
            "#productTitle",
            "h1.a-size-large",
            ".product-title"
        ]
        # from markdownify import markdownify as md
        # html_content = self.page.content()
        # markdown_content = md(html_content, heading_style="ATX")  # 自定义标题风格为ATX
        # print('product content')
        # print(markdown_content)
        for selector in title_selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible():
                    title = element.inner_text().strip()
                    if title:
                        print(f"📝 产品标题: {title[:60]}...")
                        return title
            except Exception as e:
                continue
        
        print("⚠️ 未能提取产品标题")
        return ""
    
    def _extract_product_details(self) -> Dict[str, str]:
        """
        提取产品详情表格 - 重构后的统一实现
        
        这个方法整合了原本分散在多个文件中的重复代码
        """
        print("📊 开始提取产品详情...")
        
        details = {}
        
        # 策略1: Product details表格
        details.update(self._extract_from_details_table())
        
        # 策略2: Additional Information表格
        details.update(self._extract_from_additional_info())
        
        # 策略3: Tech specs表格
        details.update(self._extract_from_tech_specs())
        
        # 策略4: Feature bullets
        details.update(self._extract_from_feature_bullets())
        
        print(f"📊 提取到 {len(details)} 个产品详情项")
        return details
    
    def _extract_from_details_table(self) -> Dict[str, str]:
        """从Product details表格提取信息"""
        details = {}
        
        try:
            # 查找产品详情表格
            table_selectors = [
                "#productOverview_feature_div",
                "#productDetails_detailBullets_sections1",
                "#detail-bullets",
                ".a-normal .a-spacing-micro",
                "#productDetails_techSpec_section_1",
                ".prodDetTable",
                ".a-keyvalue .prodDetTable"
            ]
            
            for selector in table_selectors:
                try:
                    table = self.page.locator(selector)
                    if table.count() > 0:
                        rows = table.locator("tr, .a-row")
                        count = rows.count()
                        print(f"📋 找到表格 {selector}，共 {count} 行")
                        
                        for i in range(count):
                            try:
                                row = rows.nth(i)
                                
                                # 提取键值对 - 支持多种结构
                                key_element = row.locator("td:first-child, .a-span3, .a-text-bold").first
                                value_element = row.locator("td:last-child, .a-span9, .a-color-base").first
                                
                                if key_element.count() > 0 and value_element.count() > 0:
                                    key = key_element.inner_text().strip()
                                    value = value_element.inner_text().strip()
                                    
                                    if key and value and len(key) < 100:  # 过滤无效数据
                                        # 清理键名
                                        key = key.replace('\u200e', '').replace('\u200b', '').strip()
                                        if key.endswith(':'):
                                            key = key[:-1]
                                        
                                        details[key] = value
                                        print(f"  ✓ {key}: {value[:50]}...")
                                        
                            except Exception as e:
                                continue
                                
                        if details:  # 如果找到数据就停止尝试其他选择器
                            break
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"⚠️ 提取详情表格失败: {e}")
        
        return details
    
    def _extract_from_additional_info(self) -> Dict[str, str]:
        """从Additional Information提取信息"""
        details = {}
        
        try:
            additional_info = self.page.locator("#productDetails_detailBullets_sections1 table")
            if additional_info.count() > 0:
                rows = additional_info.locator("tr")
                for i in range(rows.count()):
                    row = rows.nth(i)
                    cells = row.locator("td")
                    if cells.count() >= 2:
                        key = cells.nth(0).inner_text().strip()
                        value = cells.nth(1).inner_text().strip()
                        if key and value:
                            details[key] = value
        except:
            pass
        
        return details
    
    def _extract_from_tech_specs(self) -> Dict[str, str]:
        """从Technical Specifications提取信息"""
        details = {}
        
        try:
            tech_specs = self.page.locator("#productDetails_techSpec_section_1 table")
            if tech_specs.count() > 0:
                rows = tech_specs.locator("tr")
                for i in range(rows.count()):
                    row = rows.nth(i)
                    key_elem = row.locator("td.a-span3")
                    value_elem = row.locator("td.a-span9")
                    
                    if key_elem.count() > 0 and value_elem.count() > 0:
                        key = key_elem.inner_text().strip()
                        value = value_elem.inner_text().strip()
                        if key and value:
                            details[key] = value
        except:
            pass
        
        return details
    
    def _extract_from_feature_bullets(self) -> Dict[str, str]:
        """从Feature bullets提取信息"""
        details = {}
        
        try:
            bullets = self.page.locator("#feature-bullets ul li")
            bullet_items = []
            
            for i in range(bullets.count()):
                bullet_text = bullets.nth(i).inner_text().strip()
                if bullet_text and not bullet_text.startswith("Make sure"):
                    bullet_items.append(bullet_text)
            
            if bullet_items:
                details["Feature Bullets"] = " | ".join(bullet_items[:5])  # 限制长度
                
        except:
            pass
        
        return details
    
    def _extract_weight_with_strategies(self) -> str:
        """
        使用多种策略提取重量信息 - Good Taste实现
        """
        print("⚖️ 开始多策略重量提取...")
        
        for i, strategy in enumerate(self.weight_strategies, 1):
            try:
                weight = strategy()
                if weight and weight != "10":  # 避免默认值
                    print(f"✅ 策略{i} 成功提取重量: {weight}")
                    return weight
            except Exception as e:
                print(f"⚠️ 策略{i} 失败: {e}")
                continue
        
        print("⚠️ 所有策略都未能提取到有效重量，使用默认值")
        return "10"  # 默认重量
    
    def _extract_weight_from_table(self) -> Optional[str]:
        """策略1: 从产品详情表格提取重量"""
        if not hasattr(self, '_cached_details'):
            self._cached_details = self._extract_product_details()
        
        weight_keys = [
            "Item Weight", "Product Weight", "Shipping Weight", 
            "Weight", "Net Weight", "Package Weight"
        ]
        
        for key, value in self._cached_details.items():
            if any(weight_key.lower() in key.lower() for weight_key in weight_keys):
                weight_match = re.search(r'([0-9]+\.?[0-9]*)\s*(pounds?|lbs?|oz)', value, re.IGNORECASE)
                if weight_match:
                    weight_value = weight_match.group(1)
                    unit = weight_match.group(2).lower()
                    
                    # 转换为磅
                    if 'oz' in unit:
                        return str(round(float(weight_value) / 16, 2))
                    return weight_value
        
        return None
    
    def _extract_weight_from_specifications(self) -> Optional[str]:
        """策略2: 从规格表提取重量"""
        try:
            spec_section = self.page.locator("#productDetails_techSpec_section_1")
            if spec_section.count() > 0:
                text = spec_section.inner_text()
                weight_match = re.search(r'weight[^0-9]*([0-9]+\.?[0-9]*)\s*(pounds?|lbs?)', text, re.IGNORECASE)
                if weight_match:
                    return weight_match.group(1)
        except:
            pass
        return None
    
    def _extract_weight_from_features(self) -> Optional[str]:
        """策略3: 从产品特性提取重量"""
        try:
            features = self.page.locator("#feature-bullets")
            if features.count() > 0:
                text = features.inner_text()
                weight_match = re.search(r'([0-9]+\.?[0-9]*)\s*(pounds?|lbs?)', text, re.IGNORECASE)
                if weight_match:
                    return weight_match.group(1)
        except:
            pass
        return None
    
    def _extract_weight_from_bullets(self) -> Optional[str]:
        """策略4: 从描述要点提取重量"""
        try:
            bullets = self.page.locator(".a-unordered-list .a-list-item")
            for i in range(bullets.count()):
                bullet_text = bullets.nth(i).inner_text()
                weight_match = re.search(r'([0-9]+\.?[0-9]*)\s*(pounds?|lbs?)', bullet_text, re.IGNORECASE)
                if weight_match:
                    return weight_match.group(1)
        except:
            pass
        return None
    
    def _extract_weight_from_text(self) -> Optional[str]:
        """策略5: 从页面全文提取重量"""
        try:
            page_text = self.page.locator("body").inner_text()
            # 更严格的匹配，避免误匹配
            weight_matches = re.findall(r'(?:weight|weighs)[^0-9]*([0-9]+\.?[0-9]*)\s*(pounds?|lbs?)', 
                                       page_text, re.IGNORECASE)
            if weight_matches:
                # 返回第一个合理的重量值（大于0.1小于1000磅）
                for weight, unit in weight_matches:
                    weight_val = float(weight)
                    if 0.1 <= weight_val <= 1000:
                        return str(weight_val)
        except:
            pass
        return None
    
    def _extract_dimensions(self) -> Dict[str, str]:
        """提取产品尺寸信息"""
        dimensions = {}
        
        try:
            # 从已提取的详情中查找尺寸
            if not hasattr(self, '_cached_details'):
                self._cached_details = self._extract_product_details()
            
            dimension_keys = [
                "Product Dimensions", "Package Dimensions", "Item Dimensions",
                "Dimensions", "Size", "Length x Width x Height"
            ]
            
            for key, value in self._cached_details.items():
                if any(dim_key.lower() in key.lower() for dim_key in dimension_keys):
                    # 解析尺寸格式: "10 x 8 x 6 inches" 或 "10" x 8" x 6"
                    dim_match = re.search(r'([0-9]+\.?[0-9]*)\s*["x×]\s*([0-9]+\.?[0-9]*)\s*["x×]\s*([0-9]+\.?[0-9]*)', value)
                    if dim_match:
                        dimensions['length'] = dim_match.group(1)
                        dimensions['width'] = dim_match.group(2)
                        dimensions['height'] = dim_match.group(3)
                        print(f"📏 提取到尺寸: {value}")
                        break
        except Exception as e:
            print(f"⚠️ 提取尺寸失败: {e}")
        
        return dimensions
