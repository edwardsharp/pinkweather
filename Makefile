# Makefile for pinkweather project
# Provides easy commands for setup, development, and deployment

.PHONY: help install server preview deploy deploy-sd serial print-new-config activate generate-dataset

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install basic dependencies"
	@echo "  server       - Start development web server"
	@echo "  preview      - Generate weather display preview"
	@echo "  deploy       - Deploy code to CIRCUITPY device"
	@echo "  deploy-sd    - Copy icons and scaffold directory structure onto the SD card"
	@echo "  serial       - Attach a serial console to the connected Pico (115200 baud)"
	@echo "  print-new-config - Print new config.py settings to copy-paste into your device"
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

# Deploy icons and scaffold SD card directory structure
# This is meant to be run from the user's own computer after inserting the SD card.
# Override the auto-detected path with: make deploy-sd SD_PATH=/path/to/sd
deploy-sd:
	@echo "=== pinkweather SD card setup ==="
	@echo ""
	@SD_PATH=""; \
	if [ -n "$(SD_PATH)" ]; then \
		SD_PATH="$(SD_PATH)"; \
		echo "Using provided path: $$SD_PATH"; \
	else \
		if [ -d "/Volumes/CIRCUITPY" ]; then \
			echo "Note: /Volumes/CIRCUITPY looks like the device flash, not the SD card."; \
		fi; \
		for label in PINKWEATHER SD; do \
			if [ -d "/Volumes/$$label" ]; then SD_PATH="/Volumes/$$label"; break; fi; \
			for base in /media /run/media; do \
				if [ -d "$$base" ]; then \
					found=$$(find "$$base" -maxdepth 2 -mindepth 1 -name "$$label" -type d 2>/dev/null | head -1); \
					if [ -n "$$found" ]; then SD_PATH="$$found"; break; fi; \
				fi; \
			done; \
			if [ -n "$$SD_PATH" ]; then break; fi; \
		done; \
		if [ -z "$$SD_PATH" ] && [ -d "/Volumes/NO NAME" ]; then \
			SD_PATH="/Volumes/NO NAME"; \
		fi; \
		if [ -z "$$SD_PATH" ]; then \
			found=$$(find /media /run/media -maxdepth 2 -mindepth 1 -name "NO NAME" -type d 2>/dev/null | head -1); \
			if [ -n "$$found" ]; then SD_PATH="$$found"; fi; \
		fi; \
		if [ -z "$$SD_PATH" ]; then \
			echo "Could not auto-detect SD card. Candidates:"; \
			if [ -d "/Volumes" ]; then ls /Volumes/ 2>/dev/null; fi; \
			for base in /media /run/media; do \
				if [ -d "$$base" ]; then \
					find "$$base" -maxdepth 2 -mindepth 2 -type d 2>/dev/null; \
				fi; \
			done; \
			echo ""; \
			printf "Enter the full path to your SD card: "; \
			read SD_PATH; \
		fi; \
	fi; \
	if [ -z "$$SD_PATH" ]; then \
		echo "Error: No SD card path provided."; \
		exit 1; \
	fi; \
	if [ ! -d "$$SD_PATH" ]; then \
		echo "Error: Directory '$$SD_PATH' does not exist."; \
		exit 1; \
	fi; \
	echo ""; \
	echo "SD card path: $$SD_PATH"; \
	echo ""; \
	printf "Is this the correct SD card? [y/N] "; \
	read CONFIRM; \
	case "$$CONFIRM" in \
		[yY]|[yY][eE][sS]) ;; \
		*) echo "Aborted."; exit 1 ;; \
	esac; \
	echo ""; \
	echo "--- Scaffolding directory structure ---"; \
	mkdir -p "$$SD_PATH/bmp"; \
	echo "  created: bmp/"; \
	echo ""; \
	echo "--- Copying weather icons (iconz/bmp/ -> SD:bmp/) ---"; \
	echo "  Source: iconz/bmp/ ($(shell ls iconz/bmp/ 2>/dev/null | wc -l | tr -d ' ') files)"; \
	echo ""; \
	rsync -av --checksum --modify-window=1 \
		--exclude='.DS_Store' --exclude='._*' \
		iconz/bmp/ "$$SD_PATH/bmp/"; \
	echo ""; \
	echo "=== SD card setup complete! ==="; \
	echo ""; \
	echo "eject the SD card (safely!) and put it back into pinkweather";
# Attach a serial console to the connected Pico 2W (115200 baud)
# Override auto-detection with: make serial PORT=/dev/cu.usbmodemXXXX
serial:
	@echo "=== pinkweather serial console ==="
	@echo ""
	@PORT=""; \
	PORTS=""; \
	if [ -n "$(PORT)" ]; then \
		PORT="$(PORT)"; \
		echo "Using provided port: $$PORT"; \
	else \
		if [ "$$(uname)" = "Darwin" ]; then \
			PORTS=$$(ls /dev/cu.usbmodem* 2>/dev/null); \
		else \
			PORTS=$$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null); \
		fi; \
		if [ -z "$$PORTS" ]; then \
			echo "No serial port found. Check:"; \
			echo "  - USB cable is connected and the Pico is powered"; \
			echo "  - CircuitPython is installed (CIRCUITPY drive should appear)"; \
			echo "  - Try: make serial PORT=/dev/cu.usbmodemXXXX"; \
			exit 1; \
		fi; \
		COUNT=$$(echo "$$PORTS" | wc -l | tr -d ' '); \
		if [ "$$COUNT" -eq 1 ]; then \
			PORT="$$PORTS"; \
			echo "Found: $$PORT"; \
		else \
			echo "Multiple serial ports found:"; \
			echo "$$PORTS"; \
			echo ""; \
			printf "Enter the full port path: "; \
			read PORT; \
		fi; \
	fi; \
	if [ ! -e "$$PORT" ]; then \
		echo "Error: $$PORT does not exist"; \
		exit 1; \
	fi; \
	echo ""; \
	if command -v screen >/dev/null 2>&1; then \
		echo "Connecting via screen  |  to exit: Ctrl+A then K then Y"; \
		echo ""; \
		screen "$$PORT" 115200; \
	elif command -v picocom >/dev/null 2>&1; then \
		echo "Connecting via picocom  |  to exit: Ctrl+A then Ctrl+X"; \
		echo ""; \
		picocom -b 115200 "$$PORT"; \
	elif command -v tio >/dev/null 2>&1; then \
		echo "Connecting via tio  |  to exit: Ctrl+T then Q"; \
		echo ""; \
		tio -b 115200 "$$PORT"; \
	else \
		echo "No serial terminal found. Install one:"; \
		echo "  macOS:  brew install picocom"; \
		echo "  Linux:  sudo apt install screen"; \
		exit 1; \
	fi

# Print new config settings for users updating an existing config.py
print-new-config:
	@echo ""
	@echo "=================================================================="
	@echo " pinkweather: new config.py settings"
	@echo "=================================================================="
	@echo ""
	@echo "Add these to your config.py on the CIRCUITPY device if they are"
	@echo "missing. All values shown are the defaults - safe to add as-is."
	@echo "Your existing settings will not be affected."
	@echo ""
	@echo "------------------------------------------------------------------"
	@echo ""
	@printf '# WiFi Advanced Configuration\n'
	@printf '# Set to your router channel (1-13) for faster connect, or 0 to scan all.\n'
	@printf 'WIFI_CHANNEL = 0\n'
	@printf '\n'
	@printf '# Seconds to wait for WiFi. Increase (e.g. 30) if DHCP is slow.\n'
	@printf 'WIFI_CONNECT_TIMEOUT = 20\n'
	@printf '\n'
	@printf '# Static IP (leave as None to use DHCP).\n'
	@printf '# Set all four to skip DHCP entirely - helps with lease-pool issues.\n'
	@printf '#   WIFI_STATIC_IP      = "192.168.1.100"\n'
	@printf '#   WIFI_STATIC_NETMASK = "255.255.255.0"\n'
	@printf '#   WIFI_STATIC_GATEWAY = "192.168.1.1"\n'
	@printf '#   WIFI_STATIC_DNS     = "8.8.8.8"\n'
	@printf 'WIFI_STATIC_IP      = None\n'
	@printf 'WIFI_STATIC_NETMASK = None\n'
	@printf 'WIFI_STATIC_GATEWAY = None\n'
	@printf 'WIFI_STATIC_DNS     = None\n'
	@printf '\n'
	@printf '# Weather cache: show last known weather for up to this many\n'
	@printf '# consecutive failed hourly cycles before showing the error screen.\n'
	@printf '# Set to 0 to disable. Each cycle is roughly 1 hour.\n'
	@printf 'WEATHER_CACHE_MAX_CYCLES = 6\n'
	@echo ""
	@echo "------------------------------------------------------------------"
	@echo ""
	@echo "To edit config.py: connect pinkweather via USB, then open"
	@echo "/Volumes/CIRCUITPY/config.py (macOS) or /media/.../config.py (Linux)."
	@echo ""

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
