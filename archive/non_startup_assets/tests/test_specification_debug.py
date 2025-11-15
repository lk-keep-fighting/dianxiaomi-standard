#!/usr/bin/env python3
"""
Test script to debug specification parsing issues
"""

def test_html_parsing():
    """Test parsing the provided HTML content"""
    
    # The HTML structure you provided
    html_content = '''
    <div id="twister-plus-inline-twister-card" class="a-cardui inline-twister-card-padding" data-a-card-type="basic" name="a-cardui-deck-autoname-0-card0">
        <div class="a-cardui-body">
            <div id="twister-plus-inline-twister" class="a-section">
                <div id="inline-twister-row-style_name" data-csa-c-content-id="inline-twister-row-style_name" class="a-section a-spacing-none inline-twister-row">
                    <div id="inline-twister-expander-header-style_name" class="a-section a-spacing-none dimension-heading">
                        <div id="inline-twister-dim-title-style_name" class="a-section a-spacing-none dimension-text">
                            <div class="a-section a-spacing-none a-padding-none inline-twister-dim-title-value-truncate-expanded">
                                <span class="a-size-base a-color-secondary">Style:</span>
                                <span id="inline-twister-expanded-dimension-text-style_name" class="a-size-base a-color-base inline-twister-dim-title-value a-text-bold">Single</span>
                            </div>
                        </div>
                    </div>
                    <div id="inline-twister-expander-content-style_name" data-totalvariationcount="4" class="a-section a-spacing-none dimension-expander-content">
                        <div class="a-section">
                            <div id="tp-inline-twister-dim-values-container" class="a-section a-spacing-none" role="group">
                                <ul class="a-unordered-list a-nostyle a-button-list dimension-values-list" role="radiogroup">
                                    <li data-asin="B074V9J8SD" data-initiallyselected="true" class="dimension-value-list-item-square-image inline-twister-swatch">
                                        <span class="a-list-item">
                                            <span id="style_name_3" class="a-button a-button-selected a-button-toggle">
                                                <span class="a-button-inner">
                                                    <input name="3" role="radio" aria-checked="true" class="a-button-input" type="submit">
                                                    <img alt="Single" src="https://m.media-amazon.com/images/I/41-XeZVpPkL._SS64_.jpg" class="swatch-image">
                                                </span>
                                            </span>
                                        </span>
                                    </li>
                                    <li data-asin="B07DHMCHYV" data-initiallyselected="false" class="dimension-value-list-item-square-image inline-twister-swatch">
                                        <span class="a-list-item">
                                            <span id="style_name_0" class="a-button a-button-toggle">
                                                <span class="a-button-inner">
                                                    <input name="0" role="radio" aria-checked="false" class="a-button-input" type="submit">
                                                    <img alt="2-pack" src="https://m.media-amazon.com/images/I/5184FvlxgVL._SS64_.jpg" class="swatch-image">
                                                </span>
                                            </span>
                                        </span>
                                    </li>
                                    <li data-asin="B07MMZ4199" data-initiallyselected="false" class="dimension-value-list-item-square-image inline-twister-swatch">
                                        <span class="a-list-item">
                                            <span id="style_name_1" class="a-button a-button-toggle">
                                                <span class="a-button-inner">
                                                    <input name="1" role="radio" aria-checked="false" class="a-button-input" type="submit">
                                                    <img alt="3-pack" src="https://m.media-amazon.com/images/I/412J1GVZMhL._SS64_.jpg" class="swatch-image">
                                                </span>
                                            </span>
                                        </span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''
    
    print("🔍 HTML Analysis Results:")
    print("=" * 50)
    
    # Analyze the HTML structure
    import re
    
    # Find all inline-twister-row elements
    row_pattern = r'id="inline-twister-row-([^"]+)"'
    rows = re.findall(row_pattern, html_content)
    print(f"📊 Found {len(rows)} specification dimensions:")
    for i, row in enumerate(rows):
        print(f"  {i+1}. {row}")
    
    # Find selected values
    selected_pattern = r'<span id="inline-twister-expanded-dimension-text-([^"]+)"[^>]*>([^<]+)</span>'
    selected_values = re.findall(selected_pattern, html_content)
    print(f"\n🎯 Found {len(selected_values)} selected values:")
    for dimension, value in selected_values:
        print(f"  {dimension}: {value}")
    
    # Find available options
    alt_pattern = r'<img alt="([^"]+)"'
    options = re.findall(alt_pattern, html_content)
    print(f"\n📋 Found {len(options)} available options:")
    for i, option in enumerate(options):
        print(f"  {i+1}. {option}")
    
    # Check for radio buttons
    radio_pattern = r'<input[^>]*role="radio"[^>]*aria-checked="([^"]+)"'
    radio_states = re.findall(radio_pattern, html_content)
    print(f"\n🔘 Found {len(radio_states)} radio buttons:")
    for i, state in enumerate(radio_states):
        option_text = options[i] if i < len(options) else "Unknown"
        print(f"  {i+1}. {option_text}: {state}")
    
    print("\n" + "=" * 50)
    print("📝 Analysis Summary:")
    print("  ✅ Only found 'style_name' dimension with values: Single, 2-pack, 3-pack")
    print("  ❌ No 'pattern_name' dimension found in this HTML")
    print("  💡 The 'Pattern Name: Storage' might be in a different HTML section")
    print("     or it could be derived from product title/description")
    
    return {
        'dimensions': rows,
        'selected_values': dict(selected_values),
        'available_options': options,
        'radio_states': radio_states
    }

if __name__ == "__main__":
    print("🧪 Specification Parsing Debug Tool")
    print("=" * 60)
    
    results = test_html_parsing()
    
    print(f"\n🎯 Conclusion:")
    print(f"  📊 Dimensions found: {len(results['dimensions'])}")
    print(f"  🎯 Selected values: {len(results['selected_values'])}")
    print(f"  📋 Available options: {len(results['available_options'])}")
    
    if 'pattern_name' not in results['dimensions']:
        print(f"\n⚠️  Pattern Name Issue Identified:")
        print(f"     - The HTML only contains 'style_name' specification")
        print(f"     - 'Pattern Name: Storage' is not in this HTML structure")
        print(f"     - It might be in a separate section or derived from other content")
        print(f"\n💡 Recommended Solutions:")
        print(f"     1. Check if Pattern Name is in product title/description")
        print(f"     2. Look for Pattern information in product details table")
        print(f"     3. Search for additional twister sections in the full page")
        print(f"     4. Enable the alternative parsing methods we added")