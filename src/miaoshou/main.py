#!/usr/bin/env python3
"""
妙手ERP订单收件人信息采集器

功能：
1. 自动登录妙手ERP系统
2. 访问订单打包页面
3. 采集订单收件人信息（地区、姓名、电话、邮编）
4. 导出数据为CSV文件

设计原则：
- 基于Playwright实现自动化
- 遵循readme中的工作流程
- 健壮的错误处理
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# 添加父目录到Python路径，以便导入项目模块
BASE_DIR = Path(__file__).resolve().parent
PROJECT_SRC = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_SRC))

from playwright_env import configure_playwright_browsers_path


class MiaoshouERPCollector:
    """妙手ERP订单收件人信息采集器"""
    
    def __init__(self, headless: bool = False, debug: bool = False):
        """
        初始化采集器
        
        Args:
            headless: 是否无头模式运行
            debug: 是否开启调试模式
        """
        self.headless = headless
        self.debug = debug
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.recipient_data: List[Dict[str, str]] = []  # 存储已导出的数据（历史记录）
        self.latest_api_data: Optional[List] = None  # 临时变量，存储最近一次API返回的packageList
        self.playwright = None
        self.api_listener_active = False  # API监听器是否激活
        
        # 配置
        self.erp_url = "https://erp.91miaoshou.com/order/package/index?appPackageTab=waitProcess"
        self.login_url = "https://erp.91miaoshou.com/login"  # 登录页面URL
        self.timeout_short = 5000
        self.timeout_medium = 15000
        self.timeout_long = 30000
        
        # 登录状态保存路径
        self.auth_state_dir = BASE_DIR / "auth_states"
        self.auth_state_file = self.auth_state_dir / "miaoshou_auth_state.json"
        
    def setup_browser(self) -> None:
        """配置并启动浏览器，尝试恢复登录状态"""
        print("🚀 启动浏览器...")
        
        # 配置Playwright浏览器路径
        configure_playwright_browsers_path()
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=100 if self.debug else 0,
            args=[
                '--disable-blink-features=AutomationControlled',  # 隐藏自动化标识
                '--start-maximized',  # 启动时窗口最大化
            ]
        )
        
        # 尝试从文件恢复登录状态
        if self.auth_state_file.exists():
            try:
                print("🔑 发现已存登录状态，正在恢复...")
                self.context = self.browser.new_context(
                    storage_state=str(self.auth_state_file),
                    no_viewport=True,  # 使用浏览器窗口大小，内容自适应
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                print("✅ 登录状态恢复成功")
            except Exception as e:
                print(f"⚠️ 恢复登录状态失败: {e}")
                print("📝 将创建新的浏览器上下文")
                self.context = self.browser.new_context(
                    no_viewport=True,  # 使用浏览器窗口大小，内容自适应
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
        else:
            print("🆕 未找到保存的登录状态，将创建新上下文")
            self.context = self.browser.new_context(
                no_viewport=True,  # 使用浏览器窗口大小，内容自适应
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
        
        # 创建页面并自动打开订单页面
        self.page = self.context.new_page()
        
        # 启动API实时监听器
        self.start_api_listener()
        
        # 自动打开订单页面（优化加载策略）
        try:
            print(f"🌐 正在打开订单页面: {self.erp_url}")
            # 使用 domcontentloaded 而不是 load，更快
            self.page.goto(self.erp_url, wait_until="domcontentloaded", timeout=60000)
            print("✅ 订单页面打开成功")
            # 不等待 networkidle，让页面在后台继续加载
        except Exception as e:
            print(f"⚠️ 打开订单页面失败: {e}")
            print("📌 页面可能仍在加载中，程序将继续运行")
            print("💡 如果需要登录，请在浏览器中手动登录")
        
        print("✅ 浏览器启动成功")
    
    def check_login_status(self) -> bool:
        """
        检查是否已登录（增强版，多重检测机制）
        
        Returns:
            是否已登录
        """
        if not self.page:
            return False
            
        try:
            # 等待页面稳定
            self.page.wait_for_load_state("networkidle", timeout=10000)
            
            current_url = self.page.url
            if self.debug:
                print(f"   当前URL: {current_url}")
            
            # 检查1: URL中是否包含login（未登录）
            if 'login' in current_url.lower():
                if self.debug:
                    print("   ❌ 检测到登录页面URL")
                return False
            
            # 检查2: 尝试多个可能的已登录标志元素（增加等待时间）
            login_indicators = [
                ".package-virtual-table__row",  # 订单行（更准确）
                ".package-virtual-table__body",  # 订单表格主体
                ".table-content-container",  # 表格容器
                ".user-info",  # 用户信息
                ".user-avatar",  # 用户头像
                "[class*='user']",  # 包含user的类名
                "[class*='header']",  # 页面头部
            ]
            
            for selector in login_indicators:
                try:
                    element = self.page.locator(selector).first
                    # 增加等待时间到10秒
                    if element.count() > 0:
                        element.wait_for(state="visible", timeout=10000)
                        if self.debug:
                            print(f"   ✅ 检测到登录元素: {selector}")
                        return True
                except Exception as e:
                    if self.debug:
                        print(f"   ⏭️  元素 {selector} 未找到或不可见")
                    continue
            
            # 检查3: 页面是否有登录表单（如果有则说明未登录）
            login_form_selectors = [
                "input[type='password']",
                "input[name='password']",
                "form[class*='login']",
                "button[type='submit']:has-text('登录')",
                "button:has-text('Login')",
            ]
            
            for selector in login_form_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        if self.debug:
                            print(f"   ❌ 检测到登录表单元素: {selector}")
                        return False
                except:
                    continue
            
            # 检查4: 如果URL中包含order/package等关键词，可能已登录
            if 'order' in current_url.lower() or 'package' in current_url.lower():
                if self.debug:
                    print("   ✅ URL包含订单关键词，判断为已登录")
                return True
            
            # 默认认为未登录（保守策略）
            if self.debug:
                print("   ❌ 所有检测都未通过，判断为未登录")
            return False
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ 检查登录状态异常: {e}")
            return False
    
    def wait_for_manual_login(self, timeout: int = 300) -> bool:
        """
        等待用户手动登录（改进版，更频繁的检测）
        
        Args:
            timeout: 超时时间（秒），默认5分钟
            
        Returns:
            是否登录成功
        """
        if not self.page:
            return False
            
        print("\n" + "="*60)
        print("🔑 请在浏览器中手动登录")
        print("="*60)
        print("📌 登录步骤：")
        print("   1. 在打开的浏览器窗口中输入账号密码")
        print("   2. 点击登录按钮")
        print("   3. 等待页面跳转")
        print("   4. 程序将自动检测并继续")
        print(f"⏱️  最长等待时间: {timeout}秒")
        print("="*60 + "\n")
        
        start_time = time.time()
        check_interval = 2  # 改为每2秒检查一次，更频繁
        last_url = ""
        
        while time.time() - start_time < timeout:
            # 检查是否已登录
            current_url = self.page.url if self.page else ""
            
            # 如果URL变化，说明用户在操作
            if current_url != last_url:
                if self.debug:
                    print(f"🔄 URL变化: {current_url}")
                last_url = current_url
            
            if self.check_login_status():
                print("\n✅ 检测到登录成功！")
                # 再等待2秒确保页面完全加载
                self.page.wait_for_timeout(2000)
                return True
            
            # 显示等待进度
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            # 每5秒提示一次（更频繁）
            if elapsed % 5 == 0 and elapsed > 0:
                print(f"⏳ 等待登录中... (已等待 {elapsed} 秒，剩余 {remaining} 秒)")
            
            # 等待后再检查
            self.page.wait_for_timeout(check_interval * 1000)
        
        print(f"\n❌ 登录超时（{timeout}秒）")
        print("💡 提示：如果您已经登录但程序未检测到，请尝试：")
        print("   1. 刷新页面")
        print("   2. 检查是否真的跳转到了订单页面")
        print("   3. 使用 --debug 参数查看详细日志")
        return False
    
    def save_login_state(self) -> bool:
        """
        保存当前登录状态
        
        Returns:
            是否保存成功
        """
        if not self.context:
            return False
            
        try:
            # 确保目录存在
            self.auth_state_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存状态
            self.context.storage_state(path=str(self.auth_state_file))
            print("💾 登录状态已保存")
            print(f"   文件位置: {self.auth_state_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存登录状态失败: {e}")
            return False
    
    def wait_for_user_ready(self) -> bool:
        """
        等待用户手动导航到订单页面并确认
        
        Returns:
            用户是否确认准备就绪
        """
        print("\n" + "="*60)
        print("📍 请手动导航到订单列表页面")
        print("="*60)
        print("📄 操作步骤：")
        print("   1. 在浏览器中点击进入订单打包/订单列表页面")
        print("   2. 确认订单列表已完全加载")
        print("   3. 在下方按 Enter 键继续")
        print("="*60)
        
        try:
            # 等待用户按回车
            input("\n⏸️  准备好后按 Enter 键继续...")
            
            # 等待一下确保页面稳定
            if self.page:
                self.page.wait_for_timeout(1000)
                print(f"\n✅ 用户已确认，当前URL: {self.page.url}")
            
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️ 用户取消操作")
            return False
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            return False
    
    def verify_order_page(self) -> bool:
        """
        验证当前是否在订单页面
        
        Returns:
            是否在订单页面
        """
        if not self.page:
            print("❌ 浏览器未初始化")
            return False
        
        try:
            current_url = self.page.url
            print(f"\n🔍 验证订单页面...")
            print(f"   当前URL: {current_url}")
            
            # 检查URL是否包含订单关键词
            if 'order' in current_url.lower() or 'package' in current_url.lower():
                print("✅ URL包含订单关键词")
                return True
            
            print("⚠️ URL不包含订单关键词，但将继续尝试...")
            return True  # 即使 URL不匹配也继续，因为用户已确认
            
        except Exception as e:
            print(f"❌ 验证失败: {e}")
            return False
    
    def open_order_page(self) -> bool:
        """
        打开订单页面（节点2）
        
        Returns:
            是否成功打开
        """
        if not self.page:
            print("❌ 浏览器未初始化")
            return False
            
        try:
            print(f"🌐 正在打开订单页面: {self.erp_url}")
            self.page.goto(self.erp_url, timeout=self.timeout_long)
            print("✅ 订单页面打开成功")
            return True
        except Exception as e:
            print(f"❌ 打开订单页面失败: {e}")
            return False
    
    def wait_for_page_load(self) -> None:
        """等待页面加载（节点3）"""
        if not self.page:
            return
            
        print("⏳ 等待页面加载...")
        self.page.wait_for_timeout(3000)
        print("✅ 页面加载完成")
    
    def wait_for_table_load(self) -> bool:
        """
        等待表格加载（节点4）
        
        Returns:
            表格是否成功加载
        """
        if not self.page:
            print("❌ 浏览器未初始化")
            return False
            
        print("🔍 检测订单表格...")
        
        try:
            # 尝试多个可能的表格选择器
            table_selectors = [
                ".package-virtual-table__body",  # 订单表格主体
                ".table-content-container",  # 表格容器
                ".package-virtual-table__row",  # 订单行
            ]
            
            # 尝试10次，每次等待3秒
            for i in range(10):
                for selector in table_selectors:
                    try:
                        table = self.page.locator(selector)
                        if table.count() > 0:
                            # 等待元素可见
                            table.first.wait_for(state="visible", timeout=3000)
                            print(f"✅ 订单表格检测成功（使用选择器: {selector}）")
                            return True
                    except:
                        continue
                
                if self.debug:
                    print(f"   尝试 {i+1}/10: 表格尚未加载，等待中...")
                self.page.wait_for_timeout(3000)
            
            print("❌ 超时：未找到订单表格")
            return False
            
        except Exception as e:
            print(f"❌ 表格检测失败: {e}")
            return False
    
    def scroll_to_load_data(self) -> None:
        """滚动页面加载数据（节点5-6）- 优化为逼步滚动加载虚拟表格"""
        if not self.page:
            return
            
        print("📜 滚动页面加载所有订单数据...")
        
        try:
            # 获取表格容器
            table_body = self.page.locator(".package-virtual-table__body").first
            
            if table_body.count() == 0:
                print("⚠️ 未找到表格容器")
                return
            
            # 逐步滚动加载所有数据
            last_row_count = 0
            stable_count = 0
            max_iterations = 50  # 最多滚动50次
            
            for iteration in range(max_iterations):
                # 获取当前渲染的行数
                current_row_count = self.page.locator(".package-virtual-table__row").count()
                
                if self.debug:
                    print(f"   迭代 {iteration + 1}: 当前渲染 {current_row_count} 行")
                
                # 如果行数没有变化，记录稳定次数
                if current_row_count == last_row_count:
                    stable_count += 1
                    # 连续3次行数不变，认为已加载完成
                    if stable_count >= 3:
                        print(f"✅ 滚动加载完成，共渲染 {current_row_count} 行")
                        break
                else:
                    stable_count = 0
                    last_row_count = current_row_count
                
                # 滚动到最后一个可见的订单行
                try:
                    last_visible_row = self.page.locator(".package-virtual-table__row").last
                    last_visible_row.scroll_into_view_if_needed(timeout=2000)
                except:
                    # 如果滚动失败，尝试直接滚动容器
                    self.page.evaluate("""
                        () => {
                            const tableBody = document.querySelector('.package-virtual-table__body');
                            if (tableBody) {
                                tableBody.scrollTop = tableBody.scrollHeight;
                            }
                        }
                    """)
                
                # 等待虚拟滚动渲染
                self.page.wait_for_timeout(500)
            
            # 最终滚动到顶部，确保所有数据都被加载
            self.page.evaluate("""
                () => {
                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });
                }
            """)
            self.page.wait_for_timeout(500)
            
            # 再次滚动到底部，确保所有数据都在DOM中
            self.page.evaluate("""
                () => {
                    const tableBody = document.querySelector('.package-virtual-table__body');
                    if (tableBody) {
                        tableBody.scrollTop = tableBody.scrollHeight;
                    }
                }
            """)
            self.page.wait_for_timeout(1000)
            
            final_count = self.page.locator(".package-virtual-table__row").count()
            print(f"✅ 滚动加载完成，最终渲染 {final_count} 行")
            
        except Exception as e:
            print(f"⚠️ 滚动加载时出现警告: {e}")
    
    def get_order_rows(self) -> int:
        """
        获取所有订单行（节点7）
        
        Returns:
            订单行数量
        """
        if not self.page:
            print("❌ 浏览器未初始化")
            return 0
            
        print("📊 获取订单行元素...")
        
        try:
            # 使用正确的订单行选择器
            order_rows = self.page.locator(".package-virtual-table__row")
            count = order_rows.count()
            print(f"✅ 检测到 {count} 个订单")
            return count
            
        except Exception as e:
            print(f"❌ 获取订单行失败: {e}")
            return 0
    
    def extract_recipient_info(self, row_index: int) -> Optional[Dict[str, str]]:
        """
        提取单个订单的收件人信息（节点9-12）
        
        Args:
            row_index: 订单行索引（从0开始）
            
        Returns:
            收件人信息字典，失败返回None
        """
        if not self.page:
            return None
            
        try:
            # 获取当前订单行（使用正确的选择器）
            order_row = self.page.locator(".package-virtual-table__row").nth(row_index)
            
            # 根据实际HTML结构提取收件人信息
            # 收件人信息在 class="package-virtual-table__row-cell" style="width: 175px" 的单元格中
            recipient_cell_selector = ".package-virtual-table__row-cell[style*='width: 175px']"
            
            # 初始化所有字段
            recipient_data = {
                '收件地区': '',
                '收件人姓名': '',
                '联系电话': '',
                '省州/邮编': '',
                '买家留言': '',
                '完整信息': ''  # 保存原始完整信息
            }
            
            try:
                # 尝试获取收件人单元格
                recipient_cell = order_row.locator(recipient_cell_selector)
                if recipient_cell.count() > 0:
                    # 等待元素可见
                    recipient_cell.first.wait_for(state="visible", timeout=5000)
                    
                    # 获取整个单元格的文本内容
                    full_text = recipient_cell.inner_text().strip()
                    recipient_data['完整信息'] = full_text
                    
                    # 按行分割并按“冒号”解析标签-值（兼容冒号独立成行的情况）
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    
                    def normalize_label(label: str) -> Optional[str]:
                        l = label.replace(' ', '').replace('：', ':').strip()
                        if l in ('收件地区', '收件地区:'): return '收件地区'
                        if l in ('姓名','姓名:','姓名','姓名:','姓名:','姓名:','姓名：','姓名：','姓名:','姓名:','姓名','姓 名','姓 名:'): return '收件人姓名'
                        if l in ('联系电话','联系电话:','联系电话：','联系方式','联系方式:','联系方式：'): return '联系电话'
                        if l in ('省州/邮编','省州/邮编:','省州/邮编：','省州邮编','省州邮编:','省州邮编：'): return '省州/邮编'
                        if l in ('买家留言','买家留言:','买家留言：'): return '买家留言'
                        return None
                    
                    def is_colon_line(s: str) -> bool:
                        return s in (':','：')
                    
                    def is_label_line(s: str) -> bool:
                        return normalize_label(s) is not None
                    
                    i = 0
                    n = len(lines)
                    current_key: Optional[str] = None
                    
                    while i < n:
                        line = lines[i]
                        # 跳过纯冒号行
                        if is_colon_line(line):
                            i += 1
                            continue
                        
                        key = normalize_label(line)
                        if key:
                            current_key = key
                            i += 1
                            # 跳过可能紧随其后的冒号行
                            while i < n and is_colon_line(lines[i]):
                                i += 1
                            
                            # 聚合值直到遇到下一个标签
                            value_lines: list[str] = []
                            while i < n and not is_label_line(lines[i]):
                                if not is_colon_line(lines[i]) and lines[i] != '编辑':
                                    value_lines.append(lines[i])
                                i += 1
                            value = '\n'.join(value_lines).strip()
                            if value:
                                if recipient_data[current_key]:
                                    recipient_data[current_key] += '\n' + value
                                else:
                                    recipient_data[current_key] = value
                        else:
                            # 非标签行，若存在当前key则作为续行
                            if current_key and line != '编辑' and not is_colon_line(line):
                                if recipient_data[current_key]:
                                    recipient_data[current_key] += '\n' + line
                                else:
                                    recipient_data[current_key] = line
                            i += 1
                    
                    if self.debug:
                        print(f"\n   订单 {row_index + 1} 收件人信息:")
                        print(f"   完整内容: {full_text}")
                        print(f"   解析结果:")
                        for key, value in recipient_data.items():
                            if value and key != '完整信息':
                                print(f"     {key}: {value}")
                else:
                    if self.debug:
                        print(f"   ⚠️ 订单 {row_index + 1} 未找到收件人单元格")
                        
            except Exception as e:
                if self.debug:
                    print(f"   ⚠️ 解析收件人信息失败: {e}")
            
            return recipient_data
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ 提取第 {row_index + 1} 个订单信息失败: {e}")
            return None
    
    def start_api_listener(self) -> None:
        """启动API监听器，实时捕获searchOrderPackageList接口数据"""
        if not self.page or self.api_listener_active:
            return
        
        def handle_response(response):
            """HTTP 响应处理器 - 实时捕获API数据"""
            try:
                url = response.url
                
                # 检查是否是 searchOrderPackageList 接口
                if 'searchOrderPackageList' in url:
                    if response.status == 200:
                        try:
                            json_data = response.json()
                            
                            if json_data:
                                # 根据记忆，API响应直接在根级别，没有data包装层
                                if 'packageList' in json_data:
                                    package_list = json_data['packageList']
                                    # 保存到临时变量（永远保存最新的）
                                    self.latest_api_data = package_list
                                    print(f"\n📡 [实时监听] 捕获到 searchOrderPackageList 数据: {len(package_list)} 条")
                                    if self.debug:
                                        print(f"   [DEBUG] API URL: {url}")
                                        print(f"   [DEBUG] 响应键: {list(json_data.keys())}")
                                
                        except Exception as e:
                            if self.debug:
                                print(f"   [DEBUG] 解析API响应失败: {e}")
            except Exception as e:
                if self.debug:
                    print(f"   [DEBUG] 处理响应失败: {e}")
        
        # 注册API监听器
        self.page.on("response", handle_response)
        self.api_listener_active = True
        print("📡 API实时监听器已启动，将自动捕获 searchOrderPackageList 接口返回的数据")
    
    def stop_api_listener(self) -> None:
        """停止API监听器"""
        if self.page and self.api_listener_active:
            try:
                # Playwright不支持移除所有监听器，只能标记为不活跃
                self.api_listener_active = False
                print("🔌 API监听器已停止")
            except:
                pass
    
    def export_latest_data_to_excel(self, output_dir: Optional[Union[str, Path]] = None) -> Optional[str]:
        """
        导出最新捕获的API数据到Excel文件
        
        Args:
            output_dir: 输出目录路径，为None时使用默认路径
        
        Returns:
            导出的文件路径，失败返回None
        """
        if not self.latest_api_data:
            print("⚠️ 没有可导出的数据")
            print("💡 提示: 程序正在后台监听 searchOrderPackageList 接口")
            print("   请在浏览器页面上进行任何触发搜索的操作（点击搜索按钮、切换分页、筛选等）")
            print("   只要后台发起 searchOrderPackageList 请求，数据就会被自动捕获")
            return None
        
        print(f"\n📤 开始导出最新捕获的数据...")
        print(f"📊 数据量: {len(self.latest_api_data)} 条")
        
        try:
            # 延迟导入xlsxwriter，避免打包时的依赖问题
            import xlsxwriter
            
            # 确定输出目录
            output_path: Path
            if output_dir is None:
                # 打包后：获取exe所在目录；开发时：使用output目录
                if getattr(sys, 'frozen', False):
                    # 打包后，使用exe所在目录
                    exe_dir = Path(sys.executable).parent
                    output_path = exe_dir
                else:
                    # 开发模式，使用源码目录下的output
                    output_path = BASE_DIR / "output"
            else:
                output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
            
            # 确保输出目录存在
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"妙手ERP_收件人信息_{timestamp}.xlsx"
            output_file = output_path / filename
            
            # 创建Excel工作簿
            workbook = xlsxwriter.Workbook(str(output_file))
            worksheet = workbook.add_worksheet('收件人信息')
            
            # 定义格式
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'valign': 'top',
                'text_wrap': True
            })
            
            # 写入表头
            headers = ['收件地区', '收件人姓名', '联系电话', '省州/邮编', '买家留言', '完整信息']
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
            
            # 解析并写入数据
            row_num = 1
            for package in self.latest_api_data:
                try:
                    # 从 consigneeInfo 获取收件人信息
                    consignee_info = package.get('consigneeInfo', {})
                    
                    if not consignee_info:
                        continue
                    
                    # 从 orderInfo 获取买家留言
                    order_info = package.get('orderInfo', {})
                    buyer_message = order_info.get('buyerMessage', '') or ''
                    
                    # 提取字段
                    country_name = consignee_info.get('countryName', '')
                    name = consignee_info.get('name', '')
                    phone = consignee_info.get('phone', '') or consignee_info.get('phone1', '')
                    state = consignee_info.get('state', '')
                    zipcode = consignee_info.get('zipcode', '')
                    province_zip = f"{state} / {zipcode}" if state or zipcode else ''
                    
                    # 构建完整信息
                    full_info_parts = []
                    if country_name:
                        full_info_parts.append(f"国家: {country_name}")
                    if name:
                        full_info_parts.append(f"姓名: {name}")
                    if phone:
                        full_info_parts.append(f"电话: {phone}")
                    if state:
                        full_info_parts.append(f"省/州: {state}")
                    if consignee_info.get('city'):
                        full_info_parts.append(f"城市: {consignee_info.get('city')}")
                    if consignee_info.get('district'):
                        full_info_parts.append(f"区: {consignee_info.get('district')}")
                    if consignee_info.get('town'):
                        full_info_parts.append(f"镇: {consignee_info.get('town')}")
                    if zipcode:
                        full_info_parts.append(f"邮编: {zipcode}")
                    if consignee_info.get('address1'):
                        full_info_parts.append(f"地址1: {consignee_info.get('address1')}")
                    if consignee_info.get('address2'):
                        full_info_parts.append(f"地址2: {consignee_info.get('address2')}")
                    if consignee_info.get('fullAddress'):
                        full_info_parts.append(f"完整地址: {consignee_info.get('fullAddress')}")
                    if consignee_info.get('logisticsCompany'):
                        full_info_parts.append(f"物流公司: {consignee_info.get('logisticsCompany')}")
                    
                    full_info = '\n'.join(full_info_parts)
                    
                    # 写入行
                    worksheet.write(row_num, 0, country_name, cell_format)
                    worksheet.write(row_num, 1, name, cell_format)
                    worksheet.write(row_num, 2, phone, cell_format)
                    worksheet.write(row_num, 3, province_zip, cell_format)
                    worksheet.write(row_num, 4, buyer_message, cell_format)
                    worksheet.write(row_num, 5, full_info, cell_format)
                    
                    row_num += 1
                    
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ 解析订单数据失败: {e}")
                    continue
            
            # 自动调整列宽
            worksheet.set_column('A:A', 15)  # 收件地区
            worksheet.set_column('B:B', 20)  # 收件人姓名
            worksheet.set_column('C:C', 15)  # 联系电话
            worksheet.set_column('D:D', 30)  # 省州/邮编
            worksheet.set_column('E:E', 30)  # 买家留言
            worksheet.set_column('F:F', 50)  # 完整信息
            
            # 关闭工作簿
            workbook.close()
            
            actual_count = row_num - 1
            print(f"\n{'='*60}")
            print(f"✅ 导出成功！")
            print(f"={'='*60}")
            print(f"📊 导出数量: {actual_count} 条")
            print(f"📁 文件位置: {output_file}")
            print(f"={'='*60}\n")
            
            return str(output_file)
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def collect_all_recipients(self) -> int:
        """
        （已废弃）此方法保留但不再使用
        现在使用实时API监听+导出临时变量的方式
        
        Returns:
            成功采集的数量
        """
        print("⚠️ 此方法已废弃，请使用 'e' 导出最新捕获的数据")
        return 0
    
    def _old_collect_method(self) -> int:
        """
        旧的采集方法（已废弃，仅作备份）
        自动点击搜索按钮并监听API请求获取订单数据（节点8-13）
        
        Returns:
            成功采集的数量
        """
        print("🔍 自动点击搜索按钮并监听 API 请求...")
        
        if not self.page:
            print("❌ 浏览器未初始化")
            return 0
        
        # 存储拦截到的响应数据
        captured_data = {'packageList': None, 'captured': False}
        
        def handle_response(response):
            """HTTP 响应处理器"""
            try:
                url = response.url
                
                # 检查是否是 searchOrderPackageList 接口
                if 'searchOrderPackageList' in url:
                    print(f"   ✅ 检测到 searchOrderPackageList 接口")
                    print(f"   [INFO] 响应状态: {response.status}")
                    
                    if response.status == 200:
                        try:
                            print(f"   [INFO] 开始解析JSON...")
                            json_data = response.json()
                            print(f"   [INFO] JSON解析成功")
                            
                            if json_data:
                                print(f"   [INFO] 响应数据键: {list(json_data.keys())}")
                                
                                # 尝试从 data 字段获取（新版本API）
                                if 'data' in json_data and isinstance(json_data['data'], dict) and 'packageList' in json_data['data']:
                                    package_list = json_data['data']['packageList']
                                    print(f"   [INFO] 从 data.packageList 获取数据")
                                # 直接从根级别获取（旧版本API）
                                elif 'packageList' in json_data:
                                    package_list = json_data['packageList']
                                    print(f"   [INFO] 直接从根级别获取 packageList")
                                else:
                                    print(f"   ⚠️ 响应中没有找到 packageList 字段")
                                    return
                                
                                print(f"   [INFO] packageList类型: {type(package_list)}")
                                print(f"   [INFO] packageList长度: {len(package_list) if isinstance(package_list, list) else 'N/A'}")
                                
                                captured_data['packageList'] = package_list
                                captured_data['captured'] = True
                                print(f"   ✅ 成功拦截 API 响应，包含 {len(package_list)} 个订单")
                            else:
                                print(f"   ⚠️ json_data为空")
                                
                        except Exception as e:
                            print(f"   ❌ 解析 JSON 失败: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"   ⚠️ API 响应状态码不是200: {response.status}")
            except Exception as e:
                print(f"   ❌ 处理响应失败: {e}")
                import traceback
                traceback.print_exc()
        
        try:
            # 先注册响应监听器（在点击按钮之前）
            print("📡 注册API响应监听器...")
            self.page.on("response", handle_response)
            
            # 等待一小段时间确保监听器注册完成
            self.page.wait_for_timeout(500)
            
            # 查找搜索按钮
            search_button_selectors = [
                "button.J_queryFormSearch",
                "button[type='submit'].J_queryFormSearch",
                "button.jx-button--primary:has-text('搜索')",
                "button:has-text('搜索')",
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() > 0:
                        search_button = btn
                        print(f"   ✅ 找到搜索按钮: {selector}")
                        break
                except:
                    continue
            
            if not search_button:
                print("❌ 未找到搜索按钮，请确认页面已加载")
                return 0
            
            # 点击搜索按钮
            print("👆 正在点击搜索按钮...")
            search_button.click()
            print("   ✅ 搜索按钮已点击，等待API响应...")
            
            # 等待API响应（最多等待30秒）
            max_wait_time = 30
            check_interval = 0.5
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                if captured_data['captured']:
                    break
                self.page.wait_for_timeout(int(check_interval * 1000))
                elapsed_time += check_interval
                
                # 每5秒显示一次进度
                if int(elapsed_time) % 5 == 0 and int(elapsed_time) > 0:
                    print(f"   ⏳ 等待API响应... ({int(elapsed_time)}/{max_wait_time}秒)")
            
            if not captured_data['captured']:
                print(f"\n❌ 超时：未拦截到 searchOrderPackageList API 数据")
                print("💡 提示：")
                print("   1. 请确认页面已正确加载")
                print("   2. 请检查是否有网络问题")
                print("   3. 尝试手动点击搜索按钮看是否有响应")
                return 0
            
            # 解析数据
            print(f"\n📦 开始解析 {len(captured_data['packageList'])} 个订单数据...")
            success_count = 0
            
            for package in captured_data['packageList']:
                try:
                    # 从 consigneeInfo 获取收件人信息
                    consignee_info = package.get('consigneeInfo', {})
                    
                    if not consignee_info:
                        if self.debug:
                            print(f"   ⚠️ 订单没有 consigneeInfo 字段，跳过")
                        continue
                    
                    # 提取收件人信息
                    recipient_data = {
                        '收件地区': consignee_info.get('countryName', ''),
                        '收件人姓名': consignee_info.get('name', ''),
                        '联系电话': consignee_info.get('phone', '') or consignee_info.get('phone1', ''),
                        '省州/邮编': f"{consignee_info.get('state', '')} / {consignee_info.get('zipcode', '')}".strip(' /'),
                        '买家留言': '',  # consigneeInfo 中没有买家留言
                        '完整信息': f"""国家: {consignee_info.get('countryName', '')}
姓名: {consignee_info.get('name', '')}
电话: {consignee_info.get('phone', '') or consignee_info.get('phone1', '')}
省/州: {consignee_info.get('state', '')}
城市: {consignee_info.get('city', '')}
区/镇: {consignee_info.get('district', '')} {consignee_info.get('town', '')}
邮编: {consignee_info.get('zipcode', '')}
地址1: {consignee_info.get('address1', '')}
地址2: {consignee_info.get('address2', '')}
完整地址: {consignee_info.get('fullAddress', '')}
物流公司: {consignee_info.get('logisticsCompany', '')}"""
                    }
                    
                    self.recipient_data.append(recipient_data)
                    success_count += 1
                    
                    if self.debug:
                        print(f"\n   ✅ 订单 {success_count}:")
                        print(f"      姓名: {recipient_data['收件人姓名']}")
                        print(f"      地区: {recipient_data['收件地区']}")
                        print(f"      电话: {recipient_data['联系电话']}")
                        print(f"      省州/邮编: {recipient_data['省州/邮编']}")
                            
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ 解析订单数据失败: {e}")
                        import traceback
                        traceback.print_exc()
            
            print(f"\n✅ 采集完成，成功采集 {success_count} 个订单")
            return success_count
            
        except Exception as e:
            print(f"\n❌ 采集过程出错: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return 0
            
        finally:
            # 移除监听器
            try:
                self.page.remove_listener("response", handle_response)
                print("   🔌 已移除API监听器")
            except:
                pass
    
    def export_to_excel(self, output_dir: Optional[Union[str, Path]] = None) -> Optional[str]:
        """
        导出数据到Excel（.xlsx）文件
        """
        if not self.recipient_data:
            print("⚠️ 没有数据可以导出")
            return None
        
        print("📤 导出数据到Excel...")
        
        try:
            # 延迟导入xlsxwriter，避免打包时的依赖问题
            import xlsxwriter
            
            # 确定输出目录
            output_path: Path
            if output_dir is None:
                # 打包后：获取exe所在目录；开发时：使用output目录
                if getattr(sys, 'frozen', False):
                    # 打包后，使用exe所在目录
                    exe_dir = Path(sys.executable).parent
                    output_path = exe_dir
                else:
                    # 开发模式，使用源码目录下的output
                    output_path = BASE_DIR / "output"
            else:
                output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
            
            # 创建输出目录
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"妙手ERP_收件人信息_{timestamp}.xlsx"
            filepath = output_path / filename
            
            # 创建Excel工作簿
            workbook = xlsxwriter.Workbook(str(filepath))
            worksheet = workbook.add_worksheet("收件人信息")
            
            # 定义表头
            headers = ['收件地区', '收件人姓名', '联系电话', '省州/邮编', '买家留言', '完整信息']
            header_format = workbook.add_format({'bold': True})
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # 写入数据
            for row_index, row in enumerate(self.recipient_data, start=1):
                worksheet.write(row_index, 0, row.get('收件地区', ''))
                worksheet.write(row_index, 1, row.get('收件人姓名', ''))
                worksheet.write(row_index, 2, row.get('联系电话', ''))
                worksheet.write(row_index, 3, row.get('省州/邮编', row.get('省州邮编', '')))
                worksheet.write(row_index, 4, row.get('买家留言', ''))
                worksheet.write(row_index, 5, row.get('完整信息', ''))
            
            # 调整列宽（简单适配）
            worksheet.set_column(0, 0, 18)  # 收件地区
            worksheet.set_column(1, 1, 14)  # 收件人姓名
            worksheet.set_column(2, 2, 16)  # 联系电话
            worksheet.set_column(3, 3, 14)  # 省州/邮编
            worksheet.set_column(4, 4, 24)  # 买家留言
            worksheet.set_column(5, 5, 40)  # 完整信息
            
            workbook.close()
            
            print("✅ 数据导出成功")
            print(f"   文件路径: {filepath}")
            print(f"   数据条数: {len(self.recipient_data)}")
            
            return str(filepath)
            
        except Exception as e:
            print(f"❌ 导出Excel失败: {e}")
            return None
    
    def show_error_notification(self) -> None:
        """显示错误通知（节点15）"""
        print("\n" + "="*60)
        print("❌ 错误提示")
        print("="*60)
        print("未找到订单表格，请检查：")
        print("  1. 页面是否正确加载")
        print("  2. 是否需要登录")
        print("  3. URL是否正确")
        print("  4. 网络连接是否正常")
        print("="*60)
    
    def run(self) -> bool:
        """
        执行完整的采集流程
        
        Returns:
            是否成功完成
        """
        print("\n" + "="*60)
        print("🤖 妙手ERP订单收件人信息采集器")
        print("="*60)
        
        try:
            # 节点1: 初始化（触发器已由用户调用run()完成）
            
            # 启动浏览器（尝试恢复登录状态）
            self.setup_browser()
            
            # 节点2-3: 打开页面并等待加载（已移除，由用户手动操作）
            # if not self.open_order_page():
            #     return False
            # self.wait_for_page_load()
            
            # 检查登录状态
            print("\n🔍 检查登录状态...")
            if not self.check_login_status():
                print("⚠️ 未检测到登录状态")
                
                # 等待用户手动登录
                if not self.wait_for_manual_login(timeout=300):  # 5分钟超时
                    print("❌ 登录失败，程序退出")
                    return False
                
                # 登录成功后保存状态
                print("\n💾 保存登录状态...")
                if self.save_login_state():
                    print("✅ 登录状态已保存，下次运行将自动登录")
                else:
                    print("⚠️ 登录状态保存失败，下次需要重新登录")
            else:
                print("✅ 检测到已登录状态")
            
            # 支持多次手动触发采集
            while True:
                print("\n" + "="*60)
                print("📋 操作菜单：")
                print("  [回车] - 导出最新捕获的数据到 Excel 文件（自动清空）")
                print("  [q]   - 退出程序")
                if self.latest_api_data:
                    print(f"📊 当前捕获: {len(self.latest_api_data)} 条数据")
                else:
                    print("📊 当前捕获: 无数据")
                print("💡 提示: 程序正在后台监听 searchOrderPackageList 接口，请在页面上操作（筛选、搜索等），数据会自动捕获")
                print("="*60)
                
                # 使用非阻塞方式等待用户输入，同时保持事件循环活跃
                import sys
                import select
                import time
                
                print("请选择操作：", end='', flush=True)
                
                user_input = None
                # 在等待用户输入的同时，定期处理浏览器事件
                while user_input is None:
                    # 检查是否有输入（非阻塞）
                    if sys.platform == 'win32':
                        # Windows下使用msvcrt
                        import msvcrt
                        if msvcrt.kbhit():
                            user_input = input().strip().lower()
                    else:
                        # Unix/Linux/Mac使用select
                        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if ready:
                            user_input = sys.stdin.readline().strip().lower()
                    
                    # 处理浏览器事件，保持监听器活跃
                    if self.page and user_input is None:
                        try:
                            # 执行一个轻量级操作来触发事件循环
                            self.page.evaluate('() => true')
                        except:
                            pass
                        time.sleep(0.1)  # 避免CPU占用过高
                
                if user_input == 'q':
                    print("👋 退出程序...")
                    break
                    
                elif user_input == '' or user_input == 'e':
                    # 回车键或e键 - 导出最新捕获的API数据
                    export_path = self.export_latest_data_to_excel()
                    if export_path:
                        # 导出成功后自动清空临时数据
                        self.latest_api_data = None
                        print("🧹 已自动清空缓存数据，请继续筛选和搜索新的订单")
                    continue
                
                else:
                    # 其他输入，提示用户
                    print("⚠️ 无效的操作，请按回车导出或输入 'q' 退出")
                    continue
            
            print("\n👋 程序已退出")
            return True                
        except Exception as e:
            print(f"\n❌ 执行过程中发生错误: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
            
        finally:
            # 清理资源
            self.cleanup()
    
    def cleanup(self) -> None:
        """清理浏览器资源"""
        print("\n🧹 清理资源...")
        
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️ 清理资源时出现警告: {e}")


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='妙手ERP订单收件人信息采集器')
    parser.add_argument('--headless', action='store_true', help='无头模式运行')
    parser.add_argument('--debug', action='store_true', help='开启调试模式')
    parser.add_argument('--output', type=str, help='输出目录路径')
    
    args = parser.parse_args()
    
    # 创建采集器实例
    collector = MiaoshouERPCollector(
        headless=args.headless,
        debug=args.debug
    )
    
    # 执行采集
    success = collector.run()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
