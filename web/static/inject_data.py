#!/usr/bin/env python3
"""
Simple script to inject CSV data into HTML template
"""

import csv
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


def inject_data_into_template(template_path, data, output_path):
    """Replace DATA_PLACEHOLDER in template with actual data"""

    # Read template
    with open(template_path, "r") as f:
        template_content = f.read()

    # Convert data to JavaScript
    js_data = json.dumps(data, indent=2)

    # Replace placeholder
    output_content = template_content.replace(
        "const narrativeData = [];", f"const narrativeData = {js_data};"
    )

    # Write output
    with open(output_path, "w") as f:
        f.write(output_content)


def main():
    if len(sys.argv) < 3:
        print("Usage: python inject_data.py <csv_file> <output_html> [template.html]")
        print("Example: python inject_data.py narratives.csv viewer.html")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_path = sys.argv[2]
    template_path = sys.argv[3] if len(sys.argv) > 3 else "template.html"

    # Check if files exist
    if not os.path.exists(csv_path):
        print(f"Error: CSV file {csv_path} not found")
        sys.exit(1)

    if not os.path.exists(template_path):
        print(f"Error: Template file {template_path} not found")
        sys.exit(1)

    # Load data
    print(f"Loading data from {csv_path}...")
    data = load_csv_data(csv_path)
    print(f"Loaded {len(data)} records")

    # Inject data
    print(f"Injecting data into template {template_path}...")
    inject_data_into_template(template_path, data, output_path)

    print(f"Generated {output_path} with {len(data)} records")


if __name__ == "__main__":
    main()
