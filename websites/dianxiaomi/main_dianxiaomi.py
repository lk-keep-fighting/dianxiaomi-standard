#!/usr/bin/env python3
"""
店小秘平台自动化工具 - 双模式版本

支持两种工作模式：
1. 全自动批量模式 - 自动遍历所有编辑按钮，批量处理产品
2. 手动审核模式 - 基于用户手动打开的编辑页进行单个产品处理，支持人工审核

作者: Linus Torvalds 风格设计
原则: 简洁、可靠、用户友好
"""

import os
import re
from playwright.sync_api import sync_playwright, Page, expect
from amazon_product_parser import AmazonProductParser
# Login credentials
user_name = "liyoutest001"
password = "Aa741852963."
storage_state = user_name + "_auth_state.json"


def login_if_needed(page: Page) -> None:
    """Handle login if not already logged in"""
    if not os.path.exists(storage_state):
        print("Logging in...")
        page.goto("https://www.dianxiaomi.com/")
        page.get_by_role("paragraph").filter(has_text=re.compile(r"^$")).first.click()
        page.get_by_role("textbox", name="请输入用户名").click()
        page.get_by_role("textbox", name="请输入用户名").fill(user_name)
        page.get_by_role("textbox", name="请输入密码").click()
        page.get_by_role("textbox", name="请输入密码").fill(password)
        input("Waiting for login and navigation to product page...\n")
        # Save authentication state
        page.context.storage_state(path=storage_state)
    else:
        print("Using existing authentication state")


def get_edit_buttons(page: Page):
    """Locate all edit buttons in the product table"""
    # Wait for the table to load
    page.wait_for_selector(".vxe-table--body")
    
    # Find all edit buttons in the table
    # Based on the HTML structure, edit buttons are in the last column with text "编辑"
    edit_buttons = page.locator(".vxe-body--row .col_16 button:has-text('编辑')")
    
    # Wait for buttons to be visible
    edit_buttons.first.wait_for(state="visible")
    
    # Return the count and the locator
    count = edit_buttons.count()
    print(f"Found {count} edit buttons")
    return edit_buttons, count


def parse_amazon_product_enhanced(context, web_url):
    """
    使用增强的亚马逊产品解析器
    
    Returns:
        ProductData: 解析后的产品数据，如果失败返回None
    """
    if not web_url or not ('amazon.com' in web_url.lower() or 'amzn.to' in web_url.lower()):
        print(f"❌ 无效的亚马逊链接: {web_url}")
        return None
    
    # 打开新的亚马逊页面
    amazon_page = context.new_page()
    
    try:
        # 导航到亚马逊产品页面
        print(f"🌐 正在打开亚马逊产品页面: {web_url}")
        amazon_page.goto(web_url + '?language=en_US&currency=USD', timeout=60000)
        print("✅ 亚马逊页面加载完成")
        
    except Exception as e:
        print(f"❌ 导航到 {web_url} 失败: {e}")
        print("💡 请检查网络连接后重新执行")
        amazon_page.close()
        return None
    
    # 使用专业的产品解析器提取数据
    try:
        product_parser = AmazonProductParser(amazon_page)
        product_data = product_parser.parse_product()
        product_parser.print_summary()
        
        # 关闭亚马逊页面
        amazon_page.close()
        
        # 检查是否解析到有效数据
        if not product_data.has_valid_data():
            print("❌ 未获取到有效的产品数据")
            return None
            
        return product_data
        
    except Exception as e:
        print(f"❌ 产品解析器出错: {e}")
        amazon_page.close()
        return None


def show_product_preview_for_dianxiaomi(product_data: ProductData):
    """
    显示产品信息预览，供用户审核 - 针对店小秘平台优化
    
    Returns:
        bool: 用户是否确认继续填充表单
    """
    print("\n" + "="*80)
    print("📋 店小秘产品信息预览 - 请审核以下数据")
    print("="*80)
    
    print(f"📝 产品标题: {product_data.title}")
    print(f"⚖️ 产品重量: {product_data.weight_value} pounds")
    
    if product_data.details:
        print(f"\n📊 产品属性 ({len(product_data.details)} 个):")
        print("-" * 60)
        
        # 显示店小秘平台重要的属性
        important_attrs = ['Brand', 'Material', 'Color', 'Style', 'Product Dimensions', 
                          'Key Features', 'Feature Description', 'Item Weight']
        shown_attrs = set()
        
        # 先显示重要属性
        for attr in important_attrs:
            if attr in product_data.details:
                value = product_data.details[attr]
                display_value = value[:50] + "..." if len(value) > 50 else value
                print(f"  🔸 {attr:<20}: {display_value}")
                shown_attrs.add(attr)
        
        # 显示其他属性（限制显示数量）
        other_count = 0
        for key, value in product_data.details.items():
            if key not in shown_attrs and other_count < 5:  # 最多显示5个其他属性
                display_value = value[:50] + "..." if len(value) > 50 else value
                print(f"  📌 {key:<20}: {display_value}")
                other_count += 1
        
        remaining = len(product_data.details) - len(shown_attrs) - other_count
        if remaining > 0:
            print(f"  ⋯  还有 {remaining} 个其他属性...")
    
    print("\n" + "="*80)
    
    while True:
        choice = input("🤔 请选择操作 [Y]继续填充 / [N]跳过 / [D]查看详情: ").strip().upper()
        
        if choice in ['Y', 'YES', '']:
            print("✅ 用户确认，开始填充表单...")
            return True
        elif choice in ['N', 'NO']:
            print("⏭️ 用户跳过，不填充表单")
            return False
        elif choice in ['D', 'DETAIL', 'DETAILS']:
            # 显示完整详情
            print("\n" + "="*60)
            print("📋 完整产品详情")
            print("="*60)
            for key, value in product_data.details.items():
                print(f"{key:<30}: {value}")
            print("="*60)
            continue
        else:
            print("❌ 无效选择，请输入 Y/N/D")


def fill_edit_form_enhanced(edit_page: Page, product_data: ProductData, manual_mode: bool = False) -> None:
    """
    增强版表单填充函数 - 针对店小秘平台优化
    
    Args:
        edit_page: 编辑页面对象
        product_data: 产品数据对象
        manual_mode: 是否为手动模式（影响填充策略）
    """
    try:
        # 转换产品数据为字典格式
        product_dict = {
            'title': product_data.title,
            **product_data.details
        }
        
        print(f"🎯 开始填充店小秘表单（{'手动审核' if manual_mode else '自动'}模式）...")
        
        # Fill product title
        if "title" in product_dict and product_dict["title"]:
            try:
                title_input = edit_page.locator("input[name='productTitleBuyer']")
                if title_input.is_visible():
                    # 针对店小秘平台优化标题长度
                    optimized_title = product_dict["title"][:200]
                    title_input.fill(optimized_title)
                    print(f"✅ 产品标题: {optimized_title[:50]}...")
            except Exception as e:
                print(f"⚠️ 标题填充失败: {e}")
        
        # Fill product description - 优先使用Key Features
        description_text = ""
        if "Key Features" in product_dict:
            description_text = product_dict["Key Features"]
        elif "Feature Description" in product_dict:
            description_text = product_dict["Feature Description"]
        elif "description" in product_dict:
            description_text = product_dict["description"]
        
        if description_text:
            try:
                desc_input = edit_page.locator("textarea[name='productDesc']")
                if desc_input.is_visible():
                    # 针对店小秘平台优化描述长度
                    optimized_desc = description_text[:1000]
                    desc_input.fill(optimized_desc)
                    print(f"✅ 产品描述: {len(optimized_desc)} 字符")
            except Exception as e:
                print(f"⚠️ 描述填充失败: {e}")
        
        # Fill price (if available)
        if "price" in product_dict and product_dict["price"]:
            try:
                price_inputs = edit_page.locator("input[placeholder*='价格'], input[placeholder*='price']")
                if price_inputs.count() > 0:
                    # 清理价格数据
                    clean_price = re.sub(r'[^\\d.]', '', product_dict["price"])
                    if clean_price:
                        price_inputs.first.fill(clean_price)
                        print(f"✅ 产品价格: {clean_price}")
            except Exception as e:
                print(f"⚠️ 价格填充失败: {e}")
        
        # 在手动模式下，显示更多可填充的字段信息
        if manual_mode:
            fillable_fields = ['Brand', 'Material', 'Color', 'Style']
            available_fields = [field for field in fillable_fields if field in product_dict]
            if available_fields:
                print("📋 可用属性信息:")
                for field in available_fields:
                    print(f"  - {field}: {product_dict[field]}")
        
        print("✅ 表单填充完成")
        
    except Exception as e:
        print(f"❌ 表单填充失败: {e}")


def save_product_changes_enhanced(edit_page: Page, manual_mode: bool = False) -> bool:
    """
    增强版保存函数 - 针对店小秘平台优化
    
    Args:
        edit_page: 编辑页面对象
        manual_mode: 是否为手动模式
        
    Returns:
        bool: 保存是否成功
    """
    try:
        if manual_mode:
            # 手动模式：询问用户是否保存
            while True:
                save_choice = input("💾 是否保存产品? [Y]是 / [N]否: ").strip().upper()
                if save_choice in ['Y', 'YES', '']:
                    break
                elif save_choice in ['N', 'NO']:
                    print("⏭️ 用户选择不保存")
                    return False
                else:
                    print("❌ 无效选择，请输入 Y 或 N")
        
        # 查找保存按钮
        save_button = edit_page.get_by_role("button", name="保存")
        if not save_button.is_visible():
            # Try alternative selectors
            save_button = edit_page.locator("button:has-text('保存'), button[type='submit']")
        
        if save_button.is_visible():
            save_button.click()
            print("✅ 产品已保存")
            # Wait for save confirmation
            edit_page.wait_for_timeout(2000)
            return True
        else:
            print("❌ 未找到保存按钮")
            return False
            
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return False


def process_product_edit_enhanced(context, page: Page, edit_button, manual_mode: bool = False) -> bool:
    """
    增强版单个产品处理函数
    
    Args:
        context: Playwright上下文
        page: 主页面对象
        edit_button: 编辑按钮元素
        manual_mode: 是否为手动审核模式
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # Click the edit button
        print("🔍 点击编辑按钮...")
        with page.context.expect_page() as edit_page_info:
            edit_button.click()
        
        edit_page = edit_page_info.value
        edit_page.wait_for_load_state("networkidle")
        print("✅ 编辑页面已打开")
        
        # Extract web_url from the sourceUrl input field
        try:
            web_url = edit_page.locator("input[name='sourceUrl']").input_value()
            print(f"🔗 提取产品链接: {web_url[:60]}...")
        except Exception as e:
            print(f"⚠️ 提取链接失败: {e}")
            web_url = None
        
        if not web_url:
            print("❌ 未找到访问链接，跳过此产品")
            edit_page.close()
            return False
        
        # 解析亚马逊产品数据
        product_data = parse_amazon_product_enhanced(context, web_url)
        
        if not product_data:
            print("❌ 产品解析失败")
            edit_page.close()
            return False
        
        # 根据模式决定是否显示预览
        should_fill = True
        if manual_mode:
            should_fill = show_product_preview_for_dianxiaomi(product_data)
        
        if should_fill:
            # 填充表单
            fill_edit_form_enhanced(edit_page, product_data, manual_mode)
            
            # 保存产品
            save_success = save_product_changes_enhanced(edit_page, manual_mode)
            
            edit_page.close()
            return save_success
        else:
            print("⏭️ 跳过当前产品")
            edit_page.close()
            return False
            
    except Exception as e:
        print(f"❌ 处理产品时出错: {e}")
        try:
            edit_page.close()
        except:
            pass
        return False


def choose_mode_for_dianxiaomi():
    """
    让用户选择店小秘平台的操作模式
    
    Returns:
        str: 'manual' 或 'auto'
    """
    print("\n" + "="*80)
    print("🛍️ 店小秘平台自动化工具 - 双模式版本")
    print("="*80)
    print("请选择操作模式：")
    print()
    print("1️⃣  手动审核模式 (推荐)")
    print("   - 对每个产品进行人工审核")
    print("   - 可预览产品信息后决定是否填充")  
    print("   - 确保数据质量和准确性")
    print("   - 支持跳过不需要的产品")
    print()
    print("2️⃣  全自动批量模式")
    print("   - 自动处理所有产品")
    print("   - 无需人工干预")
    print("   - 快速批量处理")
    print("   - 适合标准化产品")
    print()
    
    while True:
        choice = input("请选择模式 [1]手动审核 / [2]全自动: ").strip()
        
        if choice in ['1', 'manual', '手动']:
            print("✅ 已选择：手动审核模式")
            return 'manual'
        elif choice in ['2', 'auto', '自动']:
            print("✅ 已选择：全自动批量模式")
            return 'auto'
        else:
            print("❌ 无效选择，请输入 1 或 2")


def run_manual_mode(context, page):
    """手动审核模式 - 逐个产品审核"""
    print("\n" + "🔍"*20)
    print("🎯 店小秘手动审核模式")
    print("🔍"*20)
    
    # Get all edit buttons
    edit_buttons, count = get_edit_buttons(page)
    
    if count == 0:
        print("❌ 未找到编辑按钮!")
        return
    
    print(f"📊 发现 {count} 个产品待处理")
    
    processed = 0
    skipped = 0
    errors = 0
    
    # Process each product with manual review
    for i in range(count):
        print(f"\n{'='*60}")
        print(f"🔍 处理产品 {i+1}/{count}")
        print("="*60)
        
        try:
            # Get fresh reference to the button (DOM might change)
            buttons, _ = get_edit_buttons(page)
            if i < buttons.count():
                success = process_product_edit_enhanced(context, page, buttons.nth(i), manual_mode=True)
                if success:
                    processed += 1
                    print(f"✅ 产品 {i+1} 处理完成")
                else:
                    skipped += 1
                    print(f"⏭️ 产品 {i+1} 已跳过")
            else:
                print(f"⚠️ 产品 {i+1} 按钮索引超出范围，跳过")
                skipped += 1
                
        except Exception as e:
            print(f"❌ 处理产品 {i+1} 时出错: {e}")
            errors += 1
        
        # 询问是否继续
        if i < count - 1:  # 不是最后一个产品
            print(f"\n📊 当前进度: 已处理 {processed}, 已跳过 {skipped}, 错误 {errors}")
            continue_choice = input("🤔 继续下一个产品? [Y]是 / [N]结束: ").strip().upper()
            if continue_choice in ['N', 'NO']:
                print("🛑 用户选择结束处理")
                break
        
        # Wait between operations
        page.wait_for_timeout(2000)
    
    print(f"\n{'='*80}")
    print("📊 手动审核模式处理完成")
    print(f"✅ 成功处理: {processed} 个产品")
    print(f"⏭️ 跳过: {skipped} 个产品") 
    print(f"❌ 错误: {errors} 个产品")
    print("="*80)


def run_auto_mode(context, page):
    """全自动批量模式 - 批量处理所有产品"""
    print("\n" + "🤖"*20)
    print("🚀 店小秘全自动批量模式")
    print("🤖"*20)
    
    # Get all edit buttons
    edit_buttons, count = get_edit_buttons(page)
    
    if count == 0:
        print("❌ 未找到编辑按钮!")
        return
    
    print(f"🚀 将自动处理 {count} 个产品...")
    
    processed = 0
    skipped = 0
    errors = 0
    
    # Process each product automatically
    for i in range(count):
        print(f"\n🤖 自动处理产品 {i+1}/{count}")
        
        try:
            # Get fresh reference to the button (DOM might change)
            buttons, _ = get_edit_buttons(page)
            if i < buttons.count():
                success = process_product_edit_enhanced(context, page, buttons.nth(i), manual_mode=False)
                if success:
                    processed += 1
                    print(f"✅ 产品 {i+1} 自动处理完成")
                else:
                    skipped += 1
                    print(f"⏭️ 产品 {i+1} 自动跳过")
            else:
                print(f"⚠️ 产品 {i+1} 按钮索引超出范围，跳过")
                skipped += 1
                
        except Exception as e:
            print(f"❌ 自动处理产品 {i+1} 时出错: {e}")
            errors += 1
        
        # Wait between operations
        page.wait_for_timeout(3000)
    
    print(f"\n{'='*80}")
    print("🤖 全自动批量模式处理完成")
    print(f"✅ 成功处理: {processed} 个产品")
    print(f"⏭️ 跳过: {skipped} 个产品")
    print(f"❌ 错误: {errors} 个产品")
    print("="*80)


def run_automation_dual_mode():
    """双模式主程序入口"""
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        
        # Create context with or without stored authentication
        if os.path.exists(storage_state):
            context = browser.new_context(storage_state=storage_state, no_viewport=True)
        else:
            context = browser.new_context(no_viewport=True)
        
        page = context.new_page()
        
        try:
            # Login if needed
            login_if_needed(page)
            
            # Navigate to product management page
            page.goto("https://www.dianxiaomi.com/web/sheinProduct/draft")
            
            # Wait for page to load
            page.wait_for_load_state("networkidle")
            
            # Choose operation mode
            mode = choose_mode_for_dianxiaomi()
            
            # Execute based on selected mode
            if mode == 'manual':
                run_manual_mode(context, page)
            else:
                run_auto_mode(context, page)
            
        except KeyboardInterrupt:
            print("\n\n⏹️ 用户中断操作")
        except Exception as e:
            print(f"\n❌ 程序执行出错: {e}")
        finally:
            print("\n" + "="*80)
            print("🎯 店小秘自动化处理完成")
            print("="*80)
            input("按 Enter 键退出程序并关闭浏览器...")
            browser.close()


if __name__ == "__main__":
    run_automation_dual_mode()
