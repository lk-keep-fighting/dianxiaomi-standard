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
from openai import timeout
import pandas as pd
from playwright.sync_api import Playwright, sync_playwright
from ai_category_validator import AICategoryValidator
# 导入重构后的统一组件
from amazon_product_parser import AmazonProductParser
from unified_form_filler import UnifiedFormFiller


# 登录信息
user_name = "16636131310"
password = "2042612a"
# # 备用登录信息
# user_name = "18256261013"
# password = "Aa741852963"

# 全局变量存储自定义数据
CUSTOM_DATA = {}

def load_custom_data():
    """
    从自定义数据.xlsx加载配置数据到字典
    
    返回字典结构：
    {
        'remove_words': {中文词: 英文词, ...},  # 需删除产品涉及的词语
        'product_categories': {中文: 英文, ...},  # 产品品类
        'keywords': [...],  # 关键词
        'forbidden_words': [...],  # 违禁词
        'fixed_info': {键: 值, ...}  # 固定信息
    }
    """
    global CUSTOM_DATA
    
    try:
        # 获取Excel文件路径（相对于项目根目录）
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        excel_path = os.path.join(script_dir, '自定义数据.xlsx')
        
        if not os.path.exists(excel_path):
            print(f"⚠️ 自定义数据文件不存在: {excel_path}")
            return
        
        print(f"📊 正在加载自定义数据: {excel_path}")
        
        # 读取所有工作表
        df_dict = pd.read_excel(excel_path, sheet_name=None)
        
        # 1. 处理"需删除产品涉及的词语"工作表
        if '需删除产品涉及的词语' in df_dict:
            df_remove = df_dict['需删除产品涉及的词语']
            CUSTOM_DATA['remove_words'] = {}
            if len(df_remove.columns) >= 2:
                col1, col2 = df_remove.columns[0], df_remove.columns[1]
                for _, row in df_remove.iterrows():
                    try:
                        val1, val2 = row[col1], row[col2]
                        if str(val1) != 'nan' and str(val2) != 'nan' and val1 is not None and val2 is not None:
                            CUSTOM_DATA['remove_words'][str(val2)] = str(val1)
                    except Exception:
                        continue
                print(f"   ✅ 已加载删除词语: {len(CUSTOM_DATA['remove_words'])} 条")
        
        # 2. 处理"产品品类"工作表
        if '产品品类' in df_dict:
            df_categories = df_dict['产品品类']
            CUSTOM_DATA['product_categories'] = {}
            if len(df_categories.columns) >= 2:
                col1, col2 = df_categories.columns[0], df_categories.columns[1]
                for _, row in df_categories.iterrows():
                    try:
                        val1, val2 = row[col1], row[col2]
                        if str(val1) != 'nan' and str(val2) != 'nan' and val1 is not None and val2 is not None:
                            CUSTOM_DATA['product_categories'][str(val1)] = str(val2)
                    except Exception:
                        continue
                print(f"   ✅ 已加载产品品类: {len(CUSTOM_DATA['product_categories'])} 条")
        
        # 3. 处理"关键词"工作表
        if '关键词' in df_dict:
            df_keywords = df_dict['关键词']
            CUSTOM_DATA['keywords'] = []
            if len(df_keywords.columns) > 0:
                for col in df_keywords.columns:
                    for value in df_keywords[col].dropna():
                        if str(value).strip():
                            CUSTOM_DATA['keywords'].append(str(value).strip())
                print(f"   ✅ 已加载关键词: {len(CUSTOM_DATA['keywords'])} 个")
        
        # 4. 处理"违禁词"工作表
        if '违禁词' in df_dict:
            df_forbidden = df_dict['违禁词']
            CUSTOM_DATA['forbidden_words'] = []
            if len(df_forbidden.columns) > 0:
                for col in df_forbidden.columns:
                    for value in df_forbidden[col].dropna():
                        if str(value).strip():
                            CUSTOM_DATA['forbidden_words'].append(str(value).strip())
                print(f"   ✅ 已加载违禁词: {len(CUSTOM_DATA['forbidden_words'])} 个")
        
        # 5. 处理"固定信息"工作表
        if '固定信息' in df_dict:
            df_fixed = df_dict['固定信息']
            CUSTOM_DATA['fixed_info'] = {}
            if len(df_fixed.columns) >= 2:
                # 假设第一列是键，第二列是值
                key_col = df_fixed.columns[0] if 'Unnamed' not in df_fixed.columns[0] else df_fixed.columns[1]
                value_col = df_fixed.columns[1] if len(df_fixed.columns) > 1 else df_fixed.columns[0]
                
                # 如果第一列是Unnamed，则使用第二列作为键列
                if 'Unnamed' in str(df_fixed.columns[0]):
                    if len(df_fixed.columns) >= 2:
                        for _, row in df_fixed.iterrows():
                            try:
                                val1, val2 = row.iloc[0], row.iloc[1]
                                if str(val1) != 'nan' and str(val2) != 'nan' and val1 is not None and val2 is not None:
                                    CUSTOM_DATA['fixed_info'][str(val1)] = str(val2)
                            except Exception:
                                continue
                else:
                    for _, row in df_fixed.iterrows():
                        try:
                            key_val, value_val = row[key_col], row[value_col]
                            if str(key_val) != 'nan' and str(value_val) != 'nan' and key_val is not None and value_val is not None:
                                CUSTOM_DATA['fixed_info'][str(key_val)] = str(value_val)
                        except Exception:
                            continue
                            
                print(f"   ✅ 已加载固定信息: {len(CUSTOM_DATA['fixed_info'])} 条")
        
        print(f"🎉 自定义数据加载完成！")
        print(f"📋 数据概览:")
        print(f"   - 删除词语: {len(CUSTOM_DATA.get('remove_words', {}))} 条")
        print(f"   - 产品品类: {len(CUSTOM_DATA.get('product_categories', {}))} 条")
        print(f"   - 关键词: {len(CUSTOM_DATA.get('keywords', []))} 个")
        print(f"   - 违禁词: {len(CUSTOM_DATA.get('forbidden_words', []))} 个")
        print(f"   - 固定信息: {len(CUSTOM_DATA.get('fixed_info', {}))} 条")
        
    except Exception as e:
        print(f"❌ 加载自定义数据失败: {e}")
        # 设置默认空数据
        CUSTOM_DATA = {
            'remove_words': {},
            'product_categories': {},
            'keywords': [],
            'forbidden_words': [],
            'fixed_info': {}
        }

def get_custom_data():
    """
    获取自定义数据字典
    """
    return CUSTOM_DATA
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
        edit_frame = page.locator('iframe[name*="iframeModal_editItem_"]').content_frame

        # 提取Amazon产品URL，支持.ca域名
        web_url = edit_frame.locator("a.linkUrl").get_attribute("href")
        
        # 检查URL是否有效
        if not web_url:
            print("❌ 无法提取产品URL")
            return
            
        # 如果是Amazon.ca链接，保持原样；如果是其他Amazon域名，也保持原样
        print(f"🌐 提取的产品URL: {web_url}")
        
        # 检查是否为Amazon链接
        if "amazon." not in web_url.lower():
            print("⚠️ 警告：检测到非Amazon链接")
        elif "amazon.ca" in web_url.lower():
            print("🍁 检测到Amazon加拿大站点链接")
        else:
            print("🌍 检测到其他Amazon站点链接")
        if not web_url:
            print("❌ 无法获取有效的产品URL")
            return
        
        print(f"🌐 准备处理产品: {web_url}")
        
        # 使用统一的Amazon产品解析器
        amazon_page = context.new_page()
        try:
            # 导航到Amazon页面（添加语言和货币参数）
            print("🌐 正在导航到Amazon产品页面...")
            try:
                amazon_page.goto(web_url + '?language=en_US&currency=USD', timeout=5000)
            except Exception:
                pass
            
            # 检查配送地址设置
            # try:
            #     amazon_page.wait_for_selector("#glow-ingress-line1",timeout=1000)
            #     deliver_to = amazon_page.locator("#glow-ingress-line1").inner_text()
            #     print(f"📍 配送地址: {deliver_to}")
            #     # 这里可以添加地址切换逻辑，如果需要的话
            # except Exception as e:
            #     print(f"⚠️ 无法获取配送地址信息: {e}")
            
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
        
        # 传递自定义数据给表单填充器
        custom_data = get_custom_data()
        
        
        if custom_data:
            print(f"📋 使用自定义数据:")
            print(f"   - 删除词语: {len(custom_data.get('remove_words', {}))} 条")
            print(f"   - 固定信息: {len(custom_data.get('fixed_info', {}))} 条")
            
            print(f"   - 需要删除字段:")
            print(custom_data.get('remove_words'))
            print(f"   - 固定信息:")
            print(custom_data.get('fixed_info'))
    
        product_data.details.update(custom_data.get('fixed_info', {}))
        ai_category_validator = AICategoryValidator(
                api_base_url="https://api.hunyuan.cloud.tencent.com/v1",  # 腾讯云混元API
                api_key="sk-fc0nyVUKNiqO4gYEMPtmQbai53cUoAvBVhlW4fROn69LTthI",  # 替换为实际的混元API密钥
                model_name="hunyuan-turbos-latest"    # 混元最新turbo模型
            )
        # 获取违禁词列表并转换为字符串
        forbidden_words_list = custom_data.get('forbidden_words', [])
        forbidden_words_str = ', '.join(forbidden_words_list) if isinstance(forbidden_words_list, list) else str(forbidden_words_list)
        inv_sku= edit_frame.locator("div[attrkey='dc_inventorySku'] textarea").inner_text()
        print('sku:', inv_sku)
        newDes=ai_category_validator.new_title_and_key_features(
            title=product_data.title, 
            key_features=product_data.details.get("key features", "").split("|"), 
            remove_words=forbidden_words_str, 
            category=product_data.details.get("Category", "Musical Instruments")
        )
        print("AI 优化结果")
        print(newDes)
        
        
        # 检查AI结果是否有效
        if newDes is None:
            print("❌ AI生成失败，使用原始数据")
            new_title = product_data.title or ''
            new_key_features = product_data.details.get("key features", '')
            new_description = product_data.details.get("description", '')
            formatted_bullets = []
        else:
            new_title = newDes.get('title', '')
            new_key_features = newDes.get('bullet_points', '')
            new_description = newDes.get('description', '')
            formatted_bullets_raw = newDes.get('formatted_bullets', [])
            
            # 确保 formatted_bullets 是列表类型
            if isinstance(formatted_bullets_raw, list):
                formatted_bullets = formatted_bullets_raw
            else:
                formatted_bullets = []
                
            print(f"📋 获取到 {len(formatted_bullets)} 个格式化要点")
            for idx, bullet in enumerate(formatted_bullets):
                print(f"   要点{idx+1}: {bullet[:50]}...")
            # 更新产品数据
            product_data.details["title"] = new_title
            product_data.details["key features"] = new_key_features
            product_data.details["description"] = new_description
            # 将列表转换为字符串存储
            product_data.details["formatted_bullets"] = '\n'.join(formatted_bullets) if formatted_bullets else ''
        
        
        # 更新产品数据（保证所有情况下都执行）
        product_data.details["title"] = new_title
        product_data.details["key features"] = new_key_features
        product_data.details["description"] = new_description
        print("🚀 产品数据已更新为AI返回")
        edit_frame.get_by_role("radio", name="单属性").check()
        edit_frame.locator("div.category-select-row").click()
        edit_frame.get_by_role("searchbox", name="请输入类目名称或ID").click()
        edit_frame.get_by_role("searchbox", name="请输入类目名称或ID").fill("Musical Instruments")
        page.press("body", "Enter")
        edit_frame.get_by_role("listitem").filter(has_text="Musical Instruments").locator("b").click()
        edit_frame.get_by_role("button", name="确定").click()
        edit_frame.locator("#page-anchor-1-1 textarea").nth(4).dblclick()
        edit_frame.locator("#page-anchor-1-1 textarea").nth(4).fill(product_data.details.get("在线初始库存", ""))
        edit_frame.locator(".currencyInput.currencyInput2 > .number").click()
        edit_frame.locator(".currencyInput.currencyInput2 > .number").fill(product_data.details.get("ShippingWeight", ""))
        edit_frame.locator("div[attrkey=\"dc_price\"] input").fill(product_data.details.get("价格", ""))
        edit_frame.locator("div[attrkey=\"dc_title\"] textarea").fill(new_title)
        edit_frame.locator("div[attrkey=\"dc_lagTime\"] input").fill(product_data.details.get("Lag Time", ""))
        
        edit_frame.locator(f"#mce_0_ifr").content_frame.locator("#tinymce").fill(new_description)
        
        # 填充五点描述到表单
        if formatted_bullets:
            print(f"🔄 开始填充 {len(formatted_bullets)} 个要点到表单...")
            
            # 首先获取所有可用的TinyMCE iframe元素
            try:
                # 等待一下让页面加载完成
                import time
                time.sleep(2)
                
                # 查找所有的TinyMCE iframe
                tinymce_iframes = edit_frame.locator("iframe[id*='mce_'][id$='_ifr']")
                iframe_count = tinymce_iframes.count()
                print(f"   找到 {iframe_count} 个TinyMCE编辑器")
                
                # 填充每个要点（从第二个开始，第一个通常是描述）
                for i in range(min(len(formatted_bullets), iframe_count - 1)):
                    iframe_index = i + 1  # 跳过第0个（描述框）
                    content = formatted_bullets[i]
                    
                    try:
                        print(f"   正在填充要点 {i+1} 到第{iframe_index+1}个编辑器: {content[:30]}...")
                        
                        # 获取具体的iframe
                        target_iframe = tinymce_iframes.nth(iframe_index)
                        
                        # 等待iframe出现并可见
                        target_iframe.wait_for(state='visible', timeout=3000)
                        
                        # 进入iframe并填充内容
                        tinymce_element = target_iframe.content_frame.locator("#tinymce, body[contenteditable='true'], .mce-content-body")
                        tinymce_element.wait_for(state='visible', timeout=3000)
                        
                        # 清空并填入新内容
                        tinymce_element.click()
                        tinymce_element.fill(content)
                        
                        print(f"   ✅ 要点 {i+1} 填充成功")
                        
                    except Exception as e:
                        print(f"   ❌ 要点 {i+1} 填充失败: {e}")
                        # 尝试备用方案
                        try:
                            print(f"   🔄 尝试备用填充方案...")
                            # 直接通过索引查找
                            backup_selector = f"iframe[id*='mce_'][id$='_ifr']:nth-of-type({iframe_index + 1})"
                            backup_iframe = edit_frame.locator(backup_selector)
                            if backup_iframe.count() > 0:
                                backup_iframe.content_frame.locator("body").fill(content)
                                print(f"   ✅ 备用方案填充成功")
                            else:
                                print(f"   ❌ 备用方案也失败")
                        except Exception as backup_error:
                            print(f"   ❌ 备用方案失败: {backup_error}")
                        continue
                        
            except Exception as e:
                print(f"   ❌ 整体填充流程失败: {e}")
                # 最后的备用方案 - 使用原来的方法
                print("   🔄 使用原始方法尝试填充...")
                for i in range(len(formatted_bullets)):
                    try:
                        selector = f"#mce_{i+1}_ifr"
                        content = formatted_bullets[i]
                        if edit_frame.locator(selector).count() > 0:
                            edit_frame.locator(selector).content_frame.locator("body").fill(content)
                            print(f"   ✅ 原始方法填充要点 {i+1} 成功")
                    except:
                        continue
        else:
            print("⚠️ 没有可填充的要点数据")

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
    
    # 加载自定义数据
    load_custom_data()
    print()
    
    with sync_playwright() as playwright:
        run(playwright)


if __name__ == "__main__":
    main()
