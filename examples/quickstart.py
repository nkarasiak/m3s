"""
Quickstart Guide for M3S v0.6.0+ Modern API
==========================================

This example demonstrates the new fluent interface and intelligent
precision selection introduced in M3S v0.6.0.
"""

from m3s import GridBuilder, PrecisionSelector

# ============================================================================
# Example 1: Basic Point Query with Explicit Precision
# ============================================================================

print("=" * 70)
print("Example 1: Basic Point Query")
print("=" * 70)

# Query a single point using H3 grid at precision 7
result = (
    GridBuilder.for_system("h3").with_precision(7).at_point(40.7128, -74.0060).execute()
)

# Access single cell result
cell = result.single
print(f"Cell ID: {cell.identifier}")
print(f"Area: {cell.area_km2:.2f} km²")
print(f"Precision: {cell.precision}")
print()

# ============================================================================
# Example 2: Intelligent Precision Selection
# ============================================================================

print("=" * 70)
print("Example 2: Intelligent Precision Selection")
print("=" * 70)

# Create precision selector for H3 grid
selector = PrecisionSelector("h3")

# Strategy 1: Use-case based (most common)
rec = selector.for_use_case("neighborhood")
print("\nUse-case 'neighborhood' recommendation:")
print(f"  Precision: {rec.precision}")
print(f"  Confidence: {rec.confidence:.0%}")
print(f"  {rec.explanation}")

# Strategy 2: Area-based
rec = selector.for_area(target_area_km2=10.0)
print("\nArea-based (target 10 km²) recommendation:")
print(f"  Precision: {rec.precision}")
print(f"  Actual area: {rec.actual_area_km2:.2f} km²")
print(f"  Confidence: {rec.confidence:.0%}")

# Strategy 3: Distance-based
rec = selector.for_distance(edge_length_m=500.0)
print("\nDistance-based (target 500m edges) recommendation:")
print(f"  Precision: {rec.precision}")
print(f"  Actual edge length: {rec.edge_length_m:.1f} m")
print(f"  Confidence: {rec.confidence:.0%}")
print()

# ============================================================================
# Example 3: Fluent Workflow with Auto-Precision
# ============================================================================

print("=" * 70)
print("Example 3: Complete Fluent Workflow")
print("=" * 70)

# Intelligent precision + point query + neighbors
selector = PrecisionSelector("geohash")
rec = selector.for_use_case("city")

result = (
    GridBuilder.for_system("geohash")
    .with_auto_precision(rec)
    .at_point(51.5074, -0.1278)  # London
    .find_neighbors(depth=1)
    .execute()
)

print(f"\nFound {len(result)} cells (original + neighbors)")
print(f"Using precision: {rec.precision} (confidence: {rec.confidence:.0%})")
print("\nFirst few cells:")
for cell in result.many[:5]:
    print(f"  {cell.identifier} - {cell.area_km2:.2f} km²")
print()

# ============================================================================
# Example 4: Batch Operations
# ============================================================================

print("=" * 70)
print("Example 4: Batch Point Queries")
print("=" * 70)

# Query multiple cities simultaneously
cities = [
    (40.7128, -74.0060),  # New York
    (34.0522, -118.2437),  # Los Angeles
    (51.5074, -0.1278),  # London
    (35.6762, 139.6503),  # Tokyo
]

result = GridBuilder.for_system("h3").with_precision(7).at_points(cities).execute()

print(f"\nQueried {len(result)} cities:")
for i, cell in enumerate(result.many):
    city_names = ["New York", "Los Angeles", "London", "Tokyo"]
    print(f"  {city_names[i]}: {cell.identifier}")
print()

# ============================================================================
# Example 5: Regional Analysis with Filtering
# ============================================================================

print("=" * 70)
print("Example 5: Regional Analysis with Filtering")
print("=" * 70)

# Get cells in Manhattan bounding box, filter by size
result = (
    GridBuilder.for_system("geohash")
    .with_precision(6)
    .in_bbox(40.7, -74.05, 40.85, -73.9)  # Manhattan area
    .filter(lambda cell: cell.area_km2 < 1.0)  # Only smaller cells
    .limit(10)  # Limit for display
    .execute()
)

print(f"\nFound {len(result)} cells in Manhattan (filtered, limited to 10)")
print(f"Average area: {sum(c.area_km2 for c in result.many) / len(result):.3f} km²")
print()

# ============================================================================
# Example 6: Convert to GeoDataFrame
# ============================================================================

print("=" * 70)
print("Example 6: Export to GeoPandas")
print("=" * 70)

result = (
    GridBuilder.for_system("s2")
    .with_precision(12)
    .in_bbox(40.75, -74.0, 40.77, -73.97)
    .limit(5)
    .execute()
)

gdf = result.to_geodataframe()
print("\nGeoDataFrame columns:", list(gdf.columns))
print(f"Shape: {gdf.shape}")
print("\nFirst row:")
print(gdf.head(1))
print()

# ============================================================================
# Example 7: Multi-Grid Comparison
# ============================================================================

print("=" * 70)
print("Example 7: Multi-Grid Comparison")
print("=" * 70)

from m3s import MultiGridComparator

# Compare same location across different grid systems
comparator = MultiGridComparator([("geohash", 5), ("h3", 7), ("s2", 10)])

results = comparator.query_all(40.7128, -74.0060)

print("\nSame point in different grid systems:")
for system, cell in results.items():
    print(f"  {system:10s}: {cell.identifier:20s} ({cell.area_km2:.2f} km²)")

# Compare coverage for a region
coverage_df = comparator.compare_coverage((40.7, -74.1, 40.8, -73.9))
print("\nRegional coverage comparison:")
print(coverage_df[["system", "precision", "cell_count", "avg_cell_size_km2"]])
print()

# ============================================================================
# Example 8: Performance-Based Precision
# ============================================================================

print("=" * 70)
print("Example 8: Performance-Based Precision Selection")
print("=" * 70)

selector = PrecisionSelector("h3")

# Balance precision vs computational cost
rec = selector.for_performance(
    operation_type="intersect",
    time_budget_ms=50.0,  # 50ms budget
    region_size_km2=100.0,  # 100 km² region
)

print("\nPerformance-optimized precision:")
print(f"  Precision: {rec.precision}")
print(f"  Estimated time: {rec.metadata['estimated_time_ms']:.1f} ms")
print(f"  Estimated cells: {rec.metadata['estimated_cells']}")
print(f"  Confidence: {rec.confidence:.0%}")
print()

print("=" * 70)
print("Quickstart Complete!")
print("=" * 70)
print("\nKey Takeaways:")
print("  1. Use GridBuilder for all queries (replaces direct grid class usage)")
print("  2. Use PrecisionSelector for intelligent precision selection")
print("  3. Method chaining enables elegant, readable workflows")
print("  4. Type-safe results with .single, .many, .to_geodataframe()")
print("  5. All grid systems use unified 'precision' parameter")
