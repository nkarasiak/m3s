#!/usr/bin/env python
"""Analyze A5 test failures and categorize them."""

import subprocess
import re

def run_test(test_name):
    """Run a single test and capture output."""
    cmd = f"pytest tests/test_a5.py::{test_name} -v --tb=short"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

# List of all failing tests
failing_tests = [
    "TestA5Grid::test_init_invalid_precision",
    "TestA5Grid::test_get_cell_from_point_various_locations",
    "TestA5Grid::test_get_cell_from_identifier_invalid",
    "TestA5Grid::test_neighbors",
    "TestA5Grid::test_coordinate_transformations",
    "TestA5Grid::test_pentagon_vertex_generation",
    "TestA5Grid::test_cell_encoding_decoding",
    "TestA5Grid::test_polygon_validity",
    "TestA5CoordinateTransformations::test_latlon_to_xyz_conversions",
    "TestA5CoordinateTransformations::test_xyz_coordinate_properties",
    "TestA5M3SIntegration::test_a5_error_handling",
    "TestA5API::test_cell_to_lonlat",
    "TestA5API::test_cell_to_parent_invalid_resolution",
    "TestA5API::test_cell_to_children",
    "TestA5API::test_cell_to_children_invalid_resolution",
    "TestA5API::test_cell_area",
    "TestA5API::test_roundtrip_conversions",
]

categories = {
    "Error Message Mismatch": [],
    "Palmer Import Required": [],
    "Pole/Edge Case": [],
    "Expected Value Mismatch": [],
    "Missing Method/Attribute": [],
    "API Signature": [],
}

print("Analyzing A5 Test Failures")
print("=" * 80)

for test in failing_tests:
    print(f"\nAnalyzing {test}...")
    output = run_test(test)

    # Categorize based on error patterns
    if "Regex pattern did not match" in output or "match=" in output:
        categories["Error Message Mismatch"].append((test, output))
    elif "ImportError" in output or "a5 as palmer" in output:
        categories["Palmer Import Required"].append((test, output))
    elif "pole" in output.lower() or "90.0" in output or "-90.0" in output:
        categories["Pole/Edge Case"].append((test, output))
    elif "assert" in output and ("==" in output or "!=" in output):
        categories["Expected Value Mismatch"].append((test, output))
    elif "AttributeError" in output or "has no attribute" in output:
        categories["Missing Method/Attribute"].append((test, output))
    elif "TypeError" in output and "argument" in output:
        categories["API Signature"].append((test, output))
    else:
        categories["Expected Value Mismatch"].append((test, output))

# Print summary
print("\n" + "=" * 80)
print("FAILURE CATEGORIES")
print("=" * 80)

for category, tests in categories.items():
    if tests:
        print(f"\n{category}: {len(tests)} tests")
        for test, _ in tests:
            print(f"  - {test}")

print(f"\nTotal failures: {sum(len(tests) for tests in categories.values())}")
