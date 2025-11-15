#!/bin/bash

# Digital Chief Automation Project - Dependency Installation Script
# This script installs all required dependencies for the browser automation project

set -e  # Exit on any error

echo "=================================================="
echo "  Digital Chief Automation - Dependency Installer"
echo "=================================================="

# Check if Python is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Error: Python is not installed or not in PATH"
        echo "Please install Python 3.7+ from https://www.python.org/"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    echo "✅ Found Python: $($PYTHON_CMD --version)"
    
    # Check if version is 3.7+
    if [[ $(echo "$PYTHON_VERSION 3.7" | tr " " "\n" | sort -V | head -n1) != "3.7" ]]; then
        echo "❌ Error: Python 3.7+ is required, found $PYTHON_VERSION"
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        echo "❌ Error: pip is not installed"
        echo "Please install pip or use 'python -m pip' instead"
        exit 1
    fi
    echo "✅ Found pip: $($PIP_CMD --version)"
}

# Install Python dependencies
install_python_deps() {
    echo ""
    echo "📦 Installing Python dependencies..."
    
    # Upgrade pip first
    echo "⬆️  Upgrading pip..."
    $PIP_CMD install --upgrade pip
    
    # Install dependencies from requirements.txt
    echo "📋 Installing from requirements.txt..."
    $PIP_CMD install -r requirements.txt
    
    echo "✅ Python dependencies installed successfully"
}

# Install Playwright browsers
install_playwright_browsers() {
    echo ""
    echo "🌐 Installing Playwright browsers..."
    
    # Install browser binaries
    $PYTHON_CMD -m playwright install
    
    echo "✅ Playwright browsers installed successfully"
}

# Create virtual environment (optional)
create_venv() {
    if [ "$1" = "--venv" ]; then
        echo ""
        echo "🐍 Creating virtual environment..."
        
        if [ ! -d "venv" ]; then
            $PYTHON_CMD -m venv venv
            echo "✅ Virtual environment created"
        else
            echo "ℹ️  Virtual environment already exists"
        fi
        
        echo "📝 To activate virtual environment, run:"
        echo "   source venv/bin/activate  (Linux/macOS)"
        echo "   venv\\Scripts\\activate     (Windows)"
        echo ""
        
        # Ask if user wants to activate now
        read -p "Do you want to activate the virtual environment now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            source venv/bin/activate
            echo "✅ Virtual environment activated"
        fi
    fi
}

# Verify installation
verify_installation() {
    echo ""
    echo "🔍 Verifying installation..."
    
    # Check if playwright is properly installed
    if $PYTHON_CMD -c "import playwright; print('Playwright version:', playwright.__version__)" 2>/dev/null; then
        echo "✅ Playwright is working correctly"
    else
        echo "❌ Playwright installation verification failed"
        return 1
    fi
    
    # Check if pytest is working
    if $PYTHON_CMD -c "import pytest; print('Pytest version:', pytest.__version__)" 2>/dev/null; then
        echo "✅ Pytest is working correctly"
    else
        echo "❌ Pytest installation verification failed"
        return 1
    fi
    
    echo "✅ All dependencies verified successfully"
}

# Show usage info
show_usage() {
    echo ""
    echo "🚀 Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Run the main application:"
    echo "   ./run.sh              (Linux/macOS)"
    echo "   run.bat               (Windows)"
    echo "   python src/main_refactored_dianxiaomi.py    (Direct)"
    echo ""
    echo "2. Run tests (archived utilities):"
    echo "   pytest archive/non_startup_assets/tests/"
    echo ""
    echo "3. For development with virtual environment:"
    echo "   ./install_dependencies.sh --venv"
    echo ""
}

# Main installation process
main() {
    echo "🔍 Checking system requirements..."
    check_python
    check_pip
    
    # Check if --venv flag is provided
    create_venv "$1"
    
    install_python_deps
    install_playwright_browsers
    verify_installation
    show_usage
}

# Run main function with all arguments
main "$@"