#!/usr/bin/env python3
"""
Configuration module for Digital Chief Automation
Contains all configuration settings and constants
"""

import os
from typing import Dict, Any

class Config:
    """Main configuration class for the automation project"""
    
    # Browser settings
    HEADLESS_MODE = False
    BROWSER_TIMEOUT = 60000  # 60 seconds
    PAGE_TIMEOUT = 30000     # 30 seconds
    
    # Default viewport
    VIEWPORT_WIDTH = 1280
    VIEWPORT_HEIGHT = 720
    
    # Supported browsers
    SUPPORTED_BROWSERS = ["chromium", "firefox", "webkit"]
    DEFAULT_BROWSER = "chromium"
    
    # File paths
    AUTH_STATE_FILE = "auth_state.json"
    SCREENSHOTS_DIR = "screenshots"
    LOGS_DIR = "logs"
    
    # URLs
    LOGIN_URL = "https://www.datacaciques.com/login"
    ERP_URL = "https://erp.datacaciques.com/newpro/inventory?platform=ebay#/all/all"
    
    # Credentials (should be moved to environment variables in production)
    DEFAULT_USERNAME = os.getenv("DC_USERNAME", "")
    DEFAULT_PASSWORD = os.getenv("DC_PASSWORD", "")
    
    # Automation settings
    WAIT_TIME_SHORT = 200    # milliseconds
    WAIT_TIME_MEDIUM = 1000  # milliseconds
    WAIT_TIME_LONG = 5000    # milliseconds
    
    # Form filling timeout
    FILL_TIMEOUT = 1000
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2000  # milliseconds
    
    @classmethod
    def get_browser_config(cls) -> Dict[str, Any]:
        """Get browser configuration dictionary"""
        return {
            "headless": cls.HEADLESS_MODE,
            "timeout": cls.BROWSER_TIMEOUT,
            "viewport": {
                "width": cls.VIEWPORT_WIDTH,
                "height": cls.VIEWPORT_HEIGHT
            }
        }
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        for directory in [cls.SCREENSHOTS_DIR, cls.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    @classmethod
    def get_credentials(cls) -> tuple:
        """Get credentials from environment or default values"""
        username = os.getenv("DC_USERNAME", cls.DEFAULT_USERNAME)
        password = os.getenv("DC_PASSWORD", cls.DEFAULT_PASSWORD)
        return username, password


class TestConfig(Config):
    """Configuration for testing environment"""
    
    HEADLESS_MODE = True  # Tests run in headless mode by default
    BROWSER_TIMEOUT = 10000  # Shorter timeout for tests
    PAGE_TIMEOUT = 5000


class ProductionConfig(Config):
    """Configuration for production environment"""
    
    HEADLESS_MODE = True  # Production runs in headless mode
    # Remove default credentials for security
    DEFAULT_USERNAME = ""
    DEFAULT_PASSWORD = ""


# Configuration mapping
config_map = {
    "development": Config,
    "testing": TestConfig,
    "production": ProductionConfig
}

def get_config(environment: str = "development") -> Config:
    """Get configuration based on environment"""
    return config_map.get(environment, Config)