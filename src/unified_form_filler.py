#!/usr/bin/env python3
"""
统一表单填充引擎 - 重构后的单一表单填充系统

设计原则：
1. Single Source of Truth - 一套映射系统
2. Good Taste - 简单的字段填充逻辑
3. No Duplication - 不再有多套实现

作者: Linus Torvalds (风格)
"""

import time
from typing import Dict, List, Any, Optional
from playwright.sync_api import Frame, Page
from product_data import ProductData, FIELD_MAPPING


class UnifiedFormFiller:
    """
    统一表单填充引擎
    
    职责：
    1. 使用统一的映射系统填充表单
    2. 处理各种表单元素类型（文本框、下拉框、编辑器）
    3. 提供填充结果反馈
    """
    
    def __init__(self, frame: Frame, page: Optional[Page] = None, timeout: int = 1000):
        self.frame = frame
        self.page = page
        self.timeout = timeout
        self.wait_time = 200  # 基于验证可行的等待时间
        
        # 填充统计
        self.fill_stats = {
            'total_attempts': 0,
            'successful_fills': 0,
            'failed_fills': 0,
            'skipped_fields': 0
        }
    
    def fill_form(self, product_data: ProductData) -> Dict[str, Any]:
        """
        主要的表单填充方法
        
        Args:
            product_data: 统一的产品数据结构
        
        Returns:
            填充结果统计
        """
        print("🔄 开始统一表单填充...")
        
        try:
            # 1. 填充固定值字段
            self._fill_fixed_values()
            
            # 2. 填充映射字段
            self._fill_mapped_fields(product_data)
            
            # 3. 填充Key Features
            self._fill_key_features(product_data)
            
            # 4. 填充复合字段（尺寸、重量等）
            self._fill_compound_fields(product_data)
            
            print("✅ 统一表单填充完成")
            return self.fill_stats
            
        except Exception as e:
            print(f"❌ 表单填充发生错误: {e}")
            self.fill_stats['error'] = str(e)
            return self.fill_stats
    
    def _fill_fixed_values(self) -> None:
        """填充固定值字段"""
        print("⚙️ 填充固定值字段...")
        
        for field_name, value in FIELD_MAPPING.fixed_values.items():
            try:
                self._fill_form_field(field_name, value)
                self._wait()
            except Exception as e:
                print(f"⚠️ 填充固定字段 {field_name} 失败: {e}")
                self.fill_stats['failed_fills'] += 1
    
    def _fill_mapped_fields(self, product_data: ProductData) -> None:
        """填充映射字段"""
        print("⚙️ 填充映射字段...")
        
        for amazon_key, amazon_value in product_data.details.items():
            form_field = FIELD_MAPPING.get_form_field(amazon_key)
            
            if form_field and form_field != 'Key Features':
                try:
                    print(f"✅ 映射匹配: {amazon_key} -> {form_field}")
                    self._fill_form_field(form_field, amazon_value)
                    self._wait()
                    self.fill_stats['successful_fills'] += 1
                except Exception as e:
                    print(f"⚠️ 填充映射字段 {form_field} 失败: {e}")
                    self.fill_stats['failed_fills'] += 1
            else:
                # 检查是否是制造商相关的未匹配字段
                if 'manufacturer' in amazon_key.lower() or 'brand' in amazon_key.lower():
                    if not form_field:
                        print(f"⚠️ 未匹配的制造商相关键: {amazon_key} = {amazon_value}")
    
    def _fill_key_features(self, product_data: ProductData) -> None:
        """填充Key Features字段（TinyMCE编辑器）"""
        print("⚙️ 填充Key Features编辑器...")
        
        # 收集所有应该聚合到Key Features的内容
        key_features = []
        key_features_keys = FIELD_MAPPING.get_key_features_keys()
        
        for amazon_key, amazon_value in product_data.details.items():
            if amazon_key in key_features_keys:
                key_features.append(f"{amazon_key}: {amazon_value}")
        
        if key_features:
            try:
                features_text = "\\n".join(key_features)
                self._fill_tinymce_editor('Key Features', features_text)
                self._wait()
                self.fill_stats['successful_fills'] += 1
            except Exception as e:
                print(f"⚠️ 填充Key Features失败: {e}")
                self.fill_stats['failed_fills'] += 1
    
    def _fill_compound_fields(self, product_data: ProductData) -> None:
        """填充复合字段（尺寸、重量等）"""
        print("⚙️ 填充复合字段...")
        
        # 提取尺寸和重量数据
        dimensions = FIELD_MAPPING.extract_dimensions(product_data)
        weight_value = FIELD_MAPPING.extract_weight(product_data)
        
        # 填充尺寸字段
        dimension_fields = ['Assembled Product Depth', 'Assembled Product Width', 'Assembled Product Height']
        dimension_values = [dimensions.get('depth'), dimensions.get('width'), dimensions.get('height')]
        
        for field_name, value in zip(dimension_fields, dimension_values):
            if value and field_name in FIELD_MAPPING.compound_fields:
                try:
                    compound_config = FIELD_MAPPING.compound_fields[field_name]
                    unit = compound_config.get('unit', 'in (英寸)')
                    self._fill_compound_field(field_name, value, unit)
                    self.fill_stats['successful_fills'] += 1
                except Exception as e:
                    print(f"⚠️ 填充尺寸字段 {field_name} 失败: {e}")
                    self.fill_stats['failed_fills'] += 1
        
        # 填充重量字段
        if weight_value and weight_value != "10":
            try:
                compound_config = FIELD_MAPPING.compound_fields['Assembled Product Weight']
                unit = compound_config.get('unit', 'lb (磅)')
                self._fill_compound_field('Assembled Product Weight', weight_value, unit)
                self.fill_stats['successful_fills'] += 1
            except Exception as e:
                print(f"⚠️ 填充重量字段失败: {e}")
                self.fill_stats['failed_fills'] += 1
        
        # 填充Net Content
        try:
            net_content_config = FIELD_MAPPING.compound_fields['Net Content']
            measure = net_content_config.get('measure', '1')
            unit = net_content_config.get('unit', 'Each (每个)')
            self._fill_compound_field('Net Content', measure, unit)
            self.fill_stats['successful_fills'] += 1
        except Exception as e:
            print(f"⚠️ 填充Net Content失败: {e}")
            self.fill_stats['failed_fills'] += 1
    
    def _fill_form_field(self, attrkey: str, value: str) -> None:
        """
        填充表单字段 - 基于验证可行的逻辑
        
        Good Taste: 简单的元素定位和填充，支持多种输入类型
        """
        print(f"📝 填充字段 {attrkey}: {value}")
        self.fill_stats['total_attempts'] += 1
        
        # 定位字段容器
        field_container = self.frame.locator(f"div[attrkey='{attrkey}']")
        field_container.wait_for(state="visible", timeout=self.timeout)
        
        # 1. 尝试文本域（优先）
        textarea = field_container.locator("textarea")
        if textarea.count() > 0:
            textarea.first.fill(str(value))
            print(f"✅ 成功填充文本域: {attrkey}")
            return
        
        # 2. 尝试下拉选择
        select_container = field_container.locator("div[class='select2-container selectBatchAdd']")
        if select_container.count() > 0:
            try:
                # 点击打开下拉菜单
                select_container.get_by_role("link", name="请选择").click(timeout=self.timeout)
                
                # 等待下拉菜单加载
                self._wait()
                
                # 尝试选择选项
                option = self.frame.get_by_role("option", name=value)
                if option.count() > 0:
                    option.click()
                    print(f"✅ 成功选择下拉选项: {attrkey} = {value}")
                    return
                else:
                    # 尝试部分匹配
                    partial_option = self.frame.get_by_role("option").filter(has_text=value[:10])
                    if partial_option.count() > 0:
                        partial_option.first.click()
                        print(f"✅ 成功选择下拉选项 (部分匹配): {attrkey}")
                        return
                
                # 如果没找到，关闭下拉菜单
                if self.page:
                    self.page.keyboard.press("Escape")
                print(f"⚠️ 未找到匹配的选项: {value}")
            except Exception as dropdown_error:
                print(f"⚠️ 下拉选择失败 {attrkey}: {dropdown_error}")
        
        # 3. 尝试普通输入框
        input_field = field_container.locator("input[type='text']")
        if input_field.count() > 0:
            input_field.first.fill(str(value))
            input_field.first.press("Enter")
            print(f"✅ 成功填充输入框: {attrkey}")
            return
        
        print(f"⚠️ 未找到合适的输入元素: {attrkey}")
    
    def _fill_tinymce_editor(self, attrkey: str, content: str) -> None:
        """填充TinyMCE编辑器"""
        print(f"📝 填充TinyMCE编辑器 {attrkey}: {content[:50]}...")
        
        # 定位 Key Features 容器
        key_features_container = self.frame.locator(f"div[attrkey='{attrkey}']")
        key_features_container.wait_for(state="visible", timeout=self.timeout)
        
        # 定位 TinyMCE iframe
        iframes = key_features_container.locator("iframe")
        
        if iframes.count() > 0:
            # 获取第一个 iframe
            iframe = iframes.first
            iframe_content = iframe.content_frame
            
            # 填充内容
            body = iframe_content.locator("body")
            body.fill(content)
            
            print(f"✅ 成功填充TinyMCE编辑器: {attrkey}")
        else:
            print(f"⚠️ 未找到TinyMCE编辑器iframe: {attrkey}")
    
    def _fill_compound_field(self, attrkey: str, measure_value: str, unit: str) -> None:
        """填充复合字段（数值 + 单位）"""
        print(f"📝 填充复合字段 {attrkey}: {measure_value} {unit}")
        
        # 1. 填充数值部分
        measure_input = self.frame.locator(f"div[attrkey='{attrkey}'] input[class='select2-input select2-default']")
        if measure_input.count() > 0:
            measure_input.fill(measure_value, timeout=self.timeout)
            # 按Enter提交
            self.frame.locator(f"div[attrkey='{attrkey}'] input[class='select2-input']").press("Enter")
            print(f"✅ 成功填充数值部分: {measure_value}")
        else:
            print(f"⚠️ 未找到数值输入框: {attrkey}")
        
        # 等待UI响应
        self._wait()
        
        # 2. 选择单位
        unit_dropdown = self.frame.locator(f"div[attrkey='{attrkey}'] div[class='select2-container selectBatchAdd']")
        if unit_dropdown.count() > 0:
            # 点击打开下拉菜单
            unit_dropdown.get_by_role("link", name="请选择").click(timeout=self.timeout)
            
            # 等待下拉菜单加载
            self._wait()
            
            # 选择单位选项
            unit_option = self.frame.get_by_role("option", name=unit)
            if unit_option.count() > 0:
                unit_option.click()
                print(f"✅ 成功选择单位: {unit}")
            else:
                # 尝试部分匹配
                partial_unit = unit.split(' ')[0]  # 只使用单位的第一部分
                partial_option = self.frame.get_by_role("option").filter(has_text=partial_unit)
                if partial_option.count() > 0:
                    partial_option.first.click()
                    print(f"✅ 成功选择单位 (部分匹配): {partial_unit}")
                else:
                    print(f"⚠️ 未找到单位选项: {unit}")
        else:
            print(f"⚠️ 未找到单位下拉菜单: {attrkey}")
        
        print(f"✅ 复合字段填充完成: {attrkey}")
    
    def _wait(self) -> None:
        """等待UI响应"""
        if self.page:
            self.page.wait_for_timeout(self.wait_time)
        else:
            time.sleep(self.wait_time / 1000)
    
    def print_fill_stats(self) -> None:
        """打印填充统计"""
        print(f"\n📊 表单填充统计:")
        print(f"   总尝试次数: {self.fill_stats['total_attempts']}")
        print(f"   成功填充: {self.fill_stats['successful_fills']}")
        print(f"   填充失败: {self.fill_stats['failed_fills']}")
        print(f"   跳过字段: {self.fill_stats['skipped_fields']}")
        
        if self.fill_stats['total_attempts'] > 0:
            success_rate = (self.fill_stats['successful_fills'] / self.fill_stats['total_attempts']) * 100
            print(f"   成功率: {success_rate:.1f}%")
