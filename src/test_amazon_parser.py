#!/usr/bin/env python3
"""
Amazon Product Parser 测试脚本

用于验证 AmazonProductParser 类的功能
"""

import sys
import os
from playwright.sync_api import sync_playwright
from amazon_product_parser import AmazonProductParser, ProductData


def test_parser_with_url(url: str):
    """
    使用真实的亚马逊URL测试解析器
    """
    print("=" * 80)
    print("🧪 Amazon Product Parser 测试")
    print("=" * 80)
    print(f"📍 测试URL: {url}")
    
    with sync_playwright() as playwright:
        # 启动浏览器
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 导航到页面
            print("🌐 正在打开页面...")
            page.goto(url + '?language=en_US&currency=USD', timeout=60000)
            print("✅ 页面加载完成")
            
            # 创建解析器并解析
            parser = AmazonProductParser(page)
            product_data = parser.parse_product()
            
            # 显示解析结果
            parser.print_summary()
            
            # 额外的测试验证
            print("\n" + "=" * 40)
            print("🔬 测试结果验证")
            print("=" * 40)
            
            # 验证基础数据
            if product_data.title:
                print(f"✅ 标题解析: 成功 ({len(product_data.title)} 字符)")
            else:
                print("❌ 标题解析: 失败")
            
            if product_data.weight_value and product_data.weight_value != '10':
                print(f"✅ 重量解析: 成功 ({product_data.weight_value} pounds)")
            else:
                print("⚠️ 重量解析: 使用默认值或解析失败")
            
            # 验证详情数量
            details_count = len(product_data.details)
            if details_count > 5:
                print(f"✅ 详情解析: 优秀 ({details_count} 个属性)")
            elif details_count > 0:
                print(f"⚠️ 详情解析: 一般 ({details_count} 个属性)")
            else:
                print("❌ 详情解析: 失败，未找到任何属性")
            
            # 验证关键属性
            key_attributes = ['Material', 'Brand', 'Style', 'Key Features', 'Feature Description']
            found_key_attrs = [attr for attr in key_attributes if attr in product_data.details]
            
            if len(found_key_attrs) >= 3:
                print(f"✅ 关键属性: 优秀 (找到 {len(found_key_attrs)} 个关键属性)")
            elif len(found_key_attrs) > 0:
                print(f"⚠️ 关键属性: 一般 (找到 {len(found_key_attrs)} 个关键属性)")
            else:
                print("❌ 关键属性: 未找到重要属性")
            
            # 验证解析成功状态
            if product_data.parse_success:
                print("✅ 解析状态: 成功")
            else:
                print("❌ 解析状态: 失败")
                if product_data.parse_errors:
                    print("错误详情:")
                    for error in product_data.parse_errors:
                        print(f"  - {error}")
            
            # 计算总体评分
            score = 0
            if product_data.title: score += 25
            if product_data.weight_value != '10': score += 15
            if details_count > 5: score += 30
            elif details_count > 0: score += 15
            if len(found_key_attrs) >= 3: score += 30
            elif len(found_key_attrs) > 0: score += 15
            
            print(f"\n📊 解析器综合评分: {score}/100")
            if score >= 80:
                print("🎉 解析器表现: 优秀")
            elif score >= 60:
                print("👍 解析器表现: 良好")
            elif score >= 40:
                print("⚠️ 解析器表现: 一般")
            else:
                print("❌ 解析器表现: 需要改进")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
        
        finally:
            browser.close()
            print("\n🔚 测试完成")


def test_product_data_structure():
    """
    测试 ProductData 数据结构
    """
    print("\n" + "=" * 40)
    print("🧪 ProductData 数据结构测试")
    print("=" * 40)
    
    # 创建测试数据
    product = ProductData()
    
    # 测试基础功能
    print("测试基础功能...")
    assert product.title == ""
    assert product.weight_value == "10"
    assert len(product.details) == 0
    assert not product.parse_success
    assert len(product.parse_errors) == 0
    print("✅ 基础数据结构正确")
    
    # 测试添加详情
    product.add_detail("Material", "Wood")
    product.add_detail("Color", "Brown")
    product.add_detail("", "Empty Key")  # 应该被忽略
    product.add_detail("Brand", "")      # 应该被忽略
    
    assert len(product.details) == 2
    assert product.get_detail("Material") == "Wood"
    assert product.get_detail("Color") == "Brown"
    assert product.get_detail("NonExistent", "default") == "default"
    print("✅ 详情添加和获取功能正确")
    
    # 测试数据验证
    product.title = "Test Product"
    assert product.has_valid_data()
    print("✅ 数据验证功能正确")
    
    # 测试空数据
    empty_product = ProductData()
    assert not empty_product.has_valid_data()
    print("✅ 空数据检测正确")
    
    print("🎉 ProductData 测试全部通过!")


if __name__ == "__main__":
    # 首先测试数据结构
    # test_product_data_structure()
    
    # 如果提供了URL参数，则进行实际解析测试
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        if test_url.startswith('http'):
            test_parser_with_url(test_url)
        else:
            print("❌ 请提供有效的亚马逊产品URL")
    else:
        print("\n💡 使用方法:")
        print("python test_amazon_parser.py <amazon_product_url>")
        print("\n示例:")
        print("python test_amazon_parser.py https://www.amazon.com/dp/B08N5WRWNW")
        
        # 提供一些测试URL示例
        test_urls = [
            "https://www.amazon.com/name/dp/B0F5WP4MCY/?th=1", #多规格
            "https://www.amazon.com/name/dp/B0FC2F17FQ/?th=1",  # 单规格
            "https://www.amazon.com/dp/B074V9J8SD?th=1", # 多规格，含纯文本，且主子规格顺序颠倒
        ]
        
        print("\n📋 可以用于测试的URL示例:")
        for i, url in enumerate(test_urls, 1):
            print(f"  {i}. {url}")
