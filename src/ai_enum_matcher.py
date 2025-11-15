#!/usr/bin/env python3
"""
AI枚举值匹配器
基于产品上下文和枚举选项，使用AI选择最合适的枚举值
"""
import os
import json
from typing import Dict, List, Any, Optional, Tuple
import openai

class AIEnumMatcher:
    """AI驱动的枚举值匹配器"""
    
    def __init__(self):
        """初始化AI枚举匹配器"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        self.enabled = False
        
        if self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                self.enabled = True
                print("🤖 AI枚举匹配器初始化成功")
            except Exception as e:
                print(f"⚠️ AI枚举匹配器初始化失败: {e}")
                self.enabled = False
        else:
            print("⚠️ 未设置OPENAI_API_KEY，AI枚举匹配功能将被禁用")
    
    def match_enum_value(self, field_config: Dict[str, Any], product_details: Dict[str, Any], 
                        enum_options: List[str], context: Optional[Dict[str, Any]] = None) -> Optional[Tuple[str, float]]:
        """
        为枚举字段选择最合适的选项
        
        Args:
            field_config: 字段配置信息
            product_details: 产品详细信息
            enum_options: 可选枚举值列表
            context: 额外上下文信息
            
        Returns:
            (选中的枚举值, 置信度) 或 None
        """
        if not self.enabled or not enum_options:
            return None
        
        field_title = field_config.get('title', '')
        field_description = field_config.get('description', '')
        
        try:
            # 构建AI提示
            prompt = self._build_enum_matching_prompt(
                field_title, field_description, product_details, enum_options, context
            )
            
            # 调用AI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的产品属性匹配专家，擅长根据产品信息选择最合适的属性值。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150
            )
            
            ai_response = response.choices[0].message.content.strip()
            return self._parse_ai_response(ai_response, enum_options)
            
        except Exception as e:
            print(f"❌ AI枚举匹配失败 ({field_title}): {e}")
            return None
    
    def _build_enum_matching_prompt(self, field_title: str, field_description: str, 
                                  product_details: Dict[str, Any], enum_options: List[str], 
                                  context: Optional[Dict[str, Any]] = None) -> str:
        """构建AI匹配提示"""
        
        # 构建产品信息摘要
        product_summary = self._build_product_summary(product_details)
        
        # 构建上下文信息
        context_info = ""
        if context:
            category = context.get('category', '')
            if category:
                context_info = f"\n产品类别: {category}"
        
        prompt = f"""
请根据以下产品信息，为字段 "{field_title}" 选择最合适的枚举值。

字段描述: {field_description}

产品信息:
{product_summary}{context_info}

可选枚举值:
{chr(10).join(f'- {option}' for option in enum_options)}

请分析产品特征，选择最符合的枚举值。如果有多个可能的选项，请选择最可能的一个。

请以以下JSON格式回复：
{{
    "selected_value": "选中的枚举值",
    "confidence": 0.85,
    "reasoning": "选择理由"
}}

要求：
1. selected_value 必须是提供的枚举值之一
2. confidence 范围 0.0-1.0，表示选择的置信度
3. reasoning 简要说明选择理由
"""
        return prompt
    
    def _build_product_summary(self, product_details: Dict[str, Any]) -> str:
        """构建产品信息摘要"""
        important_keys = [
            'title', 'Brand', 'Color', 'Material', 'Style', 
            'Product Dimensions', 'Item Weight', 'Key Features',
            'Feature Description', 'Assembly Required', 'Room Type'
        ]
        
        summary_parts = []
        for key in important_keys:
            if key in product_details:
                value = product_details[key]
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value[:3])  # 限制列表长度
                elif isinstance(value, dict):
                    value = str(value)[:100]  # 限制长度
                else:
                    value = str(value)[:200]  # 限制长度
                
                summary_parts.append(f"- {key}: {value}")
        
        return '\n'.join(summary_parts)
    
    def _parse_ai_response(self, ai_response: str, enum_options: List[str]) -> Optional[Tuple[str, float]]:
        """解析AI响应"""
        try:
            # 尝试解析JSON响应
            if ai_response.startswith('{') and ai_response.endswith('}'):
                response_data = json.loads(ai_response)
                selected_value = response_data.get('selected_value', '')
                confidence = float(response_data.get('confidence', 0.0))
                reasoning = response_data.get('reasoning', '')
                
                # 验证选中的值是否在枚举选项中
                if selected_value in enum_options:
                    print(f"🤖 AI枚举推荐: {selected_value} (置信度: {confidence:.2f}) - {reasoning}")
                    return (selected_value, confidence)
            
            # 如果JSON解析失败，尝试从响应中提取枚举值
            for option in enum_options:
                if option.lower() in ai_response.lower():
                    print(f"🤖 AI枚举推荐 (文本匹配): {option}")
                    return (option, 0.6)  # 默认置信度
            
            print(f"⚠️ AI响应无法解析有效枚举值: {ai_response}")
            return None
            
        except Exception as e:
            print(f"❌ 解析AI响应失败: {e}")
            return None
    
    def batch_match_enums(self, field_enum_pairs: List[Tuple[Dict[str, Any], List[str]]], 
                         product_details: Dict[str, Any], 
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Tuple[str, float]]:
        """
        批量匹配多个枚举字段
        
        Args:
            field_enum_pairs: [(字段配置, 枚举选项列表)]的列表
            product_details: 产品详细信息
            context: 上下文信息
            
        Returns:
            {字段标题: (选中值, 置信度)}
        """
        results = {}
        
        if not self.enabled:
            return results
        
        for field_config, enum_options in field_enum_pairs:
            field_title = field_config.get('title', '')
            
            # 单独匹配每个字段
            match_result = self.match_enum_value(field_config, product_details, enum_options, context)
            
            if match_result:
                results[field_title] = match_result
        
        return results
    
    def get_enum_confidence_threshold(self, field_title: str) -> float:
        """
        获取不同字段类型的置信度阈值
        
        Args:
            field_title: 字段标题
            
        Returns:
            置信度阈值
        """
        # 为不同类型的字段设置不同的置信度阈值
        critical_fields = [
            'Age Group', 'Condition', 'Is Prop 65 Warning Required',
            'Has Written Warranty', 'Is Assembly Required'
        ]
        
        descriptive_fields = [
            'Color Category', 'Desk Chair Type', 'Material',
            'Additional Features', 'Arm Style', 'Upholstered'
        ]
        
        if field_title in critical_fields:
            return 0.8  # 关键字段要求高置信度
        elif field_title in descriptive_fields:
            return 0.6  # 描述性字段接受中等置信度
        else:
            return 0.7  # 默认置信度阈值
    
    def suggest_enum_improvements(self, field_title: str, selected_value: str, 
                                 confidence: float, product_details: Dict[str, Any]) -> List[str]:
        """
        为低置信度的枚举选择提供改进建议
        
        Args:
            field_title: 字段标题
            selected_value: 选中的值
            confidence: 置信度
            product_details: 产品详情
            
        Returns:
            改进建议列表
        """
        suggestions = []
        
        threshold = self.get_enum_confidence_threshold(field_title)
        
        if confidence < threshold:
            suggestions.append(f"置信度 {confidence:.2f} 低于阈值 {threshold:.2f}")
            
            # 根据字段类型提供具体建议
            if field_title == 'Color Category':
                if 'Color' not in product_details:
                    suggestions.append("建议添加产品颜色信息以提高颜色类别匹配准确度")
            
            elif field_title == 'Material':
                if 'Material' not in product_details:
                    suggestions.append("建议添加材质信息以提高材质匹配准确度")
            
            elif 'Age Group' in field_title:
                suggestions.append("建议检查产品描述中的年龄相关信息")
            
            elif 'Assembly' in field_title:
                suggestions.append("建议检查产品特征中是否提到组装相关信息")
        
        return suggestions
    
    def is_available(self) -> bool:
        """检查AI枚举匹配器是否可用"""
        return self.enabled
