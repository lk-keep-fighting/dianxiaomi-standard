"""
Amazon Product Parser - 亚马逊产品信息解析工具类

重构后的统一Amazon产品解析器。
合并了main.py和main-table-model.py中的重复解析逻辑。

作者: Linus Torvalds (风格)
设计原则: Single Source of Truth, Good Taste, No Duplication
"""

import re
from typing import Dict, List, Optional, Any
from playwright.sync_api import Page
from product_data import ProductData


# ProductData 现在从 product_data.py 导入，不再重复定义


class AmazonProductParser:
    """
    亚马逊产品解析器
    
    单一职责：只负责从亚马逊页面提取产品信息
    Good Taste：每个方法只做一件事，数据结构简单清晰
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.product_data = ProductData()
        
        # 解析器配置 - 所有的选择器和关键词都在这里，便于维护
        self.selectors = {
            'title': '#productTitle',
            'product_table_top': "table[class='a-normal a-spacing-micro']",
            'product_table_bottom': "table[class='a-keyvalue prodDetTable']",
            'glance_icons': '#glance_icons_div',
            'feature_bullets': '#feature-bullets ul.a-unordered-list li span.a-list-item',
            'weight_cell': "td:has-text('Item Weight')"
        }
        
        # 智能提取关键词
        self.keywords = {
            'materials': ['bamboo', 'wood', 'metal', 'plastic', 'steel', 'aluminum', 'glass', 'fabric'],
            'styles': ['modern', 'boho', 'scandinavian', 'industrial', 'rustic', 'minimalist', 'contemporary'],
            'rooms': ['living room', 'bedroom', 'bathroom', 'office', 'kitchen', 'entryway'],
            'assembly_no_tools': ['no hardware', 'tool-free', 'no screws', 'snap together'],
            'assembly_required': ['assembly', 'install', 'assemble']
        }
    
    def parse_product(self) -> ProductData:
        """
        解析产品信息的主入口
        
        这是唯一的public方法 - 简单明了
        """
        print("🔍 开始解析亚马逊产品信息...")
        
        try:
            # 确保页面完全加载
            self._prepare_page()
            
            # 按顺序解析各个部分
            self._parse_title()
            self._parse_price()
            # self._parse_colors()
            # self._parse_item_package_quantity()
            self._parse_specifications()  # 新增规格数据分析
            
            self._parse_product_details_tables()
            
            self._parse_weight()
            
            self._parse_product_props_from_details()  # 新增尺寸解析和单位转换
            
            self._parse_glance_icons()
            self._parse_feature_bullets()
            
            self.product_data.parse_success = True
            print(f"✅ 产品解析完成，共提取 {len(self.product_data.details)} 个属性")
            
        except Exception as e:
            error_msg = f"产品解析失败: {e}"
            print(f"❌ {error_msg}")
            self.product_data.parse_errors.append(error_msg)
        
        return self.product_data
    def _parse_product_props_from_details(self)-> None:
        """解析产品尺寸信息并转换为厘米单位"""
        print("开始解析产品尺寸信息")
        dimensions_str = self.product_data.details.get("product dimensions")
        print(f"product dimensions: {dimensions_str}")
        if dimensions_str: # product dimensions: 15"D x 22.83"W x 24"H
            depth_cm, width_cm, height_cm = self._parse_dimensions(dimensions_str)
            if depth_cm:
                self.product_data.add_detail("depth_cm", str(depth_cm))
            if width_cm:
                self.product_data.add_detail("width_cm", str(width_cm))
            if height_cm:
                self.product_data.add_detail("height_cm", str(height_cm))
        else: ##item dimensions d x w x h:15"D x 22.83"W x 24"H  
            dimensions_str = self.product_data.details.get("item dimensions d x w x h")
            print(f"item dimensions d x w x h :{dimensions_str}")
            if dimensions_str:
                depth_cm, width_cm, height_cm = self._parse_dimensions(dimensions_str)
                if depth_cm:
                    self.product_data.add_detail("depth_cm", str(depth_cm))
                if width_cm:
                    self.product_data.add_detail("width_cm", str(width_cm))
                if height_cm:
                    self.product_data.add_detail("height_cm", str(height_cm))
    
    def _parse_dimensions(self, dimensions_str: str) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        解析尺寸字符串并转换为厘米
        
        Args:
            dimensions_str: 尺寸字符串，如 "15\"D x 22.83\"W x 24\"H"
            
        Returns:
            tuple: (depth_cm, width_cm, height_cm) 或 (None, None, None)
        """
        try:
            import re
            
            # 清理字符串，移除多余空格
            dimensions_str = dimensions_str.strip()
            print(f"🔍 解析尺寸字符串: {dimensions_str}")
            
            # 初始化结果
            depth_cm = None
            width_cm = None
            height_cm = None
            
            # 正则表达式匹配模式：数字 + 可选小数 + 英寸符号 + 维度标识
            # 匹配如: 15"D, 22.83"W, 24"H
            dimension_pattern = r'([0-9]*\.?[0-9]+)"([DWHL])'
            matches = re.findall(dimension_pattern, dimensions_str, re.IGNORECASE)
            
            if not matches:
                # 尝试其他可能的格式
                # 格式如: "15 x 22.83 x 24 inches" 或 "D15 x W22.83 x H24"
                number_pattern = r'([0-9]*\.?[0-9]+)'
                numbers = re.findall(number_pattern, dimensions_str)
                
                if len(numbers) >= 3:
                    # 假设顺序为 D x W x H
                    try:
                        depth_cm = self._inches_to_cm(float(numbers[0]))
                        width_cm = self._inches_to_cm(float(numbers[1]))
                        height_cm = self._inches_to_cm(float(numbers[2]))
                        print(f"  ✅ 按顺序解析: D={depth_cm}cm, W={width_cm}cm, H={height_cm}cm")
                        return depth_cm, width_cm, height_cm
                    except (ValueError, IndexError):
                        pass
                        
                print(f"  ⚠️ 无法解析尺寸格式: {dimensions_str}")
                return None, None, None
            
            # 解析匹配到的尺寸
            for value_str, dimension_type in matches:
                try:
                    value_inches = float(value_str)
                    value_cm = self._inches_to_cm(value_inches)
                    
                    if dimension_type.upper() == 'D' or dimension_type.upper() == 'L':
                        depth_cm = value_cm
                        print(f"  📏 深度: {value_inches}\" = {value_cm}cm")
                    elif dimension_type.upper() == 'W':
                        width_cm = value_cm
                        print(f"  📏 宽度: {value_inches}\" = {value_cm}cm")
                    elif dimension_type.upper() == 'H':
                        height_cm = value_cm
                        print(f"  📏 高度: {value_inches}\" = {value_cm}cm")
                        
                except ValueError as e:
                    print(f"  ❌ 解析数值失败: {value_str} - {e}")
                    continue
            
            return depth_cm, width_cm, height_cm
            
        except Exception as e:
            print(f"❌ 尺寸解析失败: {e}")
            return None, None, None
    
    def _inches_to_cm(self, inches: float) -> float:
        """
        将英寸转换为厘米
        
        Args:
            inches: 英寸值
            
        Returns:
            float: 厘米值（保留2位小数）
        """
        # 1英寸 = 2.54厘米
        cm = inches * 2.54
        return round(cm, 2)
    def _prepare_page(self) -> None:
        """准备页面 - 滚动确保内容加载"""
        try:
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
        
            self.page.wait_for_load_state("domcontentloaded")
      
            # 滚动到页面底部，然后回到顶部，确保所有内容加载
            print("滚动页面到底部显示所有元素...")
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(2000)
            self.page.wait_for_load_state("load")
            
            # 滚动回到顶部
            self.page.evaluate("window.scrollTo(0, 0)")
            self.page.wait_for_timeout(2000)
            
            # 再次滚动到中间位置，确保产品详情区域可见
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            self.page.wait_for_timeout(1000)
            
            print("页面滚动完成，准备开始解析...")
           
        except Exception as e:
            print(f"⚠️ 页面准备过程中出现警告: {e}")
    
    def _parse_title(self) -> None:
        """解析产品标题"""
        try:
            title_element = self.page.locator(self.selectors['title']).first
            self.product_data.asin = self.page.url.split('/dp/')[1].split('?')[0].replace('/','')
            self.product_data.title = title_element.inner_text()
            print(f"📝 产品标题: {self.product_data.title[:50]}...")
            self.product_data.add_detail('Title', self.product_data.title)
            self.product_data.add_detail('ASIN', self.product_data.asin)
        except Exception as e:
            self._add_error(f"标题解析失败: {e}")
    
    def _parse_price(self) -> None:
        """解析产品价格 - 支持普通页面、弹框模式和Prime Member价格模式"""
        try:
            # 首先尝试从隐藏字段获取非会员价格
            # base_price_success = self._parse_price_from_hidden_fields()
            # if base_price_success:
            #     return
            
            # 检查是否存在需要弹框获取价格信息的情况
            buybox_choices = self.page.locator("span#buybox-see-all-buying-choices")
            
            if buybox_choices.count() > 0:
                print("🔍 检测到buybox-see-all-buying-choices，尝试从弹框获取价格...")
                success = self._parse_price_from_modal()
                if success:
                    return
            
            # 标准价格解析方法
            print("🔍 使用标准方法解析价格...")
            self._parse_price_standard()
            
        except Exception as e:
            self._add_error(f"价格解析失败: {e}")
    
    def _parse_price_from_hidden_fields(self) -> bool:
        """
        从隐藏字段解析非会员价格
        优先选择非会员价格（Regular Price），避免Prime Member价格
        
        Returns:
            bool: 是否成功解析价格
        """
        try:
            print("🔍 尝试从隐藏字段获取非会员价格...")
            
            # 方法1: 从attach-base-product-price隐藏字段获取基础价格（非会员价格）
            base_price_element = self.page.locator("input#attach-base-product-price")
            if base_price_element.count() > 0:
                price_value = base_price_element.get_attribute('value')
                if price_value:
                    try:
                        self.product_data.price = float(price_value)
                        print(f"💰 从隐藏字段获取基础价格（非会员价格）: ${self.product_data.price:.2f}")
                        # 尝试获取货币符号
                        currency_element = self.page.locator("input#attach-base-product-currency-symbol")
                        if currency_element.count() > 0:
                            currency_symbol = currency_element.get_attribute('value')
                            print(f"💱 货币符号: {currency_symbol}")
                        
                        # 添加到产品详情
                        self.product_data.add_detail('Price', f"{self.product_data.price}")
                        self.product_data.add_detail('Price Source', 'Base Product Price (Non-Member)')
                        return True
                    except ValueError as e:
                        print(f"⚠️ 基础价格值转换失败: {price_value} - {e}")
            else:
                print("⚠️ 未找到隐藏字段中的价格信息")
                #方法2: 尝试从Regular Price accordion中获取非会员价格
                regular_price_success = self._parse_regular_price_from_accordion()
                if regular_price_success:
                    return True

            return False
        except Exception as e:
            print(f"⚠️ 从隐藏字段解析价格失败: {e}")
            return False
    
    def _parse_regular_price_from_accordion(self) -> bool:
        """
        从手风琴面板中解析Regular Price（非会员价格）
        
        Returns:
            bool: 是否成功解析价格
        """
        try:
            print("🔍 尝试从Regular Price手风琴面板获取非会员价格...")
            
            # 查找包含"Regular Price"的手风琴面板
            regular_price_panels = self.page.locator("div[data-a-accordion-row-name='newAccordionRow']")
            panel_count = regular_price_panels.count()
            
            for i in range(panel_count):
                try:
                    panel = regular_price_panels.nth(i)
                    
                    # 检查面板标题是否包含"Regular Price"
                    caption_element = panel.locator(".accordion-caption, [id*='Caption']")
                    if caption_element.count() > 0:
                        caption_text = caption_element.inner_text().strip()
                        if "Regular Price" in caption_text:
                            print(f"📋 找到Regular Price面板: {caption_text}")
                            
                            # 从该面板中获取价格
                            price_elements = panel.locator("span.a-offscreen")
                            price_count = price_elements.count()
                            
                            for j in range(price_count):
                                try:
                                    price_text = price_elements.nth(j).inner_text().strip()
                                    if '$' in price_text and len(price_text) < 20:
                                        clean_price = price_text.replace('$', '').strip()
                                        if clean_price and clean_price.replace('.', '').replace(',', '').isdigit():
                                            self.product_data.price = float(clean_price.replace(',', ''))
                                            print(f"💰 从Regular Price面板获取价格: ${self.product_data.price:.2f}")
                                            
                                            # 设置默认运费
                                            # self.product_data.delivery_price = 0
                                            
                                            # 添加到产品详情
                                            self.product_data.add_detail('Price', f"{self.product_data.price}")
                                            self.product_data.add_detail('Price Source', 'Regular Price (Non-Member)')
                                            
                                            return True
                                except Exception:
                                    continue
                except Exception as e:
                    print(f"  面板 {i+1} 处理失败: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"⚠️ 从Regular Price面板解析价格失败: {e}")
            return False

    def _parse_price_from_modal(self) -> bool:
        """从弹框模式解析价格信息"""
        try:
            # 点击 "See all buying options" 按钮打开弹框
            buybox_button = self.page.locator("span#buybox-see-all-buying-choices")
            if buybox_button.count() > 0:
                buybox_button.click()
                print("✅ 点击了buybox按钮，等待弹框加载...")
                
                # 等待弹框内容加载
                self.page.wait_for_timeout(2000)
                
                # 方法1: 尝试从弹框中的 aok-offscreen 获取价格
                modal_price_elements = self.page.locator("span.aok-offscreen")
                modal_price_count = modal_price_elements.count()
                
                price_found = False
                for i in range(modal_price_count):
                    try:
                        price_text = modal_price_elements.nth(i).inner_text().strip()
                        if '$' in price_text and len(price_text) < 20:  # 价格文本通常较短
                            clean_price = price_text.replace('$', '').strip()
                            if clean_price and clean_price.replace('.', '').replace(',', '').isdigit():
                                self.product_data.price = float(clean_price.replace(',', ''))
                                print(f"💰 从弹框获取产品价格: ${self.product_data.price:.2f}")
                                price_found = True
                                break
                    except Exception as inner_e:
                        continue
                
                if not price_found:
                    print("⚠️ 未能从aok-offscreen获取价格，尝试其他选择器...")
                    # 方法2: 尝试其他价格选择器
                    alt_price_selectors = [
                        "span.a-price-whole",
                        "span[id*='aod-price'] span.a-price-whole",
                        "div[id*='aod-offer-price'] span.a-price-whole"
                    ]
                    
                    for selector in alt_price_selectors:
                        try:
                            price_element = self.page.locator(selector).first
                            if price_element.count() > 0:
                                whole_price = price_element.inner_text().strip()
                                # 尝试获取小数部分
                                fraction_element = price_element.locator("..//span[contains(@class, 'a-price-fraction')]").first
                                if fraction_element.count() > 0:
                                    fraction = fraction_element.inner_text().strip()
                                    full_price = f"{whole_price}.{fraction}"
                                else:
                                    full_price = whole_price
                                
                                self.product_data.price = float(full_price.replace(',', ''))
                                print(f"💰 从弹框备用方法获取产品价格: ${self.product_data.price:.2f}")
                                price_found = True
                                break
                        except Exception:
                            continue
                
                # 解析运费信息
                try:
                    delivery_elements = self.page.locator("span[data-csa-c-delivery-price]")
                    if delivery_elements.count() > 0:
                        delivery_price_str = delivery_elements.first.get_attribute('data-csa-c-delivery-price')
                        self.product_data.delivery_price = 0
                        if delivery_price_str and delivery_price_str != 'FREE':
                            self.product_data.delivery_price = float(delivery_price_str.replace('$', ''))
                        print(f"🚚 从弹框获取运费价格: ${self.product_data.delivery_price:.2f}")
                except Exception as delivery_e:
                    print(f"⚠️ 弹框运费解析失败: {delivery_e}")
                    self.product_data.delivery_price = 0
                
                # 关闭弹框（如果有关闭按钮）
                try:
                    close_button = self.page.locator("button[aria-label*='Close'], button.a-button-close, [data-action*='close']")
                    if close_button.count() > 0:
                        close_button.first.click()
                        print("✅ 关闭了价格弹框")
                except Exception:
                    # 按Escape键关闭弹框
                    self.page.keyboard.press('Escape')
                
                if price_found:
                    self.product_data.add_detail('Price', f"{self.product_data.price}")
                    self.product_data.add_detail('Delivery Price', f"{self.product_data.delivery_price}")
                    return True
                
            return False
            
        except Exception as e:
            print(f"⚠️ 弹框价格解析失败: {e}")
            return False
    
    def _parse_price_standard(self) -> None:
        """标准价格解析方法 - 优先选择非会员价格"""
        try:
            # 尝试隐藏字段域获取价格
            self._parse_price_from_hidden_fields()   
            # 解析运费
            delivery_price_str = self.page.locator("span[data-csa-c-delivery-type='delivery']").last.get_attribute('data-csa-c-delivery-price')
            self.product_data.delivery_price = 0
            if delivery_price_str=='fastest':
                delivery_price_str = self.page.locator("span[data-csa-c-delivery-type='delivery']").first.get_attribute('data-csa-c-delivery-price')
            if delivery_price_str != 'FREE':
                self.product_data.delivery_price = float((delivery_price_str or '0').replace('$', ''))
            if self.product_data.price==0:
                self._parse_price_fallback()
            print(f"💰 产品价格: ${self.product_data.price:.2f}")
            print(f"🚚 运费价格: ${self.product_data.delivery_price:.2f}")
            self.product_data.add_detail('Price', f"{self.product_data.price}")
            self.product_data.add_detail('Delivery Price', f"{self.product_data.delivery_price}")
            self.product_data.add_detail('Price Source', 'Standard Core Price')
            
        except Exception as e:
            print(f"⚠️ 标准价格解析失败: {e}")
            # 尝试备用价格选择器
            self._parse_price_fallback()
    
    def _try_parse_non_member_price(self) -> bool:
        """
        尝试解析非会员价格（Regular Price）从价格区域
        
        Returns:
            bool: 是否成功找到非会员价格
        """
        try:
            print("🔍 尝试找到非会员价格区域...")
            
            # 查找包含"Regular Price"标题的元素
            regular_price_headers = self.page.locator("*:has-text('Regular Price')")
            header_count = regular_price_headers.count()
            
            for i in range(header_count):
                try:
                    header = regular_price_headers.nth(i)
                    # 查找该标题附近的价格元素
                    nearby_prices = header.locator("..").locator("span.a-offscreen, span.a-price-whole")
                    
                    price_count = nearby_prices.count()
                    for j in range(price_count):
                        try:
                            price_element = nearby_prices.nth(j)
                            element_class = price_element.get_attribute('class')
                            if element_class == 'a-offscreen':
                                # 从 a-offscreen 获取完整价格
                                price_text = price_element.inner_text().strip()
                                if '$' in price_text:
                                    clean_price = price_text.replace('$', '').strip()
                                    if clean_price and clean_price.replace('.', '').replace(',', '').isdigit():
                                        self.product_data.price = float(clean_price.replace(',', ''))
                                        print(f"💰 从 Regular Price 区域获取价格: ${self.product_data.price:.2f}")
                                
                                        
                                        # 添加到产品详情
                                        self.product_data.add_detail('Price', f"{self.product_data.price}")
                                        self.product_data.add_detail('Price Source', 'Regular Price Section')
                                        
                                        return True
                            elif element_class and 'a-price-whole' in element_class:
                                # 从 a-price-whole 和 a-price-fraction 组合获取价格
                                whole_price = price_element.inner_text().strip()
                                fraction_element = price_element.locator("../span[contains(@class, 'a-price-fraction')]")
                                
                                if fraction_element.count() > 0:
                                    fraction = fraction_element.inner_text().strip()
                                    full_price = f"{whole_price}.{fraction}"
                                else:
                                    full_price = whole_price
                                
                                if full_price.replace('.', '').replace(',', '').isdigit():
                                    self.product_data.price = float(full_price.replace(',', ''))
                                    print(f"💰 从 Regular Price 区域获取价格: ${self.product_data.price:.2f}")
                                    
                                    # 设置默认运费
                                    # self.product_data.delivery_price = 0
                                    
                                    # 添加到产品详情
                                    self.product_data.add_detail('Price', f"{self.product_data.price}")
                                    self.product_data.add_detail('Delivery Price', f"{self.product_data.delivery_price}")
                                    self.product_data.add_detail('Price Source', 'Regular Price Section')
                                    
                                    return True
                        except Exception:
                            continue
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            print(f"⚠️ 解析非会员价格失败: {e}")
            return False
    
    def _parse_price_fallback(self) -> None:
        """备用价格解析方法"""
        fallback_selectors = [
            "span.a-price.a-text-price.a-size-medium span.a-offscreen",
            "span.a-price span.a-offscreen",
            "span[data-a-color='price'] span.a-offscreen",
            "div.a-price span.a-offscreen"
        ]
        
        for selector in fallback_selectors:
            try:
                price_element = self.page.locator(selector).first
                if price_element.count() > 0:
                    price_str = price_element.inner_text()
                    self.product_data.price = float(price_str.replace('$', ''))
                    print(f"💰 备用方法获取价格: ${self.product_data.price:.2f}")
                    
                    self.product_data.add_detail('Price', f"{self.product_data.price}")
                    return
            except Exception:
                continue
        
        print("❌ 所有价格解析方法都失败了")
    
    
    def _parse_colors(self) -> None:
        """
        解析产品颜色 - 从Amazon产品变体选择器中获取颜色信息
        
        Good Taste: 多策略提取颜色信息，优先获取当前选中的颜色，同时收集所有可用颜色选项
        """
        try:
            # 策略1: 获取当前选中的颜色（从展开的维度文本中）
            selected_color = self._get_selected_color()
            
            # 策略2: 获取所有可用的颜色选项
            available_colors: List[str] = self._get_available_colors()
            
            # 设置颜色信息
            if selected_color:
                self.product_data.add_detail('Selected Color', str(selected_color))
                print(f"✅ 当前选中颜色: {selected_color}")
            
            if available_colors:
                self.product_data.add_detail('Available Colors', ', '.join(available_colors))
                print(f"✅ 可用颜色选项: {', '.join(available_colors)}")
            
            # # 如果没有找到任何颜色信息，尝试从产品详情中获取
            # if not selected_color and not available_colors:
            #     self._get_color_from_details()
                
        except Exception as e:
            print(f"⚠️ 颜色解析失败: {e}")
            # 设置默认值
            if 'Color' not in self.product_data.details:
                self.product_data.add_detail('Color', 'Not specified')
    
    def _get_selected_color(self) -> Optional[object]:
        """获取当前选中的颜色"""
        try:
            # 多种选择器策略获取选中的颜色
            selectors = [
                # 策略1: 从展开的维度文本中获取
                "#inline-twister-expanded-dimension-text-color_name",
                # 策略2: 从颜色标题区域获取
                ".inline-twister-dim-title-value",
                # 策略3: 从选中的按钮获取
                ".a-button-selected img[alt*='pack']",
                # 策略4: 更通用的选中颜色选择器
                "[id*='color_name'][class*='selected'] img"
            ]
            
            for selector in selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.count() > 0:
                        if 'img' in selector:
                            # 从图片的alt属性获取颜色
                            alt_text = element.get_attribute('alt')
                            color_text = alt_text
                        else:
                            # 从文本内容获取颜色
                            color_text = element.inner_text().strip()
                        
                        if color_text:
                            return color_text
                            # # 清理和标准化颜色文本
                            # cleaned_color = self._clean_color_text(color_text)
                            # if cleaned_color:
                            #     print(f"  ✅ 使用选择器 {selector[:30]}... 获取到颜色: {cleaned_color}")
                            #     return cleaned_color
                except Exception as e:
                    print(f"  选择器 {selector[:30]}... 失败: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"获取选中颜色失败: {e}")
            return None
    
    def _get_available_colors(self) -> List[str]:
        """获取所有可用的颜色选项"""
        colors = []
        try:
            # 查找所有颜色选项的图片元素
            color_images = self.page.locator("#inline-twister-row-color_name li img.swatch-image")
            count = color_images.count()
            
            print(f"  🎨 找到 {count} 个颜色选项")
            
            for i in range(count):
                try:
                    img = color_images.nth(i)
                    alt_text = img.get_attribute('alt')
                    
                    if alt_text:
                        colors.append(alt_text)
                        # cleaned_color = self._clean_color_text(alt_text)
                        # if cleaned_color and cleaned_color not in colors:
                        #     colors.append(cleaned_color)
                        #     print(f"    ✅ 颜色选项 {i+1}: {cleaned_color}")
                            
                except Exception as e:
                    print(f"    ❌ 颜色选项 {i+1} 处理失败: {e}")
                    continue
            
            return colors
            
        except Exception as e:
            print(f"获取可用颜色失败: {e}")
            return []
    
    def _clean_color_text(self, color_text: str) -> Optional[str]:
        """清理和标准化颜色文本"""
        if not color_text:
            return None
        
        # 移除常见的前缀和后缀
        cleaned = color_text.strip()
        
        # 移除包装数量信息（如 "1-pack", "2-pack"）
        import re
        cleaned = re.sub(r'^\d+-pack\s+', '', cleaned, flags=re.IGNORECASE)
        
        # 移除其他常见前缀
        prefixes_to_remove = ['color:', 'colour:', 'selected color is']
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # 移除末尾的标点符号
        cleaned = re.sub(r'[.。]+$', '', cleaned)
        
        # 如果清理后为空或太短，返回None
        if len(cleaned.strip()) < 2:
            return None
            
        return cleaned.strip()
    
    def _get_color_from_details(self) -> None:
        """从产品详情中获取颜色信息（备用方案）"""
        try:
            # 检查是否已经从产品详情表格中获取了颜色信息
            color_keys = ['Color', 'Colour', 'Item Color', 'Product Color']
            
            for key in color_keys:
                if key in self.product_data.details:
                    color_value = self.product_data.details[key]
                    print(f"  ✅ 从产品详情获取颜色: {color_value}")
                    return
            
            # 如果没有找到，设置默认值
            self.product_data.add_detail('Color', 'Not specified')
            print("  ⚠️ 未找到颜色信息，使用默认值")
            
        except Exception as e:
            print(f"从产品详情获取颜色失败: {e}")
    
    def _parse_item_package_quantity(self) -> None:
        """
        解析产品包装数量 - 从Amazon产品变体选择器中获取包装数量信息
        
        Good Taste: 多策略提取包装数量信息，优先获取当前选中的数量，同时收集所有可用选项
        """
        try:
            # 策略1: 获取当前选中的包装数量（从展开的维度文本中）
            selected_quantity = self._get_selected_package_quantity()
            
            # 策略2: 获取所有可用的包装数量选项
            available_quantities = self._get_available_package_quantities()
            
            # 设置包装数量信息
            if selected_quantity:
                self.product_data.add_detail('Selected Package Quantity', str(selected_quantity))
                print(f"✅ 当前选中包装数量: {selected_quantity}")
            
            if available_quantities:
                quantities_str = ', '.join(map(str, available_quantities))
                self.product_data.add_detail('Available Package Quantities', quantities_str)
                print(f"✅ 可用包装数量选项: {quantities_str}")
            
            # # 如果没有找到任何包装数量信息，尝试从产品详情中获取
            # if not selected_quantity and not available_quantities:
            #     self._get_package_quantity_from_details()
                
        except Exception as e:
            print(f"⚠️ 包装数量解析失败: {e}")
            # 设置默认值
            if 'Package Quantity' not in self.product_data.details:
                self.product_data.add_detail('Package Quantity', '1')
    
    def _get_selected_package_quantity(self) -> Optional[str]:
        """获取当前选中的包装数量"""
        try:
            # 多种选择器策略获取选中的包装数量
            selectors = [
                # 策略1: 从展开的维度文本中获取
                "#inline-twister-expanded-dimension-text-item_package_quantity",
                # 策略2: 从包装数量标题区域获取
                "#inline-twister-dim-title-item_package_quantity .inline-twister-dim-title-value",
                # 策略3: 从选中的按钮获取
                ".a-button-selected .swatch-title-text-display",
                # 策略4: 更通用的选中数量选择器
                "[id*='item_package_quantity'][class*='selected'] .swatch-title-text"
            ]
            
            for selector in selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.count() > 0:
                        quantity_text = element.inner_text().strip()
                        
                        if quantity_text:
                            # 清理和标准化数量文本
                            cleaned_quantity = self._clean_quantity_text(quantity_text)
                            if cleaned_quantity:
                                print(f"  ✅ 使用选择器 {selector[:40]}... 获取到数量: {cleaned_quantity}")
                                return cleaned_quantity
                except Exception as e:
                    print(f"  选择器 {selector[:40]}... 失败: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"获取选中包装数量失败: {e}")
            return None
    
    def _get_available_package_quantities(self) -> List[str]:
        """获取所有可用的包装数量选项"""
        quantities = []
        try:
            # 查找所有包装数量选项的文本元素
            quantity_elements = self.page.locator("#inline-twister-row-item_package_quantity .swatch-title-text-display")
            count = quantity_elements.count()
            
            print(f"  📦 找到 {count} 个包装数量选项")
            
            for i in range(count):
                try:
                    element = quantity_elements.nth(i)
                    quantity_text = element.inner_text().strip()
                    
                    if quantity_text:
                        cleaned_quantity = self._clean_quantity_text(quantity_text)
                        if cleaned_quantity and cleaned_quantity not in quantities:
                            quantities.append(cleaned_quantity)
                            print(f"    ✅ 数量选项 {i+1}: {cleaned_quantity}")
                            
                except Exception as e:
                    print(f"    ❌ 数量选项 {i+1} 处理失败: {e}")
                    continue
            
            return quantities
            
        except Exception as e:
            print(f"获取可用包装数量失败: {e}")
            return []
    
    def _clean_quantity_text(self, quantity_text: str) -> Optional[str]:
        """清理和标准化数量文本"""
        if not quantity_text:
            return None
        
        # 移除常见的前缀和后缀
        cleaned = quantity_text.strip()
        
        # 移除常见前缀
        import re
        prefixes_to_remove = ['item package quantity:', 'package quantity:', 'quantity:']
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # 提取数字
        number_match = re.search(r'(\d+)', cleaned)
        if number_match:
            return number_match.group(1)
        
        # 如果没有数字，返回原文本（去除空格）
        if len(cleaned.strip()) >= 1:
            return cleaned.strip()
            
        return None
    
    def _get_package_quantity_from_details(self) -> None:
        """从产品详情中获取包装数量信息（备用方案）"""
        try:
            # 检查是否已经从产品详情表格中获取了包装数量信息
            quantity_keys = ['Package Quantity', 'Item Package Quantity', 'Quantity', 'Pack Size']
            
            for key in quantity_keys:
                if key in self.product_data.details:
                    quantity_value = self.product_data.details[key]
                    print(f"  ✅ 从产品详情获取包装数量: {quantity_value}")
                    return
            
            # 如果没有找到，设置默认值
            self.product_data.add_detail('Package Quantity', '1')
            print("  ⚠️ 未找到包装数量信息，使用默认值: 1")
            
        except Exception as e:
            print(f"从产品详情获取包装数量失败: {e}")
    
    def _parse_specifications(self) -> None:
        """
        解析产品规格数据 - 通过inline-twister-expanded-dimension-text-前缀直接获取所有选中规格
        
        Good Taste: 简化方法，直接获取所有已选中的规格值
        """
        specifications_summary = []
        try:
            print("🔍 开始解析产品规格数据...")
            
            # 新方法：直接查找所有已选中的规格值
            expanded_specs = self.page.locator("span[id^='inline-twister-expanded-dimension-text-']")
            spec_count = expanded_specs.count()
            
            if spec_count == 0:
                print("⚠️ 未找到任何已选中的规格，跳过规格解析")
                return
            
            print(f"📊 找到 {spec_count} 个已选中的规格")
            
            # 遍历每个已选中的规格
            for i in range(spec_count):
                try:
                    spec_element = expanded_specs.nth(i)
                    spec_id = spec_element.get_attribute('id')
                    spec_value = spec_element.inner_text().strip()
                    
                    if not spec_id or not spec_value:
                        continue
                    
                    # 从ID中提取维度名称 (inline-twister-expanded-dimension-text-style_name -> style_name)
                    dimension_name = spec_id.replace('inline-twister-expanded-dimension-text-', '')
                    display_name = self._format_dimension_name(dimension_name)
                    
                    print(f"  🔍 发现规格: {display_name} = {spec_value} (ID: {spec_id})")
                    
                    # 获取该规格的所有可用选项
                    available_options = self._get_specification_options_by_dimension(dimension_name)
                    
                    # 构建规格信息
                    spec_info = {
                        'dimension_name': dimension_name,
                        'display_name': display_name,
                        'selected_value': spec_value,
                        'available_options': available_options,
                        'options_count': len(available_options)
                    }
                    
                    specifications_summary.append(spec_info)
                    self._add_specification_to_product_data(spec_info)
                    print(f"    ✅ 成功解析规格: {display_name} = {spec_value}, 共 {len(available_options)} 个选项")
                    
                except Exception as e:
                    print(f"    ❌ 规格 {i + 1} 解析失败: {e}")
                    continue
            
            # 添加规格概要
            if specifications_summary:
                self._add_specifications_summary(specifications_summary)
                print(f"✅ 规格数据解析完成，共处理 {len(specifications_summary)} 个规格维度")
            else:
                print("⚠️ 未成功解析任何规格数据")
                
        except Exception as e:
            print(f"⚠️ 规格数据解析失败: {e}")
    
    def _get_specification_options_by_dimension(self, dimension_name: str) -> List[str]:
        """
        根据维度名称获取所有可用选项
        
        Args:
            dimension_name: 维度名称，如 'style_name', 'pattern_name'
            
        Returns:
            List[str]: 可用选项列表
        """
        options = []
        try:
            # 查找对应的inline-twister-row元素
            row_selector = f"#inline-twister-row-{dimension_name}"
            row_element = self.page.locator(row_selector)
            
            if row_element.count() > 0:
                # 使用原有的方法获取选项
                options = self._get_available_specification_options(row_element.first, dimension_name)
            else:
                print(f"    ⚠️ 未找到维度 {dimension_name} 的容器元素")
            
            return options
            
        except Exception as e:
            print(f"    ❌ 获取维度 {dimension_name} 选项失败: {e}")
            return []
    
    def _parse_single_specification(self, row_element, row_index: int) -> Optional[Dict[str, Any]]:
        """
        解析单个规格维度
        
        Args:
            row_element: 规格行元素
            row_index: 行索引
            
        Returns:
            规格信息字典或None
        """
        try:
            # 获取规格维度ID和名称
            row_id = row_element.get_attribute('id')
            if not row_id:
                return None
            
            # 从 ID 中提取维度名称 (inline-twister-row-color_name -> color_name)
            dimension_name = row_id.replace('inline-twister-row-', '')
            
            print(f"  🔍 处理规格维度 {row_index}: {dimension_name}")
            
            # 获取当前选中的值
            selected_value = self._get_selected_specification_value(row_element, dimension_name)
            
            # 获取所有可用选项
            available_options = self._get_available_specification_options(row_element, dimension_name)
            
            # 构建规格信息
            spec_info = {
                'dimension_name': dimension_name,
                'display_name': self._format_dimension_name(dimension_name),
                'selected_value': selected_value,
                'available_options': available_options,
                'options_count': len(available_options)
            }
            
            print(f"    ✅ 规格 '{spec_info['display_name']}': 当前选中 '{selected_value}', 共 {len(available_options)} 个选项")
            
            return spec_info
            
        except Exception as e:
            print(f"    ❌ 规格维度 {row_index} 解析失败: {e}")
            return None
    
    def _get_selected_specification_value(self, row_element, dimension_name: str) -> Optional[str]:
        """获取当前选中的规格值"""
        try:
            # 策略1: 从展开的维度文本中获取
            expanded_text_selector = f"#inline-twister-expanded-dimension-text-{dimension_name}"
            expanded_element = row_element.locator(expanded_text_selector)
            
            if expanded_element.count() > 0 and expanded_element.is_visible():
                selected_text = expanded_element.inner_text().strip()
                if selected_text:
                    return selected_text
            
            # 策略2: 从选中的按钮获取 (新增radio button支持)
            selected_button = row_element.locator(".a-button-selected")
            if selected_button.count() > 0:
                # 尝试从 alt 属性获取（适用于图片型选项）
                img_element = selected_button.locator("img")
                if img_element.count() > 0:
                    alt_text = img_element.get_attribute('alt')
                    if alt_text:
                        return alt_text
                
                # 尝试从文本内容获取
                button_text = selected_button.inner_text().strip()
                if button_text and len(button_text) < 100:  # 过滤过长的文本
                    return button_text
            
            # 策略3: 新增 - 从选中的radio button获取 (Pattern Name等格式)
            selected_radio = row_element.locator("input[role='radio'][aria-checked='true']")
            if selected_radio.count() > 0:
                # 获取对应的按钮容器
                radio_button = selected_radio.locator("..").locator("..")
                if radio_button.count() > 0:
                    # 尝试从图片alt属性获取
                    img_element = radio_button.locator("img")
                    if img_element.count() > 0:
                        alt_text = img_element.get_attribute('alt')
                        if alt_text:
                            print(f"      🎯 从radio button获取选中值: {alt_text}")
                            return alt_text
                    
                    # 尝试从文本内容获取
                    button_text = radio_button.inner_text().strip()
                    # 只取第一行简短文本，避免包含价格信息
                    lines = button_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not '$' in line and len(line) < 50:
                            print(f"      🎯 从radio button文本获取选中值: {line}")
                            return line
            
            return None
            
        except Exception as e:
            print(f"      获取选中值失败: {e}")
            return None
    
    def _get_available_specification_options(self, row_element, dimension_name: str) -> List[str]:
        """获取所有可用的规格选项"""
        options = []
        try:
            # 查找所有的选项元素
            option_selectors = [
                # 策略1: radio button + 图片样式 (Pattern Name等格式)
                "ul.dimension-values-list li[data-asin]",
                # 策略2: 图片型选项
                "ul.dimension-values-list li img.swatch-image",
                # 策略3: 文本型选项
                "ul.dimension-values-list li .a-button",
                # 策略4: 更广泛的选项选择器
                "ul.dimension-values-list li"
            ]
            
            for selector in option_selectors:
                try:
                    option_elements = row_element.locator(selector)
                    count = option_elements.count()
                    
                    if count > 0:
                        print(f"      使用选择器 '{selector}' 找到 {count} 个选项")
                        
                        for i in range(count):
                            try:
                                element = option_elements.nth(i)
                                option_value = None
                                
                                # 根据选择器类型提取值
                                if "li[data-asin]" in selector:
                                    # 新增: 处理radio button + 图片样式
                                    img = element.locator("img")
                                    if img.count() > 0:
                                        alt_text = img.get_attribute('alt')
                                        if alt_text:
                                            option_value = alt_text
                                            print(f"        🖼️ 从数据元素获取图片选项: {alt_text}")
                                    
                                    # 如果没有图片，尝试从按钮文本获取
                                    if not option_value:
                                        button = element.locator(".a-button .a-button-text")
                                        if button.count() > 0:
                                            button_text = button.inner_text().strip()
                                            # 只取第一行简短文本
                                            lines = button_text.split('\n')
                                            for line in lines:
                                                line = line.strip()
                                                if line and not '$' in line and len(line) < 50:
                                                    option_value = line
                                                    print(f"        🏷️ 从数据元素获取按钮选项: {line}")
                                                    break
                                                    
                                elif "img.swatch-image" in selector:
                                    # 支持纯文本显示的规格选项
                                    alt_text = element.get_attribute('alt')
                                    if alt_text:
                                        option_value = alt_text
                                        # 检查是否是纯文本规格（如 "Single", "2-pack", "3-pack"）
                                        if self._is_text_only_specification(alt_text):
                                            print(f"        🔤 检测到文本规格: {alt_text}")
                                elif ".a-button" in selector:
                                    # 从按钮内部的img或文本获取
                                    img = element.locator("img")
                                    if img.count() > 0:
                                        alt_text = img.get_attribute('alt')
                                        if alt_text:
                                            option_value = alt_text
                                            # 检查是否是纯文本规格
                                            if self._is_text_only_specification(alt_text):
                                                print(f"        🔤 检测到按钮文本规格: {alt_text}")
                                    else:
                                        button_text = element.inner_text().strip()
                                        # 过滤掉价格信息和过长的文本
                                        lines = button_text.split('\n')
                                        for line in lines:
                                            line = line.strip()
                                            if line and not '$' in line and len(line) < 50:
                                                option_value = line
                                                break
                                else:
                                    # 通用处理
                                    data_asin = element.get_attribute('data-asin')
                                    if data_asin:
                                        # 尝试从子元素获取值
                                        img = element.locator("img")
                                        if img.count() > 0:
                                            alt_text = img.get_attribute('alt')
                                            if alt_text:
                                                option_value = alt_text
                                                # 检查是否是纯文本规格
                                                if self._is_text_only_specification(alt_text):
                                                    print(f"        🔤 检测到通用文本规格: {alt_text}")
                                
                                if option_value and option_value not in options:
                                    options.append(option_value)
                                    print(f"        ✅ 选项 {len(options)}: {option_value}")
                                    
                            except Exception as e:
                                print(f"        ❌ 选项 {i+1} 处理失败: {e}")
                                continue
                        
                        # 如果找到了选项，停止尝试其他选择器
                        if options:
                            break
                            
                except Exception as e:
                    print(f"      选择器 '{selector}' 处理失败: {e}")
                    continue
            
            # 新增：如果没有找到任何选项，尝试从纯文本规格中提取
            if not options:
                text_only_options = self._extract_text_only_specifications(row_element, dimension_name)
                if text_only_options:
                    options.extend(text_only_options)
                    print(f"      🔤 从文本规格中提取到 {len(text_only_options)} 个选项")
            
            return options
            
        except Exception as e:
            print(f"      获取可用选项失败: {e}")
            return []
    
    def _is_text_only_specification(self, text: str) -> bool:
        """
        判断是否是纯文本规格（不可选择的文本显示）
        
        Args:
            text: 规格文本
            
        Returns:
            bool: 是否为纯文本规格
        """
        if not text:
            return False
            
        text_lower = text.lower().strip()
        
        # 常见的文本规格模式
        text_patterns = [
            # 数量相关
            r'^\d+-pack$',  # 1-pack, 2-pack, 3-pack
            r'^\d+\s*pack$',  # 1 pack, 2 pack
            r'^single$',  # single
            r'^pack\s*of\s*\d+$',  # pack of 2, pack of 3
            
            # 尺寸相关
            r'^\d+(\.\d+)?\s*(inch|inches|cm|mm|ft|feet)$',  # 12 inch, 5.5 cm
            r'^\d+(\.\d+)?"$',  # 12", 5.5"
            r'^\d+x\d+$',  # 12x18
            
            # 样式相关
            r'^(small|medium|large|xl|xxl)$',  # 尺寸
            r'^(round|square|rectangular|oval)$',  # 形状
            r'^(set|individual|pair)$',  # 组合方式
            
            # 新增: Pattern Name相关的文本规格模式
            r'^(solid|striped|floral|geometric|abstract)$',  # 图案类型
            r'^(storage|decorative|functional)$',  # 功能类型
            r'^[a-z]+\s*(style|pattern|design)$',  # 如 "storage style", "floral pattern"
            r'^[a-z]+(-[a-z]+)*$',  # 连字符分隔的单词，如 "solid-color", "multi-pattern"
        ]
        
        import re
        for pattern in text_patterns:
            if re.match(pattern, text_lower):
                return True
                
        return False
    
    def _extract_text_only_specifications(self, row_element, dimension_name: str) -> List[str]:
        """
        从纯文本规格区域提取选项（当没有可选按钮时）
        
        Args:
            row_element: 规格行元素
            dimension_name: 维度名称
            
        Returns:
            List[str]: 提取到的文本选项列表
        """
        options = []
        try:
            print(f"      🔍 尝试提取文本规格选项: {dimension_name}")
            
            # 策略1: 从展开内容区域的aria-label获取选项数量信息
            expander_content = row_element.locator(f"#inline-twister-expander-content-{dimension_name}")
            if expander_content.count() > 0:
                total_variations = expander_content.get_attribute('data-totalvariationcount')
                if total_variations:
                    print(f"        📊 检测到 {total_variations} 个变体选项")
            
            # 策略2: 从当前选中的文本获取至少一个选项
            selected_text_element = row_element.locator(f"#inline-twister-expanded-dimension-text-{dimension_name}")
            if selected_text_element.count() > 0 and selected_text_element.is_visible():
                selected_text = selected_text_element.inner_text().strip()
                if selected_text and selected_text not in options:
                    options.append(selected_text)
                    print(f"        ✅ 当前选中文本: {selected_text}")
            
            # 策略3: 新增 - 专门处理radio button + image swatch结构
            radio_button_selectors = [
                "li[data-asin] input[role='radio']",  # radio button元素
                "li.inline-twister-swatch input[role='radio']",  # 带有inline-twister-swatch类的radio
                "ul[role='radiogroup'] li[data-asin]",  # radiogroup中的li元素
            ]
            
            for selector in radio_button_selectors:
                try:
                    radio_elements = row_element.locator(selector)
                    count = radio_elements.count()
                    
                    if count > 0:
                        print(f"        🎯 使用radio选择器 '{selector}' 找到 {count} 个元素")
                        
                        for i in range(count):
                            try:
                                radio_element = radio_elements.nth(i)
                                # 获取对应的li容器
                                li_container = radio_element.locator("../..")
                                if li_container.count() > 0:
                                    # 尝试从li容器中的img获取alt文本
                                    img_element = li_container.locator("img")
                                    if img_element.count() > 0:
                                        alt_text = img_element.get_attribute('alt')
                                        if alt_text and alt_text.strip() and alt_text not in options:
                                            cleaned_text = alt_text.strip()
                                            if len(cleaned_text) > 0 and len(cleaned_text) < 50:
                                                options.append(cleaned_text)
                                                print(f"        ✅ Radio选项: {cleaned_text}")
                                
                            except Exception as e:
                                print(f"        ⚠️ 处理radio元素 {i+1} 失败: {e}")
                                continue
                        
                        # 如果通过radio button找到了选项，可以停止尝试其他策略
                        if len(options) >= 2:
                            break
                            
                except Exception as e:
                    print(f"        ⚠️ Radio选择器 '{selector}' 处理失败: {e}")
                    continue
            
            # 策略4: 尝试从隐藏的选项元素中提取（即使不可点击）
            hidden_options_selectors = [
                "li[data-asin] img[alt]",  # 从data-asin的li元素中的img alt获取
                "li[data-initiallyselected] img[alt]",  # 从初始选中状态的元素获取
                ".dimension-value-list-item img[alt]",  # 从维度值列表项获取
            ]
            
            for selector in hidden_options_selectors:
                try:
                    hidden_elements = row_element.locator(selector)
                    count = hidden_elements.count()
                    
                    if count > 0:
                        print(f"        🔍 使用隐藏选择器 '{selector}' 找到 {count} 个元素")
                        
                        for i in range(count):
                            try:
                                element = hidden_elements.nth(i)
                                alt_text = element.get_attribute('alt')
                                
                                if alt_text and alt_text.strip() and alt_text not in options:
                                    # 验证是否是有效的规格文本
                                    cleaned_text = alt_text.strip()
                                    if len(cleaned_text) > 0 and len(cleaned_text) < 50:  # 合理的长度
                                        options.append(cleaned_text)
                                        print(f"        ✅ 隐藏选项: {cleaned_text}")
                                        
                            except Exception as e:
                                print(f"        ⚠️ 处理隐藏元素 {i+1} 失败: {e}")
                                continue
                        
                        # 如果找到了选项，可以停止或继续查找更多
                        if len(options) >= 2:  # 找到足够的选项就停止
                            break
                            
                except Exception as e:
                    print(f"        ⚠️ 隐藏选择器 '{selector}' 处理失败: {e}")
                    continue
            
            # 策略4: 如果仍然只有一个或没有选项，尝试从ARIA标签获取提示
            if len(options) <= 1:
                aria_label_element = row_element.locator(f"#dim-values-aria-label-{dimension_name}")
                if aria_label_element.count() > 0:
                    aria_text = aria_label_element.inner_text().strip()
                    if aria_text:
                        print(f"        💬 ARIA提示: {aria_text}")
                        # 可以根据ARIA文本推断选项类型，但这里暂时不实现
            
            if options:
                print(f"      ✅ 成功提取文本规格选项: {options}")
            else:
                print(f"      ⚠️ 未能提取到文本规格选项")
                
            return options
            
        except Exception as e:
            print(f"      ❌ 提取文本规格选项失败: {e}")
            return []
    
    def _format_dimension_name(self, dimension_name: str) -> str:
        """格式化维度名称为显示名称"""
        # 将下划线替换为空格，并进行首字母大写
        formatted = dimension_name.replace('_', ' ').title()
        
        # 特殊名称映射
        name_mapping = {
            'Color Name': 'Color',
            'Size Name': 'Size', 
            'Style Name': 'Style',
            'Pattern Name': 'Pattern',
            'Item Package Quantity': 'Package Quantity'
        }
        
        return name_mapping.get(formatted, formatted)
    
    def _add_specification_to_product_data(self, spec_info: Dict[str, Any]) -> None:
        """将规格信息添加到产品数据中"""
        try:
            display_name = spec_info['display_name']
            selected_value = spec_info['selected_value']
            available_options = spec_info['available_options']
            
            # 添加当前选中的值
            if selected_value:
                self.product_data.add_detail(f'Selected {display_name}', selected_value)
            
            # 添加所有可用选项（如果有多个）
            if len(available_options) > 1:
                options_str = ', '.join(available_options)
                self.product_data.add_detail(f'Available {display_name} Options', options_str)
                self.product_data.add_detail(f'{display_name} Options Count', str(len(available_options)))
            
            # 为兼容性，也添加简单的键名
            if selected_value and display_name in ['Color', 'Size', 'Style', 'Pattern']:
                self.product_data.add_detail(display_name, selected_value)
                
        except Exception as e:
            print(f"      添加规格数据失败: {e}")
    
    def _add_specifications_summary(self, specifications_summary: List[Dict[str, Any]]) -> None:
        """添加规格概要信息"""
        try:
            # 构建规格概要
            summary_parts = []
            total_combinations = 1
            
            for spec in specifications_summary:
                display_name = spec['display_name']
                selected_value = spec['selected_value']
                options_count = spec['options_count']
                
                if selected_value:
                    summary_parts.append(f"{display_name}: {selected_value}")
                    total_combinations *= max(1, options_count)
            
            if summary_parts:
                specifications_summary_str = ' | '.join(summary_parts)
                self.product_data.add_detail('Specifications Summary', specifications_summary_str)
                
                # 添加总组合数
                if total_combinations > 1:
                    self.product_data.add_detail('Total Variations', str(total_combinations))
                
                print(f"  ✅ 规格概要: {specifications_summary_str}")
                print(f"  ✅ 总变体数: {total_combinations}")
                
        except Exception as e:
            print(f"  添加规格概要失败: {e}")
        
    def _parse_weight(self) -> None:
        """
        解析产品重量 - 合并main.py中的增强鲁棒策略
        
        Good Taste: 简单的回退机制，不过度设计
        """
        weight_value = '10'  # 默认值
        
        # 策略1: 从已提取的detail_pairs中查找重量
        if 'Item Weight' in self.product_data.details:
            try:
                weight_str = self.product_data.details['Item Weight']
                weight_match = re.search(r'([0-9.]+)', weight_str)
                if weight_match:
                    weight_value = weight_match.group(1)
                    print(f"✅ 从产品详情获取重量: {weight_value} (原值: {weight_str})")
            except Exception as e:
                print(f"解析产品详情重量失败: {e}")
        
        # 策略2: 尝试直接定位重量元素（如果上面没有找到）
        if weight_value == '10':  # 还是默认值，说明上面没找到
            weight_selectors = [
                # 策略2a: 原始选择器
                "td:has-text('Item Weight') span.a-size-base.handle-overflow",
                # 策略2b: 简化选择器
                "td:has-text('Item Weight') span",
                # 策略2c: 更宽泛的选择器
                "td:has-text('Item Weight')",
                # 策略2d: 包含weight的所有元素
                "[data-feature-name*='weight'], [id*='weight'], .weight-info",
                # 策略2e: 产品详情表格中的重量
                "#productDetails_detailBullets_sections1 span:has-text('pounds'), #productDetails_detailBullets_sections1 span:has-text('lbs')"
            ]
            
            for i, selector in enumerate(weight_selectors, 1):
                try:
                    print(f"🔍 尝试策略 {i}: {selector[:50]}...")
                    # 使用较短的超时时间
                    self.page.wait_for_selector(selector.split()[0], timeout=3000)
                    
                    elements = self.page.locator(selector)
                    count = elements.count()
                    print(f"   找到 {count} 个匹配元素")
                    
                    for j in range(count):
                        try:
                            element_text = elements.nth(j).inner_text(timeout=5000)
                            print(f"   元素 {j+1} 文本: {element_text[:50]}...")
                            
                            # 提取数字
                            weight_match = re.search(r'([0-9.]+)\s*(?:pounds?|lbs?)', element_text, re.IGNORECASE)
                            if weight_match:
                                weight_value = weight_match.group(1)
                                print(f"✅ 使用策略 {i} 获取重量: {weight_value}")
                                break
                            
                            # 如果没有单位，尝试提取任意数字
                            number_match = re.search(r'([0-9.]+)', element_text)
                            if number_match and selector == weight_selectors[0]:  # 只在精确选择器下使用
                                weight_value = number_match.group(1)
                                print(f"✅ 使用策略 {i} 获取数字: {weight_value}")
                                break
                                
                        except Exception as element_error:
                            print(f"   元素 {j+1} 处理失败: {element_error}")
                            continue
                    
                    if weight_value != '10':  # 找到了
                        break
                        
                except Exception as selector_error:
                    print(f"   策略 {i} 失败: {selector_error}")
                    continue
        
        # 设置最终重量值
        self.product_data.weight_value = weight_value
        if 'Item Weight' not in self.product_data.details:
            self.product_data.add_detail('Item Weight', f"{weight_value} pounds")
        
        print(f"🎩 最终重量值: {weight_value}")
    
    def _parse_product_details_tables(self) -> None:
        """解析产品详情表格"""
        # 解析顶部表格
        self._parse_table(self.selectors['product_table_top'], "顶部产品详情")
        
        # 解析底部表格们 - 先展开可扩展区域，再解析表格
        try:
            # 首先尝试展开所有可扩展的产品详情区域
            self._expand_product_details_sections()
            
            # 等待一下让展开动画完成
            self.page.wait_for_timeout(1000)
            
            # 检查元素是否存在
            print("🔍 检查底部表格存在性...")
            bottom_tables = self.page.locator(self.selectors['product_table_bottom'])
            count = bottom_tables.count()
            print(f"📊 找到底部表格数量: {count}")
            
            if count == 0:
                print("⚠️ 未找到任何底部表格，跳过")
                return
            
            # 智能处理：检查每个表格的可见性
            visible_count = 0
            for i in range(count):
                try:
                    table = bottom_tables.nth(i)
                    
                    # 检查这个表格是否可见
                    try:
                        # 短时间等待这个特定表格变为可见
                        table.wait_for(state="visible", timeout=3000)
                        visible_count += 1
                        print(f"✅ 表格 {i+1} 已可见，开始解析...")
                        
                        # 使用结构化方法解析这个表格
                        self._parse_single_table_structured(table, f"底部表格 {i+1}")
                        
                    except Exception as visibility_error:
                        print(f"⚠️ 表格 {i+1} 不可见或等待超时，跳过: {visibility_error}")
                        continue
                        
                except Exception as table_error:
                    print(f"⚠️ 第 {i+1} 个底部表格处理失败: {table_error}")
                    continue
            
            print(f"📋 底部表格解析完成，{visible_count}/{count} 个表格成功处理")
                    
        except Exception as e:
            print(f"⚠️ 底部产品详情获取失败: {e}")
    
    def _parse_table(self, selector: str, table_name: str) -> None:
        """解析单个表格"""
        try:
            self.page.wait_for_selector(selector, state="attached", timeout=5000)
            table_text = self.page.locator(selector).inner_text()
            self._parse_table_text(table_text)
            print(f"✅ {table_name} 解析完成")
        except Exception as e:
            print(f"⚠️ {table_name} 解析失败: {e}")
    
    def _parse_table_text(self, table_text: str) -> None:
        """解析表格文本内容"""
        lines = table_text.strip().split('\n')
        for line in lines:
            if '\t' in line:
                key, value = line.split('\t', 1)
                self.product_data.add_detail(key, value)
    
    def _expand_product_details_sections(self) -> None:
        """展开所有产品详情可扩展区域"""
        try:
            print("🔍 查找并展开产品详情区域...")
            
            # 查找所有可扩展的产品详情区域
            expander_selectors = [
                # 主要的产品详情展开器
                "a.a-expander-header[data-action='a-expander-toggle']",
                # 带有 Item details 文本的展开器
                "a.a-expander-header:has-text('Item details')",
                # 产品详情区域的展开器
                ".a-expander-container .a-expander-header",
                # 更通用的展开器选择器
                "[data-action='a-expander-toggle']"
            ]
            
            expanded_count = 0
            for selector in expander_selectors:
                try:
                    expanders = self.page.locator(selector)
                    count = expanders.count()
                    
                    if count > 0:
                        print(f"  找到 {count} 个展开器 (选择器: {selector[:40]}...)")
                        
                        for i in range(count):
                            try:
                                expander = expanders.nth(i)
                                
                                # 检查是否已经展开 - 缩短超时时间
                                try:
                                    aria_expanded = expander.get_attribute("aria-expanded", timeout=2000)  # 减少到2秒
                                    if aria_expanded == "true":
                                        print(f"    展开器 {i+1} 已经展开，跳过")
                                        continue
                                except Exception:
                                    # 如果获取属性失败，继续尝试点击
                                    pass
                                
                                # 尝试点击展开 - 缩短超时时间
                                try:
                                    if expander.is_visible(timeout=1000):  # 减少到1秒
                                        expander.click(timeout=3000)  # 减少到3秒
                                        expanded_count += 1
                                        print(f"    ✅ 展开器 {i+1} 点击成功")
                                        
                                        # 短暂等待展开动画
                                        self.page.wait_for_timeout(300)  # 减少等待时间
                                    else:
                                        print(f"    ⚠️ 展开器 {i+1} 不可见，跳过")
                                except Exception as click_error:
                                    print(f"    ⚠️ 展开器 {i+1} 点击失败(快速跳过): {str(click_error)[:50]}...")
                                    continue
                                    
                            except Exception as e:
                                print(f"    ⚠️ 展开器 {i+1} 处理失败(快速跳过): {str(e)[:50]}...")
                                continue
                except Exception as e:
                    print(f"  选择器 {selector[:40]}... 处理失败: {str(e)[:50]}...")
                    continue
            
            print(f"✅ 成功展开 {expanded_count} 个产品详情区域")
            
        except Exception as e:
            print(f"⚠️ 展开产品详情区域失败: {e}")
    
    def _parse_single_table_structured(self, table_element, table_name: str) -> None:
        """解析单个结构化表格 (th/td格式)"""
        try:
            # 查找所有的tr元素
            tr_elements = table_element.locator("tr")
            
            parsed_count = 0
            for i in range(tr_elements.count()):
                try:
                    tr = tr_elements.nth(i)
                    # 查找th和td元素
                    th_elements = tr.locator("th")
                    td_elements = tr.locator("td")
                    
                    # 确保有一个th和一个td
                    if th_elements.count() >= 1 and td_elements.count() >= 1:
                        key = th_elements.first.inner_text().strip()
                        # 对于td中的复杂内容，我们只取文本部分
                        value = td_elements.first.inner_text().strip()
                        
                        # 过滤掉空值
                        if key and value:
                            # 清理值中的多余空白字符
                            value = re.sub(r'\s+', ' ', value).strip()
                            self.product_data.add_detail(key, value)
                            parsed_count += 1
                            print(f"  ✅ {key}: {value[:50]}{'...' if len(value) > 50 else ''}")
                except Exception as e:
                    print(f"  ❌ 表格行 {i+1} 解析失败: {e}")
            
            print(f"✅ {table_name} 结构化解析完成，共提取 {parsed_count} 个属性")
        except Exception as e:
            print(f"⚠️ {table_name} 结构化解析失败: {e}")

    def _parse_glance_icons(self) -> None:
        """解析产品特征区域 (glance_icons_div)"""
        try:
            self.page.wait_for_selector(self.selectors['glance_icons'], timeout=1000)
            glance_icons = self.page.locator(self.selectors['glance_icons'])
            bold_elements = glance_icons.locator("span.a-text-bold")
            
            extracted_count = 0
            for i in range(bold_elements.count()):
                try:
                    # 获取标题
                    title_element = bold_elements.nth(i)
                    title = title_element.inner_text().strip()
                    
                    # 获取值
                    parent_td = title_element.locator("xpath=ancestor::td[1]")
                    value_spans = parent_td.locator("span.handle-overflow:not(.a-text-bold)")
                    
                    if value_spans.count() > 0:
                        value = value_spans.first.inner_text().strip()
                        self.product_data.add_detail(title, value)
                        extracted_count += 1
                        print(f"  ✅ {title}: {value}")
                
                except Exception as e:
                    print(f"  ❌ 第{i+1}个特征提取失败: {e}")
            
            print(f"✅ 从产品特征区域提取了 {extracted_count} 个属性")
            
        except Exception as e:
            print(f"⚠️ 产品特征区域解析失败: {e}")
    
    def _parse_feature_bullets(self) -> None:
        """解析产品功能描述区域"""
        try:
            self.page.wait_for_selector("#feature-bullets", timeout=3000)
            feature_bullets = self.page.locator(self.selectors['feature_bullets'])
            
            # 提取所有功能特点
            feature_descriptions = []
            for i in range(feature_bullets.count()):
                try:
                    feature_text = feature_bullets.nth(i).inner_text().strip()
                    if feature_text and len(feature_text) > 10:  # 过滤太短的文本
                        feature_descriptions.append(feature_text)
                        print(f"  ✅ 功能特点 {i+1}: {feature_text[:60]}...")
                except Exception as e:
                    print(f"  ❌ 第{i+1}个功能特点提取失败: {e}")
            
            if feature_descriptions:
                # 处理功能描述
                self._process_feature_descriptions(feature_descriptions)
                print(f"✅ 从功能描述提取了 {len(feature_descriptions)} 个特点")
            else:
                print("⚠️ 未找到任何功能特点")
                
        except Exception as e:
            print(f"⚠️ 产品功能描述解析失败: {e}")
    
    def _process_feature_descriptions(self, feature_descriptions: List[str]) -> None:
        """处理功能描述，提取关键信息"""
        # 合并所有功能特点
        combined_features = " | ".join(feature_descriptions)
        # self.product_data.add_detail('Feature Description', combined_features)
        self.product_data.add_detail('Key Features', combined_features)
        
        features_text = combined_features.lower()
        
        # 智能提取各种属性
        self._extract_material(features_text)
        self._extract_weight_capacity(features_text)
        self._extract_assembly_info(features_text)
        self._extract_style(features_text)
        self._extract_room_type(features_text)
    
    def _extract_material(self, text: str) -> None:
        """提取材质信息"""
        for material in self.keywords['materials']:
            if material in text and 'Material' not in self.product_data.details:
                self.product_data.add_detail('Material', material.capitalize())
                print(f"  ✨ 智能提取材质: {material.capitalize()}")
                break
    
    def _extract_weight_capacity(self, text: str) -> None:
        """提取承重信息"""
        weight_pattern = r'(\d+)\s*(?:lb|lbs|pound|pounds)'
        weight_matches = re.findall(weight_pattern, text)
        if weight_matches and 'Max Weight Capacity' not in self.product_data.details:
            max_weight = max([int(w) for w in weight_matches])
            self.product_data.add_detail('Max Weight Capacity', f"{max_weight} lbs")
            print(f"  ✨ 智能提取承重: {max_weight} lbs")
    
    def _extract_assembly_info(self, text: str) -> None:
        """提取组装信息"""
        if any(keyword in text for keyword in self.keywords['assembly_no_tools']):
            self.product_data.add_detail('Assembly Required', 'No')
            self.product_data.add_detail('Assembly Type', 'Tool-Free')
            print("  ✨ 智能提取组装信息: 无需工具")
        elif any(keyword in text for keyword in self.keywords['assembly_required']):
            self.product_data.add_detail('Assembly Required', 'Yes')
            print("  ✨ 智能提取组装信息: 需要组装")
    
    def _extract_style(self, text: str) -> None:
        """提取风格信息"""
        for style in self.keywords['styles']:
            if style in text and 'Style' not in self.product_data.details:
                self.product_data.add_detail('Style', style.capitalize())
                print(f"  ✨ 智能提取风格: {style.capitalize()}")
                break
    
    def _extract_room_type(self, text: str) -> None:
        """提取适用房间信息"""
        found_rooms = []
        for room in self.keywords['rooms']:
            if room in text:
                found_rooms.append(room.title())
        
        if found_rooms and 'Room Type' not in self.product_data.details:
            self.product_data.add_detail('Room Type', ', '.join(found_rooms))
            print(f"  ✨ 智能提取适用房间: {', '.join(found_rooms)}")
    
    def _add_error(self, error_msg: str) -> None:
        """添加错误信息"""
        self.product_data.parse_errors.append(error_msg)
        print(f"❌ {error_msg}")
    
    def print_summary(self) -> None:
        """打印解析结果摘要"""
        if not self.product_data.has_valid_data():
            print("❌ 未获取到任何产品数据")
            return
            
        print("\n" + "="*80)
        print("🎯 AMAZON 产品解析结果摘要")
        print("="*80)
        
        if self.product_data.title:
            print(f"📝 标题: {self.product_data.title}")
        
        if self.product_data.weight_value != '10':
            print(f"⚖️ 重量: {self.product_data.weight_value} pounds")
        
        print(f"📊 提取属性总数: {len(self.product_data.details)}")
        
        if self.product_data.details:
            print("\n📋 产品详情:")
            print("{:<30} {:<50}".format("属性", "值"))
            print("-" * 80)

            # 按key值升序排列后输出
            for key, value in sorted(self.product_data.details.items()):
                # 限制输出长度
                display_value = str(value)[:47] + "..." if len(str(value)) > 50 else str(value)
                print("{:<30} {:<50}".format(str(key)[:27], display_value))
        
        if self.product_data.parse_errors:
            print(f"\n⚠️ 解析过程中的错误 ({len(self.product_data.parse_errors)} 个):")
            for error in self.product_data.parse_errors:
                print(f"  - {error}")
        
        print("="*80)


# =======================
# 测试和示例代码
# =======================

def test_specification_pattern_matching():
    """
    测试规格模式匹配功能
    """
    print("🧪 测试规格模式匹配功能")
    print("="*40)
    
    # 创建一个模拟的解析器实例来测试方法
    from playwright.sync_api import sync_playwright
    
    class TestParser:
        def _is_text_only_specification(self, text: str) -> bool:
            """测试版本的规格判断方法"""
            if not text:
                return False
                
            text_lower = text.lower().strip()
            
            # 常见的文本规格模式
            text_patterns = [
                # 数量相关
                r'^\d+-pack$',  # 1-pack, 2-pack, 3-pack
                r'^\d+\s*pack$',  # 1 pack, 2 pack
                r'^single$',  # single
                r'^pack\s*of\s*\d+$',  # pack of 2, pack of 3
                
                # 尺寸相关
                r'^\d+(\.\d+)?\s*(inch|inches|cm|mm|ft|feet)$',  # 12 inch, 5.5 cm
                r'^\d+(\.\d+)?"$',  # 12", 5.5"
                r'^\d+x\d+$',  # 12x18
                
                # 样式相关
                r'^(small|medium|large|xl|xxl)$',  # 尺寸
                r'^(round|square|rectangular|oval)$',  # 形状
                r'^(set|individual|pair)$',  # 组合方式
                
                # 新增: Pattern Name相关的文本规格模式
                r'^(solid|striped|floral|geometric|abstract)$',  # 图案类型
                r'^(storage|decorative|functional)$',  # 功能类型
                r'^[a-z]+\s*(style|pattern|design)$',  # 如 "storage style", "floral pattern"
                r'^[a-z]+(-[a-z]+)*$',  # 连字符分隔的单词，如 "solid-color", "multi-pattern"
            ]
            
            import re
            for pattern in text_patterns:
                if re.match(pattern, text_lower):
                    return True
                    
            return False
    
    # 测试用例
    test_cases = [
        # Pattern Name相关测试
        ("Single", True, "单一样式"),
        ("Storage", True, "存储功能"),
        ("2-pack", True, "2件装"),
        ("3-Pack", True, "3件装"),
        ("Decorative", True, "装饰功能"),
        ("solid-color", True, "纯色样式"),
        
        # 其他规格测试
        ("Large", True, "大尺寸"),
        ("Round", True, "圆形"),
        ("12 inch", True, "12英寸"),
        ("15x20", True, "15x20尺寸"),
        
        # 非规格文本测试
        ("$33.70", False, "价格信息"),
        ("In Stock", False, "库存状态"),
        ("", False, "空字符串"),
        ("Very long description that should not be considered as specification", False, "过长描述"),
    ]
    
    parser = TestParser()
    passed_tests = 0
    total_tests = len(test_cases)
    
    for text, expected, description in test_cases:
        result = parser._is_text_only_specification(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{text}' -> {result} ({description})")
        
        if result == expected:
            passed_tests += 1
    
    print(f"\n📊 测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！Pattern Name规格匹配功能正常")
        return True
    else:
        print("⚠️ 部分测试失败，需要检查规格匹配逻辑")
        return False


if __name__ == "__main__":
    print("🔍 Amazon产品解析器 - 规格解析增强测试")
    print("="*60)
    print("📝 本次增强内容:")
    print("   ✅ 支持radio button + image swatch规格格式")
    print("   ✅ 增强Pattern Name等文本规格识别")
    print("   ✅ 改进当前选中值的获取逻辑")
    print("   ✅ 扩展规格选项提取策略")
    print()
    
    # 运行测试
    test_result = test_specification_pattern_matching()
    
    print("\n💡 使用说明:")
    print("   - 新的解析器可以处理您提供的Pattern Name: Storage格式")
    print("   - 支持带有data-asin和role='radio'的复杂HTML结构")
    print("   - 自动识别Single、2-pack、Storage等文本规格")
    print("   - 增强的错误处理和调试日志")
