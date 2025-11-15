#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI内容生成结构化数据使用示例
展示如何使用new_title_and_key_features方法返回的结构化数据
"""

from src.ai_category_validator import AICategoryValidator

def example_usage():
    """演示如何使用AI生成的结构化数据"""
    
    # 初始化AI验证器
    validator = AICategoryValidator(
        api_base_url="https://api.hunyuan.cloud.tencent.com/v1",
        api_key="sk-fc0nyVUKNiqO4gYEMPtmQbai53cUoAvBVhlW4fROn69LTthI",
        model_name="hunyuan-turbos-latest"
    )
    
    # 示例产品数据
    product_title = "Server Rack Shelf Mount Tray"
    product_features = [
        "19-inch universal rack mount", 
        "Ventilated design",
        "110lb weight capacity",
        "Cantilever mounting",
        "Wall mount compatible"
    ]
    forbidden_words = "Amazon, brand, certified, tested"
    category = "Computer Accessories"
    
    print("🚀 开始AI内容生成...")
    print(f"原始标题: {product_title}")
    print(f"原始特征: {', '.join(product_features)}")
    print()
    
    # 调用AI生成内容
    result = validator.new_title_and_key_features(
        title=product_title,
        key_features=product_features,
        remove_words=forbidden_words,
        category=category
    )
    
    if result:
        print("✅ AI内容生成成功！")
        print()
        
        # 访问结构化数据
        optimized_title = result.get('title', '')
        bullet_points = result.get('bullet_points', '')
        description = result.get('description', '')
        
        # 展示如何使用数据
        print("📝 优化后的标题:")
        print(f"   {optimized_title}")
        print(f"   长度: {len(optimized_title)} 字符")
        print()
        
        print("📋 五点描述:")
        bullet_list = bullet_points.split('\n') if bullet_points else []
        for i, bullet in enumerate(bullet_list, 1):
            if bullet.strip():
                print(f"   {i}. {bullet.strip()}")
        print(f"   共 {len([b for b in bullet_list if b.strip()])} 个要点")
        print()
        
        print("📄 详情描述:")
        print(f"   {description}")
        print(f"   长度: {len(description)} 字符")
        print()
        
        # 实际应用示例
        print("🔧 实际应用示例:")
        print("# 在你的自动化脚本中可以这样使用:")
        print()
        print("# 1. 获取AI优化的内容")
        print("ai_result = validator.new_title_and_key_features(...)")
        print()
        print("# 2. 提取各个字段")
        print("if ai_result:")
        print("    product_title = ai_result['title']")
        print("    product_bullets = ai_result['bullet_points'].split('\\n')")
        print("    product_description = ai_result['description']")
        print()
        print("# 3. 在表单填充中使用")
        print("# edit_frame.locator('#title-input').fill(product_title)")
        print("# for i, bullet in enumerate(product_bullets):")
        print("#     edit_frame.locator(f'#bullet-{i+1}').fill(bullet.strip())")
        print("# edit_frame.locator('#description-textarea').fill(product_description)")
        
        return result
    else:
        print("❌ AI内容生成失败")
        return None

def structure_data_access_demo():
    """演示结构化数据访问的各种方式"""
    
    # 模拟AI返回的结构化数据
    mock_result = {
        'title': '1U Server Rack Shelf 2-Pack, 19-Inch Universal Rack Mount Tray, Ventilated Design for Equipment Cooling',
        'bullet_points': '''- Promotes airflow with ventilated design to help maintain optimal operating temperature
- Fits both full and half-width non-rack mount equipment in standard 19-inch server racks
- Suitable for various environments including studios, stage setups, and small home networks
- Compatible with all 19-inch rack systems and 1U rack spaces for easy integration
- Supports up to 110lb weight capacity with sturdy construction''',
        'description': 'These 1U server rack shelves are designed to provide a stable and ventilated platform for mounting equipment in professional and home environments.'
    }
    
    print("📊 结构化数据访问演示:")
    print()
    
    # 1. 基本访问
    print("1️⃣ 基本数据访问:")
    print(f"   标题: {mock_result['title']}")
    print(f"   标题长度: {len(mock_result['title'])} 字符")
    print()
    
    # 2. 五点描述处理
    print("2️⃣ 五点描述处理:")
    bullets = mock_result['bullet_points'].split('\n')
    for i, bullet in enumerate(bullets, 1):
        clean_bullet = bullet.strip().lstrip('- ')
        print(f"   要点{i}: {clean_bullet}")
    print()
    
    # 3. 数据验证
    print("3️⃣ 数据验证:")
    print(f"   标题是否为空: {'否' if mock_result['title'] else '是'}")
    print(f"   五点描述数量: {len([b for b in bullets if b.strip()])}")
    print(f"   详情描述长度: {len(mock_result['description'])} 字符")
    print()
    
    # 4. 格式化输出
    print("4️⃣ 格式化输出示例:")
    formatted_bullets = []
    for bullet in bullets:
        if bullet.strip():
            # 确保以"- "开头
            clean_bullet = bullet.strip()
            if not clean_bullet.startswith('- '):
                clean_bullet = '- ' + clean_bullet.lstrip('- ')
            formatted_bullets.append(clean_bullet)
    
    print("   格式化后的五点描述:")
    for bullet in formatted_bullets:
        print(f"     {bullet}")

if __name__ == "__main__":
    print("🌟 AI内容生成结构化数据使用指南")
    print("=" * 50)
    print()
    
    # 演示结构化数据访问
    structure_data_access_demo()
    
    print("\n" + "=" * 50)
    print("🔄 如果你想测试真实的AI生成，请取消下面一行的注释:")
    print("# example_usage()")
    
    # 真实AI测试（可选）
    # example_usage()