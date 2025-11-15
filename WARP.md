# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **Digital Chief Automation** project - a Playwright-based browser automation tool designed for e-commerce product information extraction and form filling. The system automates interactions with the DataCaciques ERP system by extracting product details from Amazon and automatically filling product specification forms.

## Architecture Overview

### Core Components

- **`src/main.py`**: Main automation orchestrator containing login flow, product extraction pipeline, and form filling coordination
- **`src/auto_form_filler.py`**: Intelligent form filling engine with field mapping logic and multi-input type handling
- **`src/config/config.py`**: Environment-aware configuration system with browser, timeout, and credential management

### Key Workflows

1. **Login & Session Management**: Handles authentication with DataCaciques ERP and persists session state via `auth_state.json`
2. **Product Data Extraction**: Opens Amazon product pages, handles language/region switching, and extracts structured product details from tables
3. **Intelligent Form Filling**: Maps extracted product attributes to form fields using `attrkey` selectors and handles various input types (text, dropdowns, TinyMCE editors)

### Critical Architecture Patterns

- **Dual-Frame Navigation**: Complex iframe nesting (`iframeModal_flag_0` → `iframeModal_editPostTemplet`) requires careful frame switching
- **Dynamic Field Mapping**: Product detail keys are intelligently mapped to form `attrkey` attributes with fallback strategies
- **Expiration Control System**: Built-in time-limited usage control for distribution versions

## Development Commands

### Setup and Installation
```bash
# Quick setup (creates venv and installs all dependencies)
./install_dependencies.sh --venv

# Manual setup
pip install -r requirements.txt
python -m playwright install
```

### Running the Application
```bash
# Start main automation
python src/main.py

# Alternative using convenience script
./run.sh
```

### Testing
```bash
# Run all tests
pytest src/tests/

# Run specific test with detailed output
pytest src/tests/test_example.py -v

# Run tests with HTML report
pytest src/tests/ --html=report.html
```

### Development Tools
```bash
# Check expiration status (for distributed versions)
python manage_expiration.py status

# Reset expiration timer (before distribution)  
python manage_expiration.py reset

# Create clean distribution package
python manage_expiration.py package
```

## Configuration Management

### Environment Variables
```bash
# Required for production
export DC_USERNAME="your_username"
export DC_PASSWORD="your_password"

# Optional
export ENVIRONMENT="development"  # or "testing", "production"
export DEBUG="1"  # Enable detailed logging
```

### Config Environments
- **Development** (`Config`): Headless=false, full timeouts, includes default credentials
- **Testing** (`TestConfig`): Headless=true, shorter timeouts for faster test execution  
- **Production** (`ProductionConfig`): Headless=true, no default credentials for security

## Key Technical Details

### Browser Automation Specifics
- **Multi-browser support**: Chromium (default), Firefox, WebKit via Playwright configuration
- **Session persistence**: Login state saved to `auth_state.json` to avoid repeated authentication
- **Dynamic element handling**: Robust retry logic for element interactions with configurable timeouts

### Form Field Intelligence  
- **Attribute-based targeting**: Uses `div[attrkey='fieldname']` pattern for reliable field location
- **Multi-input support**: Handles textarea, select2 dropdowns, regular inputs, and TinyMCE iframes
- **Smart value mapping**: Product attributes automatically mapped to appropriate form fields with special handling for compound fields like "Key Features"

### Error Handling Strategy
- **Graceful degradation**: Missing product details don't stop form filling
- **Comprehensive logging**: Detailed success/failure reporting for each field operation
- **Timeout management**: Configurable timeouts per operation type (short/medium/long)

## Debugging and Troubleshooting

### Common Issues
```bash
# Browser permission issues
chmod +x install_dependencies.sh run.sh

# Playwright browser installation
python -m playwright install --with-deps

# Debug mode with detailed logging
export DEBUG=1 && python src/main.py
```

### Development Workflow
1. **iframe debugging**: Use browser DevTools to inspect nested iframe structure when selectors fail
2. **Field mapping**: Check `attrkey` values in target forms when adding new field mappings
3. **Product extraction**: Test Amazon page structure changes by examining table selectors for product details

## Distribution and Deployment

### Creating Distribution Packages
The project includes an expiration management system for controlled distribution:

```bash
# Before distributing, reset the timer
python manage_expiration.py reset

# Create clean package (removes auth files, logs, git history)
python manage_expiration.py package
```

### Environment-Specific Deployment
- **Development**: Use `Config` class with visible browser for debugging
- **Production**: Use `ProductionConfig` with headless mode and environment variables for credentials

## Architecture Decision Context

The system handles complex multi-layer browser automation with significant iframe nesting and dynamic form structures. The separation between extraction (`main.py`) and form filling (`auto_form_filler.py`) allows for independent testing and modification of either pipeline. The configuration system supports multiple deployment environments while maintaining security through environment variable injection.

<citations>
<document>
    <document_type>RULE</document_type>
    <document_id>ZVco2ER3LFye55Ef1SLECm</document_id>
</document>
</citations>
