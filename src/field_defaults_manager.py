#!/usr/bin/env python3
"""
字段默认值配置管理器
提供灵活的默认值配置系统，支持多种匹配策略
"""
import json
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
try:
    from ai_enum_matcher import AIEnumMatcher
except ImportError:
    from .ai_enum_matcher import AIEnumMatcher

class FieldDefaultsManager:
    """默认值配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化默认值管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "field_defaults.json"
        
        self.config_path = Path(config_path)
        self.config = None
        self.cache = {}
        self.enable_logging = True
        
        # 初始化AI枚举匹配器
        self.ai_enum_matcher = None
        try:
            self.ai_enum_matcher = AIEnumMatcher()
        except Exception as e:
            if self.enable_logging:
                print(f"⚠️ AI枚举匹配器初始化失败: {e}")
        
        # 加载配置
        self.load_config()
    
    def load_config(self) -> bool:
        """加载默认值配置文件"""
        try:
            if not self.config_path.exists():
                print(f"⚠️ 默认值配置文件不存在: {self.config_path}")
                self._create_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            # 读取配置选项
            config_settings = self.config.get('configuration', {})
            self.enable_logging = config_settings.get('enable_logging', True)
            cache_enabled = config_settings.get('cache_defaults', True)
            
            if not cache_enabled:
                self.cache = {}
            
            if self.enable_logging:
                print(f"✅ 已加载默认值配置: {self.config_path}")
                print(f"📊 配置版本: {self.config.get('version', 'Unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ 加载默认值配置失败: {e}")
            return False
    
    def _create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "description": "字段默认值配置",
            "version": "1.0",
            "defaults": {
                "exact_match": {
                    "values": {
                        "Is Prop 65 Warning Required": "No",
                        "Age Group": "Adult",
                        "Condition": "New"
                    }
                },
                "pattern_match": {
                    "values": {
                        "*Weight*": "10",
                        "*Size*": "Medium"
                    }
                },
                "type_based": {
                    "values": {
                        "text": "",
                        "number": "0"
                    }
                }
            },
            "configuration": {
                "priority_order": ["exact_match", "pattern_match", "type_based"],
                "enable_logging": True,
                "cache_defaults": True
            }
        }
        
        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"📝 已创建默认配置文件: {self.config_path}")
    
    def get_default_value(self, field_config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        获取字段的默认值
        
        Args:
            field_config: 字段配置信息，包含title、input_type等
            context: 上下文信息，用于智能匹配
            
        Returns:
            默认值，如果没有找到则返回None
        """
        if not self.config:
            return None
        
        field_title = field_config.get('title', '')
        field_type = field_config.get('input_type', 'text')
        
        # 检查缓存
        cache_key = f"{field_title}|{field_type}"
        if cache_key in self.cache:
            if self.enable_logging:
                print(f"💾 从缓存获取默认值: {field_title} -> {self.cache[cache_key]}")
            return self.cache[cache_key]
        
        # 按优先级顺序尝试获取默认值
        priority_order = self.config.get('configuration', {}).get('priority_order', 
                                                                 ['exact_match', 'pattern_match', 'type_based'])
        
        default_value = None
        match_strategy = None
        
        for strategy in priority_order:
            if strategy == 'exact_match':
                default_value = self._get_exact_match_value(field_title)
                if default_value is not None:
                    match_strategy = 'exact_match'
                    break
            
            elif strategy == 'pattern_match':
                default_value = self._get_pattern_match_value(field_title)
                if default_value is not None:
                    match_strategy = 'pattern_match'
                    break
            
            elif strategy == 'contextual_defaults':
                default_value = self._get_contextual_value(field_title, context)
                if default_value is not None:
                    match_strategy = 'contextual_defaults'
                    break
            
            elif strategy == 'category_based':
                default_value = self._get_category_value(field_title, field_type)
                if default_value is not None:
                    match_strategy = 'category_based'
                    break
            
            elif strategy == 'type_based':
                default_value = self._get_type_based_value(field_type)
                if default_value is not None:
                    match_strategy = 'type_based'
                    break
        
        # 应用后备策略（优化：明确区分空值和无配置）
        if default_value is None:
            fallback_strategy = self.config.get('configuration', {}).get('fallback_strategy', 'none')  # 默认改为none
            if fallback_strategy == 'empty_string':
                default_value = ""
                match_strategy = 'fallback_empty_string'
            elif fallback_strategy == 'none':
                default_value = None
                match_strategy = 'no_config_found'  # 明确标识无配置情况
        
        # 缓存结果
        if default_value is not None:
            self.cache[cache_key] = default_value
        
        # 如果常规默认值为空且字段有枚举值，尝试使用AI匹配
        if default_value is None and self.ai_enum_matcher and self.ai_enum_matcher.is_available():
            enum_options = self._extract_enum_options(field_config)
            if enum_options:
                product_details = context.get('product_details', {}) if context else {}
                ai_result = self.ai_enum_matcher.match_enum_value(field_config, product_details, enum_options, context)
                
                if ai_result:
                    selected_value, confidence = ai_result
                    threshold = self.ai_enum_matcher.get_enum_confidence_threshold(field_title)
                    
                    if confidence >= threshold:
                        default_value = selected_value
                        match_strategy = 'ai_enum_matching'
                        
                        # 缓存AI结果
                        if default_value is not None:
                            self.cache[cache_key] = default_value
                    elif self.enable_logging:
                        print(f"⚠️ AI枚举匹配置信度较低: {field_title} -> {selected_value} ({confidence:.2f} < {threshold:.2f})")
        
        # 日志记录（优化：对无配置情况跳过日志输出）
        if self.enable_logging and default_value is not None and match_strategy != 'no_config_found':
            print(f"🔧 应用默认值: {field_title} -> '{default_value}' (策略: {match_strategy})")
        elif self.enable_logging and match_strategy == 'no_config_found':
            print(f"🚀 无默认值配置: {field_title} (跳过DOM操作)")
        
        return default_value
    
    def _get_exact_match_value(self, field_title: str) -> Optional[Any]:
        """获取精确匹配的默认值"""
        exact_match = self.config.get('defaults', {}).get('exact_match', {}).get('values', {})
        return exact_match.get(field_title)
    
    def _get_pattern_match_value(self, field_title: str) -> Optional[Any]:
        """获取模式匹配的默认值"""
        pattern_match = self.config.get('defaults', {}).get('pattern_match', {}).get('values', {})
        
        for pattern, value in pattern_match.items():
            # 将通配符模式转换为正则表达式
            regex_pattern = pattern.replace('*', '.*')
            if re.search(regex_pattern, field_title, re.IGNORECASE):
                return value
        
        return None
    
    def _get_contextual_value(self, field_title: str, context: Optional[Dict[str, Any]]) -> Optional[Any]:
        """获取基于上下文的默认值"""
        if not context:
            return None
        
        contextual_defaults = self.config.get('defaults', {}).get('contextual_defaults', {})
        
        # 尝试根据上下文类型获取默认值
        context_type = context.get('category', 'general')
        if context_type in contextual_defaults:
            context_values = contextual_defaults[context_type]
            return context_values.get(field_title)
        
        return None
    
    def _get_category_value(self, field_title: str, field_type: str) -> Optional[Any]:
        """获取基于字段类别的默认值"""
        category_based = self.config.get('defaults', {}).get('category_based', {}).get('values', {})
        
        # 根据字段名称推断类别
        field_lower = field_title.lower()
        
        if any(keyword in field_lower for keyword in ['weight', 'mass']):
            return category_based.get('weight')
        elif any(keyword in field_lower for keyword in ['width', 'height', 'depth', 'length', 'size']):
            return category_based.get('dimension')
        elif any(keyword in field_lower for keyword in ['quantity', 'count', 'number']):
            return category_based.get('quantity')
        elif any(keyword in field_lower for keyword in ['percent', '%']):
            return category_based.get('percentage')
        elif any(keyword in field_lower for keyword in ['url', 'link']):
            return category_based.get('url')
        elif any(keyword in field_lower for keyword in ['email', 'mail']):
            return category_based.get('email')
        elif any(keyword in field_lower for keyword in ['phone', 'tel']):
            return category_based.get('phone')
        elif any(keyword in field_lower for keyword in ['yes', 'no', 'required', 'enabled']):
            return category_based.get('boolean')
        
        return None
    
    def _get_type_based_value(self, field_type: str) -> Optional[Any]:
        """获取基于字段类型的默认值"""
        type_based = self.config.get('defaults', {}).get('type_based', {}).get('values', {})
        return type_based.get(field_type)
    
    def add_default_value(self, field_title: str, default_value: Any, strategy: str = 'exact_match') -> bool:
        """
        动态添加默认值
        
        Args:
            field_title: 字段标题
            default_value: 默认值
            strategy: 匹配策略
            
        Returns:
            是否添加成功
        """
        try:
            if not self.config:
                return False
            
            if strategy not in self.config['defaults']:
                self.config['defaults'][strategy] = {'values': {}}
            
            if 'values' not in self.config['defaults'][strategy]:
                self.config['defaults'][strategy]['values'] = {}
            
            self.config['defaults'][strategy]['values'][field_title] = default_value
            
            # 更新缓存
            cache_key = f"{field_title}|text"  # 假设为text类型
            self.cache[cache_key] = default_value
            
            if self.enable_logging:
                print(f"➕ 添加默认值: {field_title} -> '{default_value}' (策略: {strategy})")
            
            return True
            
        except Exception as e:
            print(f"❌ 添加默认值失败: {e}")
            return False
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            if not self.config:
                return False
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            if self.enable_logging:
                print(f"💾 已保存配置: {self.config_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        if self.enable_logging:
            print("🗑️ 已清空默认值缓存")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取配置统计信息"""
        if not self.config:
            return {}
        
        defaults = self.config.get('defaults', {})
        stats = {
            'total_strategies': len(defaults),
            'cache_size': len(self.cache),
            'strategies': {}
        }
        
        for strategy, data in defaults.items():
            if isinstance(data, dict) and 'values' in data:
                stats['strategies'][strategy] = len(data['values'])
        
        return stats
    
    def _extract_enum_options(self, field_config: Dict[str, Any]) -> List[str]:
        """从字段配置中提取枚举选项"""
        enum_options = []
        
        # 检查直接的enum字段
        if 'enum' in field_config:
            enum_options = field_config['enum']
        
        # 检查嵌套的enum字段（如array类型的items.enum）
        elif 'items' in field_config and isinstance(field_config['items'], dict):
            if 'enum' in field_config['items']:
                enum_options = field_config['items']['enum']
        
        # 检查复合字段中的枚举选项（如尺寸字段的unit）
        elif 'properties' in field_config:
            properties = field_config['properties']
            for prop_name, prop_config in properties.items():
                if prop_name == 'unit' and 'enum' in prop_config:
                    enum_options = prop_config['enum']
                    break
        
        return enum_options if isinstance(enum_options, list) else []
    
    def get_ai_enum_recommendations(self, field_configs: List[Dict[str, Any]], 
                                  product_details: Dict[str, Any], 
                                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Tuple[str, float]]:
        """
        批量获取AI枚举推荐
        
        Args:
            field_configs: 字段配置列表
            product_details: 产品详情
            context: 上下文信息
            
        Returns:
            {字段标题: (推荐值, 置信度)}
        """
        if not self.ai_enum_matcher or not self.ai_enum_matcher.is_available():
            return {}
        
        # 准备字段-枚举对
        field_enum_pairs = []
        for field_config in field_configs:
            enum_options = self._extract_enum_options(field_config)
            if enum_options:
                field_enum_pairs.append((field_config, enum_options))
        
        if not field_enum_pairs:
            return {}
        
        # 添加产品详情到上下文
        enhanced_context = context.copy() if context else {}
        enhanced_context['product_details'] = product_details
        
        # 调用AI批量匹配
        return self.ai_enum_matcher.batch_match_enums(field_enum_pairs, product_details, enhanced_context)
