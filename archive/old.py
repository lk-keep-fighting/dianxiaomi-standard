#!/usr/bin/env python3
"""
旧版表单填充代码片段 - 用于参考和验证新实现
从main.py中提取的关键操作模式
"""

def old_form_filling_logic(frame, detail_pairs, page, weight_value):
    """
    旧版表单填充逻辑 - 从main.py注释代码中提取的关键模式
    用于理解和验证新实现的正确性
    """
    
    # === 旧代码中的关键模式 ===
    
    # 1. 尺寸数据提取模式
    if 'Product Dimensions' in detail_pairs:
        dimensions_str = str(detail_pairs['Product Dimensions'])
        print(f"Raw Product Dimensions string: {repr(dimensions_str)}")
        
        # 优化分割逻辑确保准确提取数值
        parts = dimensions_str.split('x')
        depth = parts[0].strip().split('"')[0] if len(parts) > 0 else None
        width = parts[1].strip().split('"')[0] if len(parts) > 1 else None
        height = parts[2].strip().split('"')[0] if len(parts) > 2 else None
        print(f"获取到尺寸值 - Depth: {depth}, Width: {width}, Height: {height}")
    
    # 2. 基础配置
    waitTime = 200
    fill_timeout = 1000
    
    # === 旧代码中的字段填充模式 ===
    
    # 3. 简单文本输入模式 
    def fill_simple_textbox():
        try:
            frame.get_by_role("textbox", name="请输入").first.fill("NONE")
        except Exception as e:
            print(f"填写NONE失败: {e}")
    
    # 4. 下拉选择模式 (带选项文本)
    def fill_select_with_option_text():
        try:
            frame.locator("div[attrkey='Is Prop 65 Warning Required'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="No (否)").click()
        except Exception as e:
            print(f"设置Prop 65失败: {e}")
    
    # 5. Select2输入模式 (可输入的下拉)
    def fill_select2_input_pattern():
        try:
            frame.locator("div[attrkey='Age Group'] input[class='select2-input select2-default']").fill('Adult (成人)', timeout=fill_timeout)
            frame.locator("div[attrkey='Age Group'] input[class='select2-input select2-focused']").press("Enter")
        except Exception as e:
            print(f"设置Age Group失败: {e}")
    
    # 6. 复合字段模式 (数值+单位)
    def fill_compound_field_pattern():
        try:
            # 填充数值
            frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input select2-default']").fill(depth, timeout=fill_timeout)
            frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input']").press("Enter")
            
            # 选择单位
            frame.locator("div[attrkey='Assembled Product Depth'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="in (英寸)").click()
        except Exception as e:
            print(f"设置Depth单位失败: {e}")
    
    # 7. 文本域模式
    def fill_textarea_pattern():
        try:
            color_val = str(detail_pairs.get('Color', ''))
            frame.locator("div[attrkey='Color'] textarea").fill(color_val, timeout=fill_timeout)
        except Exception as e:
            print(f"填写Color失败: {e}")
    
    # 8. 等待时间模式
    def wait_pattern():
        page.wait_for_timeout(waitTime)


# === 从旧代码中提取的具体字段操作 ===

def old_specific_field_operations(frame, detail_pairs, page, weight_value):
    """
    旧代码中具体字段的操作方式 - 用于验证新实现
    """
    waitTime = 200
    fill_timeout = 1000
    
    # 处理尺寸数据
    if 'Product Dimensions' in detail_pairs:
        dimensions_str = str(detail_pairs['Product Dimensions'])
        parts = dimensions_str.split('x')
        depth = parts[0].strip().split('"')[0] if len(parts) > 0 else None
        width = parts[1].strip().split('"')[0] if len(parts) > 1 else None  
        height = parts[2].strip().split('"')[0] if len(parts) > 2 else None
        color_val = str(detail_pairs.get('Color', ''))
        
        # 基础字段填充
        try:
            frame.get_by_role("textbox", name="请输入").first.fill("NONE")
        except Exception as e:
            print(f"填写NONE失败: {e}")
        
        # Prop 65 Warning
        try:
            frame.locator("div[attrkey='Is Prop 65 Warning Required'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="No (否)").click()
        except Exception as e:
            print(f"设置Prop 65失败: {e}")
        
        page.wait_for_timeout(waitTime)
        
        # Age Group
        try:
            frame.locator("div[attrkey='Age Group'] input[class='select2-input select2-default']").fill('Adult (成人)', timeout=fill_timeout)
            frame.locator("div[attrkey='Age Group'] input[class='select2-input select2-focused']").press("Enter")
        except Exception as e:
            print(f"设置Age Group失败: {e}")
        
        page.wait_for_timeout(waitTime)
        
        # 深度 (Depth)
        try:
            frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input select2-default']").fill(depth, timeout=fill_timeout)
            frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input']").press("Enter")
            frame.locator("div[attrkey='Assembled Product Depth'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="in (英寸)").click()
        except Exception as e:
            print(f"设置Depth单位失败: {e}")
        
        page.wait_for_timeout(waitTime)
        
        # 宽度 (Width)
        try:
            frame.locator("div[attrkey='Assembled Product Width'] input[class='select2-input select2-default']").fill(width, timeout=fill_timeout)
            frame.locator("div[attrkey='Assembled Product Width'] input[class='select2-input']").press("Enter")
            frame.locator("div[attrkey='Assembled Product Width'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="in (英寸)").click()
        except Exception as e:
            print(f"设置Width单位失败: {e}")
            
        page.wait_for_timeout(waitTime)
        
        # 高度 (Height)  
        try:
            frame.locator("div[attrkey='Assembled Product Height'] input[class='select2-input select2-default']").fill(height, timeout=fill_timeout)
            frame.locator("div[attrkey='Assembled Product Height'] input[class='select2-input']").press("Enter")
            frame.locator("div[attrkey='Assembled Product Height'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="in (英寸)").click()
        except Exception as e:
            print(f"设置Height单位失败: {e}")
            
        page.wait_for_timeout(waitTime)
        
        # 重量 (Weight)
        try:
            frame.locator("div[attrkey='Assembled Product Weight'] input[class='select2-input select2-default']").fill(weight_value, timeout=fill_timeout)
            frame.locator("div[attrkey='Assembled Product Weight'] input[class='select2-input']").press("Enter")
            frame.locator("div[attrkey='Assembled Product Weight'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="lb (磅)").click()
        except Exception as e:
            print(f"设置Weight单位失败: {e}")
            
        page.wait_for_timeout(waitTime)
        
        # 颜色 (Color)
        try:
            frame.locator("div[attrkey='Color'] textarea").fill(color_val, timeout=fill_timeout)
        except Exception as e:
            print(f"填写Color失败: {e}")
            
        # 条件 (Condition)
        try:
            frame.locator("div[attrkey='Condition'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="New (全新)").click()
        except Exception as e:
            print(f"设置Condition单位失败: {e}")
            
        page.wait_for_timeout(waitTime)
        
        # 保修 (Warranty)
        try:
            frame.locator("div[attrkey='Has Written Warranty'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="No (否)").click(timeout=fill_timeout)
        except Exception as e:
            print(f"设置Has Written Warranty单位失败: {e}")
            
        page.wait_for_timeout(waitTime)
        
        # 净含量 (Net Content)
        try:
            frame.locator("div[attrkey='Net Content'] input[class='select2-input select2-default']").fill('1', timeout=fill_timeout)
            frame.locator("div[attrkey='Net Content'] input[class='select2-input']").press("Enter")
            frame.locator("div[attrkey='Net Content'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
            frame.get_by_role("option", name="Each (每个)").click()
        except Exception as e:
            print(f"设置Net Content单位失败: {e}")
            
        page.wait_for_timeout(waitTime)
        
        # 推荐位置 (Recommended Locations)
        try:
            frame.locator("div[attrkey='Recommended Locations'] input[class='select2-input select2-default']").fill('Indoor', timeout=fill_timeout)
            frame.locator("div[attrkey='Recommended Locations'] input[class='select2-input select2-focused']").press("Enter")
        except Exception as e:
            print(f"设置Recommended Locations单位失败: {e}")
            
        page.wait_for_timeout(waitTime)
        
        # 小零件警告码 (Small Parts Warning Code)
        try:
            frame.locator("div[attrkey='Small Parts Warning Code'] input[class='select2-input select2-default']").fill('0', timeout=fill_timeout)
            frame.locator("div[attrkey='Small Parts Warning Code'] input[class='select2-input select2-focused']").press("Enter")
        except Exception as e:
            print(f"设置Small Parts Warning Code单位失败: {e}")
        
        print(f"填充完毕，尺寸值 - Depth: {depth}, Width: {width}, Height: {height}")
