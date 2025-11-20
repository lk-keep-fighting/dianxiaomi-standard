#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Category Validator - 使用OpenAI兼容的大模型验证产品分类是否合理
支持腾讯云混元大模型等OpenAI兼容API
"""

import json
from typing import Dict, List, Optional, Tuple, Any
import logging

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore

class AICategoryValidator:
    """
    AI分类验证器 - 使用OpenAI兼容的大模型API验证产品分类
    """
    
    def __init__(self, 
                 api_base_url: str = "",
                 api_key: str = "",
                 model_name: str = "",
                 timeout: int = 30):
        """
        初始化AI分类验证器
        
        Args:
            api_base_url: API基础URL (支持OpenAI兼容的服务，如腾讯云混元)
            api_key: API密钥
            model_name: 模型名称
            timeout: 请求超时时间(秒)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "AI功能需要openai库。请安装: pip install openai\n"
                "或在打包时确保openai被正确包含。"
            )
        
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base_url,
            timeout=self.timeout
        )
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def _make_api_request(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        发送API请求到OpenAI兼容的服务（包括腾讯云混元）
        
        Args:
            messages: 对话消息列表
            
        Returns:
            模型回复内容，失败时返回None
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,  # type: ignore
                temperature=0.1,  # 低温度确保稳定输出
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            return content.strip() if content else None
            
        except Exception as e:
            self.logger.error(f"API请求异常: {e}")
            return None
    
    def validate_category(self, 
                         title: str, 
                         key_features: List[str], 
                         current_category: str) -> Tuple[bool, str, Optional[str]]:
        """
        验证产品分类是否合理
        
        Args:
            title: 产品标题
            key_features: 关键特征列表
            current_category: 当前分类
            
        Returns:
            Tuple[是否合理, 分析原因, 建议分类(如果当前分类不合理)]
        """
        # 构建验证提示词
        features_text = "\n".join([f"- {feature}" for feature in key_features[:10]])  # 限制特征数量
        
        prompt = f"""请分析以下产品信息，判断当前分类是否合理：

产品标题: {title}

关键特征:
{features_text}

当前分类: {current_category}

请按照以下JSON格式回复：
{{
    "is_reasonable": true/false,
    "reason": "详细分析原因",
    "suggested_category": "如果当前分类不合理，请提供建议分类，否则为null"
}}

分析要求：
1. 基于产品标题和特征判断分类的准确性
2. 考虑产品的主要功能和用途
3. 如果分类不合理，建议更准确的分类
4. 回复必须是有效的JSON格式"""

        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的产品分类专家，擅长根据产品信息判断分类是否准确。你的回复必须是严格的JSON格式。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # 发送API请求
        response = self._make_api_request(messages)
        
        if not response:
            self.logger.warning("AI验证失败，返回默认结果")
            return True, "AI验证服务不可用，默认认为分类合理", None
        
        # 解析响应
        try:
            # 尝试提取JSON部分
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            
            is_reasonable = result.get('is_reasonable', True)
            reason = result.get('reason', '无具体原因')
            suggested_category = result.get('suggested_category')
            
            return is_reasonable, reason, suggested_category
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}, 原始响应: {response}")
            return True, "响应解析失败，默认认为分类合理", None
    
    def suggest_category(self, title: str, key_features: List[str]) -> Optional[str]:
        """
        基于产品信息建议分类
        
        Args:
            title: 产品标题
            key_features: 关键特征列表
            
        Returns:
            建议的分类名称，失败时返回None
        """
        features_text = "\n".join([f"- {feature}" for feature in key_features[:10]])
        
        prompt = f"""请根据以下产品信息建议一个准确的产品分类：

        产品标题: {title}

        关键特征:
        {features_text}

        请按照以下JSON格式回复：
        {{
            "category": "建议的产品分类",
            "confidence": "置信度(1-10)",
            "reason": "选择这个分类的理由"
        }}

        要求：
        1. 分类要准确反映产品的主要功能和用途
        2. 使用常见的电商产品分类标准
        3. 回复必须是有效的JSON格式"""

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的产品分类专家，擅长为产品推荐准确的分类。你的回复必须是严格的JSON格式。"
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        response = self._make_api_request(messages)
        
        if not response:
            return None
            
        try:
            # 清理响应格式
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            return result.get('category')
            
        except json.JSONDecodeError as e:
            self.logger.error(f"建议分类JSON解析失败: {e}")
            return None

    def new_title_and_key_features(self, title: str, key_features: List[str], remove_words: str, category: str) -> Optional[Dict[str, str]]:
        """
        基于产品信息生成新的标题和描述
        
        Args:
            title: 产品标题
            key_features: 关键特征列表
            remove_words: 需要移除的违规词
            category: 产品分类
            
        Returns:
            包含title、bullet_points、description的结构化字典，失败时返回None
        """
        print("正在使用AI生成新的标题和描述")
        features_text = "\n".join([f"- {feature}" for feature in key_features[:10]])
        
        prompt = f"""
        以以下格式回复我：
        优化内容
        ​​标题：
        ​​五点描述：
        ​​详情描述：
        原标题内容可供参考：
        {title}
        
        原五点描述内容可供参考：
        {features_text}
        
        编写标题注意事项：
        1、标题字符数:150字符-200字符、避免同一字词出现两次以上；
        2、权重:遵循标题>bullet points>description>search term原则；
        3、核心:核心关键词放在标题最左侧，在80个字符内，埋入2-3个其他关键词；
        4、去掉文案中包含的品牌词、违规词、侵权词，这一点一定要执行；
        5、去掉文案中不是英文单词的词语；避免同一字词出现两次以上；
        6、不要使用沃尔玛的侵权词、违规词编写标题,比如：（{remove_words}）等；
        7、具备可读性，体现卖点、痛点、适用对象、使用场景等；
        8、不要使用主观性较强的关键词。
        
        编写五点描述、详情描述注意事项：
        1、五点描述每一点采取总分结构,利用现有信息编写，不要额外延伸；
        2、五点描述每一行字符数在250个字符以内；
        3、五点描述、详情描述中要埋入其他关键词；
        4、去掉文案中包含的品牌词、违规词、侵权词，这一点一定要执行；
        5、去掉文案中不是英文单词的词语；
        6、五点描述、详情描述不要使用违规词,比如：（{remove_words}）等；
        7、不要使用主观性较强的关键词，不要使用"专利产品"、"经过认证"、"经过测试"、"售后"、"保修"、"促销"、"折扣"等语句；
        8、五点描述、详情描述包含产品卖点、痛点、使用场景、适用对象等。
        
        """

        messages = [
            {
                "role": "system",
                "content": f"你是一个专业的沃尔玛加拿大站产品文案优化专家，专门优化（{category}）类产品。你需要用英语生成新的标题、五点描述、详情描述。"
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        print("正在使用AI生成新的标题和描述,提示词如下：")
        print(prompt)
        response = self._make_api_request(messages)
        
        if not response:
            self.logger.warning("AI内容生成失败，API无响应")
            return None
            
        try:
            # 解析文本格式的AI响应为结构化数据
            return self._parse_structured_response(response)
            
        except Exception as e:
            self.logger.error(f"AI内容解析失败: {e}")
            return None
    
    def _parse_structured_response(self, response: str) -> Optional[Dict[str, str]]:
        """
        解析AI返回的结构化文本响应
        
        Args:
            response: AI返回的原始文本响应
            
        Returns:
            包含title、bullet_points、description的字典
        """
        import re
        
        try:
            # 清理响应文本
            response = response.strip()
            self.logger.info(f"开始解析AI响应: {response[:100]}...")
            
            # 使用正则表达式提取各部分内容
            result = {}
            
            # 提取标题 - 支持多种格式
            title_patterns = [
                r'(?:标题[：:]|Title[：:]|​​标题[：:])\s*([^\n]+)',
                r'标题[：:]?\s*\n([^\n]+)',
                r'Title[：:]?\s*\n([^\n]+)'
            ]
            
            for pattern in title_patterns:
                title_match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
                if title_match:
                    result['title'] = title_match.group(1).strip()
                    break
            
            # 提取五点描述 - 改进的解析逻辑
            # 先找到五点描述的开始位置
            bullet_start_patterns = [
                r'五点描述[：:]',
                r'bullet.*points?[：:]',
                r'​​五点描述[：:]'
            ]
            
            bullet_start_pos = -1
            for pattern in bullet_start_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    bullet_start_pos = match.end()
                    break
            
            if bullet_start_pos >= 0:
                # 找到详情描述的开始位置作为结束
                desc_patterns = [r'详情描述[：:]', r'description[：:]', r'​​详情描述[：:]']
                desc_start_pos = len(response)
                
                for pattern in desc_patterns:
                    match = re.search(pattern, response[bullet_start_pos:], re.IGNORECASE)
                    if match:
                        desc_start_pos = bullet_start_pos + match.start()
                        break
                
                # 提取五点描述部分
                bullet_section = response[bullet_start_pos:desc_start_pos].strip()
                
                # 提取所有以"-"或"•"开头的行
                bullet_lines = []
                for line in bullet_section.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•')):
                        bullet_lines.append(line)
                
                if bullet_lines:
                    result['bullet_points'] = '\n'.join(bullet_lines)
                    result["bullet_lines"]=bullet_lines
            
            # 提取详情描述
            desc_patterns = [
                r'(?:详情描述[：:]|description[：:]|​​详情描述[：:])\s*([\s\S]*?)$',
                r'详情描述[：:]?\s*\n([\s\S]*?)$',
                r'description[：:]?\s*\n([\s\S]*?)$'
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
                if desc_match:
                    desc_text = desc_match.group(1).strip()
                    # 清理描述文本
                    desc_text = re.sub(r'\n+', ' ', desc_text)  # 合并多个换行
                    desc_text = re.sub(r'\s+', ' ', desc_text)  # 合并多个空格
                    if desc_text:
                        result['description'] = desc_text
                        break
            
            # 备用解析方案 - 如果上述方法失败，尝试简单的文本分割
            if not result:
                self.logger.warning("使用备用文本分割方案")
                lines = response.split('\n')
                current_section = None
                temp_content = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # 检测节标题
                    if any(keyword in line for keyword in ['标题', 'Title']) and ':' in line:
                        if current_section and temp_content:
                            result[current_section] = '\n'.join(temp_content)
                        current_section = 'title'
                        temp_content = [line.split(':', 1)[1].strip()]
                    elif any(keyword in line for keyword in ['五点描述', 'bullet', 'points']) and ':' in line:
                        if current_section and temp_content:
                            result[current_section] = '\n'.join(temp_content)
                        current_section = 'bullet_points'
                        temp_content = []
                    elif any(keyword in line for keyword in ['详情描述', 'description']) and ':' in line:
                        if current_section and temp_content:
                            result[current_section] = '\n'.join(temp_content)
                        current_section = 'description'
                        temp_content = []
                    elif line.startswith('-') and current_section == 'bullet_points':
                        temp_content.append(line)
                    elif current_section and line:
                        temp_content.append(line)
                
                # 处理最后一个段落
                if current_section and temp_content:
                    result[current_section] = '\n'.join(temp_content)
            
            # 验证结果并清理数据
            if result:
                # 清理标题中的多余字符
                if 'title' in result:
                    result['title'] = re.sub(r'^[^a-zA-Z0-9]*', '', result['title']).strip()
                
                # 确保五点描述格式正确
                if 'bullet_points' in result:
                    bullet_lines = result['bullet_points'].split('\n')
                    formatted_bullets = []
                    for line in bullet_lines:
                        line = line.strip()
                        if line and not line.startswith('-'):
                            line = '- ' + line
                        if line:
                            formatted_bullets.append(line)
                    result['bullet_points'] = '\n'.join(formatted_bullets)
                    result["formatted_bullets"]=formatted_bullets
                
                self.logger.info(f"✅ 成功解析AI响应 - 标题: {len(result.get('title', ''))}, 五点描述: {len(result.get('bullet_points', ''))}, 描述: {len(result.get('description', ''))} 字符")
                return result
            else:
                self.logger.warning("⚠️ 未能从AI响应中提取任何有效内容")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 解析AI响应时发生异常: {e}")
            # 最后的备用方案 - 返回原始响应的简单分割
            try:
                return {
                    'title': 'AI生成失败 - 请手动处理',
                    'bullet_points': '- 解析失败，请检查AI响应格式',
                    'description': response[:500] + '...' if len(response) > 500 else response
                }
            except:
                return None

# 使用示例
if __name__ == "__main__":
    # 腾讯云混元大模型配置示例
    validator = AICategoryValidator(
        api_base_url="https://api.hunyuan.cloud.tencent.com/v1",  # 腾讯云混元API
        api_key="sk-fc0nyVUKNiqO4gYEMPtmQbai53cUoAvBVhlW4fROn69LTthI",  # 替换为实际的混元API密钥
        model_name="hunyuan-turbos-latest"    # 混元最新turbo模型
    )
    
    # 测试数据
    title = "床头柜实木简约现代卧室储物柜"
    features = [
        "实木材质",
        "简约设计", 
        "储物功能",
        "卧室家具",
        "现代风格"
    ]
    current_category = "床头柜(Nightstands)"
    
    # 验证分类
    is_reasonable, reason, suggested = validator.validate_category(title, features, current_category)
    
    print(f"分类是否合理: {is_reasonable}")
    print(f"分析原因: {reason}")
    if suggested:
        print(f"建议分类: {suggested}")