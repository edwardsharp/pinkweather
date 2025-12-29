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
	@echo "  generate-dataset [DATASET] [csv-only] [COUNT] - Generate dataset (csv-only for fast iteration)"
	@echo "    Available datasets: ny_2024 (default), toronto_2025"
	@echo "    Examples: make generate-dataset toronto_2025 csv-only 50"
	@echo "              make generate-dataset ny_2024 100"
	@echo "  generate-images [COUNT] - Generate images for existing narratives_*.csv (backup option)"
	@echo "    Images saved to images/DATASET/ directories (e.g. images/nyc_2024/)"
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
		. venv/bin/activate && cd web && python http_server.py; \
	else \
		echo "No virtual environment found. Run 'make setup' first or activate manually."; \
		cd web && python http_server.py; \
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

# Data generation target with dataset support - using optimized preview system
generate-dataset:
	@# Parse arguments to extract csv-only and count
	@CSV_ONLY=""; COUNT=""; UNKNOWN_ARG=""; CSV_FILE="../misc/open-meteo-40.65N73.98W25m.csv"; \
	for arg in $(filter-out generate-dataset,$(MAKECMDGOALS)); do \
		case $$arg in \
			ny_2024) CSV_FILE="../misc/open-meteo-40.65N73.98W25m.csv" ;; \
			toronto_2025) CSV_FILE="../misc/open-meteo-43.70N79.40W165m.csv" ;; \
			csv-only) CSV_ONLY="true" ;; \
			[0-9]*) COUNT=$$arg ;; \
			*) UNKNOWN_ARG=$$arg ;; \
		esac; \
	done; \
	if [ "$$UNKNOWN_ARG" ]; then \
		echo "Error: Unknown argument '$$UNKNOWN_ARG'"; \
		echo "Available datasets: ny_2024, toronto_2025"; \
		echo "Usage: make generate-dataset [DATASET] [csv-only] [COUNT]"; \
		exit 1; \
	fi; \
	if [ "$$CSV_ONLY" ]; then \
		if [ "$$COUNT" ]; then \
			echo "Generating narratives CSV with count $$COUNT using optimized preview system..."; \
			COMMAND="batch-narratives $$CSV_FILE --max-count $$COUNT"; \
		else \
			echo "Generating narratives CSV (all records) using optimized preview system..."; \
			COMMAND="batch-narratives $$CSV_FILE"; \
		fi; \
	elif [ "$$COUNT" ]; then \
		echo "Generating complete dataset with count $$COUNT using optimized preview system..."; \
		COMMAND="complete $$CSV_FILE --max-count $$COUNT"; \
	else \
		echo "Generating complete dataset (all records) using optimized preview system..."; \
		COMMAND="complete $$CSV_FILE"; \
	fi; \
	if [ -f "venv/bin/activate" ]; then \
		. venv/bin/activate && cd preview && python main.py $$COMMAND; \
	else \
		cd preview && python main.py $$COMMAND; \
	fi

csv-only ny_2024 toronto_2025:
	@# Dummy targets for argument parsing

# Dummy targets to prevent make from complaining about unknown targets
%:
	@:

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
		echo "Virtual environment exists. activating"; \
		echo ""; \
		echo "To deactivate later: deactivate"; \
		. venv/bin/activate; \
	else \
		echo "No virtual environment found."; \
		echo "Create one with: make venv"; \
	fi
