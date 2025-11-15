#!/usr/bin/env python3
"""
统一配置系统 - 管理所有系统设置和环境变量

设计原则：
1. Environment-aware - 根据环境自动调整配置
2. Single Configuration Source - 所有设置集中管理
3. Backward Compatible - 兼容原有配置逻辑

作者: Linus Torvalds (风格)
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class SystemConfig:
    """
    系统配置类 - 统一管理所有配置项
    
    Good Taste: 简单的配置结构，易于扩展和维护
    """
    
    # 环境设置
    environment: str = "development"  # development, testing, production
    debug: bool = True
    
    # 浏览器设置
    headless: bool = False
    no_viewport: bool = True
    browser_timeout: int = 60000
    
    # 表单填充设置
    form_timeout: int = 1000
    wait_time: int = 200
    
    # 脚本控制设置
    expiration_hours: int = 2
    
    # 登录设置（环境变量优先）
    default_username: str = "16636131310"
    default_password: str = "2042612a"
    
    # Amazon解析设置
    amazon_timeout: int = 20000
    amazon_selectors: Dict[str, str] = None
    
    def __post_init__(self):
        """初始化后处理 - 设置默认值和环境变量覆盖"""
        # 从环境变量获取配置
        self.environment = os.getenv("ENVIRONMENT", self.environment)
        self.debug = os.getenv("DEBUG", "0").lower() in ("1", "true", "yes")
        
        # 根据环境调整配置
        if self.environment == "testing":
            self.headless = True
            self.browser_timeout = 30000
            self.form_timeout = 500
            self.wait_time = 100
        elif self.environment == "production":
            self.headless = True
            self.debug = False
            # 生产环境不使用默认密码
            self.default_username = ""
            self.default_password = ""
        
        # 从环境变量获取登录信息（生产环境必需）
        username_from_env = os.getenv("DC_USERNAME")
        password_from_env = os.getenv("DC_PASSWORD")
        
        if username_from_env:
            self.default_username = username_from_env
        if password_from_env:
            self.default_password = password_from_env
        
        # 设置Amazon选择器
        if self.amazon_selectors is None:
            self.amazon_selectors = {
                'title': '#productTitle',
                'product_table_top': "table[class='a-normal a-spacing-micro']",
                'product_table_bottom': "table[class='a-keyvalue prodDetTable']",
                'glance_icons': '#glance_icons_div',
                'feature_bullets': '#feature-bullets ul.a-unordered-list li span.a-list-item',
                'weight_cell': "td:has-text('Item Weight')"
            }
    
    def get_browser_options(self) -> Dict[str, Any]:
        """获取浏览器启动选项"""
        return {
            'headless': self.headless,
            'timeout': self.browser_timeout
        }
    
    def get_context_options(self) -> Dict[str, Any]:
        """获取浏览器上下文选项"""
        return {
            'no_viewport': self.no_viewport
        }
    
    def get_credentials(self):
        """
        获取登录凭据
        
        Returns:
            tuple: (username, password)
        """
        if not self.default_username or not self.default_password:
            if self.environment == "production":
                raise ValueError(
                    "生产环境必须设置 DC_USERNAME 和 DC_PASSWORD 环境变量"
                )
            else:
                print("⚠️ 警告: 使用默认登录凭据（仅开发环境）")
        
        return self.default_username, self.default_password
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        try:
            # 验证必需的配置项
            if self.environment == "production":
                username, password = self.get_credentials()
                if not username or not password:
                    return False
            
            # 验证超时设置
            if self.browser_timeout <= 0 or self.form_timeout <= 0:
                return False
            
            return True
        except Exception:
            return False
    
    def print_config(self) -> None:
        """打印当前配置（隐藏敏感信息）"""
        print(f"🔧 系统配置:")
        print(f"   环境: {self.environment}")
        print(f"   调试模式: {self.debug}")
        print(f"   无头模式: {self.headless}")
        print(f"   表单超时: {self.form_timeout}ms")
        print(f"   等待时间: {self.wait_time}ms")
        print(f"   脚本期限: {self.expiration_hours}小时")
        
        if self.default_username:
            masked_username = self.default_username[:3] + "*" * (len(self.default_username) - 3)
            print(f"   用户名: {masked_username}")
        
        print()


# 全局配置实例
config = SystemConfig()


def get_config() -> SystemConfig:
    """获取全局配置实例"""
    return config


def load_config_from_file(config_path: str) -> Optional[SystemConfig]:
    """
    从配置文件加载配置（预留接口）
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        SystemConfig实例或None
    """
    # 这里可以实现从JSON/YAML文件加载配置的逻辑
    # 暂时返回None，使用默认配置
    return None
