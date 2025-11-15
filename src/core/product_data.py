#!/usr/bin/env python3
"""
统一产品数据结构 - 核心通用组件

职责：
1. 定义ProductData数据结构
2. 提供字段映射引擎
3. 跨网站复用，网站无关的核心数据模型

设计原则：
- Single Source of Truth for product data
- Website-agnostic data structure
- Good Taste: Simple and clear
"""

import re
from typing import Dict, List, Optional, Any


class ProductData:
    """
    统一产品数据结构
    
    这是所有网站策略都使用的统一数据模型
    Amazon解析器产生ProductData，网站策略消费ProductData
    """
    
    def __init__(self, title: str = "", common_info: Dict[str, str] = None, details: Dict[str, str] = None, 
                 weight_value: str = "10", dimensions: Dict[str, str] = None):
        self.title = title
        self.common_info = common_info or {}
        self.details = details or {}
        self.weight_value = weight_value
        self.dimensions = dimensions or {}
    
    def has_valid_data(self) -> bool:
        """检查是否有有效的产品数据"""
        return bool(self.title or self.details or self.common_info)
    def get_common_info(self, key: str, default: str = "") -> str:
        """获取通用信息字段"""
        return self.common_info.get(key, default)
    def get_detail(self, key: str, default: str = "") -> str:
        """获取产品详情字段"""
        return self.details.get(key, default)
    
    def get_dimension(self, dim_type: str) -> str:
        """获取尺寸信息"""
        return self.dimensions.get(dim_type, "")
    def to_dic(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            **self.common_info,
            **self.details,
            "weight_value": self.weight_value,
            **self.dimensions
        }
        
        
    def __str__(self) -> str:
        return f"ProductData(title='{self.title[:30]}...', details={len(self.details)} items)"


class FieldMappingEngine:
    """
    字段映射引擎 - 网站无关的基础映射系统
    
    这是一个基础映射引擎，具体网站可以继承并扩展
    """
    
    def __init__(self):
        # 基础固定值映射（所有网站通用）
        self.base_fixed_values = {
            "Category": "Electronics",
            "Condition": "New"
        }
        
        # 基础Amazon到表单字段的映射
        self.base_amazon_to_form = {
            "Brand": "Manufacturer Name",
            "Manufacturer": "Manufacturer Name",
            "Material": "Material",
            "Color": "Color",
            "Model": "Model Number",
            "Item model number": "Model Number",
            "ASIN": "UPC"
        }
        
        # 基础复合字段配置
        self.base_compound_fields = {
            "Assembled Product Weight": {
                "type": "number_with_unit",
                "unit": "lb (磅)"
            },
            "Net Content": {
                "type": "measure_with_unit", 
                "measure": "1",
                "unit": "Each (每个)"
            }
        }
    
    def get_form_field(self, amazon_key: str) -> Optional[str]:
        """将Amazon字段映射到表单字段"""
        # 精确匹配
        if amazon_key in self.base_amazon_to_form:
            return self.base_amazon_to_form[amazon_key]
        
        # 模糊匹配制造商相关字段
        if self._is_manufacturer_field(amazon_key):
            return "Manufacturer Name"
        
        return None
    
    def _is_manufacturer_field(self, key: str) -> bool:
        """判断是否为制造商相关字段"""
        manufacturer_keywords = ['brand', 'manufacturer', 'made by', 'company']
        key_lower = key.lower()
        return any(keyword in key_lower for keyword in manufacturer_keywords)
    
    def extract_dimensions(self, product_data: ProductData) -> Dict[str, str]:
        """从产品数据中提取尺寸信息"""
        dimensions = {}
        
        # 首先尝试从已解析的dimensions获取
        if product_data.dimensions:
            dimensions.update(product_data.dimensions)
        
        # 然后尝试从details中提取
        dimension_keys = [
            "Product Dimensions", "Package Dimensions", "Item Dimensions",
            "Dimensions", "Assembled Product Depth", "Assembled Product Width", 
            "Assembled Product Height"
        ]
        
        for key, value in product_data.details.items():
            if any(dim_key.lower() in key.lower() for dim_key in dimension_keys):
                # 解析尺寸格式
                dim_match = re.search(r'([0-9]+\.?[0-9]*)\s*["x×]\s*([0-9]+\.?[0-9]*)\s*["x×]\s*([0-9]+\.?[0-9]*)', value)
                if dim_match and not dimensions:
                    dimensions['depth'] = dim_match.group(1)
                    dimensions['width'] = dim_match.group(2) 
                    dimensions['height'] = dim_match.group(3)
                    break
        
        return dimensions
    
    def extract_weight(self, product_data: ProductData) -> str:
        """从产品数据中提取重量信息"""
        return product_data.weight_value


# 全局基础映射引擎实例（网站特定的可以继承并扩展）
BASE_FIELD_MAPPING = FieldMappingEngine()
