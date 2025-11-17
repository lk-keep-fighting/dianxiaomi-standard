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
from socket import timeout
from timeit import Timer
from turtle import width
from playwright.sync_api._generated import Locator
import re
import sys
import time
import datetime
import csv
from pathlib import Path
from typing import Optional
from playwright.sync_api import Page, Playwright, sync_playwright

# 导入重构后的统一组件
from amazon_product_parser import AmazonProductParser
from product_data import ProductData
from unified_form_filler import UnifiedFormFiller
from ai_category_validator import AICategoryValidator
from csv_logger import write_unreasonable_category_to_csv, write_processing_exception_to_csv, csv_logger
from client_authorization import ensure_client_authorized
from playwright_env import configure_playwright_browsers_path


# 登录信息
# user_name = "liyoutest001"
# user_name = "getongtong2025"
user_name = "你的用户名"
password = ""
run_model="default"
# # 备用登录信息
# user_name = "18256261013"
# password = "Aa741852963"

# 路径配置
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
AUTH_STATE_DIR = PROJECT_ROOT / "data" / "auth_states"
AUTH_STATE_DIR.mkdir(parents=True, exist_ok=True)

configure_playwright_browsers_path()


class UserInteractionFlow:
    """统一的控制台用户界面，负责展示功能和收集确认信息。"""

    def __init__(self) -> None:
        self.section_divider = "═" * 72

    def display_welcome_screen(self) -> None:
        print("\n" + self.section_divider)
        print("🌟 欢迎使用店小秘自动化系统")
        print(self.section_divider)
        print("📋 使用流程:")
        print("  • 选择[1]打开自动打开店小秘界面；")
        print("  • 登录账号后回到当前界面按提示操作")
        print(self.section_divider)

    def _display_main_menu(self) -> None:
        print("\n主操作菜单:")
        print("  [1] 开始处理采集箱产品")
        print("  [2] 打开测试工具")
        print("  [3] 退出程序")

    def prompt_main_action(self) -> str:
        while True:
            self._display_main_menu()
            choice = input("请选择操作 [1-3]: ").strip().lower()
            if choice == "":
                choice = "1"
            if choice in {"1", "start", "s"}:
                return "start"
            if choice in {"2", "test", "t"}:
                return "test"
            if choice in {"3", "exit", "e", "q", "quit"}:
                return "exit"
            print("❌ 无效的选择，请重新输入。")

    def wait_for_confirmation(self, message: str) -> None:
        input(f"{message.strip()}\n按回车继续...")

    def notify(self, message: str) -> None:
        print(message)

    def prompt_manual_continue(self, processed: int, skipped: int, errors: int, remaining: int) -> str:
        print(f"\n📊 当前进度: 已处理 {processed}, 已跳过 {skipped}, 错误 {errors}, 剩余 {remaining}")
        while True:
            choice = input("🤔 是否继续? [Y]是 / [N]结束 / [A] 自动继续: ").strip().upper()
            if choice in {"", "Y", "YES"}:
                return "continue"
            if choice in {"N", "NO"}:
                return "stop"
            if choice in {"A", "AUTO"}:
                print("⚙️ 已启用自动继续模式，不再提示确认。")
                return "auto"
            print("❌ 无效输入，请输入 Y/N/A。")

    def prompt_product_preview_action(self) -> str:
        while True:
            choice = input("🤔 请选择操作 [Y]继续填充 / [N]跳过 / [D]查看详情: ").strip().upper()
            if choice in {"", "Y", "YES"}:
                return "continue"
            if choice in {"N", "NO"}:
                return "skip"
            if choice in {"D", "DETAIL", "DETAILS"}:
                return "detail"
            print("❌ 无效选择，请输入 Y/N/D。")

    def prompt_return_to_menu(self) -> bool:
        choice = input("\n是否返回主菜单继续操作? [Y]是 / [N]否: ").strip().lower()
        if choice in {"", "y", "yes"}:
            return True
        return False

    def prompt_test_url(self) -> str:
        return input("\n📝 请输入编辑页面URL (例如: https://www.dianxiaomi.com/web/sheinProduct/productEdit?id=12345): ").strip()

    def prompt_test_mode(self) -> str:
        print("\n测试模式:")
        print("  [1] 完整流程测试 (解析 + 填充)")
        print("  [2] 仅表单填充测试")
        print("  [3] 仅Amazon解析测试")
        print("  [4] 仅规格选择测试")
        while True:
            choice = input("请选择测试类型 [1-4]: ").strip()
            if choice in {"1", "2", "3", "4"}:
                return choice
            print("❌ 无效的选择，请输入 1-4。")

    def pause_for_review(self, message: str) -> None:
        input(f"{message.strip()}\n检查完成后按回车继续...")

    def say_goodbye(self) -> None:
        print("\n感谢使用店小秘自动化系统，期待再次见到您！")


def check_script_expiration():
    """
    检查脚本有效期 - 保持原有的期限控制逻辑
    """
    timestamp_file = ".script_start_time"
    current_time = time.time()
    
    # 2小时有效期
    EXPIRATION_HOURS = 24*7
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
                print(f"⏱️ 使用期限: {EXPIRATION_HOURS} 小时")
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
    """
    检查脚本有效期 - 保持原有的期限控制逻辑
    """
    timestamp_file = ".script_start_time"
    current_time = time.time()
    
    # 2小时有效期
    EXPIRATION_HOURS = 24*7
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


def handle_dynamic_specifications(edit_page: Page, product_dict: dict) -> None:
    """
    处理动态规格选择 - 根据Amazon解析的规格数据自动选择对应的checkbox
    
    Args:
        edit_page: 编辑页面对象
        product_dict: 产品数据字典
    """
    try:
        print("🔍 开始处理动态规格选择...")
        
        # 从产品数据中提取规格概要信息
        specifications_summary = product_dict.get('specifications summary', '')
        
        if not specifications_summary:
            print("⚠️ 未找到规格概要信息，跳过规格选择")
            return
        
        print(f"📊 规格概要: {specifications_summary}")
        
        # 解析规格概要 (格式: "Color: White | Size: 1 Pack")
        spec_pairs = []
        if '|' in specifications_summary:
            parts = specifications_summary.split('|')
            for part in parts:
                part = part.strip()
                if ':' in part:
                    key, value = part.split(':', 1)
                    spec_pairs.append((key.strip(), value.strip()))
        elif ':' in specifications_summary:
            # 单个规格的情况
            key, value = specifications_summary.split(':', 1)
            spec_pairs.append((key.strip(), value.strip()))
        
        if not spec_pairs:
            print("⚠️ 无法解析规格信息，跳过规格选择")
            return
        
        print(f"📋 解析到 {len(spec_pairs)} 个规格维度:")
        for key, value in spec_pairs:
            print(f"  - {key}: {value}")
        
        # 首先执行插头规格清理逻辑（直接检查页面大标题）
        _hanlde_specification_selection(edit_page, spec_pairs)
        
        # 构建目标规格的匹配模式
        target_specifications = {}
        for spec_key, spec_value in spec_pairs:
            match_patterns = []
            
            # 基本匹配模式
            match_patterns.extend([
                f"{spec_value}",  # 直接匹配值
                f"{spec_value}(",  # 值 + 左括号 (适配中文翻译格式)
                # f"({spec_value})",  # 括号包围
            ])
            
            # 如果是颜色，添加颜色翻译匹配
            if spec_key.lower() in ['color', 'colour']:
                color_translations = {
                    'white': '白色', 'black': '黑色', 'red': '红色', 'blue': '蓝色',
                    'green': '绿色', 'yellow': '黄色', 'gray': '灰色', 'grey': '灰色',
                    'brown': '棕色', 'pink': '粉色', 'purple': '紫色', 'orange': '橙色',
                    'beige': '米色', 'silver': '银色', 'gold': '金色'
                }
                
                color_lower = spec_value.lower()
                if color_lower in color_translations:
                    chinese_color = color_translations[color_lower]
                    match_patterns.extend([
                        f"{spec_value}({chinese_color})",
                        # f"{chinese_color}({spec_value})",
                        # chinese_color
                    ])
            
            target_specifications[spec_key] = {
                'value': spec_value,
                'patterns': match_patterns
            }
        
        # 获取所有当前选中的规格选项
        try:
            print("📊 分析当前选中的规格...")
            all_checkboxes = edit_page.locator("div.options-module label input[type='checkbox']")
            checkbox_count = all_checkboxes.count()
            
            if checkbox_count == 0:
                print("⚠️ 未找到任何规格选项")
                return
            
            print(f"  📊 找到 {checkbox_count} 个规格选项")
            
            # 分析每个checkbox的匹配情况
            matched_checkboxes = []
            unmatched_checkboxes = []
            
            for i in range(checkbox_count):
                try:
                    checkbox = all_checkboxes.nth(i)
                    is_checked = checkbox.is_checked()
                    
                    # 获取checkbox对应的标签文本
                    label_element = checkbox.locator('xpath=ancestor::label[1]')
                    if label_element.count() > 0:
                        title_attr = label_element.get_attribute('title')
                        label_text = title_attr or label_element.text_content() or ''
                        
                        # 检查是否匹配任何目标规格
                        is_target_match = False
                        matched_spec = None
                        
                        for spec_key, spec_info in target_specifications.items():
                            for pattern in spec_info['patterns']:
                                if '(' in pattern and label_text.lower().startswith(pattern.lower()) or label_text.lower() == pattern.lower(): # 根据前缀匹配
                                    is_target_match = True
                                    matched_spec = f"{spec_key}: {spec_info['value']}"
                                    break
                            if is_target_match:
                                break
                        
                        checkbox_info = {
                            'index': i,
                            'checkbox': checkbox,
                            'label_text': label_text,
                            'is_checked': is_checked,
                            'is_target_match': is_target_match,
                            'matched_spec': matched_spec
                        }
                        
                        if is_target_match:
                            matched_checkboxes.append(checkbox_info)
                            print(f"    ✅ 匹配项 {i+1}: '{label_text}' -> {matched_spec} (当前: {'已选中' if is_checked else '未选中'})")
                        else:
                            unmatched_checkboxes.append(checkbox_info)
                            if is_checked:
                                print(f"    ❌ 非匹配项 {i+1}: '{label_text}' (当前: 已选中，需要取消)")
                            
                except Exception as e:
                    print(f"    ⚠️ 分析第 {i+1} 个选项失败: {e}")
                    continue
            
            print(f"\n📋 匹配分析结果:")
            print(f"  ✅ 匹配目标规格的选项: {len(matched_checkboxes)} 个")
            print(f"  ❌ 不匹配的选项: {len([cb for cb in unmatched_checkboxes if cb['is_checked']])} 个需要取消")
            
            # 执行智能选择逻辑
            operations_count = 0
            
            # 1. 确保所有匹配的选项都被选中
            # for cb_info in matched_checkboxes:
            #     if not cb_info['is_checked']:
            #         try:
            #             cb_info['checkbox'].check(timeout=2000)
            #             operations_count += 1
            #             print(f"  ✅ 选中匹配项: {cb_info['label_text'][:30]}...")
            #             edit_page.wait_for_timeout(300)
            #         except Exception as e:
            #             print(f"    ⚠️ 选中失败: {e}")
            
            # 2. 如果有匹配项选中了，则取消所有不匹配但已选中的选项，方式异常情况一项都没选中
            if len(matched_checkboxes) >= 1:
                for cb_info in unmatched_checkboxes:
                    if cb_info['is_checked']:
                        try:
                            label_lower = cb_info['label_text'].lower()
                            if not ('default' in label_lower or '默认' in label_lower):
                                cb_info['checkbox'].uncheck(timeout=2000)
                                operations_count += 1
                                print(f"  ❌ 取消非匹配项: {cb_info['label_text'][:30]}...")
                                edit_page.wait_for_timeout(300)
                            else:
                                print(f"  ⚠️ 忽略取消项: {cb_info['label_text'][:30]}...")
                            
                        except Exception as e:
                            print(f"    ⚠️ 取消失败: {e}")
            else:
                print("  ⚠️ 匹配项小于2个，忽略操作")
            
            # 3. 检查是否有目标规格没有找到匹配项
            matched_specs = set()
            for cb_info in matched_checkboxes:
                if cb_info['matched_spec']:
                    matched_specs.add(cb_info['matched_spec'])
            
            target_specs = set(f"{key}: {info['value']}" for key, info in target_specifications.items())
            missing_specs = target_specs - matched_specs
            
            if missing_specs:
                print(f"\n⚠️ 以下目标规格未找到匹配的选项:")
                for missing_spec in missing_specs:
                    print(f"    - {missing_spec}")
                print(f"  📋 可能需要手动检查可用选项")
            
            print(f"\n🎉 规格选择优化完成，执行了 {operations_count} 个操作")
            
            _remove_all_specifications_with_link(edit_page)
            
            # 等待规格选择生效
            edit_page.wait_for_timeout(1000)
                
        except Exception as e:
            print(f"⚠️ 智能规格匹配失败: {e}")
            # 如果智能匹配失败，回退到原始逻辑
            print("🔄 回退到传统规格选择逻辑...")
            _fallback_specification_selection(edit_page, spec_pairs)
        
    except Exception as e:
        print(f"❌ 动态规格处理失败: {e}")

def _remove_all_specifications_with_link(edit_page: Page) -> None:
    """
    移除所有包含"移除"链接的规格容器
    
    功能说明:
    - 查找所有规格容器（div.sku-info-box）
    - 检查容器头部是否包含"移除"链接
    - 点击"移除"链接并在弹出的确认对话框中点击"确定"
    - 处理所有包含移除链接的规格，不判断规格名称
    
    Args:
        edit_page: 编辑页面对象
    """
    try:
        print(f"🗑️ 开始移除所有包含'移除'链接的规格容器...")
        
        # 查找所有规格容器
        spec_containers = edit_page.locator("div.sku-info-box")
        container_count = spec_containers.count()
        
        if container_count == 0:
            print("  ℹ️ 未找到规格容器")
            return
        
        print(f"  📊 找到 {container_count} 个规格容器，开始检查...")
        
        removed_count = 0
        
        # 遍历每个规格容器
        for i in range(container_count):
            try:
                # 重新获取容器（因为DOM可能已变化）
                spec_containers = edit_page.locator("div.sku-info-box")
                if i >= spec_containers.count():
                    break
                    
                container = spec_containers.nth(i)
                
                # 获取规格大标题（用于日志显示）
                header_selector = ".sku-info-box-header .flex div:first-child"
                header_element = container.locator(header_selector)
                header_text = "未知规格"
                
                if header_element.count() > 0:
                    header_text = header_element.inner_text().strip()
                
                # 查找"移除"链接
                remove_link = container.locator(".sku-info-box-header .link")
                
                if remove_link.count() > 0 and remove_link.is_visible():
                    print(f"    📋 规格容器 {i+1}: {header_text}")
                    print(f"      🖱️ 发现'移除'链接，点击中...")
                    
                    # 添加悬停效果（符合用户UI/UX偏好）
                    remove_link.hover()
                    edit_page.wait_for_timeout(200)
                    remove_link.click()
                    
                    # 等待确认对话框出现
                    edit_page.wait_for_timeout(500)
                    
                    # 点击确认对话框中的"确定"按钮
                    try:
                        # 方法1: 通过类名和文本内容精确匹配
                        confirm_btn = edit_page.locator("button.ant-btn-primary:has-text('确认')")
                        if confirm_btn.count() > 0:
                            confirm_btn.click(force=True)
                            print("      ✅ 已点击确认对话框中的'确认'按钮")
                        else:
                            # 方法2: 备用选择器 - 查找包含"确认"或"确 认"的按钮
                            confirm_btn = edit_page.locator("button:has-text('确认'), button:has-text('确 认')")
                            if confirm_btn.count() > 0:
                                confirm_btn.first.click(force=True)
                                print("      ✅ 已点击确认对话框中的'确认'按钮 (备用方法)")
                            else:
                                print("      ⚠️ 未找到确认对话框的'确认'按钮")
                    except Exception as confirm_error:
                        print(f"      ⚠️ 点击确认按钮失败: {confirm_error}")
                    
                    # 等待操作完成
                    edit_page.wait_for_timeout(800)
                    print(f"      🎉 规格'{header_text}'移除完成")
                    removed_count += 1
                    
                    # 由于容器被移除，索引需要回退
                    i -= 1
                    
            except Exception as e:
                print(f"    ❌ 处理规格容器时发生错误: {e}")
                continue
        
        if removed_count > 0:
            print(f"\n  ✨ 移除操作完成！共移除 {removed_count} 个规格容器")
        else:
            print(f"\n  ℹ️ 未找到包含'移除'链接的规格容器")
        
    except Exception as e:
        print(f"❌ 移除规格失败: {e}")
        print("  🛡️ 错误已被安全处理，不会影响主流程")


def _hanlde_specification_selection(edit_page: Page, spec_pairs: list) -> None:
    """
    处理特殊规格选择逻辑 - 当页面大标题包含"其他规格：插头"时，取消该标题下所有选项框的选中
    
    功能说明:
    - 直接检查页面上的规格大标题，不依赖传入参数
    - 当大标题包含"其他规格：插头"时，取消该标题下所有小选项框
    - 无论小选项框的具体名称是什么，都会被取消选中
    - 其他标题下的选项框（如尺寸、颜色等）不受影响
    
    Args:
        edit_page: 编辑页面对象
        spec_pairs: 规格对列表（本函数不使用此参数，保留为兼容性）
    """
    try:
        print("🔧 执行插头规格选择清理逻辑...")
        
        # 查找所有规格容器
        spec_containers = edit_page.locator("div.sku-info-box")
        container_count = spec_containers.count()
        
        if container_count == 0:
            print("  ℹ️ 未找到规格容器，跳过处理")
            return
        
        print(f"  📊 找到 {container_count} 个规格容器，开始检查...")
        
        # 统计信息
        total_unchecked = 0
        processed_containers = 0
        
        # 遍历每个规格容器
        for i in range(container_count):
            try:
                container = spec_containers.nth(i)
                
                # 获取规格大标题
                header_selector = ".sku-info-box-header .flex div:first-child"
                header_element = container.locator(header_selector)
                
                if header_element.count() > 0:
                    header_text = header_element.inner_text().strip()
                    print(f"    📋 规格容器 {i+1}: {header_text}")
                    
                    # 检查大标题是否包含"其他规格：插头"
                    is_plug_container = (
                        "其他规格：插头" in header_text or 
                        "插头" in header_text or
                        ("其他规格" in header_text and "插头" in header_text)
                    )
                    
                    if is_plug_container:
                        print(f"      🔌 检测到插头规格容器，开始清理所有选中项...")
                        
                        # 找到该容器内的所有checkbox
                        checkboxes = container.locator("div.options-module label input[type='checkbox']")
                        checkbox_count = checkboxes.count()
                        
                        if checkbox_count > 0:
                            unchecked_count = 0
                            checked_items = []
                            
                            # 首先收集所有已选中项的信息
                            for j in range(checkbox_count):
                                try:
                                    checkbox = checkboxes.nth(j)
                                    if checkbox.is_checked():
                                        # 获取选项文本用于日志
                                        label_element = checkbox.locator("xpath=ancestor::label")
                                        label_text = "未知选项"
                                        if label_element.count() > 0:
                                            title_attr = label_element.get_attribute('title')
                                            if title_attr:
                                                label_text = title_attr
                                            else:
                                                label_text = label_element.inner_text().strip()
                                            
                                            # 限制显示长度保持日志清晰
                                            if len(label_text) > 50:
                                                label_text = label_text[:47] + "..."
                                        checked_items.append(label_text)
                                except Exception:
                                    continue
                            
                            if checked_items:
                                print(f"        📊 发现 {len(checked_items)} 个已选中项，开始取消...")
                                
                                # 逐个取消选中（添加平滑动画效果）
                                for j in range(checkbox_count):
                                    try:
                                        checkbox = checkboxes.nth(j)
                                        if checkbox.is_checked():
                                            checkbox.uncheck(timeout=2000)
                                            unchecked_count += 1
                                            edit_page.wait_for_timeout(120)  # 平滑的操作间隔
                                            
                                    except Exception as e:
                                        print(f"        ⚠️ 取消第 {j+1} 个选项时出错: {e}")
                                        continue
                                
                                # 统计和反馈
                                total_unchecked += unchecked_count
                                processed_containers += 1
                                
                                print(f"      🎯 插头规格清理完成：")
                                print(f"        ✅ 成功取消 {unchecked_count} 个选中项")
                                
                                # 显示前几个被取消的项目（用户友好的反馈）
                                for idx, item in enumerate(checked_items[:3], 1):
                                    print(f"        ▫️ {idx}. {item}")
                                if len(checked_items) > 3:
                                    print(f"        ▫️ ... 及其他 {len(checked_items) - 3} 个选项")
                            else:
                                print(f"      ℹ️ 插头规格容器内无已选中项")
                        else:
                            print(f"      ℹ️ 插头规格容器内无选项框")
                    else:
                        print(f"      ➡️ 非插头规格容器，跳过: {header_text}")
                else:
                    print(f"    ⚠️ 规格容器 {i+1} 无法获取标题")
                    
            except Exception as e:
                print(f"    ❌ 处理规格容器 {i+1} 时发生错误: {e}")
                continue
        
        # 最终反馈
        if total_unchecked > 0:
            print(f"\n  ✨ 插头规格清理完成！")
            print(f"    📊 处理统计: 处理了 {processed_containers} 个插头容器")
            print(f"    ✅ 成功取消: {total_unchecked} 个选中项")
            print(f"    🎯 结果: 所有插头相关选中已清理，其他规格保持不变")
        else:
            print(f"\n  ℹ️ 插头规格清理完成，未发现需要取消的选中项")
        
        # 等待页面状态稳定（优化用户体验）
        edit_page.wait_for_timeout(600)
        
    except Exception as e:
        print(f"❌ 插头规格选择清理失败: {e}")
        print("  🛡️ 错误已被安全处理，不会影响主流程")
        # 发生错误时不中断主流程
        return
def _fallback_specification_selection(edit_page: Page, spec_pairs: list) -> None:
    """
    备用规格选择逻辑 - 当智能匹配失败时使用
    
    Args:
        edit_page: 编辑页面对象
        spec_pairs: 规格对列表
    """
    try:
        print("🔄 执行备用规格选择逻辑...")
        
        # 先取消所有已选中的规格
        all_checkboxes = edit_page.locator("div.options-module label input[type='checkbox']")
        checkbox_count = all_checkboxes.count()
        
        if checkbox_count > 0:
            for i in range(checkbox_count):
                try:
                    checkbox = all_checkboxes.nth(i)
                    if checkbox.is_checked():
                        checkbox.uncheck(timeout=1000)
                except Exception:
                    continue
            
            edit_page.wait_for_timeout(1000)
            print("  ✅ 已重置所有规格选择")
        
        # 根据解析的规格进行选择
        selected_count = 0
        
        for spec_key, spec_value in spec_pairs:
            # 构建匹配模式
            match_patterns = [
                f"{spec_value}",
                f"{spec_value}(",
                f"({spec_value})",
            ]
            
            # 颜色翻译
            if spec_key.lower() in ['color', 'colour']:
                color_translations = {
                    'white': '白色', 'black': '黑色', 'red': '红色', 'blue': '蓝色',
                    'green': '绿色', 'yellow': '黄色', 'gray': '灰色', 'grey': '灰色',
                    'brown': '棕色', 'pink': '粉色', 'purple': '紫色', 'orange': '橙色',
                    'beige': '米色', 'silver': '银色', 'gold': '金色'
                }
                
                color_lower = spec_value.lower()
                if color_lower in color_translations:
                    chinese_color = color_translations[color_lower]
                    match_patterns.extend([
                        f"{spec_value}({chinese_color})",
                        f"{chinese_color}({spec_value})",
                        chinese_color
                    ])
            
            # 尝试匹配并选择
            found_match = False
            for pattern in match_patterns:
                try:
                    selector = f"div.options-module label[title*='{pattern}'] input[type='checkbox']"
                    checkbox = edit_page.locator(selector).first
                    
                    if checkbox.count() > 0 and checkbox.is_visible():
                        checkbox.check(timeout=2000)
                        selected_count += 1
                        found_match = True
                        print(f"  ✅ 备用选择成功: {pattern}")
                        edit_page.wait_for_timeout(500)
                        break
                        
                except Exception:
                    continue
            
            if not found_match:
                print(f"  ⚠️ 备用选择未找到匹配: {spec_key} = {spec_value}")
        
        print(f"🎯 备用逻辑完成，选中 {selected_count} 个规格")
        
    except Exception as e:
        print(f"❌ 备用规格选择失败: {e}")


def convert_weight_to_grams(weight_str: str) -> str:
    """
    将重量从磅转换为克，并移除单位
    
    Args:
        weight_str: 重量字符串，如 "39.68 Pounds" 或 "39.68"
        
    Returns:
        str: 转换后的克数，如 "17993"
    """
    import re
    
    try:
        if not weight_str:
            return "10"
        
        # 提取数字部分
        weight_match = re.search(r'([0-9.]+)', str(weight_str))
        if not weight_match:
            return "10"
        
        weight_pounds = float(weight_match.group(1))
        
        # 1磅 = 453.592克
        weight_grams = weight_pounds * 453.592
        
        # 返回整数克数
        return str(int(round(weight_grams)))
        
    except Exception as e:
        print(f"⚠️ 重量转换失败: {e}")
        return "10"


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

        # 确保URL有https前缀
        if not web_url.startswith(('http://', 'https://')):
            web_url = 'https://' + web_url
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

def show_product_preview_for_dianxiaomi(
    product_data: ProductData,
    ui: Optional[UserInteractionFlow] = None,
) -> bool:
    """
    显示产品信息预览，供用户审核 - 针对店小秘平台优化
    
    Returns:
        bool: 用户是否确认继续填充表单
    """
    print("\n" + "="*80)
    print("📋 店小秘产品信息预览 - 请审核以下数据")
    print("="*80)
    print("\n" + "="*80)
    
    while True:
        if ui is not None:
            decision = ui.prompt_product_preview_action()
        else:
            choice = input("🤔 请选择操作 [Y]继续填充 / [N]跳过 / [D]查看详情: ").strip().upper()
            if choice in {"", "Y", "YES"}:
                decision = "continue"
            elif choice in {"N", "NO"}:
                decision = "skip"
            elif choice in {"D", "DETAIL", "DETAILS"}:
                decision = "detail"
            else:
                print("❌ 无效选择，请输入 Y/N/D")
                continue
        
        if decision == "continue":
            print("✅ 用户确认，开始填充表单...")
            return True
        if decision == "skip":
            print("⏭️ 用户跳过，不填充表单")
            return False
        
        # 显示完整详情
        print("\n" + "="*60)
        print("📋 完整产品详情")
        print("="*60)
        for key, value in product_data.to_dict().items():
            print(f"{key:<30}: {value}")
        print("="*60)
        # 循环继续，直到用户做出明确选择


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
        product_dict=   product_data.details
        print(f"🎯 开始填充店小秘表单（{'手动审核' if manual_mode else '自动'}模式）...")
        print(product_dict)
        try:
            asin_input = edit_page.locator("input[name='productItemNumber']")
            if asin_input.is_visible():
                asin_input.fill(product_dict["asin"])
                print(f"✅ 产品货号: {product_dict['asin']}")
        except Exception as e:
            print(f"⚠️ 货号填充失败: {e}")
        # Fill product model with "|" as specified
        try:
            edit_page.wait_for_selector("div.sheinDynamicAttr1000546 input.ant-input",timeout=1000)
            prod_model= edit_page.locator("div.sheinDynamicAttr1000546 input.ant-input")
            prod_model.fill("\\")
        except Exception as e:
            print(f"⚠️ 产品型号填充失败: {e}")
            
         # 处理多个规格的checkbox，只保留当前选中规格
        handle_dynamic_specifications(edit_page, product_dict)
        # 填充产品标题
        if "title" in product_dict and product_dict["title"]:
            try:
                title_input = edit_page.locator("input[name='productTitleBuyer']")
                if title_input.is_visible():
                    # 针对店小秘平台优化标题长度
                    optimized_title = product_dict["title"][:1000]
                    
                    # 不区分大小写地去除品牌名称
                    brand_keys = ['brand']
                    for brand_key in brand_keys:
                        if brand_key in product_dict and product_dict[brand_key]:
                            brand_name = product_dict[brand_key]
                            # 清理品牌名中的不可见字符（Unicode方向标记等）
                            clean_brand_name = brand_name.strip().strip('\u200e\u200f\u202a\u202b\u202c\u202d\u202e')
                            if clean_brand_name:  # 确保清理后不为空
                                # 使用re.sub进行不区分大小写的替换，并去除首尾空格
                                optimized_title = re.sub(re.escape(clean_brand_name), '', optimized_title, flags=re.IGNORECASE).strip()
                                print(f"✅ 去除标题中的品牌 {clean_brand_name}: {optimized_title[:50]}...")
                                break
                    title_input.fill(optimized_title)
                    print(f"✅ 产品标题: {optimized_title[:50]}...")
            except Exception as e:
                print(f"⚠️ 标题填充失败: {e}")
        
        # Fill product description - 优先使用Key Features
        description_text = ""
        if "key features" in product_dict:
            description_text = product_dict["key features"]
        
        if description_text:
            try:
                desc_input = edit_page.locator("textarea[name='productDesc']")
                if desc_input.is_visible():
                    # 针对店小秘平台优化描述长度
                    optimized_desc = description_text[:5000]
                    
                    # 不区分大小写地去除品牌名称
                    brand_keys = ['brand']
                    for brand_key in brand_keys:
                        if brand_key in product_dict and product_dict[brand_key]:
                            brand_name = product_dict[brand_key]
                            # 清理品牌名中的不可见字符（Unicode方向标记等）
                            clean_brand_name = brand_name.strip().strip('\u200e\u200f\u202a\u202b\u202c\u202d\u202e')
                            if clean_brand_name:  # 确保清理后不为空
                                # 使用re.sub进行不区分大小写的替换，并去除首尾空格
                                optimized_desc = re.sub(re.escape(clean_brand_name), '', optimized_desc, flags=re.IGNORECASE).strip()
                                print(f"✅ 去除描述中的品牌 {clean_brand_name}")
                                break
                    desc_input.fill(optimized_desc)
                    print(f"✅ 产品描述: {len(optimized_desc)} 字符")
            except Exception as e:
                print(f"⚠️ 描述填充失败: {e}")
                
                
        
        # 表格信息开始------
         # Fill sku (if available)
        if "asin" in product_dict and product_dict["asin"]:
            try:
                sku_inputs = edit_page.locator("input[name='sku']")
                if sku_inputs.count() > 0:
                    # 清理价格数据
                        sku_inputs.first.fill(product_dict["asin"])
                        print(f"✅ 表格中sku: {product_dict['asin']}")
            except Exception as e:
                print(f"⚠️ sku填充失败: {e}")
        
        # Fill price (if available)
        if "price" in product_dict and product_dict["price"]:
            try:
                price_inputs = edit_page.locator("input[name='price']")
                if price_inputs.count() > 0:
                    # 清理价格数据
                    clean_price = float(product_dict["price"]) + float(product_dict['delivery price'])
                    if clean_price:
                        price_inputs.first.fill(str(clean_price))
                        print(f"✅ 产品价格: {clean_price}")
            except Exception as e:
                print(f"⚠️ 价格填充失败: {e}")

        try:
            inventory_inputs =  edit_page.locator("input[name='price'][maxlength='7']")
            if inventory_inputs.count() > 0:
                # 清理价格数据
                default_inventory = "2"
                # 设置默认库存数量
                default_inventory = "2"  # 可以根据需要调整默认值
                inventory_inputs.fill(default_inventory)
                print(f"✅ 已填充库存: {default_inventory}")
        except Exception as e:
            print(f"⚠️ 库存填充失败: {e}")
    

        
        # Fill weight (convert from pounds to grams)
        if "item weight" in product_dict and product_dict["item weight"]:
            try:
                weight_inputs = edit_page.locator("input[name='weight']")
                if weight_inputs.count() > 0:
                    # 转换重量从磅到克
                    weight_in_grams = convert_weight_to_grams(product_dict["item weight"])
                    if weight_in_grams:
                        weight_inputs.first.fill(weight_in_grams)
                        print(f"✅ 产品重量: {weight_in_grams}g (原值: {product_dict['item weight']})")
            except Exception as e:
                print(f"⚠️ 重量填充失败: {e}")
         # Fill length
        try:
            length_inputs = edit_page.locator("input[name='packageLength']")
            if length_inputs.count() > 0:
                    length_inputs.first.fill(product_dict.get("depth_cm", "50"))
        except Exception as e:
            print(f"⚠️ 长度填充失败: {e}")
        # Fill width
        try:
            width_inputs = edit_page.locator("input[name='packageWidth']")
            if width_inputs.count() > 0:
                width_inputs.first.fill(product_dict.get("width_cm", "50"))
        except Exception as e:
            print(f"⚠️ 宽度填充失败: {e}")
        # Fill height
        try:
            height_inputs = edit_page.locator("input[name='packageHeight']")
            if height_inputs.count() > 0:
                    height_inputs.first.fill(product_dict.get("height_cm", "50"))
        except Exception as e:
            print(f"⚠️ 高度填充失败: {e}")
        # SKU引用采集图片
        try:
            print("🖼️ 开始SKU引用采集图片流程...")
            
            # 1. 点击SKU图片区域触发下拉菜单
            sku_image_trigger = edit_page.locator("div.sku-data-table tbody div.sku-image").first
            sku_image_trigger.hover()  # 添加悬停效果，符合UI/UX偏好
            edit_page.wait_for_timeout(200)
            sku_image_trigger.click()
            print("  📌 已点击SKU图片区域，等待菜单出现...")
            
            # 2. 等待并点击"引用采集图片"菜单项（多种定位策略）
            edit_page.wait_for_timeout(300)  # 等待菜单渲染
            getPic = edit_page.locator("li.ant-dropdown-menu-item", has_text="引用采集图片")
            
            if getPic.count() > 0 and getPic.is_visible():
                print(f"  ✅ 找到菜单项: {getPic.first.text_content()}")
                getPic.hover()  # 平滑的悬停动画
                edit_page.wait_for_timeout(150)
                getPic.click()
                print("  🎯 已点击'引用采集图片'，等待弹框加载...")
                
                # 3. 等待图片选择弹框出现（遵循模态对话框操作规范）
                edit_page.wait_for_timeout(500)
                
                # 4. 选中第一个图片的checkbox（多种定位策略）
                try:
                    # 策略1: 通过标准的ant-checkbox-group定位
                    first_checkbox = edit_page.locator('div.ant-checkbox-group.img-box div.ant-checkbox-wrapper').first
                    
                    if first_checkbox.count() > 0:
                        # 等待checkbox可见
                        first_checkbox.wait_for(state="visible", timeout=2000)
                        
                        # 添加悬停效果（符合用户UI/UX偏好）
                        first_checkbox.hover()
                        edit_page.wait_for_timeout(150)
                        
                        # 点击选中第一个checkbox
                        first_checkbox.click(force=True)
                        print("  ✅ 已选中第一个图片的checkbox")
                    else:
                        # 备用策略2: 通过input[type='checkbox']定位
                        first_checkbox_input = edit_page.locator('div.img-box input[type="checkbox"]').first
                        if first_checkbox_input.count() > 0:
                            first_checkbox_input.check(force=True)
                            print("  ✅ 已选中第一个图片的checkbox（备用方法）")
                        else:
                            print("  ⚠️ 未找到图片checkbox，可能弹框未正确加载")
                            raise Exception("无法定位图片checkbox")
                    
                    edit_page.wait_for_timeout(300)  # 等待选中状态生效
                    
                except Exception as checkbox_error:
                    print(f"  ❌ 选中checkbox失败: {checkbox_error}")
                    raise
                
                # 5. 点击"选择"按钮（多种定位策略）
                try:
                    # 策略1: 通过primary按钮和文本定位

                    # 首先等待弹框出现并通过标题定位
                    edit_page.wait_for_selector('.ant-modal-title:has-text("引用采集图片")', timeout=3000)
                    
                    # 在弹框内定位"选择"按钮
                    select_btn = edit_page.locator('.ant-modal:has(.ant-modal-title:has-text("引用采集图片")) button.ant-btn-primary:has-text("选择")').first
                    
                    if select_btn.count() > 0 and select_btn.is_visible():
                        edit_page.wait_for_timeout(150)
                        select_btn.click(force=True)
                        print("  ✅ 已点击'选择'按钮")
                    else:
                        # 备用策略2: 通过文本内容定位
                        select_btn_alt = edit_page.locator('button:has-text("选择")').first
                        if select_btn_alt.count() > 0:
                            select_btn_alt.click(force=True)
                            print("  ✅ 已点击'选择'按钮（备用方法）")
                        else:
                            print("  ⚠️ 未找到'选择'按钮")
                            raise Exception("无法定位'选择'按钮")
                    
                    # 等待操作完成
                    edit_page.wait_for_timeout(800)
                    print("🎉 SKU引用采集图片完成！")
                    
                except Exception as btn_error:
                    print(f"  ❌ 点击'选择'按钮失败: {btn_error}")
                    raise
                    
            else:
                print("  ⚠️ '引用采集图片'菜单项不可见或不存在")
                raise Exception("菜单项不可用")
                
        except Exception as e:
            print(f"❌ SKU引用采集图片流程失败: {e}")
            print("  💡 建议：检查页面是否已正确加载，或者采集图片是否存在")
        
        
        # 批量编辑SKU图片大小
        try:
            edit_page.locator("table").filter(has_text="SKU图片").get_by_text("批量").first.click()
            editPic= edit_page.locator("li.ant-dropdown-menu-item", has_text="批量改图片尺寸")
            print("✅ 准备编辑sku图片")
            if editPic.is_visible():
                editPic.click()
                edit_page.wait_for_selector('span[title="等比例调整"]', timeout=2000)
                sel = edit_page.locator('span[title="等比例调整"]').locator('..')  # 找到父级 ant-select
                # 打开第一个下拉 - 使用强制点击
                try:
                    sel.wait_for(state="visible", timeout=1000)
                    sel.click(force=True)  # 强制点击打开下拉
                    edit_page.wait_for_timeout(500)
                    
                    list_id = sel.locator('input').get_attribute('aria-owns')   # 拿到 rc_select_XX_list
                    if list_id:
                        option_selector = f'#{list_id} div.ant-select-item-option[title="自定义比例调整"]'
                        edit_page.wait_for_selector(option_selector, timeout=1000)
                        edit_page.locator(option_selector).click(force=True)
                    else:
                        # 备用方法：直接选择
                        edit_page.locator('div.ant-select-item-option[title="自定义比例调整"]').first.click(force=True)
                except Exception as sel_error:
                    print(f"⚠️ 第一个下拉选择失败: {sel_error}")
                    # 备用方法：通过键盘操作
                    try:
                        sel.click(force=True)
                        edit_page.keyboard.press('ArrowDown')
                        edit_page.keyboard.press('Enter')
                    except:
                        pass
                
                # 第二个下拉选择 - 更改为 "1 : 1"
                edit_page.wait_for_timeout(500)  # 等待第一个下拉关闭
                sel2 = edit_page.locator('span[title="保持原图比例"]').locator('..')  # 找到父级 ant-select
                
                try:
                    sel2.wait_for(state="visible", timeout=2000)
                    sel2.click(force=True)  # 强制点击
                    edit_page.wait_for_timeout(500)
                    
                    list_id2 = sel2.locator('input').get_attribute('aria-owns')
                    if list_id2:
                        option_selector2 = f'#{list_id2} div.ant-select-item-option[title="1 : 1"]'
                        edit_page.wait_for_selector(option_selector2, timeout=1000)
                        edit_page.locator(option_selector2).click(force=True)
                    else:
                        # 备用方法：直接通过文本选择
                        edit_page.locator('div.ant-select-item-option[title="1 : 1"]').first.click(force=True)
                except Exception as sel2_error:
                    print(f"⚠️ 第二个下拉选择失败: {sel2_error}")
                    # 备用方法：通过键盘操作
                    try:
                        sel2.click(force=True)
                        edit_page.keyboard.press('ArrowDown')
                        edit_page.keyboard.press('Enter')
                    except:
                        pass
                edit_page.wait_for_selector("input[name='valueW']",timeout=2000)    
                inputW_elements: Locator = edit_page.locator("input[name='valueW']")    
                inputW_elements.first.fill("1000")
                submit_btn = edit_page.get_by_role("button", name="生成JPG图片")
                submit_btn.click()
                print("✅ 编辑sku图片大小完成")
        except Exception as e:
            print(f"⚠️ 编辑sku图片失败: {e}")
        # # 表格信息结束------
        # edit_page.wait_for_timeout(2000)
    #    # 批量清空SKU图片
    #     try:
    #         edit_page.locator("table").filter(has_text="SKU图片").get_by_text("批量").first.click()
    #         edit_page.locator("li.ant-dropdown-menu-item", has_text="清空图片").click()
    #         # 使用更准确的选择器匹配确定按钮
    #         try:
    #             # 方法1: 通过类名和文本内容精确匹配
    #             submit_btn = edit_page.locator("button.ant-btn-primary:has-text('确 定')")
    #             if submit_btn.count() > 0:
    #                 submit_btn.click(force=True)
    #                 print("✅ 点击确定按钮成功 (方法1)")
    #             else:
    #                 # 方法2: 备用选择器
    #                 submit_btn = edit_page.locator("button:has-text('确 定')")
    #                 if submit_btn.count() > 0:
    #                     submit_btn.click(force=True)
    #                     print("✅ 点击确定按钮成功 (方法2)")
    #                 else:
    #                     # 方法3: 通过span内容匹配
    #                     submit_btn = edit_page.locator("button span:has-text('确 定')")
    #                     if submit_btn.count() > 0:
    #                         submit_btn.click(force=True)
    #                         print("✅ 点击确定按钮成功 (方法3)")
    #                     else:
    #                         print("❌ 未找到确定按钮")
    #         except Exception as btn_error:
    #             print(f"⚠️ 点击确定按钮失败: {btn_error}")
    #         print("✅ 清空sku图片完成")
    #     except Exception as e:
    #         print(f"⚠️ 清空sku图片失败: {e}")
        # 表格信息结束------
        edit_page.wait_for_timeout(2000)
        # 批量编辑变种图片大小
        try:
            editPic = edit_page.locator("div#skuImageInfo").get_by_text("编辑图片").first
            print("✅ 准备点击变种图片的编辑图片")
            if editPic.is_visible():
                editPic.click()
                edit_page.wait_for_timeout(2000)
                edit_page.get_by_role("menuitem", name="批量改图片尺寸").first.click()
                edit_page.wait_for_selector('span[title="等比例调整"]', timeout=2000)
                sel = edit_page.locator('span[title="等比例调整"]').locator('..')  # 找到父级 ant-select
                # 打开第一个下拉 - 使用强制点击
                try:
                    sel.wait_for(state="visible", timeout=1000)
                    sel.click(force=True)  # 强制点击打开下拉
                    edit_page.wait_for_timeout(500)
                    
                    list_id = sel.locator('input').get_attribute('aria-owns')   # 拿到 rc_select_XX_list
                    if list_id:
                        option_selector = f'#{list_id} div.ant-select-item-option[title="自定义比例调整"]'
                        edit_page.wait_for_selector(option_selector, timeout=1000)
                        edit_page.locator(option_selector).click(force=True)
                    else:
                        # 备用方法：直接选择
                        edit_page.locator('div.ant-select-item-option[title="自定义比例调整"]').first.click(force=True)
                except Exception as sel_error:
                    print(f"⚠️ 第一个下拉选择失败: {sel_error}")
                    # 备用方法：通过键盘操作
                    try:
                        sel.click(force=True)
                        edit_page.keyboard.press('ArrowDown')
                        edit_page.keyboard.press('Enter')
                    except:
                        pass
                
                # 第二个下拉选择 - 更改为 "1 : 1"
                edit_page.wait_for_timeout(500)  # 等待第一个下拉关闭
                sel2 = edit_page.locator('span[title="保持原图比例"]').locator('..')  # 找到父级 ant-select
                
                try:
                    sel2.wait_for(state="visible", timeout=2000)
                    sel2.click(force=True)  # 强制点击
                    edit_page.wait_for_timeout(500)
                    
                    list_id2 = sel2.locator('input').get_attribute('aria-owns')
                    if list_id2:
                        option_selector2 = f'#{list_id2} div.ant-select-item-option[title="1 : 1"]'
                        edit_page.wait_for_selector(option_selector2, timeout=1000)
                        edit_page.locator(option_selector2).click(force=True)
                    else:
                        # 备用方法：直接通过文本选择
                        edit_page.locator('div.ant-select-item-option[title="1 : 1"]').first.click(force=True)
                except Exception as sel2_error:
                    print(f"⚠️ 第二个下拉选择失败: {sel2_error}")
                    # 备用方法：通过键盘操作
                    try:
                        sel2.click(force=True)
                        edit_page.keyboard.press('ArrowDown')
                        edit_page.keyboard.press('Enter')
                    except:
                        pass
                edit_page.wait_for_selector("input[name='valueW']",timeout=2000)    
                input_elements: Locator = edit_page.locator("input[name='valueW']")    
                input_elements.first.fill("1000")
                submit_btn = edit_page.get_by_role("button", name="生成JPG图片")
                submit_btn.click()
                print("✅ 编辑变种图片大小完成")
        except Exception as e:
            print(f"⚠️ 编辑变种图片失败: {e}")
        edit_page.wait_for_timeout(5000) 
        # 批量清空图片
        try:
            editPic = edit_page.locator("div#skuDescInfo").get_by_text("编辑图片").first
            if editPic.is_visible():
                editPic.click()
                edit_page.get_by_role("menuitem", name="清空图片").first.click()
                # 使用更准确的选择器匹配确定按钮
                try:
                    # 方法1: 通过类名和文本内容精确匹配
                    submit_btn = edit_page.locator("button.ant-btn-primary:has-text('确 定')")
                    if submit_btn.count() > 0:
                        submit_btn.click(force=True)
                        print("✅ 点击确定按钮成功")
                    else:
                        # 方法2: 备用选择器
                        submit_btn = edit_page.locator("button:has-text('确 定')")
                        if submit_btn.count() > 0:
                            submit_btn.click(force=True)
                            print("✅ 点击确定按钮成功 (备用方法)")
                        else:
                            print("❌ 详情图清空未找到确定按钮")
                except Exception as btn_error:
                    print(f"⚠️ 点击确定按钮失败: {btn_error}")
                print("✅ 详情图清空结束")
        except Exception as e:
            print(f"⚠️ 详情图清空失败: {e}")
            
            
        # 清空色块
        try:
            edit_page.locator("table").filter(has_text="色块图").get_by_text("编辑").last.click()
            edit_page.get_by_role("menuitem", name="清空图片").first.click()
            # 使用更准确的选择器匹配确定按钮
            try:
                # 方法1: 通过类名和文本内容精确匹配
                submit_btn = edit_page.locator("button.ant-btn-primary:has-text('确 定')")
                if submit_btn.count() > 0:
                    submit_btn.click(force=True)
                    print("✅ 点击确定按钮成功 (方法1)")
                else:
                    # 方法2: 备用选择器
                    submit_btn = edit_page.locator("button:has-text('确 定')")
                    if submit_btn.count() > 0:
                        submit_btn.click(force=True)
                        print("✅ 点击确定按钮成功 (方法2)")
                    else:
                        # 方法3: 通过span内容匹配
                        submit_btn = edit_page.locator("button span:has-text('确 定')")
                        if submit_btn.count() > 0:
                            submit_btn.click(force=True)
                            print("✅ 点击确定按钮成功 (方法3)")
                        else:
                            print("❌ 清空色块未找到确定按钮")
            except Exception as btn_error:
                print(f"⚠️ 点击确定按钮失败: {btn_error}")
            print("✅ 清空色块图片结束")
        except Exception as e:
            print(f"⚠️ 清空色块图片失败: {e}")
        # 批量编辑详情图大小
        # try:
        #     editPic = edit_page.locator("div#skuDescInfo").get_by_text("编辑图片").first
        #     print("✅ 准备编辑详情图片")
        #     if editPic.is_visible():
        #         editPic.click()
        #         edit_page.get_by_role("menuitem", name="批量改图片尺寸").first.click()
        #         edit_page.wait_for_selector('span[title="等比例调整"]', timeout=2000)
        #         sel = edit_page.locator('span[title="等比例调整"]').locator('..')  # 找到父级 ant-select
        #         # 打开第一个下拉 - 使用强制点击
        #         try:
        #             sel.wait_for(state="visible", timeout=1000)
        #             sel.click(force=True)  # 强制点击打开下拉
        #             edit_page.wait_for_timeout(500)
                    
        #             list_id = sel.locator('input').get_attribute('aria-owns')   # 拿到 rc_select_XX_list
        #             if list_id:
        #                 option_selector = f'#{list_id} div.ant-select-item-option[title="自定义比例调整"]'
        #                 edit_page.wait_for_selector(option_selector, timeout=1000)
        #                 edit_page.locator(option_selector).click(force=True)
        #             else:
        #                 # 备用方法：直接选择
        #                 edit_page.locator('div.ant-select-item-option[title="自定义比例调整"]').first.click(force=True)
        #         except Exception as sel_error:
        #             print(f"⚠️ 第一个下拉选择失败: {sel_error}")
        #             # 备用方法：通过键盘操作
        #             try:
        #                 sel.click(force=True)
        #                 edit_page.keyboard.press('ArrowDown')
        #                 edit_page.keyboard.press('Enter')
        #             except:
        #                 pass
                
        #         # 第二个下拉选择 - 更改为 "1 : 1"
        #         edit_page.wait_for_timeout(500)  # 等待第一个下拉关闭
        #         sel2 = edit_page.locator('span[title="保持原图比例"]').locator('..')  # 找到父级 ant-select
                
        #         try:
        #             sel2.wait_for(state="visible", timeout=2000)
        #             sel2.click(force=True)  # 强制点击
        #             edit_page.wait_for_timeout(500)
                    
        #             list_id2 = sel2.locator('input').get_attribute('aria-owns')
        #             if list_id2:
        #                 option_selector2 = f'#{list_id2} div.ant-select-item-option[title="1 : 1"]'
        #                 edit_page.wait_for_selector(option_selector2, timeout=1000)
        #                 edit_page.locator(option_selector2).click(force=True)
        #             else:
        #                 # 备用方法：直接通过文本选择
        #                 edit_page.locator('div.ant-select-item-option[title="1 : 1"]').first.click(force=True)
        #         except Exception as sel2_error:
        #             print(f"⚠️ 第二个下拉选择失败: {sel2_error}")
        #             # 备用方法：通过键盘操作
        #             try:
        #                 sel2.click(force=True)
        #                 edit_page.keyboard.press('ArrowDown')
        #                 edit_page.keyboard.press('Enter')
        #             except:
        #                 pass
        #         edit_page.wait_for_selector("input[name='valueW']",timeout=2000)    
        #         input_elements: Locator = edit_page.locator("input[name='valueW']")    
        #         input_elements.first.fill("1000")
        #         submit_btn = edit_page.get_by_role("button", name="生成JPG图片")
        #         submit_btn.click()
        #         print("✅ 编辑详情图片大小完成")
        # except Exception as e:
        #     print(f"⚠️ 编辑详情图片失败: {e}")
            
           
            
        # try:
        #     # 填充库存信息 - 定位到表格第5个td（库存列）
        #     inventory_rows = edit_page.locator("table.myj-table tbody tr")
        #     if inventory_rows.count() > 0:
        #         for i in range(inventory_rows.count()):
        #             row = inventory_rows.nth(i)
        #             # 库存在第5个td中
        #             inventory_cell = row.locator("td:nth-child(5)")
        #             if inventory_cell.is_visible():
        #                 # 查找库存输入框（name="price" 且 maxlength="7"）
        #                 inventory_input = inventory_cell.locator("input[name='price'][maxlength='7']")
        #                 if inventory_input.count() > 0:
        #                     # 设置默认库存数量
        #                     default_inventory = "2"  # 可以根据需要调整默认值
        #                     inventory_input.fill(default_inventory)
        #                     print(f"✅ 已填充库存: {default_inventory}")
        #                 else:
        #                     print("⚠️ 未找到库存输入框")
        #             else:
        #                 print(f"⚠️ 第{i+1}行库存单元格不可见")
        #     else:
        #         print("⚠️ 未找到SKU数据表格行")
        # except Exception as e:
        #     print(f"⚠️ 填充库存失败: {e}")
            
        
            
        # 删除sku图片
        # try:
        #     sku_img_deletebtns = edit_page.locator("div.sku-image-box span.img-close-icon")
        #     count=sku_img_deletebtns.count()
        #     for i in range(count):
        #         sku_img_deletebtns.nth(i).click()
        # except Exception as e:
        #     print(f"⚠️ 删除sku图片失败: {e}")
         # 删除详情图 - 改进版本
        # try:
        #     # 先关闭可能存在的模态框
        #     try:
        #         modal_elements = edit_page.locator('.ant-modal-mask, .ant-modal-wrap')
        #         if modal_elements.count() > 0:
        #             # 尝试点击模态框外部区域关闭
        #             edit_page.keyboard.press('Escape')
        #             edit_page.wait_for_timeout(500)
        #     except:
        #         pass
                
        #     img_deletebtns = edit_page.locator("#skuDescInfo a.icon_delete")
        #     count = img_deletebtns.count()
        #     print(f"🔍 找到 {count} 个详情图删除按钮")
            
        #     for i in range(count):
        #         try:
        #             delete_btn = img_deletebtns.nth(i)
        #             if delete_btn.is_visible():
        #                 # 等待元素可点击并强制点击
        #                 delete_btn.wait_for(state="visible", timeout=3000)
        #                 delete_btn.click(force=True, timeout=5000)
        #                 edit_page.wait_for_timeout(300)  # 等待点击生效
        #                 print(f"✅ 已删除第 {i+1} 个详情图")
        #             else:
        #                 print(f"⚠️ 第 {i+1} 个删除按钮不可见")
        #         except Exception as single_delete_error:
        #             print(f"⚠️ 删除第 {i+1} 个详情图失败: {single_delete_error}")
        #             continue
        # except Exception as e:
        #     print(f"⚠️ 删除详情图片失败: {e}")
        # 在手动模式下，显示更多可填充的字段信息
        if manual_mode:
            fillable_fields = ['Brand', 'Material', 'Color', 'Style']
            available_fields = [field for field in fillable_fields if field in product_dict]
            if available_fields:
                print("📋 可用属性信息:")
                for field in available_fields:
                    print(f"  - {field}: {product_dict[field]}")
        
        print("✅ 表单填充完成")
        print("📝 校验数据")
        try:
            # 从页面中获取产品分类的值
            try:
                category_element = edit_page.locator("div.category-item span.ant-select-selection-item").first
                if category_element.is_visible():
                    category_name = category_element.get_attribute("title")
                    if not category_name:
                        # 如果title属性为空，尝试获取文本内容
                        text_content = category_element.text_content()
                        category_name = text_content.strip() if text_content else "未知分类"
                    print(f"✅ 从页面获取产品分类: {category_name}")
                else:
                    # 备用方法：通过表单项标签查找
                    category_input = edit_page.locator("label:has-text('产品分类')").locator("../../../div[contains(@class, 'ant-form-item-control')] span.ant-select-selection-item").first
                    if category_input.is_visible():
                        title_attr = category_input.get_attribute("title")
                        text_content = category_input.text_content()
                        category_name = title_attr or (text_content.strip() if text_content else "未知分类")
                        print(f"✅ 通过备用方法获取产品分类: {category_name}")
                    else:
                        category_name = "未知分类"
                        print("⚠️ 无法从页面获取产品分类，使用默认值")
            except Exception as e:
                category_name = "未知分类"
                print(f"⚠️ 获取产品分类失败: {e}")
            
            print("✅ 数据校验通过")
            
            # AI分类验证
            try:
                # 加载配置文件
                import json
                config_path = os.path.join(os.path.dirname(__file__), 'config', 'ai_config.json')
                
                ai_config = None
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        ai_config = config.get('ai_validator', {})
                
                # 检查是否启用AI验证
                if ai_config and ai_config.get('enabled', False) and ai_config.get('api_key') != 'your-api-key-here':
                    # 初始化AI验证器
                    ai_validator = AICategoryValidator(
                        api_base_url=ai_config.get('api_base_url', 'https://api.openai.com/v1'),
                        api_key=ai_config.get('api_key'),
                        model_name=ai_config.get('model_name', 'gpt-3.5-turbo'),
                        timeout=ai_config.get('timeout', 30)
                    )
                    
                    # 准备验证数据
                    title = getattr(product_data, 'title', '未知标题')
                    features = []
                    
                    # 从details字典中收集关键特征
                    if hasattr(product_data, 'details') and product_data.details:
                        # 收集常见的产品特征
                        feature_keys = ['Brand', 'Color', 'Material', 'Style', 'Special Feature', 
                                       'Shape', 'Pattern', 'Theme', 'Finish Type']
                        for key in feature_keys:
                            if key in product_data.details and product_data.details[key]:
                                features.append(f"{key}: {product_data.details[key]}")
                        
                        # 添加产品尺寸信息
                        if 'Product Dimensions' in product_data.details:
                            features.append(f"尺寸: {product_data.details['Product Dimensions']}")
                        
                        # 添加重量信息
                        if 'Item Weight' in product_data.details:
                            features.append(f"重量: {product_data.details['Item Weight']}")
                    
                    print(f"🤖 正在进行AI分类验证...")
                    print(f"📝 产品标题: {title[:50]}...")
                    print(f"🔍 关键特征: {len(features)}个")
                    
                    # 执行AI验证
                    is_reasonable, reason, suggested_category = ai_validator.validate_category(
                        title=title,
                        key_features=features,
                        current_category=category_name
                    )
                    
                    print(f"🎯 AI验证结果: {'✅ 分类合理' if is_reasonable else '⚠️ 分类可能不准确'}")
                    print(f"📊 分析原因: {reason}")
                    
                    if not is_reasonable and suggested_category:
                        print(f"💡 AI建议分类: {suggested_category}")
                        
                        # 获取商品链接用于记录
                        try:
                            web_url = edit_page.locator("input[name='sourceUrl']").input_value() or "未知链接"
                        except:
                            web_url = "未知链接"
                        
                        # 将不合理的分类记录到CSV文件
                        csv_result = write_unreasonable_category_to_csv(
                            product_url=web_url,
                            title=title,
                            current_category=category_name,
                            ai_reason=reason,
                            suggested_category=suggested_category
                        )
                        
                        if csv_result:
                            print(f"📁 已记录到审核文件: {os.path.basename(csv_result)}")

                    elif not is_reasonable:
                        # 没有建议分类但分类不合理的情况
                        try:
                            web_url = edit_page.locator("input[name='sourceUrl']").input_value() or "未知链接"
                        except:
                            web_url = "未知链接"
                        
                        csv_result = write_unreasonable_category_to_csv(
                            product_url=web_url,
                            title=title,
                            current_category=category_name,
                            ai_reason=reason,
                            suggested_category=None
                        )
                        
                        if csv_result:
                            print(f"📁 已记录到审核文件: {os.path.basename(csv_result)}")
                
                else:
                    print("🤖 AI分类验证未启用或配置不完整")
                    print("📝 请在 src/config/ai_config.json 中配置API密钥")
                
            except Exception as ai_error:
                print(f"⚠️ AI分类验证失败: {ai_error}")
                print("📝 继续使用当前分类")
        except Exception as e:
            print(f"❌ 数据校验失败: {e}")
        
    except Exception as e:
        print(f"❌ 表单填充失败: {e}")
        
        # 记录表单填充异常
        try:
            web_url = "未知链接"
            title = "未知标题"
            category = "未知分类"
            
            try:
                web_url = edit_page.locator("input[name='sourceUrl']").input_value() or "未知链接"
                title = getattr(product_data, 'title', '未知标题') if 'product_data' in locals() else '未知标题'
                category_element = edit_page.locator("span.ant-select-selection-item").first
                if category_element.is_visible():
                    category = category_element.get_attribute("title") or category_element.text_content() or "未知分类"
            except:
                pass
            
            write_processing_exception_to_csv(
                product_url=web_url,
                title=title,
                current_category=category,
                exception_type=type(e).__name__,
                error_message=str(e),
                operation_step="表单填充"
            )
        except Exception as log_error:
            print(f"⚠️ 记录表单填充异常失败: {log_error}")
        
def save_product_changes_enhanced(edit_page: Page, manual_mode: bool = False,title:str='') -> bool:
    """
    增强版保存函数 - 针对店小秘平台优化
    
    Args:
        edit_page: 编辑页面对象
        manual_mode: 是否为手动模式
        
    Returns:
        bool: 保存是否成功
    """
    try:
        # if manual_mode:
            # # 手动模式：询问用户是否保存
            # while True:
            #     save_choice = input("💾 是否保存产品? [Y]是 / [N]否: ").strip().upper()
            #     if save_choice in ['Y', 'YES', '']:
            #         break
            #     elif save_choice in ['N', 'NO']:
            #         print("⏭️ 用户选择不保存")
            #         return False
            #     else:
            #         print("❌ 无效选择，请输入 Y 或 N")
        edit_page.wait_for_timeout(2000)
        
        # 先关闭可能存在的模态框
        try:
            modal_close_selectors = [
                '.ant-modal-close',
                '.ant-modal-close-x',
                'button[aria-label="关闭"]',
                '.ant-modal-wrap button[class*="close"]'
            ]
            for selector in modal_close_selectors:
                modal_close = edit_page.locator(selector)
                if modal_close.count() > 0 and modal_close.first.is_visible():
                    modal_close.first.click(force=True)
                    edit_page.wait_for_timeout(500)
                    break
        except:
            pass
        
        # 查找保存按钮 - 改进版本
        save_button = edit_page.get_by_role("button", name=re.compile(r"^保存$")).first
        if save_button.is_visible():
            try:
                # 等待按钮可点击并强制点击
                save_button.wait_for(state="visible", timeout=5000)
                save_button.click(force=True, timeout=10000)
                print("点击保存按钮")
                print(save_button.inner_html())
                print("✅ 产品已保存")
                print(f"✅ 产品标题：{title}")
                
                # Wait for save confirmation
                edit_page.wait_for_timeout(2000)
                
                # 关闭编辑页弹框
                try:
                    close_btn = edit_page.locator("button.ant-modal-close").first
                    if close_btn.is_visible():
                        close_btn.click(force=True, timeout=5000)
                        print("✅ 点击关闭编辑页弹框，自动关闭页面")
                        print("✅ 编辑页面已正常关闭")
                    else:
                        # 备用方法：按ESC键
                        edit_page.keyboard.press('Escape')
                        print("✅ 使用ESC关闭编辑页面")
                except Exception as close_error:
                    print(f"⚠️ 关闭编辑页失败: {close_error}")
                    
                return True
            except Exception as save_error:
                print(f"⚠️ 点击保存按钮失败: {save_error}")
                # 尝试备用方法：直接通过选择器点击
                try:
                    save_btn_backup = edit_page.locator('button[class*="btn-orange"]:has-text("保存")')
                    if save_btn_backup.count() > 0:
                        save_btn_backup.first.click(force=True)
                        print("✅ 使用备用方法保存成功")
                        edit_page.wait_for_timeout(1000)
                        return True
                except:
                    pass
                return False
        else:
            print("❌ 未找到保存按钮")
            return False
            
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        print("强制关闭页面")
        edit_page.close()
        return False


def process_product_edit_enhanced(context, edit_page: Page, manual_mode: bool = False) -> bool:
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
        # # Click the edit button
        # print("🔍 点击编辑按钮...")
        # with page.context.expect_page() as edit_page_info:
        #     edit_button.click()
        
        # edit_page = edit_page_info.value
        # edit_page.wait_for_timeout(3000)
        # print("✅ 编辑页面已打开")
        
        # Extract web_url from the sourceUrl input field
        source_url_input = edit_page.locator("input[name='sourceUrl']")
        web_url = None
        try:
            source_url_input.wait_for(state="attached", timeout=15000)
        except Exception as wait_error:
            print(f"⚠️ 等待访问链接输入框失败: {wait_error}")
        else:
            for attempt in range(12):
                try:
                    candidate = (source_url_input.input_value() or "").strip()
                except Exception:
                    candidate = ""
                if not candidate:
                    candidate = (source_url_input.get_attribute("value") or "").strip()
                if candidate:
                    web_url = candidate
                    break
                if attempt == 0:
                    print("⏳ 页面加载较慢，正在等待访问链接...")
                edit_page.wait_for_timeout(1000)

        if web_url:
            print(f"🔗 提取产品链接: {web_url[:60]}...")
        else:
            print("❌ 未找到访问链接，跳过此产品")
            edit_page.close()
            return False
        
        # 解析亚马逊产品数据
        product_data = parse_amazon_product_enhanced(context, web_url)
        
        if not product_data:
            print("❌ 产品解析失败")
            edit_page.close()
            return False
                   # 填充表单
        fill_edit_form_enhanced(edit_page, product_data, manual_mode)
            
        if manual_mode:
            if run_model=='test':
                print("测试模式，跳过保存")
                return True
                
            # 保存产品
            save_success = save_product_changes_enhanced(edit_page, manual_mode, product_data.title)
            
            return save_success
        else:
            # 非手动模式的处理逻辑
            print("⚠️ 非手动模式暂未实现")
            edit_page.close()
            return False
            
    except Exception as e:
        print(f"❌ 处理产品时出错: {e}")
        
        # 记录处理异常
        try:
            # 获取商品信息用于异常记录
            web_url = "未知链接"
            title = "未知标题"
            category = "未知分类"
            
            if edit_page is not None:
                try:
                    web_url = edit_page.locator("input[name='sourceUrl']").input_value() or "未知链接"
                    # 尝试获取标题和分类
                    title_element = edit_page.locator("input[name='title'], .product-title, h1").first
                    if title_element.is_visible():
                        title = title_element.input_value() or title_element.text_content() or "未知标题"
                    
                    category_element = edit_page.locator("span.ant-select-selection-item").first
                    if category_element.is_visible():
                        category = category_element.get_attribute("title") or category_element.text_content() or "未知分类"
                except:
                    pass  # 如果获取失败，使用默认值
            
            # 记录异常到CSV
            write_processing_exception_to_csv(
                product_url=web_url,
                title=title,
                current_category=category,
                exception_type=type(e).__name__,
                error_message=str(e),
                operation_step="产品处理"
            )
        except Exception as log_error:
            print(f"⚠️ 记录异常信息失败: {log_error}")
        
        try:
            if edit_page is not None:
                edit_page.close()
        except:
            pass
        return False


def run_manual_mode(context, page, ui: UserInteractionFlow):
    """手动审核模式 - 逐个产品审核，可切换自动模式"""
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
    auto_mode = False
    
    # Process each product with manual review
    for i in range(count):
        print(f"\n{'='*60}")
        print(f"🔍 处理产品 {i+1}/{count}")
        print("="*60)
        
        try:
            # Get fresh reference to the button (DOM might change)
            buttons, _ = get_edit_buttons(page)
            if i < buttons.count():
                  # Click the edit button
                print("🔍 点击编辑按钮...")
                edit_button=buttons.nth(i)
                with page.context.expect_page() as edit_page_info:
                    edit_button.click()
                edit_page = edit_page_info.value
                edit_page.wait_for_timeout(3000)
                print("✅ 编辑页面已打开")
                success = process_product_edit_enhanced(context, edit_page, manual_mode=True)
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
            remaining = count - i - 1
            if auto_mode:
                ui.notify(f"\n⚙️ 自动继续模式已开启，剩余 {remaining} 个产品将自动处理...")
            else:
                decision = ui.prompt_manual_continue(processed, skipped, errors, remaining)
                if decision == "stop":
                    ui.notify("🛑 用户选择结束处理")
                    break
                if decision == "auto":
                    auto_mode = True
        
        # Wait between operations
        page.wait_for_timeout(2000)
    
    print(f"\n{'='*80}")
    print("📊 手动审核模式处理完成")
    print(f"✅ 成功处理: {processed} 个产品")
    print(f"⏭️ 跳过: {skipped} 个产品") 
    print(f"❌ 错误: {errors} 个产品")
    
    # 使用CSV日志工具显示汇总信息
    csv_logger.print_daily_summary()
    
    print("="*80)
    
def closeAdModal(page: Page):
    """
    处理连续弹出的弹窗 - 优化版本
    处理先弹出一个，关闭后又弹出另一个的情况
    """
    try:
        max_attempts = 5  # 最多尝试关闭5个连续弹窗
        popup_closed = 0
        
        print("🔍 开始检查并关闭连续弹窗...")
        
        for attempt in range(max_attempts):
            # 等待弹窗出现
            page.wait_for_timeout(1500)
            
            # 检查是否有弹窗出现
            popup_found = False
            
            # 常见的弹窗关闭按钮选择器
            close_selectors = [
                "button:has-text('关闭')",
                "button[aria-label='关闭']",
                ".ant-modal-close",
                ".ant-modal-close-x", 
                "button.ant-btn:has-text('关闭')",
                "[class*='close']:has-text('关闭')",
                "button[title='关闭']",
                ".ant-modal-mask + .ant-modal-wrap .ant-modal-close",
                ".ant-modal .ant-modal-close-icon",
                "button:has-text('取消')",
                "button:has-text('知道了')",
                "button:has-text('确定')"
            ]
            
            # 尝试每个选择器
            for selector in close_selectors:
                try:
                    close_button = page.locator(selector).first
                    
                    # 检查按钮是否可见且可点击
                    if close_button.count() > 0 and close_button.is_visible():
                        print(f"  🎯 发现弹窗 {attempt + 1}，尝试关闭...")
                        close_button.click()
                        popup_closed += 1
                        popup_found = True
                        
                        # 等待弹窗关闭动画完成
                        page.wait_for_timeout(1000)
                        print(f"  ✅ 弹窗 {attempt + 1} 已关闭")
                        break  # 成功关闭一个弹窗后，跳出选择器循环
                        
                except Exception as selector_error:
                    # 当前选择器失败，尝试下一个
                    continue
            
            # 如果本轮没有找到弹窗，说明已经全部关闭
            if not popup_found:
                if attempt == 0:
                    print("  ℹ️ 未发现弹窗")
                else:
                    print(f"  ✅ 所有弹窗已处理完毕")
                break
        
        # 最终检查：确保没有遗漏的弹窗
        page.wait_for_timeout(500)
        
        if popup_closed > 0:
            print(f"🎉 成功关闭 {popup_closed} 个连续弹窗")
        
        return popup_closed
        
    except Exception as e:
        print(f"⚠️ 处理连续弹窗时出错: {e}")
        return 0
        
    
     
def run(playwright: Playwright, ui: UserInteractionFlow) -> None:
    """
    主运行函数 - 保持原有的登录和会话管理逻辑
    """
    # 检查脚本有效期
    # check_script_expiration()

    
    browser = playwright.chromium.launch(headless=False)
    
    # 尝试加载存储的状态
    storage_state_path = AUTH_STATE_DIR / f"{user_name}_auth_state.json"
    if storage_state_path.exists():
        context = browser.new_context(storage_state=str(storage_state_path), no_viewport=True)
    else:
        context = browser.new_context(no_viewport=True)
    
    page = context.new_page()
    
    try:
        page.goto("https://www.dianxiaomi.com/")
        # 检查是否已登录
        if page.locator("text=立即登录").count() > 0:
            raise Exception("Not logged in")
    except Exception as e:
        # 需要登录
        ui.notify(f"🔐 需要登录: {e}")
        page.get_by_role("textbox", name="请输入用户名").click()
        page.get_by_role("textbox", name="请输入用户名").fill(user_name)
        page.get_by_role("textbox", name="请输入密码").click()
        page.get_by_role("textbox", name="请输入密码").fill(password)
        ui.wait_for_confirmation("请在浏览器窗口完成登录后继续。")
        # Save authentication state
        page.context.storage_state(path=str(storage_state_path))
        ui.notify("✅ 登录成功，状态已保存")
    
    page.goto("https://www.dianxiaomi.com/web/sheinProduct/draft")
    print("✅ 已导航到采集箱列表")
    ui.wait_for_confirmation("请在店小秘采集箱页面完成筛选后继续。")
    

    closeAdModal(page)
    run_manual_mode(context, page, ui)
    
    # 清理资源
    print("\n🏁 所有操作已完成，浏览器保持打开状态供您继续操作...")
    ui.wait_for_confirmation("按回车退出程序并关闭浏览器。")
    context.close()
    browser.close()


def test_process_product_edit_enhanced(ui: UserInteractionFlow):
    """
    测试用例：直接输入edit_page的URL来测试process_product_edit_enhanced函数
    
    Usage:
        python src/main.py --test
    """
    print("\n" + "🧪"*20)
    print("🧪 产品编辑处理测试模式")
    print("🧪"*20)
    
    # 获取测试URL
    test_url = ui.prompt_test_url()
    
    if not test_url or not test_url.startswith('https://www.dianxiaomi.com'):
        print("❌ 无效的URL，请输入有效的店小秘编辑页面URL")
        return
    
    print(f"🔗 测试URL: {test_url}")
    
    # 创建浏览器实例
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        
        # 尝试加载存储的登录状态
        storage_state_path = AUTH_STATE_DIR / f"{user_name}_auth_state.json"
        
        if storage_state_path.exists():
            context = browser.new_context(storage_state=str(storage_state_path), no_viewport=True)
            print("✅ 已加载保存的登录状态")
        else:
            context = browser.new_context(no_viewport=True)
            print("⚠️ 未找到登录状态，请先登录")
        
        try:
            # 打开编辑页面
            edit_page = context.new_page()
            print("🌐 正在打开编辑页面...")
            edit_page.goto(test_url)
            edit_page.wait_for_load_state("domcontentloaded")
            print("✅ 编辑页面加载完成")
            
            # 检查是否需要登录
            if edit_page.locator("text=立即登录").count() > 0 or edit_page.locator("input[placeholder*='用户名']").count() > 0:
                ui.notify("🔐 需要登录，请在浏览器中完成登录")
                ui.wait_for_confirmation("登录完成后按回车继续。")
                
                # 重新加载页面
                edit_page.reload()
                edit_page.wait_for_load_state("domcontentloaded")
            
            # 验证页面是否正确加载
            try:
                # 检查是否存在产品编辑相关元素
                edit_page.wait_for_selector("input[name='sourceUrl'], input[name='productTitleBuyer'], .ant-form", timeout=10000)
                print("✅ 编辑页面验证通过")
            except Exception as e:
                print(f"❌ 编辑页面验证失败: {e}")
                print("请确保URL指向正确的产品编辑页面")
                browser.close()
                return
            
            # 显示测试选项
            choice = ui.prompt_test_mode()
            
            if choice == "1":
                # 完整流程测试
                print("\n🚀 开始完整流程测试...")
                edit_page.wait_for_timeout(3000)
                success = process_product_edit_enhanced(context, edit_page, manual_mode=True)
                print(f"\n{'✅ 测试成功' if success else '❌ 测试失败'}")
                
            elif choice == "2":
                # 仅填充表单测试
                print("\n📝 开始表单填充测试...")
                test_product_data = create_test_product_data()
                fill_edit_form_enhanced(edit_page, test_product_data, manual_mode=True)
                print("\n✅ 表单填充测试完成")
                
            elif choice == "3":
                # 仅解析Amazon产品
                print("\n🔍 开始Amazon产品解析测试...")
                try:
                    web_url = edit_page.locator("input[name='sourceUrl']").input_value()
                    if web_url:
                        print(f"🔗 Amazon URL: {web_url}")
                        product_data = parse_amazon_product_enhanced(context, web_url)
                        if product_data:
                            print("✅ Amazon产品解析成功")
                            print(f"📝 产品标题: {product_data.title}")
                            print(f"📊 解析属性数: {len(product_data.details)}")
                        else:
                            print("❌ Amazon产品解析失败")
                    else:
                        print("❌ 未找到Amazon URL")
                except Exception as e:
                    print(f"❌ 解析测试失败: {e}")
                    
            elif choice == "4":
                # 仅规格选择测试
                print("\n🎯 开始规格选择测试...")
                test_specs = {
                    'Specifications Summary': 'Color: White | Size: 1 Pack'
                }
                handle_dynamic_specifications(edit_page, test_specs)
                print("\n✅ 规格选择测试完成")
                
            else:
                print("❌ 无效选择")
            
            # 保持页面打开供检查
            ui.pause_for_review("🔍 测试完成，请检查页面结果。")
            
        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            browser.close()


def create_test_product_data():
    """
    创建用于测试的模拟产品数据
    """
    from product_data import ProductData
    
    test_data = ProductData()
    test_data.title = "Test Product - Bamboo Storage Organizer"
    test_data.asin = "B0TEST123"
    test_data.price = 29.99
    test_data.delivery_price = 0.0
    test_data.weight_value = "2.5"
    
    # 添加详细信息
    test_data.add_detail('ASIN', 'B0TEST123')
    test_data.add_detail('Title', 'Test Product - Bamboo Storage Organizer')
    test_data.add_detail('Price', '29.99')
    test_data.add_detail('Delivery Price', '0.0')
    test_data.add_detail('Item Weight', '2.5 pounds')
    test_data.add_detail('Material', 'Bamboo')
    test_data.add_detail('Color', 'Natural')
    test_data.add_detail('Brand', 'TestBrand')
    test_data.add_detail('Selected Color', 'White')
    test_data.add_detail('Selected Package Quantity', '1 Pack')
    test_data.add_detail('Available Colors', 'White, Black, Brown')
    test_data.add_detail('Available Package Quantities', '1 Pack, 2 Pack')
    test_data.add_detail('Specifications Summary', 'Color: White | Size: 1 Pack')
    test_data.add_detail('Key Features', 
        'Made from sustainable bamboo | '
        'Multiple compartments for organization | '
        'Easy to clean and maintain | '
        'Perfect for kitchen, bathroom, or office use')
    
    test_data.parse_success = True
    
    return test_data


def main():
    """程序入口点"""
    import sys

    ensure_client_authorized()
    
    global run_model
    ui = UserInteractionFlow()
    
    # 检查是否是测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_model = 'test'
        test_process_product_edit_enhanced(ui)
        return
    
    ui.display_welcome_screen()
    while True:
        action = ui.prompt_main_action()
        if action == "start":
            run_model = "default"
            ui.notify("\n🚀 准备启动采集箱处理流程...")
            try:
                with sync_playwright() as playwright:
                    run(playwright, ui)
            except Exception as exc:
                ui.notify(f"❌ 运行过程中出现异常: {exc}")
            if not ui.prompt_return_to_menu():
                break
            ui.display_welcome_screen()
        elif action == "test":
            run_model = "test"
            test_process_product_edit_enhanced(ui)
            run_model = "default"
            if not ui.prompt_return_to_menu():
                break
            ui.display_welcome_screen()
        else:  # exit
            break
    
    ui.say_goodbye()


if __name__ == "__main__":
    main()
