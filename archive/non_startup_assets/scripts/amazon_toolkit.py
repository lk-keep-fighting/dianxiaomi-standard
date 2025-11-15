#!/usr/bin/env python3
"""
Amazon产品解析工具包 - 独立可复用模块

这是一个完全独立的Amazon产品信息解析工具，可以轻松在不同项目间复制使用。

特性：
- 零依赖（除了Playwright）
- 单文件实现
- 完整的产品信息解析
- 多种策略的重量和尺寸提取
- 详细的错误处理和日志

使用方法：
    from amazon_toolkit import AmazonParser
    
    parser = AmazonParser(page)
    product = parser.parse()
    print(f"产品: {product.title}")
    print(f"品牌: {product.brand}")
    print(f"重量: {product.weight}")

作者: Linus风格实现
版本: 1.0
"""

import re
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass
from playwright.sync_api import Page


@dataclass
class AmazonProduct:
    """Amazon产品数据结构"""
    title: str = ""
    brand: str = ""
    manufacturer: str = ""
    details: Dict[str, str] = None
    weight: str = "10"  # 默认重量(磅)
    dimensions: Dict[str, str] = None
    features: List[str] = None
    asin: str = ""
    
    def __post_init__(self):
        """初始化默认值"""
        if self.details is None:
            self.details = {}
        if self.dimensions is None:
            self.dimensions = {}
        if self.features is None:
            self.features = []
    
    def has_valid_data(self) -> bool:
        """检查是否有有效数据"""
        return bool(self.title or self.details)
    
    def get_detail(self, key: str, default: str = "") -> str:
        """获取详情字段"""
        return self.details.get(key, default)
    
    def get_dimension(self, dim_type: str) -> str:
        """获取尺寸信息"""
        return self.dimensions.get(dim_type, "")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'title': self.title,
            'brand': self.brand,
            'manufacturer': self.manufacturer,
            'details': self.details,
            'weight': self.weight,
            'dimensions': self.dimensions,
            'features': self.features,
            'asin': self.asin
        }


class AmazonParser:
    """
    Amazon产品解析器 - 独立工具类
    
    Good Taste实现：
    - 单一职责：只负责Amazon页面解析
    - 简单接口：一个parse()方法搞定
    - 无外部依赖：只需要Playwright的Page对象
    """
    
    def __init__(self, page: Page, debug: bool = False):
        """
        初始化解析器
        
        Args:
            page: Playwright页面对象
            debug: 是否启用调试日志
        """
        self.page = page
        self.debug = debug
        
        # 重量提取策略
        self.weight_strategies = [
            self._extract_weight_from_table,
            self._extract_weight_from_specs,
            self._extract_weight_from_features,
            self._extract_weight_from_bullets,
            self._extract_weight_from_text
        ]
    
    def parse(self) -> AmazonProduct:
        """
        解析Amazon产品页面
        
        Returns:
            AmazonProduct对象，包含所有解析的产品信息
        """
        self._log("🔍 开始解析Amazon产品页面...")
        
        product = AmazonProduct()
        
        # 基本信息提取
        product.title = self._extract_title()
        product.asin = self._extract_asin()
        
        # 详情表格解析
        product.details = self._extract_product_details()
        
        # 从详情中提取品牌信息
        product.brand, product.manufacturer = self._extract_brand_info(product.details)
        
        # 重量和尺寸提取
        product.weight = self._extract_weight_with_strategies()
        product.dimensions = self._extract_dimensions(product.details)
        
        # 特性要点提取
        product.features = self._extract_features()
        
        self._log(f"✅ 解析完成: 标题={bool(product.title)}, 详情={len(product.details)}项, 重量={product.weight}")
        
        return product
    
    def _extract_title(self) -> str:
        """提取产品标题"""
        title_selectors = [
            "#productTitle",
            "h1.a-size-large",
            ".product-title",
            "h1[data-automation-id='product-title']"
        ]
        
        for selector in title_selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible():
                    title = element.inner_text().strip()
                    if title:
                        self._log(f"📝 产品标题: {title[:60]}...")
                        return title
            except:
                continue
        
        self._log("⚠️ 未能提取产品标题")
        return ""
    
    def _extract_asin(self) -> str:
        """提取ASIN"""
        try:
            # 从URL中提取
            url = self.page.url
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
            if asin_match:
                asin = asin_match.group(1)
                self._log(f"🏷️ ASIN: {asin}")
                return asin
        except:
            pass
        
        return ""
    
    def _extract_product_details(self) -> Dict[str, str]:
        """提取产品详情表格"""
        self._log("📊 开始提取产品详情...")
        details = {}
        
        # 多种表格选择器
        table_selectors = [
            "#productDetails_detailBullets_sections1",
            "#detail-bullets",
            "#productDetails_techSpec_section_1",
            ".prodDetTable",
            "#feature-bullets",
            "#productDetails_feature_div"
        ]
        
        for selector in table_selectors:
            try:
                table = self.page.locator(selector)
                if table.count() > 0:
                    table_details = self._parse_table_content(table, selector)
                    details.update(table_details)
            except Exception as e:
                self._log(f"⚠️ 解析表格失败 {selector}: {e}")
                continue
        
        self._log(f"📊 提取到 {len(details)} 个详情项")
        return details
    
    def _parse_table_content(self, table_element, selector_name: str) -> Dict[str, str]:
        """解析具体的表格内容"""
        details = {}
        
        try:
            # 尝试标准表格行解析
            rows = table_element.locator("tr, .a-row")
            count = rows.count()
            
            if count > 0:
                self._log(f"📋 解析表格 {selector_name}, 共 {count} 行")
                
                for i in range(count):
                    try:
                        row = rows.nth(i)
                        
                        # 多种键值对结构支持
                        key_selectors = ["td:first-child", ".a-span3", ".a-text-bold", "th"]
                        value_selectors = ["td:last-child", ".a-span9", ".a-color-base", "td"]
                        
                        key_text = ""
                        value_text = ""
                        
                        # 尝试提取键
                        for key_sel in key_selectors:
                            try:
                                key_elem = row.locator(key_sel)
                                if key_elem.count() > 0:
                                    key_text = key_elem.first.inner_text().strip()
                                    if key_text:
                                        break
                            except:
                                continue
                        
                        # 尝试提取值
                        for val_sel in value_selectors:
                            try:
                                val_elem = row.locator(val_sel)
                                if val_elem.count() > 0:
                                    value_text = val_elem.first.inner_text().strip()
                                    if value_text:
                                        break
                            except:
                                continue
                        
                        # 清理和存储
                        if key_text and value_text and len(key_text) < 100:
                            key_text = self._clean_key(key_text)
                            details[key_text] = value_text
                            self._log(f"  ✓ {key_text}: {value_text[:50]}...")
                            
                    except:
                        continue
            
            # 尝试其他格式的内容
            else:
                # 处理特殊格式，如feature bullets
                if "feature" in selector_name.lower() or "bullet" in selector_name.lower():
                    bullets = table_element.locator("li, .a-list-item")
                    for i in range(bullets.count()):
                        try:
                            bullet_text = bullets.nth(i).inner_text().strip()
                            if bullet_text and not bullet_text.startswith("Make sure"):
                                details[f"Feature {i+1}"] = bullet_text[:200]  # 限制长度
                        except:
                            continue
                            
        except Exception as e:
            self._log(f"⚠️ 解析表格内容失败: {e}")
        
        return details
    
    def _clean_key(self, key: str) -> str:
        """清理键名"""
        # 移除特殊字符和多余空格
        key = key.replace('\u200e', '').replace('\u200b', '').strip()
        if key.endswith(':'):
            key = key[:-1]
        return key
    
    def _extract_brand_info(self, details: Dict[str, str]) -> tuple[str, str]:
        """从详情中提取品牌和制造商信息"""
        brand = ""
        manufacturer = ""
        
        # 品牌关键词
        brand_keys = ['Brand', 'Manufacturer', 'Made by', 'Company', 'Seller']
        
        for key, value in details.items():
            key_lower = key.lower()
            
            # 精确匹配
            if key in brand_keys:
                if not brand:
                    brand = value
                if not manufacturer:
                    manufacturer = value
            
            # 模糊匹配
            elif any(brand_key.lower() in key_lower for brand_key in brand_keys):
                if not brand:
                    brand = value
                if not manufacturer:
                    manufacturer = value
        
        self._log(f"🏷️ 品牌信息: Brand={brand}, Manufacturer={manufacturer}")
        return brand, manufacturer
    
    def _extract_weight_with_strategies(self) -> str:
        """使用多种策略提取重量"""
        self._log("⚖️ 开始多策略重量提取...")
        
        for i, strategy in enumerate(self.weight_strategies, 1):
            try:
                weight = strategy()
                if weight and weight != "10":  # 避免默认值
                    self._log(f"✅ 策略{i} 成功提取重量: {weight} lbs")
                    return weight
            except Exception as e:
                self._log(f"⚠️ 策略{i} 失败: {e}")
                continue
        
        self._log("⚠️ 所有重量提取策略失败，使用默认值")
        return "10"
    
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
                weight = self._parse_weight_value(value)
                if weight:
                    return weight
        
        return None
    
    def _extract_weight_from_specs(self) -> Optional[str]:
        """策略2: 从技术规格提取重量"""
        try:
            spec_section = self.page.locator("#productDetails_techSpec_section_1")
            if spec_section.count() > 0:
                text = spec_section.inner_text()
                return self._parse_weight_from_text(text)
        except:
            pass
        return None
    
    def _extract_weight_from_features(self) -> Optional[str]:
        """策略3: 从产品特性提取重量"""
        try:
            features = self.page.locator("#feature-bullets")
            if features.count() > 0:
                text = features.inner_text()
                return self._parse_weight_from_text(text)
        except:
            pass
        return None
    
    def _extract_weight_from_bullets(self) -> Optional[str]:
        """策略4: 从描述要点提取重量"""
        try:
            bullets = self.page.locator(".a-unordered-list .a-list-item")
            for i in range(bullets.count()):
                bullet_text = bullets.nth(i).inner_text()
                weight = self._parse_weight_from_text(bullet_text)
                if weight:
                    return weight
        except:
            pass
        return None
    
    def _extract_weight_from_text(self) -> Optional[str]:
        """策略5: 从页面全文提取重量"""
        try:
            page_text = self.page.locator("body").inner_text()
            return self._parse_weight_from_text(page_text)
        except:
            pass
        return None
    
    def _parse_weight_value(self, value: str) -> Optional[str]:
        """解析重量值"""
        weight_match = re.search(r'([0-9]+\.?[0-9]*)\s*(pounds?|lbs?|oz)', value, re.IGNORECASE)
        if weight_match:
            weight_value = weight_match.group(1)
            unit = weight_match.group(2).lower()
            
            # 转换为磅
            if 'oz' in unit:
                return str(round(float(weight_value) / 16, 2))
            return weight_value
        
        return None
    
    def _parse_weight_from_text(self, text: str) -> Optional[str]:
        """从文本中解析重量"""
        # 更严格的匹配模式
        weight_patterns = [
            r'weight[^0-9]*([0-9]+\.?[0-9]*)\s*(pounds?|lbs?)',
            r'weighs[^0-9]*([0-9]+\.?[0-9]*)\s*(pounds?|lbs?)',
            r'([0-9]+\.?[0-9]*)\s*(lbs?|pounds?)\s*weight'
        ]
        
        for pattern in weight_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for weight, unit in matches:
                    weight_val = float(weight)
                    if 0.1 <= weight_val <= 1000:  # 合理范围
                        return str(weight_val)
        
        return None
    
    def _extract_dimensions(self, details: Dict[str, str]) -> Dict[str, str]:
        """提取产品尺寸"""
        dimensions = {}
        
        dimension_keys = [
            "Product Dimensions", "Package Dimensions", "Item Dimensions",
            "Dimensions", "Size", "Length x Width x Height"
        ]
        
        for key, value in details.items():
            if any(dim_key.lower() in key.lower() for dim_key in dimension_keys):
                # 解析尺寸格式: "10 x 8 x 6 inches" 或 "10\" x 8\" x 6\""
                dim_match = re.search(r'([0-9]+\.?[0-9]*)\s*[\"x×]\s*([0-9]+\.?[0-9]*)\s*[\"x×]\s*([0-9]+\.?[0-9]*)', value)
                if dim_match:
                    dimensions['length'] = dim_match.group(1)
                    dimensions['width'] = dim_match.group(2)
                    dimensions['height'] = dim_match.group(3)
                    self._log(f"📏 提取到尺寸: {value}")
                    break
        
        return dimensions
    
    def _extract_features(self) -> List[str]:
        """提取产品特性要点"""
        features = []
        
        try:
            # 从feature bullets提取
            bullets = self.page.locator("#feature-bullets ul li")
            for i in range(bullets.count()):
                try:
                    bullet_text = bullets.nth(i).inner_text().strip()
                    if bullet_text and not bullet_text.startswith("Make sure") and len(bullet_text) > 10:
                        features.append(bullet_text[:200])  # 限制长度
                except:
                    continue
            
            self._log(f"📋 提取到 {len(features)} 个特性要点")
            
        except Exception as e:
            self._log(f"⚠️ 提取特性失败: {e}")
        
        return features[:10]  # 最多保留10个特性
    
    def _log(self, message: str):
        """调试日志"""
        if self.debug:
            print(message)


# 便捷函数
def parse_amazon_product(page: Page, debug: bool = False) -> AmazonProduct:
    """
    便捷函数：解析Amazon产品页面
    
    Args:
        page: Playwright页面对象
        debug: 是否启用调试日志
    
    Returns:
        AmazonProduct对象
    
    Usage:
        product = parse_amazon_product(page, debug=True)
        print(f"产品: {product.title}")
    """
    parser = AmazonParser(page, debug=debug)
    return parser.parse()


# 示例使用代码
if __name__ == "__main__":
    """
    使用示例
    """
    print("Amazon产品解析工具包")
    print("="*50)
    print("这是一个独立的Amazon产品解析工具，可以轻松在不同项目间复制使用。")
    print()
    print("使用方法:")
    print("1. from amazon_toolkit import AmazonParser")
    print("2. parser = AmazonParser(page, debug=True)")
    print("3. product = parser.parse()")
    print("4. print(product.title, product.brand, product.weight)")
    print()
    print("或者使用便捷函数:")
    print("product = parse_amazon_product(page, debug=True)")
