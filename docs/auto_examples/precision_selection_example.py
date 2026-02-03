"""
Precision Selection Strategies - Complete Guide
===============================================

This example demonstrates all 5 intelligent precision selection strategies
in M3S v0.6.0+, helping you choose the optimal precision level for any use case.
"""

import pandas as pd

from m3s import GridBuilder, PrecisionSelector

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 120)

print("=" * 80)
print("M3S Intelligent Precision Selection - All 5 Strategies")
print("=" * 80)
print()

# Initialize selector for H3 grid system
selector = PrecisionSelector("h3")

# ============================================================================
# Strategy 1: Area-Based Selection
# ============================================================================

print("=" * 80)
print("Strategy 1: Area-Based Selection")
print("=" * 80)
print("\nUse when: You know the desired cell size in km²")
print("Examples: 'I need cells around 10 km²', 'Show me 100 hectare cells'")
print()

# Find precision for different target areas
target_areas = [1000.0, 100.0, 10.0, 1.0, 0.1]

print("Finding precision for various target areas:")
print("-" * 80)

for target_area in target_areas:
    rec = selector.for_area(target_area_km2=target_area, tolerance=0.3)

    deviation = (
        abs(rec.actual_area_km2 - target_area) / target_area * 100
        if target_area > 0
        else 0
    )

    print(
        f"Target: {target_area:8.1f} km² → Precision: {rec.precision:2d} "
        f"(Actual: {rec.actual_area_km2:8.3f} km², Deviation: {deviation:5.1f}%, "
        f"Confidence: {rec.confidence:.0%})"
    )

print()

# ============================================================================
# Strategy 2: Count-Based Selection
# ============================================================================

print("=" * 80)
print("Strategy 2: Count-Based Selection")
print("=" * 80)
print("\nUse when: You want a specific number of cells in a region")
print("Examples: 'Split this city into ~100 cells', 'I want about 1000 cells here'")
print()

# Manhattan bounding box
manhattan_bounds = (40.70, -74.05, 40.85, -73.90)

target_counts = [10, 50, 100, 500]

print("Finding precision for Manhattan area with different target counts:")
print("-" * 80)

for target_count in target_counts:
    rec = selector.for_region_count(
        bounds=manhattan_bounds, target_count=target_count, tolerance=0.4
    )

    deviation = (
        abs(rec.actual_cell_count - target_count) / target_count * 100
        if target_count > 0
        else 0
    )

    print(
        f"Target: {target_count:4d} cells → Precision: {rec.precision:2d} "
        f"(Actual: ~{rec.actual_cell_count:4d} cells, Deviation: {deviation:5.1f}%, "
        f"Confidence: {rec.confidence:.0%})"
    )

print()

# ============================================================================
# Strategy 3: Use-Case Based Selection
# ============================================================================

print("=" * 80)
print("Strategy 3: Use-Case Based Selection (Curated Presets)")
print("=" * 80)
print("\nUse when: You have a common spatial analysis use case")
print("Examples: Analyzing neighborhoods, city planning, country-level analysis")
print()

use_cases = [
    "global",
    "continental",
    "country",
    "region",
    "city",
    "neighborhood",
    "street",
    "building",
]

print("H3 precision recommendations for common use cases:")
print("-" * 80)

for use_case in use_cases:
    rec = selector.for_use_case(use_case)
    print(
        f"{use_case:15s} → Precision: {rec.precision:2d} "
        f"(Avg area: {rec.actual_area_km2:12.3f} km², Confidence: {rec.confidence:.0%})"
    )

print()

# Compare across grid systems
print("Same use case ('city') across different grid systems:")
print("-" * 80)

systems = ["geohash", "h3", "s2", "quadkey"]
city_recs = []

for system in systems:
    sel = PrecisionSelector(system)
    rec = sel.for_use_case("city")
    city_recs.append(
        {
            "system": system,
            "precision": rec.precision,
            "area_km2": rec.actual_area_km2,
            "confidence": rec.confidence,
        }
    )

df = pd.DataFrame(city_recs)
print(df.to_string(index=False))
print()

# ============================================================================
# Strategy 4: Distance-Based Selection
# ============================================================================

print("=" * 80)
print("Strategy 4: Distance-Based Selection")
print("=" * 80)
print("\nUse when: You care about cell edge length rather than area")
print("Examples: 'Cells with ~100m edges', 'I need 1km grid spacing'")
print()

target_distances = [10000, 5000, 1000, 500, 100, 50]  # meters

print("Finding precision for various target edge lengths:")
print("-" * 80)

for target_dist in target_distances:
    rec = selector.for_distance(edge_length_m=target_dist, tolerance=0.3)

    deviation = (
        abs(rec.edge_length_m - target_dist) / target_dist * 100
        if target_dist > 0
        else 0
    )

    print(
        f"Target: {target_dist:6d} m → Precision: {rec.precision:2d} "
        f"(Actual: ~{rec.edge_length_m:6.1f} m, Deviation: {deviation:5.1f}%, "
        f"Confidence: {rec.confidence:.0%})"
    )

print()

# ============================================================================
# Strategy 5: Performance-Based Selection
# ============================================================================

print("=" * 80)
print("Strategy 5: Performance-Based Selection")
print("=" * 80)
print("\nUse when: You need to balance precision vs computational cost")
print("Examples: Real-time applications, limited compute budget, large regions")
print()

# Different operation types with time budgets
scenarios = [
    ("point_query", 10.0, 1000.0),  # Fast operation, large region
    ("intersect", 100.0, 500.0),  # Medium operation, medium region
    ("conversion", 200.0, 100.0),  # Expensive operation, small region
]

print("Performance-optimized precision for different scenarios:")
print("-" * 80)

for op_type, time_budget, region_size in scenarios:
    rec = selector.for_performance(
        operation_type=op_type, time_budget_ms=time_budget, region_size_km2=region_size
    )

    print(
        f"{op_type:15s} (budget: {time_budget:5.0f}ms, region: {region_size:6.0f} km²)"
    )
    print(
        f"  → Precision: {rec.precision:2d}, "
        f"Est. cells: {rec.metadata['estimated_cells']:5d}, "
        f"Est. time: {rec.metadata['estimated_time_ms']:5.1f} ms"
    )

print()

# ============================================================================
# Practical Example: Combining Strategies
# ============================================================================

print("=" * 80)
print("Practical Example: Combining Strategies in Real Workflow")
print("=" * 80)
print()

print("Scenario: Analyzing neighborhoods in San Francisco")
print("-" * 80)

# Try multiple strategies and compare
sf_bounds = (37.70, -122.52, 37.82, -122.35)

print("\n1. Use-case based approach:")
rec1 = selector.for_use_case("neighborhood")
print(f"   Precision: {rec1.precision}, Confidence: {rec1.confidence:.0%}")
print(f"   {rec1.explanation}")

print("\n2. Area-based approach (target 0.5 km² cells):")
rec2 = selector.for_area(target_area_km2=0.5)
print(f"   Precision: {rec2.precision}, Confidence: {rec2.confidence:.0%}")
print(f"   Actual area: {rec2.actual_area_km2:.3f} km²")

print("\n3. Count-based approach (target 200 cells):")
rec3 = selector.for_region_count(bounds=sf_bounds, target_count=200)
print(f"   Precision: {rec3.precision}, Confidence: {rec3.confidence:.0%}")
print(f"   Estimated cells: {rec3.actual_cell_count}")

print("\n4. Distance-based approach (target 500m edges):")
rec4 = selector.for_distance(edge_length_m=500)
print(f"   Precision: {rec4.precision}, Confidence: {rec4.confidence:.0%}")
print(f"   Actual edge length: {rec4.edge_length_m:.1f} m")

print("\nComparing all recommendations:")
print("-" * 80)
comparison = pd.DataFrame(
    [
        {
            "Strategy": "Use-case",
            "Precision": rec1.precision,
            "Confidence": f"{rec1.confidence:.0%}",
            "Area (km²)": f"{rec1.actual_area_km2:.3f}",
        },
        {
            "Strategy": "Area-based",
            "Precision": rec2.precision,
            "Confidence": f"{rec2.confidence:.0%}",
            "Area (km²)": f"{rec2.actual_area_km2:.3f}",
        },
        {
            "Strategy": "Count-based",
            "Precision": rec3.precision,
            "Confidence": f"{rec3.confidence:.0%}",
            "Area (km²)": f"{rec3.metadata.get('region_area_km2', 0) / rec3.actual_cell_count:.3f}",
        },
        {
            "Strategy": "Distance-based",
            "Precision": rec4.precision,
            "Confidence": f"{rec4.confidence:.0%}",
            "Area (km²)": "~" + f"{(rec4.edge_length_m/1000)**2:.3f}",
        },
    ]
)
print(comparison.to_string(index=False))

print("\n5. Using the recommendation in a query:")
print("-" * 80)

# Use the highest-confidence recommendation
best_rec = max([rec1, rec2, rec3, rec4], key=lambda r: r.confidence)

result = (
    GridBuilder.for_system("h3")
    .with_auto_precision(best_rec)
    .in_bbox(37.75, -122.45, 37.80, -122.40)  # Small SF area
    .limit(10)
    .execute()
)

print(f"\nExecuted query with precision {best_rec.precision}")
print(f"Found {len(result)} cells (limited to 10 for display)")
print(
    f"Average cell area: {sum(c.area_km2 for c in result.many) / len(result):.3f} km²"
)

# Display cells
print("\nSample cells:")
for cell in result.many[:5]:
    print(f"  {cell.identifier} - {cell.area_km2:.3f} km²")

print()
print("=" * 80)
print("Summary: Choosing the Right Strategy")
print("=" * 80)
print(
    """
1. Use-Case Based (Strategy 3):
   → Best for: Standard spatial analysis tasks
   → Pros: High confidence, battle-tested presets
   → Cons: Less control over exact cell size

2. Area-Based (Strategy 1):
   → Best for: When cell size matters (e.g., land parcels, service areas)
   → Pros: Precise control over cell area
   → Cons: May not account for cell count in region

3. Count-Based (Strategy 2):
   → Best for: When you need specific number of divisions
   → Pros: Predictable cell count for budgeting/planning
   → Cons: Cell sizes may vary across region

4. Distance-Based (Strategy 4):
   → Best for: Grid-like applications, routing, proximity analysis
   → Pros: Intuitive edge length specification
   → Cons: Approximation for non-square cells

5. Performance-Based (Strategy 5):
   → Best for: Real-time apps, constrained compute environments
   → Pros: Balances detail vs speed
   → Cons: May sacrifice precision for performance

General guidance:
- Start with use-case presets (Strategy 3) for common tasks
- Use area/distance (1/4) when you have specific size requirements
- Use count-based (2) for bounded cell count needs
- Use performance-based (5) when speed is critical
"""
)
