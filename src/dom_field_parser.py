#!/usr/bin/env python3
"""
DOM表单字段解析器
基于页面DOM结构解析表单字段信息，比API配置更准确地反映表单真实状态
"""
from typing import Dict, List, Any, Optional
from playwright.sync_api import Frame, Locator


class DOMFieldParser:
    """DOM表单字段解析器，通过分析页面DOM结构获取字段信息"""
    
    def __init__(self, frame: Frame):
        """
        初始化DOM字段解析器
        
        Args:
            frame: Playwright Frame对象，用于DOM操作
        """
        self.frame = frame
        self.fields_cache = None
        self.cache_valid = False
    
    def get_all_form_fields(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        获取表单中所有字段的配置信息
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            字段配置列表，每个字段包含name、title、required、input_type等信息
        """
        if not self.cache_valid or force_refresh:
            self.fields_cache = self._parse_dom_fields()
            self.cache_valid = True
        
        return self.fields_cache
    
    def get_required_fields(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        获取所有必填字段
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            必填字段配置列表
        """
        all_fields = self.get_all_form_fields(force_refresh)
        return [field for field in all_fields if field.get('required', False)]
    
    def _parse_dom_fields(self) -> List[Dict[str, Any]]:
        """解析DOM结构获取字段信息"""
        fields = []
        
        try:
            # 查找.attr-blocks容器
            attr_blocks = self.frame.locator('.attr-blocks')
            if attr_blocks.count() == 0:
                print("⚠️ 未找到.attr-blocks容器")
                return []
            
            # 查找所有带attrkey的字段行
            field_rows = attr_blocks.locator('div[attrkey]')
            field_count = field_rows.count()
            
            print(f"🔍 DOM解析发现 {field_count} 个字段")
            
            for i in range(field_count):
                field_row = field_rows.nth(i)
                field_config = self._parse_field_row(field_row)
                
                if field_config:
                    fields.append(field_config)
                    status = "✅必填" if field_config['required'] else "⭕可选"
                    print(f"   {status} {field_config['title']} ({field_config['input_type']})")
            
        except Exception as e:
            print(f"❌ DOM字段解析失败: {e}")
        
        return fields
    
    def _parse_field_row(self, field_row: Locator) -> Optional[Dict[str, Any]]:
        """
        解析单个字段行的配置信息
        
        Args:
            field_row: 字段行的Locator
            
        Returns:
            字段配置字典，如果解析失败返回None
        """
        try:
            # 获取attrkey（字段名）
            attr_key = field_row.get_attribute('attrkey')
            if not attr_key:
                return None
            
            # 解析字段标题和必填状态
            title_element = field_row.locator('.attr-name-text')
            if title_element.count() == 0:
                return None
            
            title_text = title_element.inner_text()
            
            # 检查是否必填（查找<i>*</i>标签）
            required_indicator = field_row.locator('.attr-name-text i')
            is_required = required_indicator.count() > 0 and '*' in required_indicator.inner_text()
            
            # 清理标题文本（移除*标记）
            clean_title = title_text.replace('*', '').replace(':', '').strip()
            
            # 推断输入类型
            input_type = self._infer_input_type_from_dom(field_row)
            
            return {
                'name': attr_key,
                'title': clean_title,
                'required': is_required,
                'input_type': input_type,
                'data_source': 'dom',
                'dom_info': {
                    'raw_title': title_text,
                    'has_required_marker': is_required
                }
            }
            
        except Exception as e:
            print(f"⚠️ 解析字段行失败: {e}")
            return None
    
    def _infer_input_type_from_dom(self, field_row: Locator) -> str:
        """
        根据DOM结构推断输入类型
        
        Args:
            field_row: 字段行的Locator
            
        Returns:
            推断的输入类型
        """
        try:
            # 检查TinyMCE编辑器
            if field_row.locator('.mce-tinymce').count() > 0:
                return 'tinymce'
            
            # 检查select2下拉框
            if field_row.locator('.select2-container').count() > 0:
                return 'select'
            
            # 检查textarea
            if field_row.locator('textarea').count() > 0:
                return 'textarea'
            
            # 检查input
            if field_row.locator('input[type="text"]').count() > 0:
                return 'text'
            
            # 检查checkbox
            if field_row.locator('input[type="checkbox"]').count() > 0:
                return 'checkbox'
            
            # 检查number相关class
            if field_row.locator('.input-c').get_attribute('class') and 'number' in field_row.locator('.input-c').get_attribute('class'):
                return 'number'
            
            # 默认返回text
            return 'text'
            
        except Exception as e:
            print(f"⚠️ 推断输入类型失败: {e}")
            return 'text'
    
    def get_field_by_name(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        根据字段名获取字段配置
        
        Args:
            field_name: 字段名（attrkey）
            
        Returns:
            字段配置字典，如果不存在返回None
        """
        all_fields = self.get_all_form_fields()
        for field in all_fields:
            if field['name'] == field_name:
                return field
        return None
    
    def is_field_required(self, field_name: str) -> bool:
        """
        检查指定字段是否必填
        
        Args:
            field_name: 字段名（attrkey）
            
        Returns:
            是否必填
        """
        field = self.get_field_by_name(field_name)
        return field.get('required', False) if field else False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取DOM解析统计信息
        
        Returns:
            统计信息字典
        """
        all_fields = self.get_all_form_fields()
        required_fields = [f for f in all_fields if f['required']]
        
        # 统计输入类型分布
        input_types = {}
        for field in all_fields:
            input_type = field['input_type']
            input_types[input_type] = input_types.get(input_type, 0) + 1
        
        return {
            'total_fields': len(all_fields),
            'required_fields': len(required_fields),
            'optional_fields': len(all_fields) - len(required_fields),
            'input_type_distribution': input_types,
            'required_field_names': [f['name'] for f in required_fields]
        }
    
    def print_summary(self):
        """打印DOM解析摘要"""
        stats = self.get_statistics()
        
        print("\n📊 DOM字段解析摘要:")
        print(f"   总字段数: {stats['total_fields']}")
        print(f"   必填字段: {stats['required_fields']}")
        print(f"   可选字段: {stats['optional_fields']}")
        
        print(f"\n🔧 字段类型分布:")
        for input_type, count in stats['input_type_distribution'].items():
            print(f"   {input_type}: {count}个")
        
        print(f"\n✅ 必填字段列表:")
        for field_name in stats['required_field_names']:
            print(f"   - {field_name}")
    
    def invalidate_cache(self):
        """使缓存失效，下次调用时会重新解析DOM"""
        self.cache_valid = False
        self.fields_cache = None
