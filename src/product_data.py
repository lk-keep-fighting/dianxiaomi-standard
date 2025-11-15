#!/usr/bin/env python3
"""
产品数据结构和映射系统 - 统一的数据基础

设计原则：
1. Single Source of Truth - 一个产品数据类统治一切
2. Simple Data Structure - 简单的字典操作，无复杂继承
3. Clear Mapping - Amazon字段到表单字段的直接映射

作者: Linus Torvalds (风格)
"""

from dataclasses import dataclass, field
from tokenize import Double
from typing import Dict, List, Optional, Any
import re


@dataclass
class ProductData:
    """
    标准产品数据结构 - 整个系统的数据基础
    
    Good Taste: 数据结构简单清晰，操作直接明了
    """
    
    # 基础信息
    asin: str = ""
    title: str = ""
    price: float = 0.00  # 价格（美元）默认值为0.00
    delivery_price: float = 0.00  # 运费（美元）默认值为0.00
    weight_value: str = "10"  # 默认重量
    
    # 详情字典 - Amazon解析的所有键值对
    details: Dict[str, str] = field(default_factory=dict)
    
    # 解析状态
    parse_success: bool = False
    parse_errors: List[str] = field(default_factory=list)
    
    def add_detail(self, key: str, value: str) -> None:
        """添加产品详情 - 简单的键值对操作"""
        if key and value:
            self.details[key.strip().lower()] = value.strip()
    
    def get_detail(self, key: str, default: str = "") -> str:
        """获取产品详情"""
        return self.details.get(key.strip().lower(), default)
    
    def has_valid_data(self) -> bool:
        """检查是否有有效数据"""
        return bool(self.title or self.details)
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式（兼容旧代码）"""
        result = {'title': self.title} if self.title else {}
        result.update(self.details)
        return result


class FieldMappingEngine:
    """
    统一的字段映射引擎
    
    Single Source of Truth: 只有这一个地方定义Amazon -> Form的映射
    """
    
    def __init__(self):
        # 核心映射：Amazon产品详情键 -> 表单attrkey
        self.field_mappings = {
            # 基础字段
            'Brand': 'Brand Name',
            'Brand': 'Brand',
            'Manufacturer': 'Manufacturer Name',
            'Color': 'Color',
            'Material': 'Material',
            'Item model number': 'Manufacturer Part Number',
            'ASIN': 'Manufacturer Part Number',
            
            # 模版表单中字段
            "在线初始库存": 'dc_initListingQuantity',
            "ShippingWeight": 'dc_shippingWeight',
            "Lag Time":"dc_lagTime",
            "价格":"dc_price",
            "刊登类型":"dc_skuListType",
            
            # 聚合到Key Features的字段
            'Special Feature': 'Key Features',
            'Style': 'Key Features',
            'Shape': 'Key Features',
            'Mounting Type': 'Key Features',
            'Pattern': 'Key Features',
            'Theme': 'Key Features',
            'Finish Type': 'Key Features',
            'Planter Form': 'Key Features',
            'Feature Description': 'Key Features',
        }
        
        # 固定值字段（基于验证可行的设置）
        self.fixed_values = {
            'Is Prop 65 Warning Required': 'No (否)',
            'Condition': 'New (全新)',
            'Has Written Warranty': 'No (否)',
            'Age Group': 'Adult (成人)',
            'Small Parts Warning Code': '0 - No warning applicable',
            'Recommended Locations': 'Indoor',
        }
        
        # 复合字段配置（数值 + 单位）
        self.compound_fields = {
            'Assembled Product Depth': {
                "source": "Product Dimensions",
                "extraction": "depth",
                "unit": "in (英寸)"
            },
            'Assembled Product Width': {
                "source": "Product Dimensions",
                "extraction": "width", 
                "unit": "in (英寸)"
            },
            'Assembled Product Height': {
                "source": "Product Dimensions",
                "extraction": "height",
                "unit": "in (英寸)"
            },
            'Assembled Product Weight': {
                "source": "Item Weight",
                "extraction": "weight",
                "unit": "lb (磅)"
            },
            'Net Content': {
                "measure": "1",
                "unit": "Each (每个)"
            }
        }
    
    def get_form_field(self, amazon_key: str) -> Optional[str]:
        """获取Amazon键对应的表单字段名"""
        return self.field_mappings.get(amazon_key)
    
    def get_key_features_keys(self) -> List[str]:
        """获取所有应该聚合到Key Features的键名"""
        return [key for key, value in self.field_mappings.items() if value == 'Key Features']
    
    def extract_dimensions(self, product_data: ProductData) -> Dict[str, Optional[str]]:
        """
        提取产品尺寸 - 基于验证可行的逻辑
        
        Good Taste: 简单的字符串分割，没有复杂的正则表达式
        """
        dimensions = {"depth": None, "width": None, "height": None}
        
        dimensions_str = product_data.get_detail('Product Dimensions')
        if not dimensions_str:
            return dimensions
        
        try:
            # 使用验证可行的分割逻辑
            parts = dimensions_str.split('x')
            dimensions["depth"] = parts[0].strip().split('"')[0] if len(parts) > 0 else None
            dimensions["width"] = parts[1].strip().split('"')[0] if len(parts) > 1 else None
            
            # 处理高度部分，移除多余文本
            if len(parts) > 2:
                height_part = parts[2].strip().split('"')[0].strip()
                height_part = height_part.replace(' inches', '').replace(' inch', '').replace(' in', '').strip()
                dimensions["height"] = height_part if height_part else None
            
            print(f"✅ 尺寸提取: Depth={dimensions['depth']}, Width={dimensions['width']}, Height={dimensions['height']}")
            
        except Exception as e:
            print(f"⚠️ 尺寸提取失败: {e}")
        
        return dimensions
    
    def extract_weight(self, product_data: ProductData) -> str:
        """
        提取重量值 - 基于验证可行的逻辑
        """
        if not product_data.weight_value or product_data.weight_value == "10":
            # 尝试从Item Weight中提取
            item_weight = product_data.get_detail('Item Weight')
            if item_weight:
                weight_match = re.search(r'([0-9.]+)', item_weight)
                if weight_match:
                    return weight_match.group(1).strip()
        
        return product_data.weight_value or "10"


# 全局实例 - Single Source of Truth
FIELD_MAPPING = FieldMappingEngine()
