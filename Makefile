# Makefile for pinkweather project
# Provides easy commands for setup, development, and deployment

.PHONY: help install server preview deploy activate generate-dataset

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install basic dependencies"
	@echo "  server       - Start development web server"
	@echo "  preview      - Generate weather display preview"
	@echo "  deploy       - Deploy code to CIRCUITPY device"
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

# Development server
server:
	@echo "Starting weather display development server..."
	@echo "Open http://localhost:8000 in your browser"
	@if [ -f "venv/bin/activate" ]; then \
		echo "Using virtual environment..."; \
		. venv/bin/activate && cd preview && python -m web.server; \
	else \
		echo "No virtual environment found. Run 'make setup' first or activate manually."; \
		cd preview && python -m web.server; \
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

# Deploy to CIRCUITPY device
deploy:
	@echo "Deploying code to CIRCUITPY device..."
	@# Check source exists
	@if [ ! -f "300x400/CIRCUITPY/code.py" ]; then \
		echo "Error: Source code.py not found at 300x400/CIRCUITPY/code.py"; \
		exit 1; \
	fi
	@echo "Source code.py found"
	@# Try to find CIRCUITPY device
	@if [ -d "/Volumes/CIRCUITPY" ]; then \
		DEST="/Volumes/CIRCUITPY"; \
	elif [ -d "/media/CIRCUITPY" ]; then \
		DEST="/media/CIRCUITPY"; \
	else \
		echo "Could not auto-detect CIRCUITPY device."; \
		echo -n "Please enter the full path to your CIRCUITPY device: "; \
		read DEST; \
	fi; \
	if [ ! -d "$$DEST" ]; then \
		echo "Error: Directory $$DEST does not exist"; \
		exit 1; \
	fi; \
	if [ ! -f "$$DEST/code.py" ]; then \
		echo "Error: $$DEST does not appear to be a CIRCUITPY device (no code.py)"; \
		exit 1; \
	fi; \
	echo "Found CIRCUITPY device at: $$DEST"; \
	echo ""; \
	echo "=== DRY RUN ==="; \
	rsync -av --dry-run --delete --checksum --modify-window=1 \
		--exclude='config.py' --exclude='__pycache__/' --exclude='sd/' \
		--exclude='settings.toml' --exclude='boot_out.txt' --exclude='.DS_Store' \
		--exclude='._*' --exclude='.Trashes' --exclude='.Trash-1000' --exclude='.fseventsd' --exclude='.fseventsd/fseventsd-uuid' \
		300x400/CIRCUITPY/ "$$DEST/"; \
	echo ""; \
	echo "Files excluded: config.py, __pycache__/, sd/, settings.toml, boot_out.txt, ._*, .Trashes"; \
	echo -n "Press ENTER to proceed with sync (or Ctrl+C to cancel): "; \
	read CONFIRM; \
	echo "Syncing..."; \
	rsync -av --delete --checksum --modify-window=1 \
		--exclude='config.py' --exclude='__pycache__/' --exclude='sd/' \
		--exclude='settings.toml' --exclude='boot_out.txt' --exclude='.DS_Store' \
		--exclude='._*' --exclude='.Trashes' --exclude='.Trash-1000' --exclude='.fseventsd' --exclude='.fseventsd/fseventsd-uuid' \
		300x400/CIRCUITPY/ "$$DEST/"; \
	echo "Deployment complete!"

# Show activation instructions
activate:
	@if [ -f "venv/bin/activate" ]; then \
		echo "Virtual environment exists. To activate, run:"; \
		echo ""; \
		echo "source venv/bin/activate"; \
	else \
		echo "No virtual environment found."; \
		echo "Create one with: make venv"; \
	fi
