#!/usr/bin/env python3
"""
Simple main entry point for PinkWeather preview system.

This provides the core functions that the Makefile can call:
- Batch image generation
- Batch narrative generation
- Web server
- Testing functions

Usage:
    python main.py batch-images <csv_file> <output_dir> [--max-count N]
    python main.py batch-narratives <csv_file> <output_file> [--max-count N]
    python main.py serve [--host HOST] [--port PORT]
    python main.py test-render [--source SOURCE] [--output OUTPUT]
    python main.py test-api
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path to import preview module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from batch.generator import (
    generate_complete_dataset,
    generate_images,
    generate_narratives,
)
from shared.testing import test_api_integration, test_single_render
from web.server import run_server


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="PinkWeather Preview System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Batch images command
    images_parser = subparsers.add_parser(
        "batch-images", help="Generate batch PNG images"
    )
    images_parser.add_argument("csv_file", help="Input CSV file path")
    images_parser.add_argument(
        "output_dir", nargs="?", help="Output directory for images (optional)"
    )
    images_parser.add_argument("--max-count", type=int, help="Maximum number of images")

    # Batch narratives command
    narratives_parser = subparsers.add_parser(
        "batch-narratives", help="Generate narratives CSV"
    )
    narratives_parser.add_argument("csv_file", help="Input CSV file path")
    narratives_parser.add_argument(
        "output_file", nargs="?", help="Output CSV file path (optional)"
    )
    narratives_parser.add_argument(
        "--max-count", type=int, help="Maximum number of records"
    )

    # Complete dataset command
    complete_parser = subparsers.add_parser(
        "complete", help="Generate complete dataset (narratives + images + HTML)"
    )
    complete_parser.add_argument("csv_file", help="Input CSV file path")
    complete_parser.add_argument(
        "--max-count", type=int, help="Maximum number of records"
    )

    # Web server command
    serve_parser = subparsers.add_parser("serve", help="Start web server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=5001, help="Port to serve on")
    serve_parser.add_argument(
        "--no-debug", action="store_true", help="Disable debug mode"
    )

    # Test render command
    render_parser = subparsers.add_parser("test-render", help="Test single render")
    render_parser.add_argument(
        "--source", default="live", help="Weather source: 'live' or CSV file"
    )
    render_parser.add_argument("--output", help="Output PNG file path")

    # Test API command
    subparsers.add_parser("test-api", help="Run API integration tests")

    args = parser.parse_args()

    try:
        if args.command == "batch-images":
            print(f"🖼️  Generating batch images...")
            print(f"   Input: {args.csv_file}")
            print(f"   Output: {args.output_dir}")
            if args.max_count:
                print(f"   Max count: {args.max_count}")

            success = generate_images(args.csv_file, args.output_dir, args.max_count)
            return 0 if success else 1

        elif args.command == "batch-narratives":
            print(f"📝 Generating narratives CSV...")
            print(f"   Input: {args.csv_file}")
            print(f"   Output: {args.output_file}")
            if args.max_count:
                print(f"   Max count: {args.max_count}")

            success = generate_narratives(
                args.csv_file, args.output_file, args.max_count
            )
            return 0 if success else 1

        elif args.command == "serve":
            print(f"🌐 Starting web server...")
            print(f"   Host: {args.host}")
            print(f"   Port: {args.port}")
            print(f"   Debug: {not args.no_debug}")

            run_server(args.port, args.host)
            return 0

        elif args.command == "test-render":
            print(f"🎨 Testing single render...")
            print(f"   Source: {args.source}")
            if args.output:
                print(f"   Output: {args.output}")

            success = test_single_render(args.source, args.output)
            return 0 if success else 1

        elif args.command == "complete":
            print(f"🎯 Generating complete dataset...")
            print(f"   Input: {args.csv_file}")
            if args.max_count:
                print(f"   Max count: {args.max_count}")

            success = generate_complete_dataset(args.csv_file, args.max_count)
            return 0 if success else 1

        elif args.command == "test-api":
            print(f"🧪 Running API integration tests...")

            success = test_api_integration()
            return 0 if success else 1

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled")
        return 1
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
