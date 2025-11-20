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
        self.recipient_data: List[Dict[str, str]] = []
        self.playwright = None
        
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
            slow_mo=100 if self.debug else 0
        )
        
        # 尝试从文件恢复登录状态
        if self.auth_state_file.exists():
            try:
                print("🔑 发现乊存登录状态，正在恢复...")
                self.context = self.browser.new_context(
                    storage_state=str(self.auth_state_file),
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                print("✅ 登录状态恢复成功")
            except Exception as e:
                print(f"⚠️ 恢复登录状态失败: {e}")
                print("📝 将创建新的浏览器上下文")
                self.context = self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
        else:
            print("🆕 未找到保存的登录状态，将创建新上下文")
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
        
        # 创建页面并自动打开订单页面
        self.page = self.context.new_page()
        
        # 自动打开订单页面
        try:
            print(f"🌐 正在打开订单页面: {self.erp_url}")
            self.page.goto(self.erp_url, timeout=self.timeout_long)
            self.page.wait_for_load_state("networkidle", timeout=self.timeout_long)
            print("✅ 订单页面打开成功")
        except Exception as e:
            print(f"⚠️ 打开订单页面失败: {e}")
            print("📌 请手动导航到订单页面")
        
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
        """滚动页面加载数据（节点5-6）"""
        if not self.page:
            return
            
        print("📜 滚动页面加载所有订单数据...")
        
        try:
            # 平滑滚动到页面底部
            self.page.evaluate("""
                () => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollTo({
                        top: scrollHeight,
                        behavior: 'smooth'
                    });
                }
            """)
            
            # 等待数据加载
            self.page.wait_for_timeout(2000)
            print("✅ 滚动加载完成")
            
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
    
    def collect_all_recipients(self) -> int:
        """
        循环采集所有订单的收件人信息（节点8-13）
        
        Returns:
            成功采集的数量
        """
        print("🔄 开始循环采集订单收件人信息...")
        
        # 获取订单总数
        total_orders = self.get_order_rows()
        
        if total_orders == 0:
            print("⚠️ 没有检测到订单")
            return 0
        
        # 限制最大循环次数
        max_loop = min(total_orders, 999)
        success_count = 0
        
        # 循环遍历每个订单
        for i in range(max_loop):
            if self.debug:
                print(f"\n📝 处理订单 {i + 1}/{max_loop}...")
            
            # 提取收件人信息
            recipient_info = self.extract_recipient_info(i)
            
            if recipient_info:
                # 节点13: 保存数据
                self.recipient_data.append(recipient_info)
                success_count += 1
                
                if self.debug:
                    print(f"   ✅ 姓名: {recipient_info.get('收件人姓名','')}")
                    print(f"      地区: {recipient_info.get('收件地区','')}")
                    print(f"      电话: {recipient_info.get('联系电话','')}")
                    print(f"      省州/邮编: {recipient_info.get('省州/邮编', recipient_info.get('省州邮编',''))}")
                    if recipient_info.get('买家留言'):
                        print(f"      买家留言: {recipient_info['买家留言']}")
            else:
                if self.debug:
                    print(f"   ⚠️ 跳过第 {i + 1} 个订单（数据提取失败）")
            
            # 小延迟，避免过快操作
            if i < max_loop - 1 and self.page:
                self.page.wait_for_timeout(100)
        
        print(f"\n✅ 采集完成，成功采集 {success_count}/{max_loop} 个订单")
        return success_count
    
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
            total_collected = 0
            while True:
                print("\n📋 当前页面筛选条件就绪后：")
                user_input = input("按 Enter 开始采集；输入 q 导出并结束；输入 n 清空已采集数据：").strip().lower()
                
                if user_input == 'q':
                    break
                if user_input == 'n':
                    self.recipient_data = []
                    total_collected = 0
                    print("🧹 已清空已采集数据")
                    continue
                
                # 验证是否在订单页面
                if not self.verify_order_page():
                    print("⚠️ 页面验证失败，但将继续尝试...")
                
                # 节点4: 等待表格加载
                if not self.wait_for_table_load():
                    # 节点15: 显示错误提示
                    self.show_error_notification()
                    continue  # 本轮跳过，等待用户调整后再试
                
                # 节点5-6: 滚动加载数据
                self.scroll_to_load_data()
                
                # 节点7-13: 采集所有订单数据
                collected_count = self.collect_all_recipients()
                total_collected += collected_count
                
                print(f"\n📊 本次采集: {collected_count} 条，累计: {total_collected} 条")
                # 循环继续，等待用户下一次手动触发
            
            # 导出累计数据（Excel）
            export_path = self.export_to_excel()
            
            if export_path:
                print("\n" + "="*60)
                print("✅ 采集任务完成！")
                print("="*60)
                print(f"📊 累计采集数量: {len(self.recipient_data)}")
                print(f"📁 文件位置: {export_path}")
                print("="*60)
                return True
            else:
                return False                
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
