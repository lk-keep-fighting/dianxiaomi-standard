#!/usr/bin/env python3
"""
重构系统测试脚本 - 验证重构后的功能是否正常

测试内容：
1. 统一数据结构测试
2. 映射系统测试
3. 模拟表单填充测试

作者: Linus Torvalds (风格)
"""

import sys
import os
sys.path.append('src')

from product_data import ProductData, FIELD_MAPPING, FieldMappingEngine
from system_config import get_config


def test_product_data():
    """测试ProductData类"""
    print("🧪 测试ProductData类...")
    
    # 创建测试数据
    product = ProductData()
    product.title = "Test Product"
    product.add_detail("Brand", "Nike")
    product.add_detail("Manufacturer", "Nike Inc.")
    product.add_detail("Color", "Black")
    product.add_detail("Product Dimensions", "10 x 8 x 6 inches")
    product.add_detail("Item Weight", "2.5 pounds")
    
    # 测试基本功能
    assert product.has_valid_data(), "❌ has_valid_data() 测试失败"
    assert product.get_detail("Brand") == "Nike", "❌ get_detail() 测试失败"
    assert len(product.details) == 5, f"❌ 详情数量错误: {len(product.details)}"
    
    # 测试字典转换
    product_dict = product.to_dict()
    assert "title" in product_dict, "❌ to_dict() 缺少标题"
    assert "Brand" in product_dict, "❌ to_dict() 缺少品牌"
    
    print("✅ ProductData类测试通过")
    return True


def test_field_mapping():
    """测试字段映射系统"""
    print("🧪 测试字段映射系统...")
    
    # 测试基本映射
    assert FIELD_MAPPING.get_form_field("Brand") == "Brand Name", "❌ Brand映射错误"
    assert FIELD_MAPPING.get_form_field("Manufacturer") == "Manufacturer Name", "❌ Manufacturer映射错误"
    assert FIELD_MAPPING.get_form_field("Color") == "Color", "❌ Color映射错误"
    
    # 测试Key Features聚合
    key_features_keys = FIELD_MAPPING.get_key_features_keys()
    assert "Special Feature" in key_features_keys, "❌ Special Feature应该聚合到Key Features"
    assert "Style" in key_features_keys, "❌ Style应该聚合到Key Features"
    
    # 测试固定值
    assert "Is Prop 65 Warning Required" in FIELD_MAPPING.fixed_values, "❌ 缺少固定值字段"
    assert FIELD_MAPPING.fixed_values["Condition"] == "New (全新)", "❌ 固定值错误"
    
    print("✅ 字段映射系统测试通过")
    return True


def test_dimension_extraction():
    """测试尺寸提取"""
    print("🧪 测试尺寸提取...")
    
    # 创建测试产品数据
    product = ProductData()
    product.add_detail("Product Dimensions", "17.72 x 3.9 x 3.9 inches")
    
    # 测试尺寸提取
    dimensions = FIELD_MAPPING.extract_dimensions(product)
    
    assert dimensions["depth"] == "17.72", f"❌ 深度提取错误: {dimensions['depth']}"
    assert dimensions["width"] == "3.9", f"❌ 宽度提取错误: {dimensions['width']}"  
    assert dimensions["height"] == "3.9", f"❌ 高度提取错误: {dimensions['height']}"
    
    print("✅ 尺寸提取测试通过")
    return True


def test_weight_extraction():
    """测试重量提取"""
    print("🧪 测试重量提取...")
    
    # 创建测试产品数据
    product = ProductData()
    product.add_detail("Item Weight", "16 ounces")
    product.weight_value = "1.0"  # 预设重量值
    
    # 测试重量提取
    weight = FIELD_MAPPING.extract_weight(product)
    assert weight == "1.0", f"❌ 重量提取错误: {weight}"
    
    # 测试从Item Weight中提取
    product2 = ProductData()
    product2.add_detail("Item Weight", "2.5 pounds")
    weight2 = FIELD_MAPPING.extract_weight(product2)
    assert weight2 == "2.5", f"❌ 从Item Weight提取重量错误: {weight2}"
    
    print("✅ 重量提取测试通过")
    return True


def test_config_system():
    """测试配置系统"""
    print("🧪 测试配置系统...")
    
    config = get_config()
    
    # 测试基本配置
    assert config.environment in ["development", "testing", "production"], "❌ 环境配置错误"
    assert config.form_timeout > 0, "❌ 表单超时配置错误"
    assert config.wait_time > 0, "❌ 等待时间配置错误"
    
    # 测试配置验证
    assert config.validate_config(), "❌ 配置验证失败"
    
    # 测试浏览器选项
    browser_options = config.get_browser_options()
    assert "headless" in browser_options, "❌ 缺少浏览器选项"
    assert "timeout" in browser_options, "❌ 缺少超时选项"
    
    print("✅ 配置系统测试通过")
    return True


def test_mapping_simulation():
    """模拟映射流程测试"""
    print("🧪 模拟映射流程测试...")
    
    # 模拟从Amazon提取的数据
    test_amazon_data = {
        'Brand': 'Nyrvexa',
        'Color': 'White',
        'Manufacturer': 'Nyrvexa Inc.',
        'Special Feature': 'Extendable and Rotating Design',
        'Product Dimensions': '17.72 x 3.9 x 3.9 inches',
        'Item Weight': '16 ounces',
        'ASIN': 'B0FFGYSWQ9'
    }
    
    # 创建ProductData
    product = ProductData()
    product.title = "Test Power Strip"
    for key, value in test_amazon_data.items():
        product.add_detail(key, value)
    
    # 测试映射结果
    mapped_fields = []
    key_features = []
    
    for amazon_key, amazon_value in product.details.items():
        form_field = FIELD_MAPPING.get_form_field(amazon_key)
        if form_field:
            if form_field == 'Key Features':
                key_features.append(f"{amazon_key}: {amazon_value}")
            else:
                mapped_fields.append((amazon_key, form_field, amazon_value))
    
    # 验证映射结果
    brand_mapped = any(item[1] == 'Brand Name' for item in mapped_fields)
    manufacturer_mapped = any(item[1] == 'Manufacturer Name' for item in mapped_fields)
    
    assert brand_mapped, "❌ Brand字段未正确映射"
    assert manufacturer_mapped, "❌ Manufacturer字段未正确映射"
    assert len(key_features) > 0, "❌ Key Features聚合失败"
    
    # 测试尺寸提取
    dimensions = FIELD_MAPPING.extract_dimensions(product)
    assert all(dim for dim in dimensions.values()), "❌ 尺寸提取不完整"
    
    print(f"✅ 映射流程测试通过:")
    print(f"   - 映射字段数: {len(mapped_fields)}")
    print(f"   - Key Features项数: {len(key_features)}")
    print(f"   - 提取尺寸: {dimensions}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("🌟 重构系统完整性测试")
    print("=" * 50)
    
    tests = [
        ("ProductData类", test_product_data),
        ("字段映射系统", test_field_mapping), 
        ("尺寸提取", test_dimension_extraction),
        ("重量提取", test_weight_extraction),
        ("配置系统", test_config_system),
        ("映射流程模拟", test_mapping_simulation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} 测试出错: {e}")
        print()
    
    # 打印总结
    print("=" * 50)
    print(f"📊 测试结果:")
    print(f"   ✅ 通过: {passed}")
    print(f"   ❌ 失败: {failed}")
    print(f"   📈 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("🎉 所有测试通过！重构系统运行正常。")
        print("\n🚀 可以使用以下命令运行重构后的系统:")
        print("   python src/main_refactored.py")
    else:
        print("⚠️ 部分测试失败，请检查重构代码。")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
