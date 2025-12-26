"""
Centralized CSV configuration for weather data processing
Single source of truth for all CSV file paths and scenarios
"""

import os

# Base directory for weather CSV files
CSV_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "misc")

# Available weather datasets
DATASETS = {
    "ny_2024": {
        "name": "New York 2024",
        "filename": "open-meteo-40.65N73.98W25m.csv",
        "city": "New York",
        "lat": 40.65,
        "lon": -73.98,
        "timezone": "America/New_York",
        "timezone_offset": -5,  # EST/EDT
    },
    "toronto_2025": {
        "name": "Toronto 2025",
        "filename": "open-meteo-43.70N79.40W165m.csv",
        "city": "Toronto",
        "lat": 43.70,
        "lon": -79.40,
        "timezone": "America/Toronto",
        "timezone_offset": -5,  # EST/EDT
    },
}

# Default dataset
DEFAULT_DATASET = "ny_2024"


def get_csv_path(dataset_name=None):
    """Get the full path to a CSV file for a given dataset"""
    if dataset_name is None:
        dataset_name = DEFAULT_DATASET

    if dataset_name not in DATASETS:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. Available: {list(DATASETS.keys())}"
        )

    dataset = DATASETS[dataset_name]
    csv_path = os.path.join(CSV_BASE_DIR, dataset["filename"])

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    return csv_path


def get_dataset_info(dataset_name=None):
    """Get complete dataset information"""
    if dataset_name is None:
        dataset_name = DEFAULT_DATASET

    if dataset_name not in DATASETS:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. Available: {list(DATASETS.keys())}"
        )

    dataset = DATASETS[dataset_name].copy()
    dataset["csv_path"] = get_csv_path(dataset_name)
    return dataset


def list_available_datasets():
    """List all available datasets with their basic info"""
    return {name: info["name"] for name, info in DATASETS.items()}


def find_dataset_for_csv_path(csv_path):
    """Find the dataset name for a given CSV file path"""
    csv_path = os.path.abspath(csv_path)

    for dataset_name, dataset in DATASETS.items():
        dataset_csv_path = os.path.abspath(get_csv_path(dataset_name))
        if csv_path == dataset_csv_path:
            return dataset_name

    return None


def validate_dataset_files():
    """Check which dataset CSV files exist"""
    results = {}
    for dataset_name in DATASETS.keys():
        try:
            csv_path = get_csv_path(dataset_name)
            results[dataset_name] = {
                "exists": True,
                "path": csv_path,
                "size": os.path.getsize(csv_path),
            }
        except FileNotFoundError:
            results[dataset_name] = {
                "exists": False,
                "path": None,
                "error": f"CSV file not found for {dataset_name}",
            }

    return results


if __name__ == "__main__":
    print("Weather CSV Configuration")
    print("=" * 30)
    print(f"CSV Base Directory: {CSV_BASE_DIR}")
    print(f"Default Dataset: {DEFAULT_DATASET}")
    print()

    print("Available Datasets:")
    for name, info in list_available_datasets().items():
        print(f"  {name}: {info}")
    print()

    print("File Validation:")
    validation = validate_dataset_files()
    for dataset_name, result in validation.items():
        if result["exists"]:
            size_kb = result["size"] / 1024
            print(f"  ✓ {dataset_name}: {result['path']} ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ {dataset_name}: {result['error']}")
