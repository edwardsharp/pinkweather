#!/usr/bin/env python3
"""
Simple script to inject CSV data into HTML template
Supports multiple datasets with automatic detection
"""

import csv
import glob
import json
import os
import sys


def load_csv_data(csv_path):
    """Load CSV data and return as list of dictionaries"""
    data = []

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

    return data


def detect_available_datasets(current_dir):
    """Detect available dataset CSV files"""
    datasets = {}

    # Look for narratives_*.csv files
    pattern = os.path.join(current_dir, "narratives_*.csv")
    csv_files = glob.glob(pattern)

    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        # Extract dataset name from filename (narratives_DATASET.csv)
        if filename.startswith("narratives_") and filename.endswith(".csv"):
            dataset_name = filename[len("narratives_") : -len(".csv")]

            # Map internal names to display names and dataset keys
            mapping = {
                "nyc": {"name": "New York 2024", "dataset_key": "ny_2024"},
                "toronto": {"name": "Toronto 2025", "dataset_key": "toronto_2025"},
            }

            if dataset_name in mapping:
                display_name = mapping[dataset_name]["name"]
                dataset_key = mapping[dataset_name]["dataset_key"]
            else:
                display_name = dataset_name.title()
                dataset_key = dataset_name

            datasets[dataset_key] = {
                "name": display_name,
                "csv_file": filename,
                "csv_path": csv_file,
            }

    return datasets


def inject_data_into_template(template_path, datasets, default_dataset, output_path):
    """Replace placeholders in template with actual data and dataset info"""

    # Read template
    with open(template_path, "r") as f:
        template_content = f.read()

    # Load data for ALL datasets
    all_datasets_data = {}
    for dataset_key, dataset_info in datasets.items():
        dataset_data = load_csv_data(dataset_info["csv_path"])
        all_datasets_data[dataset_key] = dataset_data

    # Load data for default dataset
    default_data = all_datasets_data[default_dataset]

    # Convert data to JavaScript
    js_data = json.dumps(default_data, indent=2)
    js_datasets = json.dumps(datasets, indent=2)
    js_all_data = json.dumps(all_datasets_data, indent=2)

    # Replace placeholders
    output_content = template_content.replace(
        "const narrativeData = [];", f"const narrativeData = {js_data};"
    )

    # Add datasets info (we'll add this placeholder to template)
    datasets_placeholder = "const availableDatasets = {};"
    output_content = output_content.replace(
        datasets_placeholder, f"const availableDatasets = {js_datasets};"
    )

    # Add all datasets data
    all_data_placeholder = "const allDatasetsData = {};"
    output_content = output_content.replace(
        all_data_placeholder, f"const allDatasetsData = {js_all_data};"
    )

    # Add current dataset info
    current_dataset_placeholder = 'let currentDataset = "";'
    output_content = output_content.replace(
        current_dataset_placeholder, f'let currentDataset = "{default_dataset}";'
    )

    # Write output
    with open(output_path, "w") as f:
        f.write(output_content)


def main():
    # Use fixed paths in same directory as script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, "viewer.html")
    template_path = os.path.join(current_dir, "template.html")

    # Check if template exists
    if not os.path.exists(template_path):
        print(f"Error: template.html not found")
        sys.exit(1)

    # Detect available datasets
    print("Detecting available datasets...")
    datasets = detect_available_datasets(current_dir)

    if not datasets:
        print("Error: No dataset CSV files found (narratives_*.csv)")
        print("Run generate_historical_data.py first")
        sys.exit(1)

    # Use first available dataset as default, prefer NYC
    default_dataset = "ny_2024" if "ny_2024" in datasets else list(datasets.keys())[0]

    print(f"Available datasets:")
    for dataset_key, dataset_info in datasets.items():
        marker = " (default)" if dataset_key == default_dataset else ""
        print(f"  {dataset_key}: {dataset_info['name']}{marker}")

    # Load data for all datasets
    total_records = 0
    for dataset_key, dataset_info in datasets.items():
        dataset_data = load_csv_data(dataset_info["csv_path"])
        total_records += len(dataset_data)
        print(f"Loaded {len(dataset_data)} records from {dataset_info['name']}")

    default_data = load_csv_data(datasets[default_dataset]["csv_path"])

    # Inject data
    print(f"Injecting data into template...")
    inject_data_into_template(template_path, datasets, default_dataset, output_path)

    print(f"Generated viewer.html with {len(datasets)} datasets available")
    print(f"Total records across all datasets: {total_records}")
    print(
        f"Default dataset: {datasets[default_dataset]['name']} ({len(default_data)} records)"
    )


if __name__ == "__main__":
    main()
