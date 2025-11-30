#!/bin/bash

# PinkWeather Installation Script for Unix/Linux/macOS
# This script sets up the development environment for the weather display system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect Python command
detect_python() {
    if command_exists python3; then
        echo "python3"
    elif command_exists python; then
        # Check if it's Python 3
        if python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            echo "python"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Function to detect pip command
detect_pip() {
    local python_cmd=$1
    if command_exists pip3; then
        echo "pip3"
    elif command_exists pip; then
        echo "pip"
    elif [ -n "$python_cmd" ]; then
        # Try using python -m pip
        if $python_cmd -m pip --version >/dev/null 2>&1; then
            echo "$python_cmd -m pip"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Main installation function
main() {
    echo "=================================================="
    echo "PinkWeather Installation Script"
    echo "Weather Display System Setup"
    echo "=================================================="
    echo

    # Check if we're in the right directory
    if [ ! -f "display_renderer.py" ] || [ ! -f "http_server.py" ]; then
        print_error "Please run this script from the pinkweather directory"
        print_error "Required files not found: display_renderer.py, http_server.py"
        exit 1
    fi

    print_status "Checking system requirements..."

    # Detect Python
    PYTHON_CMD=$(detect_python)
    if [ -z "$PYTHON_CMD" ]; then
        print_error "Python 3.8+ not found"
        print_error "Please install Python 3.8 or later:"
        echo "  • Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "  • CentOS/RHEL: sudo yum install python3 python3-pip"
        echo "  • macOS: brew install python3"
        echo "  • Or download from: https://python.org/downloads/"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_success "Found Python $PYTHON_VERSION ($PYTHON_CMD)"

    # Detect pip
    PIP_CMD=$(detect_pip "$PYTHON_CMD")
    if [ -z "$PIP_CMD" ]; then
        print_error "pip not found"
        print_error "Please install pip for Python package management"
        exit 1
    fi

    print_success "Found pip ($PIP_CMD)"

    # Ask user about installation type
    echo
    echo "Installation options:"
    echo "1) Development setup with virtual environment (recommended)"
    echo "2) System-wide installation"
    echo "3) Just check dependencies"
    echo
    read -p "Choose option [1-3]: " choice

    case $choice in
        1)
            install_with_venv
            ;;
        2)
            install_system_wide
            ;;
        3)
            check_dependencies_only
            ;;
        *)
            print_error "Invalid choice. Exiting."
            exit 1
            ;;
    esac
}

# Install with virtual environment
install_with_venv() {
    print_status "Setting up virtual environment..."

    # Create virtual environment
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Remove existing venv and recreate? [y/N]: " recreate
        if [[ $recreate =~ ^[Yy]$ ]]; then
            rm -rf venv
            $PYTHON_CMD -m venv venv
        fi
    else
        $PYTHON_CMD -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    print_success "Virtual environment created and activated"

    # Upgrade pip
    print_status "Upgrading pip..."
    python -m pip install --upgrade pip

    # Install dependencies
    print_status "Installing dependencies..."
    pip install -r requirements.txt

    # Run verification
    print_status "Running installation verification..."
    python check_install.py

    print_success "Installation complete!"
    echo
    echo "To use the development environment:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Start development server: python http_server.py"
    echo "  3. Open http://localhost:8000 in your browser"
    echo
    echo "To deactivate virtual environment later: deactivate"
}

# Install system-wide
install_system_wide() {
    print_warning "Installing system-wide..."
    print_warning "This may affect other Python projects"

    read -p "Continue with system-wide installation? [y/N]: " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_status "Installation cancelled"
        exit 0
    fi

    # Try to install dependencies
    print_status "Installing dependencies..."

    # Check if we need --user flag or --break-system-packages
    if $PIP_CMD install --dry-run Pillow >/dev/null 2>&1; then
        $PIP_CMD install -r requirements.txt
    elif $PIP_CMD install --user --dry-run Pillow >/dev/null 2>&1; then
        print_warning "Using --user installation"
        $PIP_CMD install --user -r requirements.txt
    else
        print_error "Cannot install packages. Try creating a virtual environment instead."
        print_error "Run: $0 and choose option 1"
        exit 1
    fi

    # Run verification
    print_status "Running installation verification..."
    $PYTHON_CMD check_install.py

    print_success "System-wide installation complete!"
    echo
    echo "To start development server: $PYTHON_CMD http_server.py"
    echo "To generate previews: $PYTHON_CMD weather_example.py"
}

# Check dependencies only
check_dependencies_only() {
    print_status "Checking dependencies without installing..."

    if [ -f "venv/bin/activate" ]; then
        print_status "Found virtual environment, checking within venv..."
        source venv/bin/activate
        python check_install.py
    else
        $PYTHON_CMD check_install.py
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [option]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --venv         Install with virtual environment"
        echo "  --system       Install system-wide"
        echo "  --check        Check dependencies only"
        echo
        echo "If no option provided, interactive mode will be used."
        exit 0
        ;;
    --venv)
        # Detect Python and pip first
        PYTHON_CMD=$(detect_python)
        PIP_CMD=$(detect_pip "$PYTHON_CMD")
        if [ -z "$PYTHON_CMD" ] || [ -z "$PIP_CMD" ]; then
            print_error "Python 3.8+ and pip are required"
            exit 1
        fi
        install_with_venv
        ;;
    --system)
        PYTHON_CMD=$(detect_python)
        PIP_CMD=$(detect_pip "$PYTHON_CMD")
        if [ -z "$PYTHON_CMD" ] || [ -z "$PIP_CMD" ]; then
            print_error "Python 3.8+ and pip are required"
            exit 1
        fi
        install_system_wide
        ;;
    --check)
        PYTHON_CMD=$(detect_python)
        if [ -z "$PYTHON_CMD" ]; then
            print_error "Python 3.8+ is required"
            exit 1
        fi
        check_dependencies_only
        ;;
    "")
        # No arguments, run interactively
        main
        ;;
    *)
        print_error "Unknown option: $1"
        print_error "Use --help for usage information"
        exit 1
        ;;
esac
