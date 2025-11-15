#!/usr/bin/env python3
"""
系统配置 - 核心通用组件

职责：
1. 统一的系统配置管理
2. 支持多环境配置
3. 网站无关的通用配置

设计原则：
- Single Source of Truth for configuration
- Environment-aware configuration
- Website-agnostic base configuration
"""

import os
from typing import Dict, Any, Optional


class SystemConfig:
    """
    系统基础配置类
    
    提供所有网站策略都需要的基础配置
    """
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', '0') == '1'
        
        # 浏览器配置
        self.browser_config = {
            'headless': self.environment == 'production',
            'slow_mo': 50 if self.debug else 0,
            'timeout': 60000,
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # 超时配置
        self.timeouts = {
            'short': 5000,
            'medium': 15000, 
            'long': 30000,
            'navigation': 60000
        }
        
        # Amazon解析配置
        self.amazon_config = {
            'language': 'en_US',
            'currency': 'USD',
            'retry_count': 3,
            'wait_between_retries': 2000
        }
    
    def get_timeout(self, timeout_type: str) -> int:
        """获取超时配置"""
        return self.timeouts.get(timeout_type, self.timeouts['medium'])
    
    def get_browser_config(self) -> Dict[str, Any]:
        """获取浏览器配置"""
        return self.browser_config.copy()
    
    def get_amazon_url_params(self) -> str:
        """获取Amazon URL参数"""
        return f"?language={self.amazon_config['language']}&currency={self.amazon_config['currency']}"
    
    def is_debug_mode(self) -> bool:
        """检查是否为调试模式"""
        return self.debug


# 全局系统配置实例
SYSTEM_CONFIG = SystemConfig()
