#!/usr/bin/env python3
"""
统一自动化引擎

职责：
1. 协调Amazon数据抓取和网站表单填充
2. 管理网站策略的注册和调度
3. 提供统一的自动化接口

设计原则：
- Single orchestrator for all automation workflows
- Strategy pattern for website-specific handling
- Clean separation between data extraction and form filling
"""

from typing import Dict, Type, Optional, Any
from playwright.sync_api import BrowserContext, Page

from core.amazon_product_parser import AmazonProductParser
from core.product_data import ProductData
from core.system_config import SYSTEM_CONFIG
from websites.base.website_strategy import WebsiteStrategy


class AutomationEngine:
    """
    统一自动化引擎 - 协调Amazon抓取和多网站填充
    
    这是多网站架构的核心协调器，实现了Strategy Pattern
    """
    
    def __init__(self):
        # 注册的网站策略
        self.strategies: Dict[str, WebsiteStrategy] = {}
        
        # 自动化统计
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'amazon_parse_failures': 0,
            'authentication_failures': 0,
            'form_fill_failures': 0
        }
    
    def register_strategy(self, strategy: WebsiteStrategy) -> None:
        """
        注册网站策略
        
        Args:
            strategy: 网站策略实例
        """
        site_name = strategy.get_site_name()
        self.strategies[site_name] = strategy
        print(f"📝 注册网站策略: {site_name}")
    
    def list_available_sites(self) -> list[str]:
        """获取所有可用的网站列表"""
        return list(self.strategies.keys())
    
    def execute_automation(self, 
                          amazon_url: str, 
                          target_site: str,
                          context: BrowserContext, 
                          page: Page) -> Dict[str, Any]:
        """
        执行完整的自动化流程
        
        Args:
            amazon_url: Amazon产品页面URL
            target_site: 目标网站名称
            context: 浏览器上下文
            page: 主页面实例
            
        Returns:
            自动化执行结果
            
        Raises:
            ValueError: 不支持的网站
            Exception: 执行过程中的各种错误
        """
        print(f"🚀 开始多网站自动化流程: {amazon_url} -> {target_site}")
        
        self.stats['total_runs'] += 1
        
        try:
            # 1. 验证目标网站
            if target_site not in self.strategies:
                available_sites = ", ".join(self.list_available_sites())
                raise ValueError(f"不支持的网站: {target_site}。可用网站: {available_sites}")
            
            strategy = self.strategies[target_site]
            
            # 2. Amazon数据抓取（通用）
            print("📊 步骤1: Amazon产品数据抓取...")
            product_data = self._extract_amazon_data(amazon_url, context)
            
            if not product_data.has_valid_data():
                self.stats['amazon_parse_failures'] += 1
                raise Exception("Amazon数据抓取失败，无有效产品数据")
            
            print(f"✅ Amazon数据抓取成功: {len(product_data.details)}个字段")
            
            # 3. 验证网站环境
            print(f"🔍 步骤2: 验证{target_site}网站环境...")
            if not strategy.validate_environment(page):
                raise Exception(f"当前页面不在{target_site}环境中")
            
            print(f"✅ {target_site}环境验证通过")
            
            # 4. 网站认证
            print(f"🔐 步骤3: {target_site}认证...")
            if not strategy.authenticate(page, context):
                self.stats['authentication_failures'] += 1
                raise Exception(f"{target_site}认证失败")
            
            print(f"✅ {target_site}认证成功")
            
            # 5. 导航到表单页面
            print(f"🧭 步骤4: 导航到{target_site}表单页面...")
            form_handle = strategy.navigate_to_form(page)
            
            if not form_handle:
                raise Exception(f"无法导航到{target_site}表单页面")
            
            print(f"✅ 成功导航到{target_site}表单页面")
            
            # 6. 表单填充
            print(f"📝 步骤5: 填充{target_site}表单...")
            fill_result = strategy.fill_form(form_handle, product_data)
            
            if not fill_result or fill_result.get('successful_fills', 0) == 0:
                self.stats['form_fill_failures'] += 1
                raise Exception(f"{target_site}表单填充失败")
            
            print(f"✅ {target_site}表单填充完成")
            
            # 成功统计
            self.stats['successful_runs'] += 1
            
            return {
                'success': True,
                'target_site': target_site,
                'product_title': product_data.title[:60] + '...' if len(product_data.title) > 60 else product_data.title,
                'amazon_fields_extracted': len(product_data.details),
                'form_fill_result': fill_result,
                'execution_stats': self._get_execution_stats()
            }
            
        except Exception as e:
            self.stats['failed_runs'] += 1
            error_msg = str(e)
            
            print(f"❌ 自动化执行失败: {error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'target_site': target_site,
                'execution_stats': self._get_execution_stats()
            }
    
    def _extract_amazon_data(self, amazon_url: str, context: BrowserContext) -> ProductData:
        """
        通用Amazon数据抓取
        
        Args:
            amazon_url: Amazon产品页面URL
            context: 浏览器上下文
            
        Returns:
            解析的产品数据
        """
        amazon_page = context.new_page()
        
        try:
            # 构建带参数的URL
            full_url = amazon_url + SYSTEM_CONFIG.get_amazon_url_params()
            print(f"🌐 导航到Amazon页面: {full_url}")
            
            amazon_page.goto(full_url, timeout=SYSTEM_CONFIG.get_timeout('navigation'))
            
            # 等待页面加载
            amazon_page.wait_for_load_state("networkidle", timeout=SYSTEM_CONFIG.get_timeout('long'))
            
            # 检查配送地址（可选）
            try:
                deliver_to = amazon_page.locator("#glow-ingress-line1").inner_text(timeout=5000)
                print(f"📍 Amazon配送地址: {deliver_to}")
            except:
                print("⚠️ 无法获取Amazon配送地址信息")
            
            # 使用统一解析器解析产品数据
            parser = AmazonProductParser(amazon_page)
            product_data = parser.parse_product()
            
            return product_data
            
        finally:
            # 确保关闭Amazon页面
            amazon_page.close()
            print("✅ Amazon页面已关闭")
    
    def _get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        total = self.stats['total_runs']
        success_rate = (self.stats['successful_runs'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'success_rate': round(success_rate, 1)
        }
    
    def get_strategy(self, site_name: str) -> Optional[WebsiteStrategy]:
        """获取指定网站的策略"""
        return self.strategies.get(site_name)
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'amazon_parse_failures': 0,
            'authentication_failures': 0,
            'form_fill_failures': 0
        }
    
    def print_summary(self) -> None:
        """打印执行摘要"""
        stats = self._get_execution_stats()
        
        print("\n" + "="*50)
        print("📊 多网站自动化引擎执行摘要")
        print("="*50)
        print(f"🎯 支持网站数量: {len(self.strategies)}")
        print(f"📈 总执行次数: {stats['total_runs']}")
        print(f"✅ 成功次数: {stats['successful_runs']}")
        print(f"❌ 失败次数: {stats['failed_runs']}")
        print(f"📊 成功率: {stats['success_rate']}%")
        
        if stats['total_runs'] > 0:
            print("\n失败原因统计:")
            print(f"  🔍 Amazon解析失败: {stats['amazon_parse_failures']}")
            print(f"  🔐 认证失败: {stats['authentication_failures']}")
            print(f"  📝 表单填充失败: {stats['form_fill_failures']}")
        
        print("\n支持的网站:")
        for i, site_name in enumerate(self.list_available_sites(), 1):
            print(f"  {i}. {site_name}")
        
        print("="*50)


# 全局自动化引擎实例
AUTOMATION_ENGINE = AutomationEngine()
