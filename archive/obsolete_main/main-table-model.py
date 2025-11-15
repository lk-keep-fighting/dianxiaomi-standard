import re
from socket import timeout
from turtle import title
from playwright.sync_api import Playwright, sync_playwright, expect
import os
import time
import datetime
import sys
from form_config_listener import FormConfigListener, FormFieldParser
from dynamic_form_filler import DynamicFormFiller
from amazon_product_parser import AmazonProductParser, ProductData


def _fallback_form_fill(edit_frame, detail_pairs, weight_value, page):
    """
    后备表单填充函数，在动态填充失败时使用
    """
    print("🔧 执行基础表单填充...")
    
    waitTime = 200
    fill_timeout = 1000
    frame = edit_frame
    
    if isinstance(detail_pairs, dict) and 'Product Dimensions' in detail_pairs:
        dimensions_str = str(detail_pairs['Product Dimensions'])
        parts = dimensions_str.split('x')
        depth = parts[0].strip().split('"')[0] if len(parts) > 0 else None
        width = parts[1].strip().split('"')[0] if len(parts) > 1 else None
        height = parts[2].strip().split('"')[0] if len(parts) > 2 else None
        
        # 填充几个最基本的必填字段
        try:
            frame.get_by_role("textbox", name="请输入").first.fill("NONE")
        except Exception as e:
            print(f"填写NONE失败: {e}")
        
        # 基础尺寸填充
        if depth:
            try:
                frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input select2-default']").fill(depth, timeout=fill_timeout)
                frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input']").press("Enter")
            except Exception as e:
                print(f"设置Depth失败: {e}")
        
        if width:
            try:
                frame.locator("div[attrkey='Assembled Product Width'] input[class='select2-input select2-default']").fill(width, timeout=fill_timeout)
                frame.locator("div[attrkey='Assembled Product Width'] input[class='select2-input']").press("Enter")
            except Exception as e:
                print(f"设置Width失败: {e}")
        
        if height:
            try:
                frame.locator("div[attrkey='Assembled Product Height'] input[class='select2-input select2-default']").fill(height, timeout=fill_timeout)
                frame.locator("div[attrkey='Assembled Product Height'] input[class='select2-input']").press("Enter")
            except Exception as e:
                print(f"设置Height失败: {e}")
        
        print(f"基础填充完成 - Depth: {depth}, Width: {width}, Height: {height}")
    
    # 保存表单
    try:
        edit_frame.locator("a[btnflag='save']").click()
        print("✅ 表单已保存")
    except Exception as e:
        print(f"❌ 保存表单失败: {e}")


def check_script_expiration():
    """
    Check if the script has expired (8 hours after first run)
    Creates a timestamp file on first run and checks against it
    """
    timestamp_file = ".script_start_time"
    current_time = time.time()
    
    # 8 hours in seconds
    EXPIRATION_HOURS = 2
    EXPIRATION_SECONDS = EXPIRATION_HOURS * 60 * 60
    
    try:
        if os.path.exists(timestamp_file):
            # Read the start time from file
            with open(timestamp_file, 'r') as f:
                start_time = float(f.read().strip())
            
            # Check if 8 hours have passed
            elapsed_time = current_time - start_time
            remaining_time = EXPIRATION_SECONDS - elapsed_time
            
            if elapsed_time >= EXPIRATION_SECONDS:
                print("\n" + "="*50)
                print("⏰ 脚本使用期限已到期")
                print(f"📅 首次运行时间: {datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⌛ 使用期限: {EXPIRATION_HOURS} 小时")
                print(f"🚫 当前时间已超过使用期限")
                print("="*50)
                print("\n如需继续使用，请联系脚本提供者获取新版本。")
                sys.exit(1)
            else:
                # Show remaining time
                remaining_hours = remaining_time / 3600
                print(f"\n✅ 脚本仍在有效期内，剩余时间: {remaining_hours:.1f} 小时")
        else:
            # First run - create timestamp file
            with open(timestamp_file, 'w') as f:
                f.write(str(current_time))
            print(f"\n🚀 脚本首次运行，使用期限: {EXPIRATION_HOURS} 小时")
            print(f"📅 开始时间: {datetime.datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"⚠️ 无法检查脚本有效期: {e}")
        # In case of error, allow script to run but warn user
        pass



def execute(context, page, web_url):
    """
    执行产品信息抓取和表单填充的主流程
    
    职责：
    1. 页面导航和初始化
    2. 调用产品解析器提取数据  
    3. 协调表单填充流程
    """
    # 获取必要的iframe引用
    main_frame = page.locator("iframe[name=\"iframeModal_flag_0\"]").content_frame
    edit_frame = main_frame.locator("iframe[name^=\"iframeModal_editPostTemplet\"]").content_frame
    
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
            print("❌ 未获取到有效的产品数据，跳过表单填充")
            return None
            
    except Exception as e:
        print(f"❌ 产品解析器出错: {e}")
        amazon_page.close()
        return None
    
    # 让页面获取焦点
    page.bring_to_front()
    
    # 转换产品数据为旧格式（为了兼容现有表单填充逻辑）
    detail_pairs = {
        'title': product_data.title,
        **product_data.details
    }
    weight_value = product_data.weight_value
    
    print(f"🎯 开始智能表单填充（共 {len(detail_pairs)} 个字段）...")
    
    # 验证是否有产品详情可供填充
    if isinstance(detail_pairs, dict) and detail_pairs:
        print("🎯 检测到产品详情，开始智能表单填充...")
        
        # 尝试加载已保存的表单配置
        config_listener = FormConfigListener()
        config_data = config_listener.load_config()
        
        if config_data:
            try:
                # 解析表单配置
                field_parser = FormFieldParser(config_data)
                field_parser.print_fields_summary()
                
                # 确保重量数据在产品详情中
                if 'Item Weight' not in detail_pairs and weight_value:
                    detail_pairs['Item Weight'] = f"{weight_value} pounds"
                
                # 使用动态表单填充引擎
                form_filler = DynamicFormFiller(edit_frame, field_parser, detail_pairs, page)
                fill_results = form_filler.fill_form()
                
                # 输出填充结果
                print(f"\n🎉 表单填充完成!")
                print(f"✅ 成功填充: {fill_results['success_count']} 个字段")
                print(f"⚠️ 失败/跳过: {fill_results['error_count']} 个字段")
                if fill_results['errors']:
                    print("❌ 错误详情:")
                    for error in fill_results['errors']:
                        print(f"  - {error}")
                
                # 保存表单
                form_filler.save_form()
                
            except Exception as e:
                print(f"❌ 动态表单填充失败: {e}")
                print("🔄 回退到基础填充模式...")
                # 基础填充逻辑作为后备方案
                _fallback_form_fill(edit_frame, detail_pairs, weight_value, page)
        else:
            print("⚠️ 未找到表单配置数据，使用基础填充模式")
            print("💡 提示：请先运行一次完整流程以捕获API配置数据")
            _fallback_form_fill(edit_frame, detail_pairs, weight_value, page)
    else:
        print("❌ 未获取到产品详情，跳过表单填充")
    # Return the detail_pairs dictionary
    return detail_pairs


def run(playwright: Playwright) -> None:
    # Check script expiration before running
    check_script_expiration()
    
    # 登录信息,用户名
    user_name = "16636131310"
    # 登录信息,密码
    password = "2042612a"
    # # 登录信息,用户名
    # user_name = "18256261013"
    # # 登录信息,密码
    # password = "Aa741852963"
    
    browser = playwright.chromium.launch(
        headless=False
        )
    
    # 尝试加载存储的状态
    storage_state = user_name+"_auth_state.json"
    if os.path.exists(storage_state):
        context = browser.new_context(storage_state=storage_state,no_viewport=True,)  
    else:
        context = browser.new_context(no_viewport=True)
    page = context.new_page()
    
    # 设置API监听器以捕获表单配置数据
    config_listener = FormConfigListener()
    config_listener.setup_listener(page)
    print("🎛️ API监听器已启动，将自动捕获表单配置数据")
    
    try:
        page.goto("https://erp.datacaciques.com/newpro/inventory?platform=ebay#/all/all")
        # 检查是否已登录
        if page.locator("text=立即登录").count() > 0:
            raise Exception("Not logged in")
    except Exception as e:
        # page.close()
        print("Need to login:", e)
        # context = browser.new_context()
        # page = context.new_page()
        # page.goto("https://www.datacaciques.com/login?payload=eyJ1cmwiOiJcL2Rhc2hib2FyZCIsInBhZ2VfYWZ0ZXJfbG9naW4iOiJodHRwczpcL1wvZXJwLmRhdGFjYWNpcXVlcy5jb21cL2F1dGhcL2xvZ2luU3VjYyJ9&sign=23e36f89d85fa8576f6b1b2fa4f45ade88aa653a2f016ae9f9c4c195469cc6dd&algo=HMAC_SHA256&sso_sess=0a2cee88e5ae8c512ef8cbf9a4bf9f139a16c9e07418a11926d7d67ce8abc1d9&checksum=dc658ec2d93abecb3e4820f164440e74")
        page.get_by_role("textbox", name="账号").click()
        page.get_by_role("textbox", name="账号").fill(user_name)
        page.get_by_role("textbox", name="密码").click()
        page.get_by_role("textbox", name="密码").fill(password)
        page.get_by_role("button", name="立即登录").click()
        # 保存登录状态
        context.storage_state(path=storage_state)
    page.goto("https://erp.datacaciques.com/newpro/inventory?platform=ebay#/all/all")
    # page.get_by_title("模板创建人").click()
    # page.get_by_role("checkbox", name="宋璇").check()
    # page.get_by_text("搜索", exact=True).click()
    # page.get_by_role("row", name="B0DHXM3BYP 编辑 单属性 - 美国 SKU").get_by_role("checkbox").check()
    # page.wait_for_selector("input[class=\"cbAll\"]").click()
    # page.get_by_role("button", name="刊登").click()
    # 切换到iframe并定位单元格
    input("等待用户点击刊登...")
    page.wait_for_selector("iframe[name=\"iframeModal_flag_0\"]")
    frame = page.frame(name="iframeModal_flag_0")
    
    # 等待表格加载
    frame.wait_for_selector("table")
    while True:
        rowNo = input("表格已加载成功，请输入要操作的行号：如1代表第一行，并按回车键继续...")
        # Fix: Use proper CSS selector syntax for multiple data attributes
        cellProdLink = frame.locator(f"td[data-y='{int(rowNo)-1}'][data-x='23']")
        cellProdLink.wait_for(state="visible")
        product_link=''
        # 确保元素可交互
        # frame.evaluate("""(cell) => {
        #     cell.scrollIntoView();
        #     cell.style.zIndex = '9999';
        # }""", cellProdLink.element_handle())
        
        try:
            cellProdLink.dblclick(timeout=5000)
            product_link = frame.locator("div[id='u-pg-excel-item'] input[type='text']").input_value()
            print(f"获取产品链接成功: {product_link}")
            # Press ESC key to close any open dialogs or menus
            page.keyboard.press("Escape")
            cellProdProps = frame.locator(f"td[data-y='{int(rowNo)-1}'][data-x='22']")
            cellProdProps.wait_for(state="visible")
            cellProdProps.dblclick(timeout=5000)
            prodDetails=execute(context,page,product_link)
            
            # Check if prodDetails is None or doesn't have required keys
            if prodDetails is None:
                print("⚠️ 未获取到产品详情，跳过此次操作")
                continue
            
            if 'title' not in prodDetails:
                print("⚠️ 产品标题不存在，跳过此次操作")
                continue
            frame.locator(f"td[data-y='{int(rowNo)-1}'][data-x='7']").dblclick(timeout=5000)
            print("正在填充产品标题...")
            print(f"正在填充产品标题: {'new'+prodDetails['title']}")
            titleInput= frame.locator(f"td[data-y='{int(rowNo)-1}'][data-x='7'] textarea[class='excelTextarea']")
            titleInput.wait_for(state="visible")
            titleInput.focus()
            
            # Check if Brand exists before using it
            if 'Brand' in prodDetails and prodDetails['Brand']:
                newTitle = prodDetails['title'].replace(prodDetails['Brand'], '')
            else:
                newTitle = prodDetails['title']  # Use title as-is if no brand
            titleInput.fill(newTitle)
        except Exception as e:
            print(f"\033[31m执行报错: {e}\033[0m")
        
        print("操作完成，等待下一次执行...")
    # ---------------------
    print("所有操作已完成，浏览器保持打开状态供您继续操作...")
    input("按Enter键退出程序并关闭浏览器...")
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
