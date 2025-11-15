#!/usr/bin/env python3
"""
网站策略抽象基类

职责：
1. 定义所有网站策略必须实现的接口
2. 提供通用的辅助方法
3. 确保策略模式的统一性

设计原则：
- Abstract Base Class for all website strategies
- Uniform interface across different websites
- Single Responsibility for each strategy
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from playwright.sync_api import Page, BrowserContext

# 避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.product_data import ProductData


class WebsiteStrategy(ABC):
    """
    网站策略抽象基类
    
    每个网站都需要实现这个接口，确保统一的行为规范
    """
    
    def __init__(self):
        self.name = self.get_site_name()
        self.authenticated = False
        self.form_handle = None
    
    @abstractmethod
    def get_site_name(self) -> str:
        """返回网站名称标识符"""
        pass
    
    @abstractmethod
    def validate_environment(self, page: Page) -> bool:
        """
        验证当前页面是否在正确的网站环境
        
        Args:
            page: 当前页面实例
            
        Returns:
            bool: 是否在正确的网站环境
        """
        pass
    
    @abstractmethod
    def authenticate(self, page: Page, context: BrowserContext) -> bool:
        """
        处理网站登录认证
        
        Args:
            page: 页面实例
            context: 浏览器上下文
            
        Returns:
            bool: 认证是否成功
        """
        pass
    
    @abstractmethod
    def navigate_to_form(self, page: Page) -> Any:
        """
        导航到目标表单页面并返回表单句柄
        
        Args:
            page: 页面实例
            
        Returns:
            表单句柄（具体类型由子类决定）
        """
        pass
    
    @abstractmethod
    def fill_form(self, form_handle: Any, product_data: "ProductData") -> Dict[str, Any]:
        """
        填充表单并返回结果统计
        
        Args:
            form_handle: 表单句柄
            product_data: 产品数据
            
        Returns:
            填充结果统计字典
        """
        pass
    
    @abstractmethod
    def get_field_mappings(self) -> Dict[str, str]:
        """
        返回网站特定的字段映射配置
        
        Returns:
            字段映射字典
        """
        pass
    
    # 通用辅助方法
    
    def wait_for_page_load(self, page: Page, timeout: int = 30000) -> None:
        """等待页面加载完成"""
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            print(f"⚠️ 页面加载等待超时: {e}")
    
    def safe_click(self, page: Page, selector: str, timeout: int = 5000) -> bool:
        """安全点击元素"""
        try:
            element = page.locator(selector)
            element.wait_for(state="visible", timeout=timeout)
            element.click()
            return True
        except Exception as e:
            print(f"⚠️ 点击元素失败 {selector}: {e}")
            return False
    
    def safe_fill(self, page: Page, selector: str, value: str, timeout: int = 5000) -> bool:
        """安全填充输入框"""
        try:
            element = page.locator(selector)
            element.wait_for(state="visible", timeout=timeout)
            element.fill(str(value))
            return True
        except Exception as e:
            print(f"⚠️ 填充输入框失败 {selector}: {e}")
            return False
    
    def get_credentials(self) -> Dict[str, str]:
        """获取认证凭据（从环境变量）"""
        import os
        username_env = f"{self.get_site_name().upper()}_USERNAME"
        password_env = f"{self.get_site_name().upper()}_PASSWORD"
        
        return {
            'username': os.getenv(username_env, ''),
            'password': os.getenv(password_env, '')
        }
    
    def log_action(self, action: str, success: bool = True, details: str = "") -> None:
        """记录操作日志"""
        status = "✅" if success else "❌"
        site_name = self.get_site_name()
        message = f"{status} [{site_name}] {action}"
        if details:
            message += f": {details}"
        print(message)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(site='{self.get_site_name()}')"
