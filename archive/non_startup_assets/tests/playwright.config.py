# playwright.config.py
# Configuration file for Playwright tests

from playwright.sync_api import sync_playwright

# Playwright configuration for pytest-playwright
config = {
    "timeout": 30000,
    "use": {
        "headless": False,  # Set to True to run tests in headless mode
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "video": "retain-on-failure",
        "screenshot": "only-on-failure",
    },
    "projects": [
        {
            "name": "chromium",
            "use": {"browserName": "chromium"},
        },
        {
            "name": "firefox",
            "use": {"browserName": "firefox"},
        },
        {
            "name": "webkit",
            "use": {"browserName": "webkit"},
        },
    ],
}

# Example usage function (for reference)
def example_playwright_usage():
    """Example function showing basic Playwright usage"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://example.com")
        print(f"Page title: {page.title()}")
        browser.close()

if __name__ == "__main__":
    example_playwright_usage()