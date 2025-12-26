# Makefile for pinkweather project
# Provides easy commands for setup, development, and deployment

.PHONY: help install install-dev clean test lint format server deploy-check preview activate generate-dataset

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install basic dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  clean        - Clean up temporary files"
	@echo "  test         - Run tests"
	@echo "  lint         - Run code linting"
	@echo "  format       - Format code with black"
	@echo "  server       - Start development web server"
	@echo "  preview      - Generate weather display preview"
	@echo "  deploy-check - Check files ready for microcontroller deployment"
	@echo "  generate-dataset [csv-only] [COUNT] - Generate dataset (csv-only for fast iteration)"
	@echo "  generate-images [COUNT] - Generate images for existing narratives.csv (backup option)"
	@echo "  venv         - Create virtual environment"
	@echo "  activate     - Show how to activate virtual environment"

# Virtual environment setup
venv:
	python3 -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # Linux/Mac"
	@echo "  venv\\Scripts\\activate     # Windows"

# Install dependencies
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# Clean up temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f *.png
	rm -f weather_preview.png
	rm -f text_preview.png

# Testing
test:
	@if [ -f "venv/bin/activate" ]; then \
		. venv/bin/activate && python -m pytest tests/ -v; \
	else \
		python -m pytest tests/ -v; \
	fi

# Code quality
lint:
	@if [ -f "venv/bin/activate" ]; then \
		. venv/bin/activate && flake8 *.py --max-line-length=88 --ignore=E203,W503 && mypy *.py --ignore-missing-imports; \
	else \
		flake8 *.py --max-line-length=88 --ignore=E203,W503; \
		mypy *.py --ignore-missing-imports; \
	fi

format:
	@if [ -f "venv/bin/activate" ]; then \
		. venv/bin/activate && black *.py && isort *.py; \
	else \
		black *.py; \
		isort *.py; \
	fi

# Development server
server:
	@echo "Starting weather display development server..."
	@echo "Open http://localhost:8000 in your browser"
	@if [ -f "venv/bin/activate" ]; then \
		echo "Using virtual environment..."; \
		. venv/bin/activate && python http_server.py; \
	else \
		echo "No virtual environment found. Run 'make setup' first or activate manually."; \
		python http_server.py; \
	fi

# Generate preview images
preview:
	@echo "Generating weather display previews..."
	@if [ -f "venv/bin/activate" ]; then \
		. venv/bin/activate && python weather_example.py; \
	else \
		python weather_example.py; \
	fi
	@echo "Preview images saved as weather_preview.png and text_preview.png"

# Check deployment readiness for microcontroller
deploy-check:
	@echo "Checking files for microcontroller deployment..."
	@echo "Required files:"
	@if [ -f "display_renderer.py" ]; then echo "  ✓ display_renderer.py"; else echo "  ✗ display_renderer.py (MISSING)"; fi
	@if [ -f "code.py" ]; then echo "  ✓ code.py"; else echo "  ✗ code.py (MISSING)"; fi
	@if [ -f "AndaleMono.ttf" ]; then echo "  ✓ AndaleMono.ttf"; else echo "  ✗ AndaleMono.ttf (MISSING)"; fi
	@echo ""
	@echo "Optional files:"
	@if [ -f "weather_example.py" ]; then echo "  ✓ weather_example.py (for weather API)"; else echo "  - weather_example.py (not needed for basic display)"; fi
	@echo ""
	@echo "Copy these files to your Pi Pico 2W CircuitPython drive"

# Quick development setup
setup: venv install-dev
	@echo "Development environment setup complete!"
	@echo "Activate your virtual environment and run 'make server' to start developing"

# Build package (if using as a package)
build:
	python3 -m build

# Install package in development mode
install-package:
	pip install -e .

# Data generation target
generate-dataset:
	@if [ "$(filter csv-only,$(MAKECMDGOALS))" ]; then \
		if [ "$(COUNT)" ]; then \
			echo "Generating CSV-only with count $(COUNT)..."; \
			ARGS="--csv-only $(COUNT)"; \
		else \
			echo "Generating CSV-only for all records..."; \
			ARGS="--csv-only"; \
		fi; \
	elif [ "$(COUNT)" ]; then \
		echo "Generating dataset with count $(COUNT)..."; \
		ARGS="$(COUNT)"; \
	else \
		echo "Generating complete dataset..."; \
		ARGS=""; \
	fi; \
	if [ -f "venv/bin/activate" ]; then \
		. venv/bin/activate && cd web/static && python generate_historical_data.py $$ARGS; \
	else \
		cd web/static && python generate_historical_data.py $$ARGS; \
	fi

csv-only:
	@# Dummy target for csv-only mode

# Generate images separately (for performance)
generate-images:
	@if [ "$(COUNT)" ]; then \
		echo "Generating images for first $(COUNT) records..."; \
	else \
		echo "Generating images for all records in narratives.csv..."; \
	fi
	@echo "Reading from web/static/narratives.csv..."
	@if [ -f "venv/bin/activate" ]; then \
		if [ "$(COUNT)" ]; then \
			. venv/bin/activate && cd web/static && python batch_image_renderer.py $(COUNT); \
		else \
			. venv/bin/activate && cd web/static && python batch_image_renderer.py; \
		fi \
	else \
		if [ "$(COUNT)" ]; then \
			cd web/static && python batch_image_renderer.py $(COUNT); \
		else \
			cd web/static && python batch_image_renderer.py; \
		fi \
	fi
	@echo "Images generated in web/static/images/"

# Show activation instructions
activate:
	@if [ -f "venv/bin/activate" ]; then \
		echo "Virtual environment exists. To activate:"; \
		echo "  source venv/bin/activate"; \
		echo ""; \
		echo "To deactivate later: deactivate"; \
	else \
		echo "No virtual environment found."; \
		echo "Create one with: make venv"; \
	fi
