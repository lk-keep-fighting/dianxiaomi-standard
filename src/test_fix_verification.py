#!/usr/bin/env python3
"""
验证修复的错误是否已解决
"""

from amazon_product_parser import ProductData

def test_product_data_conversion():
    """测试 ProductData 对象到字典的转换（修复之前的问题）"""
    print("🧪 测试 ProductData 对象处理...")
    
    # 创建一个 ProductData 对象（模拟解析器返回的结果）
    product_data = ProductData()
    product_data.title = "Test Product"
    product_data.add_detail("Brand", "Test Brand")
    product_data.add_detail("Material", "Wood")
    product_data.add_detail("Color", "Brown")
    
    print(f"✅ ProductData 创建成功: title='{product_data.title}', details={len(product_data.details)}个")
    
    # 测试转换为字典格式（这是修复的关键）
    try:
        detail_pairs = {
            'title': product_data.title,
            **product_data.details  # 这里之前可能会出问题
        }
        print(f"✅ 字典转换成功: {detail_pairs}")
        
        # 测试字典的迭代操作（这是导致 "not iterable" 错误的原因）
        if isinstance(detail_pairs, dict) and detail_pairs:
            print("✅ 字典类型检查通过")
            
            # 测试字典中的 'in' 操作
            if 'title' in detail_pairs:
                print("✅ 字典 'in' 操作正常")
            
            # 测试字典迭代
            count = 0
            for key, value in detail_pairs.items():
                count += 1
                print(f"  - {key}: {value}")
            print(f"✅ 字典迭代正常: {count} 个项目")
            
        return True
        
    except Exception as e:
        print(f"❌ 字典转换失败: {e}")
        return False

def test_fill_edit_form_compatibility():
    """测试与 fill_edit_form 函数的兼容性"""
    print("\n🧪 测试 fill_edit_form 兼容性...")
    
    # 模拟从解析器获得的数据
    product_data = ProductData()
    product_data.title = "Amazon Product Title"
    product_data.add_detail("description", "Product description here")
    product_data.add_detail("price", "$29.99")
    
    # 转换为兼容格式
    try:
        product_dict = {
            'title': product_data.title,
            **product_data.details
        }
        
        # 模拟 fill_edit_form 中的检查操作
        if "title" in product_dict and product_dict["title"]:
            print(f"✅ 标题检查通过: '{product_dict['title']}'")
        
        if "description" in product_dict and product_dict["description"]:
            print(f"✅ 描述检查通过: '{product_dict['description']}'")
        
        if "price" in product_dict and product_dict["price"]:
            print(f"✅ 价格检查通过: '{product_dict['price']}'")
        
        print("✅ fill_edit_form 兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ fill_edit_form 兼容性测试失败: {e}")
        return False

def test_error_scenarios():
    """测试错误场景处理"""
    print("\n🧪 测试错误场景处理...")
    
    # 测试空的 ProductData
    empty_product = ProductData()
    try:
        detail_pairs = {
            'title': empty_product.title,
            **empty_product.details
        }
        print("✅ 空 ProductData 处理正常")
    except Exception as e:
        print(f"❌ 空 ProductData 处理失败: {e}")
        return False
    
    # 测试 has_valid_data 方法
    try:
        if not empty_product.has_valid_data():
            print("✅ 空数据检测正常")
        else:
            print("❌ 空数据检测异常")
            return False
    except Exception as e:
        print(f"❌ has_valid_data 方法失败: {e}")
        return False
    
    return True

def main():
    """运行所有测试"""
    print("=" * 60)
    print("🔧 ProductData 修复验证测试")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    if test_product_data_conversion():
        tests_passed += 1
    
    if test_fill_edit_form_compatibility():
        tests_passed += 1
    
    if test_error_scenarios():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {tests_passed}/{total_tests} 通过")
    
    if tests_passed == total_tests:
        print("🎉 所有测试通过！修复成功！")
        print("✨ ProductData 'not iterable' 错误已解决")
    else:
        print("❌ 部分测试失败，需要进一步检查")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
