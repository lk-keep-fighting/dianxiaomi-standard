#!/usr/bin/env python3
"""
Automated script to edit products in Dianxiaomi platform
- Iterates through edit buttons in the product table
- Opens edit page and extracts visit link
- Parses data from the visit page
- Fills data back to the edit form
"""

import os
import re
from playwright.sync_api import sync_playwright, Page, expect

from amazon_product_parser import AmazonProductParser, ProductData

# Login credentials
user_name = "liyoutest001"
password = "Aa741852963."
storage_state = user_name + "_auth_state.json"


def login_if_needed(page: Page) -> None:
    """Handle login if not already logged in"""
    if not os.path.exists(storage_state):
        print("Logging in...")
        page.goto("https://www.dianxiaomi.com/")
        page.get_by_role("paragraph").filter(has_text=re.compile(r"^$")).first.click()
        page.get_by_role("textbox", name="请输入用户名").click()
        page.get_by_role("textbox", name="请输入用户名").fill(user_name)
        page.get_by_role("textbox", name="请输入密码").click()
        page.get_by_role("textbox", name="请输入密码").fill(password)
        input("Waiting for login and navigation to product page...\n")
        # Save authentication state
        page.context.storage_state(path=storage_state)
    else:
        print("Using existing authentication state")


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


def extract_visit_link(edit_page: Page) -> str | None:
    """Extract the visit link from the edit page"""
    # Wait for the page to load
    edit_page.wait_for_load_state("networkidle")
    
    # Based on the description, we need to find the "访问" link
    # This might be in a specific location on the edit page
    try:
        # Look for a link with text "访问" or similar
        visit_link_element = edit_page.get_by_role("link", name="访问")
        if not visit_link_element.is_visible():
            # Try alternative selectors
            visit_link_element = edit_page.locator("a:has-text('访问')")
        
        visit_url = visit_link_element.get_attribute("href")
        print(f"Found visit link: {visit_url}")
        return visit_url
    except Exception as e:
        print(f"Could not find visit link: {e}")
        # Try to get all links and find one that looks like a product URL
        links = edit_page.locator("a[href*='amazon']").all()
        if links:
            visit_url = links[0].get_attribute("href")
            print(f"Found Amazon link as fallback: {visit_url}")
            return visit_url
        return None


def parse_data_from_visit_page(visit_page: Page) -> dict:
    """Parse required data from the visit page"""
    # Wait for page to load
    visit_page.wait_for_load_state("networkidle")
    
    product_data = {}
    
    try:
        # Extract product title
        title_element = visit_page.locator("#productTitle, h1[data-automation-id='title']")
        if title_element.is_visible():
            product_data["title"] = title_element.text_content().strip()
        else:
            # Try alternative selectors
            title_element = visit_page.locator("h1, .product-title")
            if title_element.first.is_visible():
                product_data["title"] = title_element.first.text_content().strip()
        
        # Extract product price
        price_element = visit_page.locator(".a-price-whole, .price, [data-automation-id='price']")
        if price_element.first.is_visible():
            product_data["price"] = price_element.first.text_content().strip()
        
        # Extract product description
        desc_element = visit_page.locator("#productDescription, .product-description")
        if desc_element.is_visible():
            product_data["description"] = desc_element.text_content().strip()
        
        # Extract product images
        image_elements = visit_page.locator("img[data-a-dynamic-image], .img-tag, .image")
        image_urls = []
        for i in range(min(5, image_elements.count())):  # Get up to 5 images
            img_url = image_elements.nth(i).get_attribute("src") or image_elements.nth(i).get_attribute("data-src")
            if img_url:
                image_urls.append(img_url)
        product_data["images"] = image_urls
        
        print(f"Parsed data: {product_data}")
        return product_data
    except Exception as e:
        print(f"Error parsing visit page: {e}")
        return product_data


def fill_edit_form(edit_page: Page, product_data: dict) -> None:
    """Fill the edit form with parsed data"""
    try:
        # Fill product title
        if "title" in product_data and product_data["title"]:
            title_input = edit_page.locator("input[name='productTitleBuyer']")
            if title_input.is_visible():
                title_input.fill(product_data["title"][:200])  # Limit to 200 chars
        
        # Fill product description
        if "description" in product_data and product_data["description"]:
            desc_input = edit_page.locator("textarea[name='productDesc']")
            if desc_input.is_visible():
                desc_input.fill(product_data["description"][:1000])  # Limit to 1000 chars
        
        # Fill price (if needed)
        if "price" in product_data and product_data["price"]:
            # Find price input fields
            price_inputs = edit_page.locator("input[placeholder*='价格'], input[placeholder*='price']")
            if price_inputs.count() > 0:
                # Fill the first price input with parsed price
                clean_price = re.sub(r'[^\d.]', '', product_data["price"])
                if clean_price:
                    price_inputs.first.fill(clean_price)
        
        print("Filled edit form with parsed data")
    except Exception as e:
        print(f"Error filling edit form: {e}")


def save_product_changes(edit_page: Page) -> None:
    """Save changes made to the product"""
    try:
        # Look for save button
        save_button = edit_page.get_by_role("button", name="保存")
        if not save_button.is_visible():
            # Try alternative selectors
            save_button = edit_page.locator("button:has-text('保存'), button[type='submit']")
        
        if save_button.is_visible():
            save_button.click()
            print("Clicked save button")
            # Wait for save confirmation
            edit_page.wait_for_timeout(2000)
        else:
            print("Save button not found")
    except Exception as e:
        print(f"Error saving product: {e}")


def process_product_edit(context,page: Page, edit_button) -> None:
    """Process a single product edit operation"""
    try:
        # Click the edit button
        print("Clicking edit button...")
        with page.context.expect_page() as edit_page_info:
            edit_button.click()
        
        edit_page = edit_page_info.value
        edit_page.wait_for_load_state("networkidle")
        print("Edit page opened")
        
        # Extract web_url from the sourceList input field
        try:
            web_url = edit_page.locator("input[name='sourceUrl']").input_value()
            print(f"Extracted web_url: {web_url}")
        except Exception as e:
            print(f"Failed to extract web_url from input field: {e}")
            web_url = None
        # Extract visit link
        # web_url = extract_visit_link(edit_page)
        if not web_url:
            print("未找到访问链接，跳过...")
            edit_page.close()
            return
            # 打开新的亚马逊页面
        amazon_page = context.new_page()
        
        try:
            # 导航到亚马逊产品页面
            print(f"🌐 正在打开亚马逊产品页面: {web_url}")
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
                print("❌ 未获取到有效的产品数据，跳过表单填充")
                amazon_page.close()
                edit_page.close()
                return
            
            # 转换ProductData对象为字典格式（为了兼容fill_edit_form函数）
            product_dict = {
                'title': product_data.title,
                **product_data.details  # 展开所有产品详情
            }
            
            # Fill edit form with parsed data
            fill_edit_form(edit_page, product_dict)
        except Exception as e:
            print(f"❌ 产品解析器出错: {e}")
            amazon_page.close()
        

        
        # Save changes
        save_product_changes(edit_page)
        
        # Close edit page
        edit_page.close()
        print("Completed processing product")
        
    except Exception as e:
        print(f"Error processing product: {e}")
        # Try to close any open pages
        try:
            # These variables might not be defined if an error occurred early
            pass
        except:
            pass


def run_automation():
    """Main automation function"""
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        
        # Create context with or without stored authentication
        if os.path.exists(storage_state):
            context = browser.new_context(storage_state=storage_state, no_viewport=True)
        else:
            context = browser.new_context(no_viewport=True)
        
        page = context.new_page()
        
        # Login if needed
        login_if_needed(page)
        
        # Navigate to product management page (adjust URL as needed)
        page.goto("https://www.dianxiaomi.com/web/sheinProduct/draft")  # Adjust this URL
        
        # Wait for page to load
        page.wait_for_load_state("networkidle")
        
        # Get all edit buttons
        edit_buttons, count = get_edit_buttons(page)
        
        if count == 0:
            print("No edit buttons found!")
            browser.close()
            return
        
        # Process each product
        for i in range(count):
            print(f"\nProcessing product {i+1}/{count}")
            try:
                # Get fresh reference to the button (DOM might change)
                buttons, _ = get_edit_buttons(page)
                if i < buttons.count():
                    process_product_edit(context,page, buttons.nth(i))
                else:
                    print("Button index out of range, skipping...")
            except Exception as e:
                print(f"Error processing product {i+1}: {e}")
            
            # Wait between operations
            page.wait_for_timeout(3000)
        
        print("\nCompleted processing all products")
        input("Press Enter to close browser...")
        browser.close()


if __name__ == "__main__":
    run_automation()