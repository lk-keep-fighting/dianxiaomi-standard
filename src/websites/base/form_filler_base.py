#!/usr/bin/env python3
"""
表单填充基类

职责：
1. 提供通用的表单填充方法
2. 定义表单填充的标准流程
3. 提供各种输入类型的处理方法

设计原则：
- Base class for all form fillers
- Reusable form interaction methods
- Good Taste: Simple and consistent
"""

import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

# 避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.product_data import ProductData


class FormFillerBase(ABC):
    """
    表单填充基类
    
    提供所有网站表单填充器都需要的通用功能
    """
    
    def __init__(self, form_handle: Any, timeout: int = 5000):
        self.form_handle = form_handle
        self.timeout = timeout
        self.wait_time = 200  # 操作间等待时间
        
        # 填充统计
        self.stats = {
            'total_attempts': 0,
            'successful_fills': 0,
            'failed_fills': 0,
            'skipped_fields': 0
        }
    
    @abstractmethod
    def fill_form(self, product_data: "ProductData") -> Dict[str, Any]:
        """
        填充表单的主要方法（子类必须实现）
        
        Args:
            product_data: 产品数据
            
        Returns:
            填充结果统计
        """
        pass
    
    def wait_between_actions(self) -> None:
        """操作间等待"""
        time.sleep(self.wait_time / 1000.0)
    
    def safe_locate_field(self, selector: str) -> Any:
        """
        安全定位字段容器
        
        Args:
            selector: 选择器
            
        Returns:
            字段元素或None
        """
        try:
            if hasattr(self.form_handle, 'locator'):
                element = self.form_handle.locator(selector)
                element.wait_for(state="attached", timeout=self.timeout)
                return element
            else:
                return None
        except Exception as e:
            print(f"⚠️ 定位字段失败 {selector}: {e}")
            return None
    
    def fill_text_field(self, selector: str, value: str) -> bool:
        """
        填充文本字段
        
        Args:
            selector: 字段选择器
            value: 要填充的值
            
        Returns:
            是否成功
        """
        try:
            self.stats['total_attempts'] += 1
            
            field_container = self.safe_locate_field(selector)
            if not field_container:
                self.stats['failed_fills'] += 1
                return False
            
            # 尝试多种文本输入类型
            input_selectors = ['textarea', 'input[type="text"]', 'input:not([type])', 'input']
            
            for input_selector in input_selectors:
                try:
                    input_element = field_container.locator(input_selector)
                    if input_element.count() > 0:
                        input_element.first.fill(str(value))
                        print(f"✅ 成功填充文本字段: {selector}")
                        self.stats['successful_fills'] += 1
                        return True
                except Exception:
                    continue
            
            print(f"⚠️ 未找到可填充的文本输入: {selector}")
            self.stats['failed_fills'] += 1
            return False
            
        except Exception as e:
            print(f"⚠️ 填充文本字段失败 {selector}: {e}")
            self.stats['failed_fills'] += 1
            return False
    
    def fill_compound_field(self, selector: str, number_value: str, unit_value: str) -> bool:
        """
        填充复合字段（数值+单位）
        
        Args:
            selector: 字段选择器
            number_value: 数值
            unit_value: 单位
            
        Returns:
            是否成功
        """
        try:
            self.stats['total_attempts'] += 1
            
            field_container = self.safe_locate_field(selector)
            if not field_container:
                self.stats['failed_fills'] += 1
                return False
            
            success_count = 0
            
            # 填充数值部分
            number_input = field_container.locator('input[type="text"], input:not([type])')
            if number_input.count() > 0:
                number_input.first.fill(str(number_value))
                success_count += 1
                print(f"✅ 填充数值: {number_value}")
            
            # 填充单位部分
            unit_select = field_container.locator('select')
            if unit_select.count() > 0:
                try:
                    unit_select.first.select_option(label=unit_value)
                    success_count += 1
                    print(f"✅ 填充单位: {unit_value}")
                except Exception:
                    pass
            
            if success_count > 0:
                print(f"✅ 成功填充复合字段: {selector}")
                self.stats['successful_fills'] += 1
                return True
            else:
                print(f"⚠️ 复合字段填充失败: {selector}")
                self.stats['failed_fills'] += 1
                return False
                
        except Exception as e:
            print(f"⚠️ 填充复合字段失败 {selector}: {e}")
            self.stats['failed_fills'] += 1
            return False
    
    def fill_rich_text_editor(self, selector: str, content: str) -> bool:
        """
        填充富文本编辑器（如TinyMCE）
        
        Args:
            selector: 字段选择器
            content: 内容
            
        Returns:
            是否成功
        """
        try:
            self.stats['total_attempts'] += 1
            
            field_container = self.safe_locate_field(selector)
            if not field_container:
                self.stats['failed_fills'] += 1
                return False
            
            # 查找TinyMCE iframe
            tinymce_iframe = field_container.locator('iframe')
            if tinymce_iframe.count() > 0:
                try:
                    # 获取iframe内容
                    iframe_content = tinymce_iframe.first.content_frame()
                    body = iframe_content.locator('body')
                    
                    if body.count() > 0:
                        body.first.fill(content)
                        print(f"✅ 成功填充富文本编辑器: {selector}")
                        self.stats['successful_fills'] += 1
                        return True
                except Exception as e:
                    print(f"⚠️ TinyMCE填充失败: {e}")
            
            # 尝试普通文本域
            textarea = field_container.locator('textarea')
            if textarea.count() > 0:
                textarea.first.fill(content)
                print(f"✅ 成功填充文本域: {selector}")
                self.stats['successful_fills'] += 1
                return True
            
            print(f"⚠️ 未找到可填充的编辑器: {selector}")
            self.stats['failed_fills'] += 1
            return False
            
        except Exception as e:
            print(f"⚠️ 填充富文本编辑器失败 {selector}: {e}")
            self.stats['failed_fills'] += 1
            return False
    
    def get_fill_stats(self) -> Dict[str, Any]:
        """
        获取填充统计信息
        
        Returns:
            统计信息字典
        """
        total = self.stats['total_attempts']
        success_rate = (self.stats['successful_fills'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'success_rate': round(success_rate, 1)
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            'total_attempts': 0,
            'successful_fills': 0,
            'failed_fills': 0,
            'skipped_fields': 0
        }
