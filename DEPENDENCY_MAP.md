# Dependency Mapping for Target Files

## Critical Dependencies (DO NOT REMOVE)

### main_refactored_dianxiaomi.py Dependencies:
- `amazon_product_parser.py` (src/)
- `product_data.py` (src/)
- `unified_form_filler.py` (src/)

### main_refactored.py Dependencies:
- `amazon_product_parser.py` (src/)
- `unified_form_filler.py` (src/)

## Core Files to Preserve:
- `src/amazon_product_parser.py`
- `src/product_data.py`
- `src/unified_form_filler.py`
- `src/system_config.py`
- `src/core/amazon_product_parser.py`
- `src/core/product_data.py`
- `src/core/system_config.py`

## Files Safe to Remove (Phase 1):
### Python Cache Files:
- All `__pycache__/` directories
- `.pytest_cache/` directories

### Obsolete Test Files:
- `test_ai_enum_matching.py`
- `test_ai_mapping.py`
- `test_amazon_toolkit.py`
- `test_defaults_system.py`
- `test_dimension_extraction_fix.py`
- `test_dom_integration.py`
- `test_dom_optimization.py`
- `test_dom_parser.py`
- `test_dynamic_form.py`
- `test_feature_extraction.py`
- `test_final_fix_verification.py`
- `test_form_filler.py`
- `test_glance_extraction.py`
- `test_image_editing.py`
- `test_image_editing_simple.py`
- `test_multi_website_architecture.py`
- `test_select_option_matching.py`
- `test_unit_selection.py`
- `test_weight_conversion.py`
- `test_weight_extraction_fix.py`

### Keep for validation:
- `test_refactored_system.py` (for validation)
- `test_image_editing_unit.py` (recent)

Generated: $(date)
Current file count: 357