#!/usr/bin/env python3
"""
重构后的主程序 - 统一的Amazon产品抓取和表单填充系统

重构成果：
1. 移除了重复的Amazon解析代码（163行 -> 0行）
2. 统一了映射系统（2套 -> 1套）
3. 合并了main.py和main-table-model.py的优势
4. Single Source of Truth架构

作者: Linus Torvalds (风格)
设计原则: Good Taste, No Duplication, Simple Data Flow
"""

import os
import sys
import time
import datetime
from playwright.sync_api import Playwright, sync_playwright

# 导入重构后的统一组件
from amazon_product_parser import AmazonProductParser
from unified_form_filler import UnifiedFormFiller


def check_script_expiration():
    """
    检查脚本有效期 - 保持原有的期限控制逻辑
    """
    timestamp_file = ".script_start_time"
    current_time = time.time()
    
    # 2小时有效期
    EXPIRATION_HOURS = 2
    EXPIRATION_SECONDS = EXPIRATION_HOURS * 60 * 60
    
    try:
        if os.path.exists(timestamp_file):
            # 读取开始时间
            with open(timestamp_file, 'r') as f:
                start_time = float(f.read().strip())
            
            # 检查是否超过期限
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
                # 显示剩余时间
                remaining_hours = remaining_time / 3600
                print(f"\n✅ 脚本仍在有效期内，剩余时间: {remaining_hours:.1f} 小时")
        else:
            # 首次运行 - 创建时间戳文件
            with open(timestamp_file, 'w') as f:
                f.write(str(current_time))
            print(f"\n🚀 脚本首次运行，使用期限: {EXPIRATION_HOURS} 小时")
            print(f"📅 开始时间: {datetime.datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"⚠️ 无法检查脚本有效期: {e}")
        # 出现错误时允许脚本运行但发出警告
        pass


def extract_url_from_form(edit_frame):
    """
    从表单中提取Amazon产品URL
    
    Good Taste: 简单的URL提取逻辑，支持多种来源
    """
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
    
    if not web_url or not web_url.startswith(('http://', 'https://')):
        print(f"Error: Invalid URL: {web_url}")
        return None
    
    return web_url


def execute_automation(context, page):
    """
    执行自动化流程的核心函数
    
    重构后的简洁流程：
    1. 获取iframe和URL
    2. 使用统一解析器抓取Amazon数据  
    3. 使用统一填充引擎填充表单
    
    Good Taste: 每个步骤只做一件事
    """
    print("🚀 开始执行重构后的自动化流程...")
    
    try:
        # 获取必要的iframe引用
        main_frame = page.locator('iframe[name="iframeModal_flag_0"]').content_frame
        edit_frame = main_frame.locator('iframe[name^="iframeModal_editPostTemplet"]').content_frame
        
        # 关闭可能的弹出框
        try:
            ai_button = edit_frame.get_by_text(" AI生成 new")
            ai_button.wait_for()
            ai_button.click(timeout=5000)
            print("✅ 已点击AI生成按钮")
        except Exception as e:
            print(f"⚠️ AI按钮操作失败: {e}")
            # 尝试关闭可能的遮挡元素
            page.locator(".modal-backdrop").evaluate_all("elements => elements.forEach(el => el.remove())")
        
        # 关闭AI生成弹框
        try:
            edit_frame.locator("div.ai-generate-header > span.close-btn").wait_for(timeout=10000)
            edit_frame.locator("div.ai-generate-header > span.close-btn").click()
            print("✅ 已关闭AI生成弹框")
        except Exception as e:
            print(f"⚠️ 关闭弹框失败: {e}")
        
        # 提取Amazon产品URL
        web_url = extract_url_from_form(edit_frame)
        if not web_url:
            print("❌ 无法获取有效的产品URL")
            return
        
        print(f"🌐 准备处理产品: {web_url}")
        
        # 使用统一的Amazon产品解析器
        amazon_page = context.new_page()
        try:
            # 导航到Amazon页面（添加语言和货币参数）
            print("🌐 正在导航到Amazon产品页面...")
            amazon_page.goto(web_url + '?language=en_US&currency=USD', timeout=60000)
            
            # 检查配送地址设置
            try:
                deliver_to = amazon_page.locator("#glow-ingress-line1").inner_text()
                print(f"📍 配送地址: {deliver_to}")
                # 这里可以添加地址切换逻辑，如果需要的话
            except Exception as e:
                print(f"⚠️ 无法获取配送地址信息: {e}")
            
            # 使用统一解析器解析产品数据
            print("🔍 开始解析Amazon产品信息...")
            product_parser = AmazonProductParser(amazon_page)
            product_data = product_parser.parse_product()
            
            # 打印解析摘要
            if product_data.has_valid_data():
                print(f"✅ 产品解析成功！")
                print(f"📝 产品标题: {product_data.title[:60]}...")
                print(f"📊 提取字段数: {len(product_data.details)}")
                print(f"⚖️ 产品重量: {product_data.weight_value} lbs")
                
                # 打印产品详情键值对（格式化输出）
                if product_data.details:
                    print("\nProduct Details 键值对:")
                    print("{:<30} {:<50}".format("键", "值"))
                    print("-" * 80)
                    for key, value in product_data.details.items():
                        print("{:<30} {:<50}".format(str(key), str(value)))
                else:
                    print("⚠️ 未获取到产品详情键值对")
            else:
                print("❌ 产品解析失败，无有效数据")
                return
                
        except Exception as e:
            print(f"❌ Amazon页面处理失败: {e}")
            return
        finally:
            # 确保关闭Amazon页面
            amazon_page.close()
            print("✅ Amazon页面已关闭")
        
        # 让原页面获得焦点
        page.bring_to_front()
        
        # 使用统一表单填充引擎
        print("🔄 开始表单填充...")
        form_filler = UnifiedFormFiller(edit_frame, page)
        fill_results = form_filler.fill_form(product_data)
        
        # 打印填充统计
        form_filler.print_fill_stats()
        
        print("🎉 自动化流程执行完成！")
        
    except Exception as e:
        print(f"❌ 自动化流程执行失败: {e}")


def run(playwright: Playwright) -> None:
    """
    主运行函数 - 保持原有的登录和会话管理逻辑
    """
    # 检查脚本有效期
    # check_script_expiration()
    
    # 登录信息
    user_name = "16636131310"
    password = "2042612a"
    # # 备用登录信息
    # user_name = "18256261013"
    # password = "Aa741852963"
    
    browser = playwright.chromium.launch(headless=False)
    
    # 尝试加载存储的状态
    storage_state = f"{user_name}_auth_state.json"
    if os.path.exists(storage_state):
        context = browser.new_context(storage_state=storage_state, no_viewport=True)  
    else:
        context = browser.new_context(no_viewport=True)
    
    page = context.new_page()
    
    try:
        page.goto("https://erp.datacaciques.com/newpro/inventory?platform=ebay#/all/all")
        # 检查是否已登录
        if page.locator("text=立即登录").count() > 0:
            raise Exception("Not logged in")
    except Exception as e:
        # 需要登录
        print(f"🔐 需要登录: {e}")
        page.get_by_role("textbox", name="账号").click()
        page.get_by_role("textbox", name="账号").fill(user_name)
        page.get_by_role("textbox", name="密码").click()
        page.get_by_role("textbox", name="密码").fill(password)
        page.get_by_role("button", name="立即登录").click()
        # 保存登录状态
        context.storage_state(path=storage_state)
        print("✅ 登录成功，状态已保存")
    
    page.goto("https://erp.datacaciques.com/newpro/inventory?platform=ebay#/all/all")
    print("✅ 已导航到库存页面")
    
    # 主循环 - 等待用户触发
    while True:
        # 等待用户输入回车
        input("\n按回车键开始执行自动化流程，或Ctrl+C退出...")
        try:
            execute_automation(context, page)
        except Exception as e:
            print(f"\033[31m执行报错: {e}\033[0m")
        
        print("\n操作完成，等待下一次执行...")
    
    # 清理资源
    print("\n🏁 所有操作已完成，浏览器保持打开状态供您继续操作...")
    input("按Enter键退出程序并关闭浏览器...")
    context.close()
    browser.close()


def main():
    """程序入口点"""
    print("🌟 重构后的数字酋长自动化系统")
    print("📋 重构成果:")
    print("   ✅ 统一Amazon解析器")
    print("   ✅ 统一表单填充引擎")  
    print("   ✅ 单一映射系统")
    print("   ✅ 简化的数据流")
    print()
    
    with sync_playwright() as playwright:
        run(playwright)


if __name__ == "__main__":
    main()
