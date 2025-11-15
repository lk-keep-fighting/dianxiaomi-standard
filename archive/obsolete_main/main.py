import re
import re
from socket import timeout
from playwright.sync_api import Playwright, sync_playwright, expect
import os
import time
import datetime
import sys
from auto_form_filler import auto_fill_form_fields




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



def execute(context,page):
    # 切换到主iframe
    main_frame =page.locator("iframe[name=\"iframeModal_flag_0\"]").content_frame
    edit_frame = main_frame.locator("iframe[name^=\"iframeModal_editPostTemplet\"]").content_frame
    # 处理可能的模态框遮挡
    ai_button = edit_frame.get_by_text(" AI生成 new")
    ai_button.wait_for()
    
    try:
        ai_button.click(timeout=5000)
    except Exception as e:
        print(f"Click failed: {e}")
        # 关闭可能的遮挡元素
        page.locator(".modal-backdrop").evaluate_all("elements => elements.forEach(el => el.remove())")
        ai_button.click()
    
    # 获取URL的多种方式
    url_sources = [
        {"type": "link", "selector": "a.linkUrl", "attr": "href"},
        {"type": "input", "selector": "input[name='productUrl']", "attr": "value"}
    ]
    
    web_url = ""
    for source in url_sources:
        try:
            elements = edit_frame.locator(source["selector"])
            if elements.count() > 0:
                element = elements.first
                # 先检查元素是否存在，不强制要求可见
                element.wait_for(state="attached", timeout=5000)
                # 尝试获取属性，即使元素不可见
                web_url = element.get_attribute(source["attr"])
                if web_url:
                    print(f"URL from {source['type']}: {web_url}")
                    break
        except Exception as e:
            print(f"Failed to get URL from {source['type']}: {e}")
    
    if not web_url:
        print("All URL sources failed")
    
    if not web_url or not web_url.startswith(('http://', 'https://')):
        print("Error: Invalid URL", web_url)
        return
    print(web_url)
    try:
        edit_frame.locator("div.ai-generate-header > span.close-btn").wait_for(timeout=10000)
        edit_frame.locator("div.ai-generate-header > span.close-btn").click()
    except Exception as e:
        print(f"Failed to close popup: {e}")
    page2 = context.new_page()
    try:
        try:
            page2.goto(web_url+'?language=en_US&currency=USD',timeout=10000)
        except Exception as e:
            print(f"页面加载超时: {e}")
        deliver_to = page2.locator("#glow-ingress-line1").inner_text()
        print(f"deliver_to: {deliver_to}")
        # if deliver_to.startswith("配送至:"):
        #     language_button = page2.locator("#nav-global-location-popover-link")
        #     language_button.wait_for(timeout=1000)
        #     print("切换语言和地区设置")
        #     language_button.click()
        #     page2.get_by_role("textbox", name="或输入美国邮政编码").click()
        #     page2.get_by_role("textbox", name="或输入美国邮政编码").fill("10001")
        #     page2.get_by_label("设置", exact=True).click()
        #     page2.get_by_role("button", name="完成").click()
            # page2.wait_for_load_state("domcontentloaded")
    except Exception as e:
        print(f"导航到{web_url}失败: {e}")
        print(f"请检查网络后重新执行")
        page2.close()
        return

    # 等待语言切换完成
    try:
        # 滚动页面确保所有内容加载
        # page2.evaluate("window.scrollTo(0, 500)")
        page2.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page2.wait_for_timeout(1000)  # 等待滚动后内容加载
        page2.wait_for_load_state("load")
        page2.evaluate("window.scrollTo(0, 0)")
        page2.wait_for_timeout(1000)  # 等待回滚后内容稳定
    except Exception as e:
        print(f"Warning: Language switch timeout - {e}")
    
    # 尝试获取目标元素，如果失败则继续
    try:
        print("等待产品详情元素加载")
        page2.wait_for_selector("table[class='a-normal a-spacing-micro']", state="attached", timeout=20000)
        # page2.wait_for_selector("table[class='a-keyvalue prodDetTable']", state="attached", timeout=20000)
    except Exception as e:
        print(f"Warning: Product details element not found - {e}")
    # 等待元素可见
    try:
        print("等待产品详情元素可见")
        page2.locator("table[class='a-normal a-spacing-micro']").wait_for(state="visible")
        # page2.locator("table[class='a-keyvalue prodDetTable']").wait_for(state="visible")
    except Exception as e:
        print(f"Warning: Product details element not visible - {e}")
   # 将产品详情数据解析为键值对
    detail_pairs = {}
    try:
        print("等待顶部产品详情元素加载")
        page2.wait_for_selector("table[class='a-normal a-spacing-micro']", state="attached", timeout=1000)
        product_details = page2.locator("table[class='a-normal a-spacing-micro']").inner_text()
        lines = product_details.strip().split('\n')
        for line in lines:
            if '\t' in line:
                key, value = line.split('\t', 1)
                detail_pairs[key.strip()] = value.strip()
    except Exception as e:
            print(f"获取产品详情失败: {e}")
    try:
        print("等待底部产品详情元素加载")
        page2.wait_for_selector("table[class='a-keyvalue prodDetTable']", timeout=1000)
        product_details_arr = page2.locator("table[class='a-keyvalue prodDetTable']")
        # 遍历 product_details_arr
        for i in range(product_details_arr.count()):
            try:
                # Get all rows from the table
                rows = product_details_arr.nth(i).locator("tr")
                for j in range(rows.count()):
                    try:
                        row = rows.nth(j)
                        # Extract th (key) and td (value) from each row
                        th_elements = row.locator("th")
                        td_elements = row.locator("td")
                        
                        if th_elements.count() > 0 and td_elements.count() > 0:
                            key = th_elements.first.inner_text().strip()
                            value = td_elements.first.inner_text().strip()
                            # Clean up the value by removing extra whitespace and newlines
                            value = ' '.join(value.split())
                            if key and value:
                                detail_pairs[key] = value
                                print(f"解析到: {key} = {value}")
                    except Exception as row_error:
                        print(f"解析第 {j} 行失败: {row_error}")
                        continue
            except Exception as e:
                print(f"获取第 {i} 个产品详情表格数据失败: {e}")
    except Exception as e:
         print("底部产品详情获取失败：{e}")
    # 使用更鲁棒的策略提取重量信息
    weight_value = '10'  # 默认值
    
    # 策略1: 从已提取的detail_pairs中查找重量
    if 'Item Weight' in detail_pairs:
        try:
            weight_str = detail_pairs['Item Weight']
            weight_match = re.search(r'([0-9.]+)', weight_str)
            if weight_match:
                weight_value = weight_match.group(1)
                print(f"✅ 从产品详情获取重量: {weight_value} (原值: {weight_str})")
        except Exception as e:
            print(f"解析产品详情重量失败: {e}")
    
    # 策略2: 尝试直接定位重量元素（如果上面没有找到）
    if weight_value == '10':  # 还是默认值，说明上面没找到
        weight_selectors = [
            # 策略2a: 原始选择器
            "td:has-text('Item Weight') span.a-size-base.handle-overflow",
            # 策略2b: 简化选择器
            "td:has-text('Item Weight') span",
            # 策略2c: 更宽泛的选择器
            "td:has-text('Item Weight')",
            # 策略2d: 包含weight的所有元素
            "[data-feature-name*='weight'], [id*='weight'], .weight-info",
            # 策略2e: 产品详情表格中的重量
            "#productDetails_detailBullets_sections1 span:has-text('pounds'), #productDetails_detailBullets_sections1 span:has-text('lbs')"
        ]
        
        for i, selector in enumerate(weight_selectors, 1):
            try:
                print(f"🔍 尝试策略 {i}: {selector}")
                # 使用较短的超时时间
                page2.wait_for_selector(selector.split()[0], timeout=3000)
                
                elements = page2.locator(selector)
                count = elements.count()
                print(f"   找到 {count} 个匹配元素")
                
                for j in range(count):
                    try:
                        element_text = elements.nth(j).inner_text(timeout=5000)
                        print(f"   元素 {j+1} 文本: {element_text[:50]}...")
                        
                        # 提取数字
                        weight_match = re.search(r'([0-9.]+)\s*(?:pounds?|lbs?)', element_text, re.IGNORECASE)
                        if weight_match:
                            weight_value = weight_match.group(1)
                            print(f"✅ 使用策略 {i} 获取重量: {weight_value}")
                            break
                        
                        # 如果没有单位，尝试提取任意数字
                        number_match = re.search(r'([0-9.]+)', element_text)
                        if number_match and selector == weight_selectors[0]:  # 只在精确选择器下使用
                            weight_value = number_match.group(1)
                            print(f"✅ 使用策略 {i} 获取数字: {weight_value}")
                            break
                            
                    except Exception as element_error:
                        print(f"   元素 {j+1} 处理失败: {element_error}")
                        continue
                
                if weight_value != '10':  # 找到了
                    break
                    
            except Exception as selector_error:
                print(f"   策略 {i} 失败: {selector_error}")
                continue
    
    print(f"🎩 最终重量值: {weight_value}")
    if detail_pairs:
        print("Product Details 键值对:")
        print("{:<30} {:<50}".format("键", "值"))
        print("-" * 80)
        for key, value in detail_pairs.items():
            print("{:<30} {:<50}".format(str(key), str(value)))
    else:
        print("未获取到产品详情键值对")
    # 关闭新页面
    page2.close()
    # 确保detail_pairs是字典类型
    if not isinstance(detail_pairs, dict):
        try:
            print("product_details is not a dict, converting to dict")
            product_details = dict(line.split('\t', 1) for line in product_details.strip().split('\n') if '\t' in line)
        except Exception as e:
            print(f"Error converting product_details to dict: {e}")
    # After extracting detail_pairs, add this:
    if detail_pairs:
        print("🔄 开始自动填充表单...")
        auto_fill_form_fields(edit_frame, detail_pairs, page, timeout=1000)
        print("✅ 自动填充完成")

    # if isinstance(detail_pairs, dict) and 'Product Dimensions' in detail_pairs:
    #     dimensions_str = str(detail_pairs['Product Dimensions'])
    #     print(f"Raw Product Dimensions string: {repr(dimensions_str)}")
    #     # 优化分割逻辑确保准确提取数值
    #     parts = dimensions_str.split('x')
    #     depth = parts[0].strip().split('"')[0] if len(parts) > 0 else None
    #     width = parts[1].strip().split('"')[0] if len(parts) > 1 else None
    #     height = parts[2].strip().split('"')[0] if len(parts) > 2 else None
    #     color_val= str(detail_pairs['Color'])
    #     print(f"获取到尺寸值 - Depth: {depth}, Width: {width}, Height: {height}")
    #     # 让页面获取焦点
    #     page.bring_to_front()
    #     # 验证提取结果
    #     if dimensions_str:
    #         print("All dimensions extracted successfully")
    #         waitTime=200
    #         fill_timeout=1000
    #         frame = edit_frame
    #         try:
    #             frame.get_by_role("textbox", name="请输入").first.fill("NONE")
    #         except Exception as e:
    #             print(f"填写NONE失败: {e}")
            
    #         try:
    #             frame.locator("div[attrkey='Is Prop 65 Warning Required'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="No (否)").click()
    #         except Exception as e:
    #             print(f"设置Prop 65失败: {e}")
            
    #         page.wait_for_timeout(waitTime)
            
    #         try:
    #             frame.locator("div[attrkey='Age Group'] input[class='select2-input select2-default']").fill('Adult (成人)', timeout=fill_timeout)
    #             frame.locator("div[attrkey='Age Group'] input[class='select2-input select2-focused']").press("Enter")
    #         except Exception as e:
    #             print(f"设置Age Group失败: {e}")
            
    #         # 其他操作也按此模式添加try-catch...
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input select2-default']").fill(depth, timeout=fill_timeout)
    #             frame.locator("div[attrkey='Assembled Product Depth'] input[class='select2-input']").press("Enter")
    #             frame.locator("div[attrkey='Assembled Product Depth'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="in (英寸)").click()
    #         except Exception as e:
    #             print(f"设置Depth单位失败: {e}")
                
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Assembled Product Width'] input[class='select2-input select2-default']").fill(width, timeout=fill_timeout)
    #             frame.locator("div[attrkey='Assembled Product Width'] input[class='select2-input']").press("Enter")
    #             frame.locator("div[attrkey='Assembled Product Width'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="in (英寸)").click()
    #         except Exception as e:
    #             print(f"设置Width单位失败: {e}")
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Assembled Product Height'] input[class='select2-input select2-default']").fill(height, timeout=fill_timeout)
    #             frame.locator("div[attrkey='Assembled Product Height'] input[class='select2-input']").press("Enter")
    #             frame.locator("div[attrkey='Assembled Product Height'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="in (英寸)").click()
    #         except Exception as e:
    #             print(f"设置Height单位失败: {e}")
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Assembled Product Weight'] input[class='select2-input select2-default']").fill(weight_value, timeout=fill_timeout)
    #             frame.locator("div[attrkey='Assembled Product Weight'] input[class='select2-input']").press("Enter")
    #             frame.locator("div[attrkey='Assembled Product Weight'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="lb (磅)").click()
    #         except Exception as e:
    #             print(f"设置Weight单位失败: {e}")
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Color'] textarea").fill(color_val, timeout=fill_timeout)
    #         except Exception as e:
    #             print(f"填写Color失败: {e}")
    #         try:
    #             frame.locator("div[attrkey='Condition'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="New (全新)").click()
    #         except Exception as e:
    #             print(f"设置Condition单位失败: {e}")
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Has Written Warranty'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="No (否)").click(timeout=fill_timeout)
    #         except Exception as e:
    #             print(f"设置Has Written Warranty单位失败: {e}")
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Net Content'] input[class='select2-input select2-default']").fill('1', timeout=fill_timeout)
    #             frame.locator("div[attrkey='Net Content'] input[class='select2-input']").press("Enter")
    #             frame.locator("div[attrkey='Net Content'] div[class='select2-container selectBatchAdd']").get_by_role("link", name="请选择").click(timeout=fill_timeout)
    #             frame.get_by_role("option", name="Each (每个)").click()
    #         except Exception as e:
    #             print(f"设置Net Content单位失败: {e}")
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Recommended Locations'] input[class='select2-input select2-default']").fill('Indoor', timeout=fill_timeout)
    #             frame.locator("div[attrkey='Recommended Locations'] input[class='select2-input select2-focused']").press("Enter")
    #         except Exception as e:
    #             print(f"设置Recommended Locations单位失败: {e}")
    #         page.wait_for_timeout(waitTime)
    #         try:
    #             frame.locator("div[attrkey='Small Parts Warning Code'] input[class='select2-input select2-default']").fill('0', timeout=fill_timeout)
    #             frame.locator("div[attrkey='Small Parts Warning Code'] input[class='select2-input select2-focused']").press("Enter")
    #         except Exception as e:
    #             print(f"设置Small Parts Warning Code单位失败: {e}")

    #         print(f"填充完毕，尺寸值 - Depth: {depth}, Width: {width}, Height: {height}")
    #     else:
    #         print("未获取到产品详情")


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
    browser = playwright.chromium.launch(headless=False)
    
    # 尝试加载存储的状态
    storage_state = f"{user_name}_auth_state.json"
    if os.path.exists(storage_state):
        context = browser.new_context(storage_state=storage_state,no_viewport=True)  
    else:
        context = browser.new_context(no_viewport=True)
    page = context.new_page()
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
    # page.get_by_role("button", name="刊登").click()
    # # 切换到iframe并定位单元格
    # page.wait_for_selector("iframe[name=\"iframeModal_flag_0\"]")
    # frame = page.frame(name="iframeModal_flag_0")
    
    # # 等待表格加载
    # frame.wait_for_selector("table")
    
    # # 使用更可靠的定位方式
    # cell = frame.locator("td", has_text="个属性")
    # cell.wait_for(state="visible")
    
    # # 确保元素可交互
    # frame.evaluate("""(cell) => {
    #     cell.scrollIntoView();
    #     cell.style.zIndex = '9999';
    # }""", cell.element_handle())
    
    # 添加重试逻辑
    # max_retries = 3
    # for attempt in range(max_retries):
    #     try:
    #         cell.dblclick(timeout=10000)
    #         break
    #     except Exception as e:
    #         print(f"Attempt {attempt + 1} failed: {e}")
    #         if attempt == max_retries - 1:
    #             raise
    #         page.wait_for_timeout(2000)
    while True:
        # 等待用户输入回车
        input("按回车键开始执行流程，或Ctrl+C退出...")
        try:
            execute(context,page)
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
