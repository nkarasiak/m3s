"""
A5 Pentagonal Grid System Example.
===================================

This example demonstrates the A5 pentagonal grid system, a Discrete Global Grid System (DGGS)
that divides the Earth's surface into pentagonal cells derived from a dodecahedral projection.

A5 provides:
- Minimal geometric distortion across the globe
- Uniform cell areas at each resolution level
- 31 precision levels (0-30) for multi-scale analysis
- Global coverage using pentagonal cells (no polar singularities)
- Palmer/a5-py compatible API implementation

The A5 grid is unique in M3S as the only pentagonal DGGS, offering different
spatial properties compared to hexagonal (H3) or square (Quadkey) grids.
"""

from shapely.geometry import Point

from m3s import GridBuilder

# Try to import optional dependencies
try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Create A5 grid with different precision levels
print("=== A5 Pentagonal Grid System Demo ===\n")

# Initialize cells at different precisions to show properties
print("A5 Grid Properties at Different Precisions:")
print("(Cell edge length ~ sqrt(area); Earth surface / (12 * 5^precision))")
for precision in [5, 8, 10, 12]:
    result = (
        GridBuilder.for_system("a5")
        .with_precision(precision)
        .at_point(40.7128, -74.0060)
        .execute()
    )
    cell = result.single
    edge_km = cell.area_km2**0.5
    print(
        f"Precision {precision:2d}: Avg area = {cell.area_km2:10.2f} km²  (edge ~{edge_km:6.2f} km)"
    )
print()

# Test locations around the world
test_locations = [
    ("New York", 40.7128, -74.0060),
    ("London", 51.5074, -0.1278),
    ("Tokyo", 35.6762, 139.6503),
    ("Sydney", -33.8688, 151.2093),
    ("São Paulo", -23.5558, -46.6396),
    ("Cairo", 30.0444, 31.2357),
]

print("=== Basic Cell Operations ===")

for name, lat, lon in test_locations[:3]:  # Show first 3 for brevity
    result = GridBuilder.for_system("a5").with_precision(6).at_point(lat, lon).execute()
    cell = result.single
    print(f"{name} ({lat}, {lon}):")
    print(f"  Cell ID: {cell.identifier}")
    print(f"  Area: {cell.area_km2:.6f} km²")
    print(f"  Precision: {cell.precision}")
    print()

print("=== Grid Conversion Examples ===")
from m3s import convert_cell

# Create cells in different grid systems using GridBuilder
geohash_result = (
    GridBuilder.for_system("geohash")
    .with_precision(5)
    .at_point(51.5074, -0.1278)
    .execute()
)
london_geohash = geohash_result.single

# Convert between grid systems using centroid method
london_a5 = convert_cell(london_geohash, "a5", method="centroid", target_precision=6)
london_h3 = convert_cell(london_a5, "h3", method="centroid", target_precision=7)

print("Grid system conversions for London:")
print(f"Geohash: {london_geohash.identifier} (area: {london_geohash.area_km2:.2f} km²)")
print(f"A5: {london_a5.identifier} (area: {london_a5.area_km2:.6f} km²)")
print(f"H3: {london_h3.identifier} (area: {london_h3.area_km2:.6f} km²)")
print()

print("=== Spatial Analysis ===")
# Get cells in a bounding box around Central Park, NYC
min_lat, min_lon = 40.764, -73.982
max_lat, max_lon = 40.800, -73.949

result = (
    GridBuilder.for_system("a5")
    .with_precision(6)
    .in_bbox(min_lat, min_lon, max_lat, max_lon)
    .execute()
)
bbox_cells = result.many

print(f"Found {len(bbox_cells)} A5 cells around Central Park")

# Calculate total area covered
total_area = sum(cell.area_km2 for cell in bbox_cells)
print(f"Total area covered: {total_area:.6f} km²")
print()

print("=== Pentagon Geometry Properties ===")
central_park_result = (
    GridBuilder.for_system("a5").with_precision(6).at_point(40.785, -73.968).execute()
)
central_park_cell = central_park_result.single

# Analyze the pentagon shape
exterior_coords = list(central_park_cell.polygon.exterior.coords)
print(f"Pentagon vertices: {len(exterior_coords) - 1}")  # -1 for closing point
print(f"Cell centroid: {central_park_cell.polygon.centroid}")
print(f"Cell bounds: {central_park_cell.polygon.bounds}")

# Calculate approximate edge lengths
edge_lengths = []
for i in range(len(exterior_coords) - 1):
    p1 = Point(exterior_coords[i])
    p2 = Point(
        exterior_coords[i + 1]
        if i + 1 < len(exterior_coords) - 1
        else exterior_coords[0]
    )
    # Approximate distance (not geodesic)
    edge_lengths.append(p1.distance(p2))

print(f"Approximate edge lengths (degrees): {[f'{e:.6f}' for e in edge_lengths]}")
print()

print("=== Resolution Level Analysis ===")
# Show how precision affects cell size for the same location
paris_lat, paris_lon = 48.8566, 2.3522

print("Paris cells at different A5 precision levels:")
for precision in range(3, 10, 2):
    paris_result = (
        GridBuilder.for_system("a5")
        .with_precision(precision)
        .at_point(paris_lat, paris_lon)
        .execute()
    )
    paris_cell = paris_result.single
    print(
        f"Precision {precision}: {paris_cell.area_km2:.8f} km² (ID: {paris_cell.identifier})"
    )

print()

print("=== Relationship Analysis ===")
from m3s import analyze_relationship

# Analyze relationships between A5 cells
rome_result = (
    GridBuilder.for_system("a5").with_precision(6).at_point(41.9028, 12.4964).execute()
)
rome_cell = rome_result.single

milan_result = (
    GridBuilder.for_system("a5").with_precision(6).at_point(45.4642, 9.1900).execute()
)
milan_cell = milan_result.single

relationship = analyze_relationship(rome_cell, milan_cell)
print(f"Relationship between Rome and Milan A5 cells: {relationship}")
print()

print("=== Multi-Resolution Grid ===")
# Create A5 grids at different resolutions for Berlin
berlin_lat, berlin_lon = 52.5200, 13.4050

print("Hierarchical A5 cells for Berlin:")
for level in [3, 5, 7]:
    berlin_result = (
        GridBuilder.for_system("a5")
        .with_precision(level)
        .at_point(berlin_lat, berlin_lon)
        .execute()
    )
    berlin_cell = berlin_result.single
    print(
        f"  Level {level}: {berlin_cell.identifier} (area: {berlin_cell.area_km2:.8f} km²)"
    )

print()

print("=== Comparison with H3 Hexagons ===")
# Compare A5 pentagonal cells with H3 hexagonal cells at same location
nyc_lat, nyc_lon = 40.7128, -74.0060

a5_result = (
    GridBuilder.for_system("a5").with_precision(7).at_point(nyc_lat, nyc_lon).execute()
)
h3_result = (
    GridBuilder.for_system("h3").with_precision(7).at_point(nyc_lat, nyc_lon).execute()
)

a5_cell = a5_result.single
h3_cell = h3_result.single

print("Same location in NYC:")
print(f"  A5 (pentagon): {a5_cell.identifier} - Area: {a5_cell.area_km2:.6f} km²")
print(f"  H3 (hexagon):  {h3_cell.identifier} - Area: {h3_cell.area_km2:.6f} km²")
print(
    f"  Geometry: A5 has {len(list(a5_cell.polygon.exterior.coords)) - 1} vertices (pentagon)"
)
print(
    f"            H3 has {len(list(h3_cell.polygon.exterior.coords)) - 1} vertices (hexagon)"
)
print()

# Visualization example using Matplotlib
print("=== Map Visualization with Matplotlib ===")
print(
    "\nNOTE: For proper visualization, choose precision where cell edge is 2-5x smaller than bbox"
)
print("Example: 0.1° bbox (~11km) → use precision 9-10 (edge ~2-5km)")
if HAS_MATPLOTLIB:
    try:
        import matplotlib.patches as patches

        # Create figure and axis
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))

        # Get A5 cells around London
        # Precision 9: ~4.7km edge length (optimal for 11km x 18km bbox)
        london_result = (
            GridBuilder.for_system("a5")
            .with_precision(9)
            .in_bbox(51.45, -0.25, 51.55, -0.05)
            .limit(30)  # Limit to 30 cells for clarity
            .execute()
        )
        london_bbox_cells = london_result.many

        print(f"Plotting {len(london_bbox_cells)} A5 pentagonal cells around London...")

        # Plot each A5 cell as a polygon
        for i, cell in enumerate(london_bbox_cells):
            # Extract coordinates from the polygon
            coords = list(cell.polygon.exterior.coords)

            # Create matplotlib polygon patch
            polygon = patches.Polygon(
                coords,
                closed=True,
                fill=True,
                facecolor="lightblue",
                edgecolor="red",
                alpha=0.6,
                linewidth=1.5,
            )

            ax.add_patch(polygon)

            # Add cell ID as text at centroid
            centroid = cell.polygon.centroid
            ax.text(
                centroid.x,
                centroid.y,
                f"#{i+1}",
                fontsize=8,
                ha="center",
                va="center",
                weight="bold",
                color="darkblue",
            )

        # Set axis properties
        ax.set_xlim(-0.25, -0.05)
        ax.set_ylim(51.45, 51.55)
        ax.set_xlabel("Longitude (degrees)", fontsize=12)
        ax.set_ylabel("Latitude (degrees)", fontsize=12)
        ax.set_title("A5 Pentagonal Grid Cells over London", fontsize=14, weight="bold")
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")

        # Add legend
        legend_patch = patches.Patch(
            color="lightblue", alpha=0.6, label="A5 Pentagon Cells"
        )
        ax.legend(handles=[legend_patch], loc="upper right")

        # Save the plot
        plt.tight_layout()

        # Show additional cell information
        print("\nCell Details (first 5 cells):")
        for i, cell in enumerate(london_bbox_cells[:5]):
            print(f"  Cell {i+1}: {cell.identifier}")
            print(f"    Area: {cell.area_km2:.6f} km²")
            print(f"    Bounds: {[f'{x:.4f}' for x in cell.polygon.bounds]}")

        plt.show()

        # Create a second plot showing different precision levels
        print("\nCreating multi-precision comparison plot...")
        fig2, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig2.suptitle(
            "A5 Grid System - Different Precision Levels", fontsize=16, weight="bold"
        )

        # Test location: Central London
        center_lat, center_lon = 51.5074, -0.1278
        bbox_size = 0.03  # ~3.3km area for precision comparison

        # Use appropriate precisions: edges from ~10km down to ~0.4km
        # P8: 108 km² (edge ~10km), P10: 4.35 km² (edge ~2km)
        # P11: 0.87 km² (edge ~0.9km), P12: 0.17 km² (edge ~0.4km)
        precisions = [8, 10, 11, 12]
        colors = ["lightcoral", "lightgreen", "lightblue", "lightyellow"]

        for idx, (precision, color) in enumerate(zip(precisions, colors)):
            row = idx // 2
            col = idx % 2
            ax = axes[row, col]

            # Get cells around central London
            cells_result = (
                GridBuilder.for_system("a5")
                .with_precision(precision)
                .in_bbox(
                    center_lat - bbox_size,
                    center_lon - bbox_size,
                    center_lat + bbox_size,
                    center_lon + bbox_size,
                )
                .limit(20)  # Limit for clarity
                .execute()
            )
            cells = cells_result.many

            # Plot cells
            for cell in cells:
                coords = list(cell.polygon.exterior.coords)
                polygon = patches.Polygon(
                    coords,
                    closed=True,
                    fill=True,
                    facecolor=color,
                    edgecolor="black",
                    alpha=0.7,
                    linewidth=0.8,
                )
                ax.add_patch(polygon)

            # Mark center point
            ax.plot(center_lon, center_lat, "ro", markersize=8, label="Center Point")

            # Set axis properties
            ax.set_xlim(center_lon - bbox_size, center_lon + bbox_size)
            ax.set_ylim(center_lat - bbox_size, center_lat + bbox_size)
            ax.set_xlabel("Longitude", fontsize=10)
            ax.set_ylabel("Latitude", fontsize=10)

            # Get average area for this precision
            avg_area = cells[0].area_km2 if cells else 0
            ax.set_title(
                f"Precision {precision} ({len(cells)} cells)\nAvg Area: {avg_area:.6f} km²",
                fontsize=12,
                weight="bold",
            )
            ax.grid(True, alpha=0.3)
            ax.set_aspect("equal")
            ax.legend(fontsize=8)

        plt.tight_layout()
        print("Showing precision comparison plot...")
        plt.show()

    except Exception as e:
        print(f"Error creating matplotlib visualization: {e}")
        print("Install matplotlib with 'pip install matplotlib' to enable plotting")

else:
    print("Matplotlib not available - skipping map visualization")
    print("Install matplotlib with 'pip install matplotlib' to enable plotting")

print()
print("=== A5 Grid System Summary ===")
print("* A5 provides pentagonal cells with minimal distortion")
print("* Based on dodecahedral projection for global coverage")
print("* 31 precision levels (0-30) for multi-scale analysis")
print("* Compatible with M3S conversion and analysis tools")
print(
    "* Unique pentagonal geometry offers different spatial properties than square/hex grids"
)
print("* Palmer/a5-py compatible API for existing workflows")
print()
print("The A5 grid system is particularly useful for:")
print("- Global spatial analysis requiring uniform cell areas")
print("- Applications needing minimal geometric distortion")
print("- Research comparing different grid topologies (pentagonal vs hexagonal/square)")
print("- High-precision geospatial indexing and analysis")
print("- Climate modeling and earth system science (no polar singularities)")
print()
print("Modern API Benefits:")
print("✓ GridBuilder provides consistent interface with all M3S grids")
print("✓ Unified precision parameter (0-30) across the system")
print("✓ Fluent interface with method chaining for readable code")
print("✓ Easy conversion between A5 and other grid systems (Geohash, H3, etc.)")
